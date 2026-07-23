"""The Entity base class and the ``.meta`` metadata accessor.

Every generated ontology class subclasses :class:`Entity`. Instances are plain
Python objects; the RDF view (IRIs, triples) exists only in metadata and in
the model's serializer. User code should never need an import from ``rdflib``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Iterator, Self, overload

from . import containment as _containment
from .errors import ModelingError, RangeError
from .meta import ClassInfo, OntologyInfo, PropertySpec, Registry
from .relations import (
    EnumOne,
    EnumSet,
    Lit,
    Rel,
    RelOne,
    RelSet,
    TermOne,
    ValueOne,
)

if TYPE_CHECKING:
    from .enums import EnumValue
    from .model import Model


class ClassMetaView:
    """Read-only view of a generated class's ontology provenance.

    Accessed as ``AHU.meta``. Everything here comes from the ontology at
    generation time; the generated docstrings render the same data.
    """

    __slots__ = ("_cls",)

    def __init__(self, cls: type[Entity]) -> None:
        self._cls = cls

    @property
    def iri(self) -> str:
        """IRI of the ontology class."""
        return self._cls._classinfo.iri

    @property
    def label(self) -> str | None:
        """``rdfs:label`` of the class."""
        return self._cls._classinfo.label

    @property
    def definition(self) -> str | None:
        """``skos:definition`` / ``rdfs:comment`` text."""
        return self._cls._classinfo.definition

    @property
    def ontology(self) -> OntologyInfo:
        """The ontology this class was generated from."""
        return self._cls._classinfo.ontology

    @property
    def registry(self) -> Registry:
        """The generated package's class registry."""
        return self._cls._classinfo.registry

    @property
    def parents(self) -> tuple[type[Entity], ...]:
        """Direct ontology superclasses (as Python classes)."""
        return tuple(
            base
            for base in self._cls.__bases__
            if issubclass(base, Entity) and "_classinfo" in base.__dict__
        )

    @property
    def properties(self) -> tuple[PropertySpec, ...]:
        """Effective property specs: inherited plus own, own winning."""
        return tuple(self._cls._effective_specs().values())

    @property
    def abstract(self) -> bool:
        """True for organizational classes not meant to be instantiated."""
        return self._cls._classinfo.abstract

    def __repr__(self) -> str:
        return f"<meta of {self._cls.__name__}: {self.iri}>"


class InstanceMetaView(ClassMetaView):
    """Per-instance metadata: everything on the class view, plus identity."""

    __slots__ = ("_obj",)

    def __init__(self, obj: Entity) -> None:
        super().__init__(type(obj))
        self._obj = obj

    @property
    def cls(self) -> type[Entity]:
        """The generated class of this instance."""
        return self._cls

    @property
    def instance_iri(self) -> str:
        """The IRI minted for this instance by its model."""
        return self._obj._iri

    @property
    def model(self) -> Model:
        """The model this instance belongs to."""
        return self._obj._model

    def __repr__(self) -> str:
        return f"<meta of {self._obj!r}: {self.instance_iri}>"


class _MetaDescriptor:
    """Serves ``.meta`` on both classes and instances."""

    @overload
    def __get__(self, obj: None, owner: type[Entity]) -> ClassMetaView: ...
    @overload
    def __get__(self, obj: Entity, owner: type[Entity]) -> InstanceMetaView: ...

    def __get__(
        self, obj: Entity | None, owner: type[Entity]
    ) -> ClassMetaView | InstanceMetaView:
        if obj is None:
            return ClassMetaView(owner)
        return InstanceMetaView(obj)


