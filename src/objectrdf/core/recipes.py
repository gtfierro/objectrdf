"""Typed, portable authoring declarations for reusable equipment classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, cast, overload

if TYPE_CHECKING:
    from .entity import Entity
    from .property_schema import PropertySchema, PropertySet, QuantityAmount
    from .terms import TermValue

T = TypeVar("T")
P = TypeVar("P")


@dataclass(frozen=True)
class Policy(Generic[T]):
    """A value policy: immutable fact, replaceable default, or finite choice."""

    kind: str
    values: tuple[T, ...]

    @property
    def value(self) -> T:
        return self.values[0]


def fixed(value: T) -> Policy[T]:
    """Declare an exact value that assignments and validation must preserve."""
    return Policy("fixed", (value,))


def default(value: T) -> Policy[T]:
    """Initialize new instances with a replaceable value."""
    return Policy("default", (value,))


def choose(*values: T) -> Policy[T]:
    """Restrict a value to choices that a later author or solver resolves."""
    if not values:
        raise ValueError("choose() needs at least one allowed value")
    return Policy("choose", tuple(values))


@dataclass(frozen=True)
class PointDeclaration(Generic[P]):
    """Class-level declaration of one or more deferred connection points."""

    count: int = 1
    medium: Policy[Any] | Any | None = None
    direction: Policy[str] | str = "choose"
    label: Policy[str] | str | None = None
    _name: str = field(default="", init=False, compare=False)

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "_name", name)

    @overload
    def __get__(self, obj: None, owner: type | None = None) -> PointDeclaration[P]: ...

    @overload
    def __get__(self, obj: object, owner: type | None = None) -> P: ...

    def __get__(self, obj: Any, owner: type | None = None) -> PointDeclaration[P] | P:
        return self if obj is None else cast(P, obj._recipe_points[self._name])

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("a connection point declaration needs count >= 1")


class PointRef:
    """Stable reference to one declared point on one equipment instance."""

    __slots__ = ("owner", "name", "_port")

    def __init__(self, owner: Any, name: str, port: Any) -> None:
        self.owner = owner
        self.name = name
        self._port = port

    @property
    def medium(self) -> Any:
        """Current medium hint for the referenced connection point."""
        return self._port.medium

    @medium.setter
    def medium(self, value: Any) -> None:
        self._port.medium = value

    def __repr__(self) -> str:
        return f"<PointRef {self.owner.name}.{self.name}>"

    def apply_properties(
        self, schema: PropertySchema, *, prefix: str | None = None
    ) -> PropertySet:
        """Attach values to this exact authored or hydrated point."""
        from .property_schema import apply_properties

        return apply_properties(self, schema, prefix=prefix)

    def quantity(
        self, name: str, value: float | QuantityAmount, *,
        kind: TermValue, unit: TermValue | None = None,
        capability: Literal["static", "observable", "actuatable"] = "static",
        mode: Literal["nominal", "observable", "actuatable"] | None = None,
        label: str | None = None, **properties: Any,
    ) -> Entity:
        """Create a scalar property on this exact authored or hydrated point."""
        from objectrdf.qudt import _attached_quantity

        return _attached_quantity(
            self._port, name, value, unit=unit, kind=kind,
            capability=capability, mode=mode, label=label, **properties,
        )


class PointGroupRef:
    """Stable reference to a declared interchangeable point group."""

    __slots__ = ("owner", "name", "points")

    def __init__(self, owner: Any, name: str, points: tuple[PointRef, ...]) -> None:
        self.owner = owner
        self.name = name
        self.points = points

    def __iter__(self):
        return iter(self.points)

    def __len__(self) -> int:
        return len(self.points)

    def __repr__(self) -> str:
        return f"<PointGroupRef {self.owner.name}.{self.name} x{len(self.points)}>"


class PointDescriptor:
    """Descriptor that returns class declaration metadata or instance refs."""

    def __init__(self, declaration: PointDeclaration) -> None:
        self.declaration = declaration
        self.name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, owner: type | None = None) -> Any:
        if obj is None:
            return self.declaration
        try:
            return obj._recipe_points[self.name]
        except KeyError:
            raise AttributeError(self.name) from None


class RecipeConnectionPoint:
    """Typed ``declare`` constructor mixed into generated S223 points."""

    @staticmethod
    @overload
    def declare(
        *, count: Literal[1] = 1,
        medium: Policy[Any] | Any | None = None,
        direction: Policy[str] | str = "choose",
        label: Policy[str] | str | None = None,
    ) -> PointDeclaration[PointRef]: ...

    @staticmethod
    @overload
    def declare(
        *, count: int,
        medium: Policy[Any] | Any | None = None,
        direction: Policy[str] | str = "choose",
        label: Policy[str] | str | None = None,
    ) -> PointDeclaration[PointGroupRef]: ...

    @staticmethod
    def declare(
        *,
        count: int = 1,
        medium: Policy[Any] | Any | None = None,
        direction: Policy[str] | str = "choose",
        label: Policy[str] | str | None = None,
    ) -> PointDeclaration[Any]:
        return PointDeclaration(
            count=count, medium=medium, direction=direction, label=label
        )


def _resolve_policy(value: Any) -> Policy[Any] | None:
    return value if isinstance(value, Policy) else None


def copy_default(value: Any) -> Any:
    """Copy collection containers without copying RDF/enum member identities."""
    if isinstance(value, list):
        return [copy_default(item) for item in value]
    if isinstance(value, tuple):
        return tuple(copy_default(item) for item in value)
    if isinstance(value, dict):
        return {
            copy_default(key): copy_default(item) for key, item in value.items()
        }
    if isinstance(value, set):
        return {copy_default(item) for item in value}  # type: ignore[return-value]
    return value


def register_recipe_class(cls: type) -> type:
    """Register a recipe subclass described by class-level metadata."""
    metadata = cls.__dict__
    class_iri = metadata.get("class_iri")
    ontology_iri = metadata.get("ontology_iri")
    if not isinstance(class_iri, str) or not isinstance(ontology_iri, str):
        raise TypeError(
            f"{cls.__name__} must define class_iri and ontology_iri together"
        )
    label = metadata.get("class_label")
    if label is not None and not isinstance(label, str):
        raise TypeError(f"{cls.__name__}.class_label must be a string")
    return _configure_recipe_class(
        cls, iri=class_iri, ontology_iri=ontology_iri, label=label
    )


def _configure_recipe_class(
    cls: type, *, iri: str, ontology_iri: str, label: str | None = None
) -> type:
    """Attach runtime metadata and compile schema for a recipe subclass."""
    from .entity import Entity
    from .errors import ModelingError
    from .meta import ClassInfo, OntologyInfo

    if not issubclass(cls, Entity):
        raise TypeError("recipe metadata is valid only on Entity subclasses")
    parent_info = cls._classinfo_effective()
    registry = parent_info.registry
    if iri in registry.by_iri:
        raise ModelingError(f"class IRI {iri!r} is already registered")
    if cls.__name__ in registry.by_name:
        raise ModelingError(f"class name {cls.__name__!r} is already registered")
    ontology = OntologyInfo(cls.__name__, ontology_iri)
    info = ClassInfo(iri, ontology, registry, label=label)
    info.cls = cls
    cls._classinfo = info
    declarations: dict[str, PointDeclaration] = {
        name: declaration
        for base in reversed(cls.__mro__[1:])
        for name, declaration in base.__dict__.get("_point_declarations", {}).items()
    }
    for name, value in cls.__dict__.items():
        if isinstance(value, PointDeclaration):
            descriptor = PointDescriptor(value)
            setattr(cls, name, descriptor)
            descriptor.__set_name__(cls, name)
            declarations[name] = value
    cls._point_declarations = declarations
    cls._property_policies = _merge_policies(cls)
    effective_names = {spec.name for spec in cls._effective_specs().values()}
    invalid_policies = set(cls._property_policies) - effective_names - {"label", "comment"}
    if invalid_policies:
        raise TypeError(
            f"{cls.__name__} declares policies for unknown properties: "
            f"{', '.join(sorted(invalid_policies))}"
        )
    reserved_point_names = effective_names | {
        "name", "type", "label", "comment", "meta", "model", "contains"
    }
    collisions = set(declarations) & reserved_point_names
    if collisions:
        raise TypeError(
            f"{cls.__name__} point declarations collide with properties: "
            f"{', '.join(sorted(collisions))}"
        )
    registry.register(cls)
    import rdflib
    from rdflib import OWL, RDF, RDFS, URIRef
    from rdflib.namespace import SH

    schema = registry.schema_graph
    if schema is None:
        schema = rdflib.Graph()
        registry.schema_graph = schema
    class_ref = URIRef(iri)
    ontology_ref = URIRef(ontology_iri)
    schema.add((ontology_ref, RDF.type, OWL.Ontology))
    schema.add((class_ref, RDF.type, OWL.Class))
    schema.add((class_ref, RDFS.subClassOf, URIRef(parent_info.iri)))
    if parent_info.ontology.iri:
        schema.add(
            (ontology_ref, OWL.imports, URIRef(parent_info.ontology.iri))
        )
    if label:
        schema.add((class_ref, RDFS.label, rdflib.Literal(label)))
    shape = URIRef(f"{iri}Shape")
    schema.add((shape, RDF.type, SH.NodeShape))
    schema.add((shape, SH.targetClass, class_ref))
    has_point = URIRef("http://data.ashrae.org/standard223#hasConnectionPoint")
    has_medium = URIRef("http://data.ashrae.org/standard223#hasMedium")
    direction_class = {
        "in": URIRef("http://data.ashrae.org/standard223#InletConnectionPoint"),
        "out": URIRef("http://data.ashrae.org/standard223#OutletConnectionPoint"),
        "bi": URIRef("http://data.ashrae.org/standard223#BidirectionalConnectionPoint"),
    }
    for name, declaration in declarations.items():
        point_shape = URIRef(f"{iri}Shape/{name}")
        value_shape = URIRef(f"{iri}Shape/{name}/value")
        schema.add((shape, SH.property, point_shape))
        schema.add((point_shape, SH.path, has_point))
        schema.add((point_shape, SH.qualifiedMinCount, rdflib.Literal(declaration.count)))
        schema.add((point_shape, SH.qualifiedMaxCount, rdflib.Literal(declaration.count)))
        schema.add((point_shape, SH.qualifiedValueShape, value_shape))
        direction = declaration.direction
        if isinstance(direction, Policy) and direction.kind == "fixed":
            direction = direction.value
        direction_values = (
            direction.values
            if isinstance(direction, Policy)
            else (direction,) if isinstance(direction, str) else ()
        )
        if (
            len(direction_values) == 1
            and isinstance(direction_values[0], str)
            and direction_values[0] in direction_class
        ):
            schema.add((value_shape, SH["class"], direction_class[direction_values[0]]))
        elif len(direction_values) > 1:
            alternatives = []
            for index, value in enumerate(direction_values):
                if not isinstance(value, str) or value not in direction_class:
                    continue
                alternative = URIRef(f"{iri}Shape/{name}/direction/{index}")
                schema.add((alternative, SH["class"], direction_class[value]))
                alternatives.append(alternative)
            if alternatives:
                schema.add(
                    (value_shape, SH["or"], URIRef(f"{iri}Shape/{name}/directions/0"))
                )
                _add_stable_list(schema, iri, f"{name}/directions", alternatives)
        medium = declaration.medium
        if isinstance(medium, Policy) and medium.kind == "fixed":
            medium = medium.value
        if isinstance(medium, Policy) and medium.kind == "choose":
            medium_shape = URIRef(f"{iri}Shape/{name}/medium")
            schema.add((value_shape, SH.property, medium_shape))
            schema.add((medium_shape, SH.path, has_medium))
            medium_values = [URIRef(str(value.iri)) for value in medium.values]
            list_head = URIRef(f"{iri}Shape/{name}/mediums/0")
            schema.add((medium_shape, SH["in"], list_head))
            _add_stable_list(schema, iri, f"{name}/mediums", medium_values)
        elif hasattr(medium, "iri"):
            medium_shape = URIRef(f"{iri}Shape/{name}/medium")
            schema.add((value_shape, SH.property, medium_shape))
            schema.add((medium_shape, SH.path, has_medium))
            schema.add((medium_shape, SH.hasValue, URIRef(str(medium.iri))))
        point_label = declaration.label
        if isinstance(point_label, Policy) and point_label.kind != "default":
            label_shape = URIRef(f"{iri}Shape/{name}/label")
            schema.add((value_shape, SH.property, label_shape))
            schema.add((label_shape, SH.path, RDFS.label))
            label_values = [
                rdflib.Literal(value) for value in point_label.values
            ]
            if point_label.kind == "fixed":
                schema.add((label_shape, SH.hasValue, label_values[0]))
            else:
                list_head = URIRef(f"{iri}Shape/{name}/labels/0")
                schema.add((label_shape, SH["in"], list_head))
                _add_stable_list(schema, iri, f"{name}/labels", label_values)
    specs = {spec.name: spec for spec in cls._effective_specs().values()}
    for name, policy in cls._property_policies.items():
        if policy.kind == "default":
            continue
        spec = specs.get(name)
        predicate = (
            URIRef(spec.predicate)
            if spec is not None
            else RDFS.label if name == "label"
            else RDFS.comment if name == "comment"
            else None
        )
        if predicate is None:
            continue
        property_shape = URIRef(f"{iri}Shape/property/{name}")
        schema.add((shape, SH.property, property_shape))
        schema.add((property_shape, SH.path, predicate))
        rdf_values = [
            URIRef(value.iri)
            if hasattr(value, "iri")
            else rdflib.Literal(value)
            for value in policy.values
        ]
        if policy.kind == "fixed":
            schema.add((property_shape, SH.hasValue, rdf_values[0]))
        else:
            list_head = URIRef(f"{iri}Shape/property/{name}/list/0")
            schema.add((property_shape, SH["in"], list_head))
            _add_stable_list(schema, iri, f"property/{name}/list", rdf_values)
    return cls


def _merge_policies(cls: type) -> dict[str, Policy[Any]]:
    policies: dict[str, Policy[Any]] = {}
    for base in reversed(cls.__mro__):
        policies.update(base.__dict__.get("property_policies", {}))
    for name, policy in policies.items():
        if not isinstance(policy, Policy):
            raise TypeError(f"property_policies[{name!r}] must be fixed/default/choose")
        inherited = next(
            (base.__dict__.get("_property_policies", {}).get(name)
             for base in cls.__mro__[1:]
             if name in base.__dict__.get("_property_policies", {})),
            None,
        )
        if inherited and inherited.kind == "fixed" and policy != inherited:
            raise TypeError(f"{cls.__name__}.{name} conflicts with inherited fixed value")
        if inherited and inherited.kind == "choose" and policy.kind == "choose":
            if not set(policy.values).issubset(inherited.values):
                raise TypeError(f"{cls.__name__}.{name} widens inherited choices")
        if inherited and inherited.kind == "choose" and policy.kind == "fixed":
            if policy.value not in inherited.values:
                raise TypeError(f"{cls.__name__}.{name} fixes a value outside inherited choices")
        if inherited and inherited.kind == "fixed" and policy.kind != "fixed":
            raise TypeError(f"{cls.__name__}.{name} weakens an inherited fixed value")
    return policies


def _add_stable_list(graph: Any, base_iri: str, key: str, values: list[Any]) -> None:
    """Add an RDF collection using stable IRIs instead of random blank nodes."""
    from rdflib import RDF, URIRef

    for index, value in enumerate(values):
        cell = URIRef(f"{base_iri}Shape/{key}/{index}")
        following = (
            URIRef(f"{base_iri}Shape/{key}/{index + 1}")
            if index + 1 < len(values)
            else RDF.nil
        )
        graph.add((cell, RDF.first, value))
        graph.add((cell, RDF.rest, following))