class Entity:
    """Base class for all generated ontology classes.

    Construction requires an active :class:`~objectrdf.core.model.Model`
    (either ambient, via ``with Model(...)``, or passed as ``model=``).
    The first argument is the entity's local name; the model's namespace
    turns it into an IRI at serialization time. When omitted, a name is
    auto-generated per model as ``<class>_<n>`` (``vav_1``, ``vav_2``, ...).

    Reserved attribute names (``name``, ``label``, ``comment``, ``meta``,
    ``model``): ontology properties that would collide with these are renamed
    by the generator's collision policy.
    """

    #: Ontology provenance; set in the class body by generated code.
    _classinfo: ClassVar[ClassInfo]

    #: Property name that ``>>`` sugar maps to (e.g. Brick sets "feeds" on
    #: Equipment); None disables the operator for the class.
    _RSHIFT: ClassVar[str | None] = None

    #: Connection negotiator hook (e.g. 223 sets one on Connectable). When
    #: set, ``>>`` delegates to ``_CONNECTOR.connect(a, b)`` instead of the
    #: simple ``_RSHIFT`` property. See objectrdf.connect223.
    _CONNECTOR: ClassVar[Any | None] = None

    meta = _MetaDescriptor()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        info = cls.__dict__.get("_classinfo")
        if info is not None:
            info.registry.register(cls)

    def __init__(
        self,
        name: str | None = None,
        *,
        label: str | None = None,
        comment: str | None = None,
        model: Model | None = None,
        **props: Any,
    ) -> None:
        if "_classinfo" not in _mro_dicts(type(self)):
            raise TypeError("Entity cannot be instantiated directly")
        if self._classinfo_effective().abstract:
            raise ModelingError(
                f"{type(self).__name__} is an organizational class and "
                f"cannot be instantiated; pick a concrete subclass"
            )
        from .model import current_model

        m = model if model is not None else current_model()
        if m is None:
            raise ModelingError(
                f"no active Model: create entities inside `with Model(...):` "
                f"or pass model= to {type(self).__name__}(...)"
            )
        if name is None:
            name = m._auto_name(type(self))
        self._name = name
        self._label = label if label is not None else name
        self._comment = comment
        self._data: dict[str, Any] = {}
        self._rels: dict[str, RelSet[Any]] = {}
        self._iri: str = ""  # minted by Model._bind below
        self._model: Model = m
        m._bind(self)

        # From here on the entity is registered in the model, so any failure
        # must unbind it — otherwise a raised constructor leaves a ghost
        # entity occupying the name.
        try:
            for key, value in props.items():
                descriptor = getattr(type(self), key, None)
                if not isinstance(
                    descriptor,
                    (Rel, RelOne, TermOne, ValueOne, Lit, EnumOne, EnumSet),
                ):
                    raise ModelingError(
                        f"{type(self).__name__} has no property {key!r}"
                    )
                if value is None:
                    continue
                setattr(self, key, value)

            self._check_required()
            if not m._resolving:
                _containment.attach(self)
            if self._CONNECTOR is not None and not m._resolving:
                # e.g. 223: materialize connection points the class's shapes
                # require, so a fresh Fan already has its air inlet/outlet.
                self._CONNECTOR.on_create(self)
        except BaseException:
            m._unbind(self)
            raise

    # -- identity ---------------------------------------------------------

    @property
    def name(self) -> str:
        """Local name; combined with the model namespace to mint the IRI."""
        return self._name

    @property
    def label(self) -> str:
        """Human-readable label (``rdfs:label``); defaults to the name."""
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._model._assert_mutable()
        self._label = value
        self._model._touch(self)

    @property
    def comment(self) -> str | None:
        """Free-text note serialized as ``rdfs:comment``."""
        return self._comment

    @comment.setter
    def comment(self, value: str | None) -> None:
        self._model._assert_mutable()
        self._comment = value
        self._model._touch(self)

    # -- containment ------------------------------------------------------

    def contains(self, *children: Entity, via: str | None = None) -> Self:
        """Declare that this entity contains the given entities.

        The predicate is negotiated per (container, child) class pair from
        the package's containment table; pass ``via='<property>'`` to pick
        one explicitly. Returns ``self`` for chaining.
        """
        table = self.meta.registry.containment
        for child in children:
            table.apply(self, child, via=via)
        return self

    def port(
        self,
        name: str,
        *,
        direction: str,
        medium: EnumValue | None = None,
    ):
        """Declare a named deferred connection point for solver negotiation."""
        return self._model._defer_port(
            self, name, direction, medium=medium
        )

    def __enter__(self) -> Self:
        """Open a containment scope: entities created inside attach here."""
        _containment.push(self)
        return self

    def __exit__(self, *exc_info: object) -> None:
        _containment.pop(self)

    # -- operator sugar ---------------------------------------------------

    def __rshift__(self, other: Entity) -> Entity:
        """``a >> b``: the package-defined flow connection.

        Brick adds to the ``_RSHIFT`` property (``feeds``). S223/WaTr records
        a deferred intention for Z3 resolution. Returns ``b`` so chains read
        along the flow: ``a >> b >> c``. Use ``connect(a, b)`` when a stable
        handle is needed for a later medium hint.
        """
        if self._CONNECTOR is not None:
            self._CONNECTOR.connect(self, other)
            return other
        prop = self._RSHIFT
        if prop is None:
            raise TypeError(
                f"{type(self).__name__} does not participate in >> connections"
            )
        getattr(self, prop).add(other)
        return other

    def __lshift__(self, other: Entity) -> Entity:
        """``a << b``: mirror of ``>>`` (``b`` flows into ``a``).

        Also returns ``b``, so ``a << b << c`` reads against the flow.
        """
        if other._CONNECTOR is not None:
            other._CONNECTOR.connect(other, self)
            return other
        prop = other._RSHIFT
        if prop is None:
            raise TypeError(
                f"{type(other).__name__} does not participate in << connections"
            )
        getattr(other, prop).add(self)
        return other

    # -- internals --------------------------------------------------------

    @classmethod
    def _classinfo_effective(cls) -> ClassInfo:
        """The nearest ``_classinfo`` up the MRO (always exists for
        generated classes; Entity itself has none)."""
        for klass in cls.__mro__:
            info = klass.__dict__.get("_classinfo")
            if info is not None:
                return info
        raise TypeError(f"{cls.__name__} has no _classinfo")  # pragma: no cover

    @classmethod
    def _effective_specs(cls) -> dict[str, PropertySpec]:
        """name -> spec across the MRO; subclasses shadow parents by name.

        Cached per class (the spec set is fixed at generation time).
        """
        cached = cls.__dict__.get("_specs_cache")
        if cached is not None:
            return cached
        specs: dict[str, PropertySpec] = {}
        for klass in reversed(cls.__mro__):
            info = klass.__dict__.get("_classinfo")
            if info is not None:
                for spec in info.properties:
                    specs[spec.name] = spec
        cls._specs_cache = specs  # type: ignore[attr-defined]
        return specs

    def _store_for(self, spec: PropertySpec) -> RelSet[Any]:
        """The (lazily created) RelSet backing a multi-valued property."""
        store = self._rels.get(spec.name)
        if store is None:
            store = RelSet(self, spec)
            self._rels[spec.name] = store
        return store

    def _check_range(self, spec: PropertySpec, value: object) -> None:
        """Runtime mirror of the static range annotation."""
        from .terms import TermValue

        # External vocabulary classes are intentionally not always generated
        # as local Entity classes. A compiled named individual is then the
        # correct RDF object, rather than a newly minted local entity.
        registry = self.meta.registry
        allowed = tuple(registry.resolve(rng) for rng in spec.ranges)
        allowed_iris = {cls.meta.iri for cls in allowed}
        if isinstance(value, TermValue):
            if not spec.ranges or allowed_iris.intersection(value.types):
                return
            names = " | ".join(rng for rng in spec.ranges)
            raise RangeError(
                f"{type(self).__name__}.{spec.name} expects {names}, got "
                f"compiled term {value!r}"
            )
        if not isinstance(value, Entity):
            raise RangeError(
                f"{type(self).__name__}.{spec.name} links entities, got "
                f"{type(value).__name__} ({value!r})"
            )
        if not spec.ranges:
            return
        if not isinstance(value, allowed) and value.meta.iri not in allowed_iris:
            names = " | ".join(rng for rng in spec.ranges)
            raise RangeError(
                f"{type(self).__name__}.{spec.name} expects {names}, got "
                f"{type(value).__name__} ({value.name!r})"
            )

    def _check_required(self) -> None:
        """Raise if any SHACL-required property is still empty."""
        missing: list[str] = []
        for spec in self._effective_specs().values():
            if not spec.required:
                continue
            if spec.kind == "object" and spec.max_count != 1:
                if len(self._store_for(spec)) == 0:
                    missing.append(spec.name)
            elif not self._data.get(spec.name):
                missing.append(spec.name)
        if missing:
            raise ModelingError(
                f"{type(self).__name__}({self.name!r}) is missing required "
                f"propert{'ies' if len(missing) > 1 else 'y'}: "
                f"{', '.join(missing)}"
            )

    def _property_values(self) -> Iterator[tuple[PropertySpec, Any]]:
        """Yield (spec, value) pairs for serialization: entities for object
        properties, EnumValues for enum properties, literals otherwise."""
        for spec in self._effective_specs().values():
            if spec.kind == "object" and spec.max_count != 1:
                for target in self._store_for(spec):
                    yield spec, target
            elif spec.kind == "enum" and spec.max_count != 1:
                for value in self._data.get(spec.name) or ():
                    yield spec, value
            else:
                value = self._data.get(spec.name)
                if value is not None:
                    yield spec, value

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._name!r}>"


def provided(**kwargs: Any) -> dict[str, Any]:
    """Filter constructor kwargs down to the ones the caller actually set.

    Generated ``__init__`` methods pass every parameter through this so that
    defaults (``None`` / ``()``) don't count as explicit assignments.
    """
    return {
        key: value for key, value in kwargs.items() if value is not None and value != ()
    }


def _mro_dicts(cls: type) -> dict[str, Any]:
    """Union of class __dict__s along the MRO (nearest wins)."""
    merged: dict[str, Any] = {}
    for klass in reversed(cls.__mro__):
        merged.update(klass.__dict__)
    return merged
