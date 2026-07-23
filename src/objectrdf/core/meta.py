"""Ontology metadata carried by generated classes.

Every class the compiler emits carries a :class:`ClassInfo` (as the
``_classinfo`` class attribute) describing where it came from: its IRI, label,
definition, defining ontology, and the SHACL-derived property specs it
declares. The ``.meta`` accessor on entities (see ``entity.py``) presents this
information read-only; the docstring generator in ``objectrdf.gen`` renders
the same data, so hover-docs and runtime introspection can never disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .containment import ContainmentTable
    from .entity import Entity
    from .enums import EnumValue


@dataclass(frozen=True)
class OntologyInfo:
    """Identity of the ontology a class or property was generated from."""

    name: str
    """Short human name, e.g. ``"Brick"``."""

    iri: str
    """The ontology's IRI (the ``owl:Ontology`` subject)."""

    version: str | None = None
    """``owl:versionInfo`` at generation time, if declared."""

    source: str | None = None
    """Where the ontology was loaded from (URL or file path)."""


@dataclass(frozen=True)
class PropertySpec:
    """One generated attribute: an ontology property scoped to a class.

    Specs are declared by the class that introduces the attribute and are
    inherited by subclasses through the normal Python MRO. A subclass that
    narrows a constraint (e.g. a SHACL qualified shape raising ``minCount``)
    re-declares a spec with the same ``name``, shadowing the parent's.
    """

    name: str
    """Python attribute name (snake_cased label / local name)."""

    predicate: str
    """IRI of the RDF property this attribute serializes to."""

    kind: Literal["object", "literal", "enum", "term", "value"]
    """Object, literal, enum/term reference, or unconstrained RDF value."""

    label: str | None = None
    """``rdfs:label`` of the property."""

    definition: str | None = None
    """``skos:definition`` / ``rdfs:comment`` text for the property."""

    ranges: tuple[str, ...] = ()
    """Python class names of allowed targets (object properties only).

    Stored as names, not types, so generated modules can reference classes
    defined later in the file; resolved lazily through the :class:`Registry`.
    An empty tuple means unconstrained.
    """

    datatype: type | None = None
    """Python type of the value (literal properties only)."""

    required: bool = False
    """True when SHACL declares ``minCount >= 1`` for this class."""

    max_count: int | None = None
    """SHACL ``maxCount``; ``None`` means unbounded. ``1`` means scalar."""

    inverse: str | None = None
    """Python attribute name of the inverse property (``owl:inverseOf``),
    used to keep both directions of an edge in sync in memory."""

    enum_ranges: tuple[str, ...] = ()
    """Allowed enum roots as *IRIs* (enum properties only): a value must be
    one of these members or a descendant in the enumeration hierarchy."""

    term_ranges: tuple[str, ...] = ()
    """Allowed RDF class IRIs for compiled vocabulary individuals."""


@dataclass(frozen=True)
class CPSlot:
    """A connection-point requirement from a 223-style qualified shape.

    "A Chiller must have >= 1 OutletConnectionPoint whose medium is
    Fluid-Water" becomes ``CPSlot(cp_class='OutletConnectionPoint',
    direction='out', medium='...#Fluid-Water', min_count=1)``. The
    connection negotiator materializes these on demand.
    """

    cp_class: str
    """Python class name of the connection point (Inlet/Outlet/...)."""

    direction: Literal["in", "out", "bi"]
    """Flow direction implied by the connection-point class."""

    medium: str | None
    """Required medium as an enum IRI, or None when unconstrained."""

    medium_options: tuple[str, ...] = ()
    """Alternative allowed medium roots projected from ``sh:or``."""

    min_count: int = 1
    """``sh:qualifiedMinCount``."""

    max_count: int | None = None
    """``sh:qualifiedMaxCount``; ``None`` means unbounded."""


@dataclass(frozen=True)
class CPConstraint:
    """A recursive constructive subset of a SHACL shape.

    Boolean nodes retain SHACL's ``and``, ``or``, and ``xone`` structure;
    leaf nodes carry a :class:`CPSlot`. The connection negotiator can use this
    tree to select a complete valid layout without flattening alternatives.
    """

    operator: Literal["slot", "and", "or", "xone", "opaque"]
    """``opaque`` preserves a validation-only boolean branch."""
    slot: CPSlot | None = None
    children: tuple[CPConstraint, ...] = ()


class Registry:
    """Per-generated-package index of classes and UX negotiation tables.

    Each generated package creates exactly one ``Registry``; every class in
    the package registers itself here (via ``Entity.__init_subclass__``) so
    property ranges — stored as strings in :class:`PropertySpec` — can be
    resolved to real classes at runtime without import-order gymnastics.
    """

    def __init__(self, ontology: OntologyInfo) -> None:
        self.ontology = ontology
        self.by_name: dict[str, type[Entity]] = {}
        self.by_iri: dict[str, type[Entity]] = {}
        self.enums_by_iri: dict[str, EnumValue] = {}
        # Imported lazily to avoid a module cycle (containment needs Entity).
        from .containment import ContainmentTable

        self.containment: ContainmentTable = ContainmentTable(self)

    def register(self, cls: type[Entity]) -> None:
        """Record a generated class. Called automatically at class creation."""
        info = cls.__dict__.get("_classinfo")
        if info is None:  # pragma: no cover - guarded by __init_subclass__
            raise TypeError(f"{cls.__name__} has no _classinfo")
        info.cls = cls
        self.by_name[cls.__name__] = cls
        self.by_iri[info.iri] = cls

    def resolve(self, name: str) -> type[Entity]:
        """Look up a class by its Python name (used for range checking)."""
        try:
            return self.by_name[name]
        except KeyError:
            raise KeyError(
                f"class {name!r} is not registered in the {self.ontology.name} package"
            ) from None

    def register_enums(self, module: object) -> None:
        """Index every EnumValue constant in a generated enums module."""
        from .enums import EnumValue

        for value in vars(module).values():
            if isinstance(value, EnumValue):
                self.enums_by_iri[value.iri] = value

    def resolve_enum(self, iri: str) -> EnumValue:
        """Look an enum member up by IRI."""
        try:
            return self.enums_by_iri[iri]
        except KeyError:
            raise KeyError(
                f"enum {iri!r} is not registered in the {self.ontology.name} package"
            ) from None


@dataclass
class ClassInfo:
    """Ontology provenance for one generated class.

    Mutable only in that ``cls`` is back-filled when the class object is
    created; everything else is fixed at generation time.
    """

    iri: str
    ontology: OntologyInfo
    registry: Registry
    label: str | None = None
    definition: str | None = None
    properties: tuple[PropertySpec, ...] = ()
    """Specs *introduced or narrowed* by this class (not inherited ones)."""

    abstract: bool = False
    """True for organizational classes that should not be instantiated."""

    cp_slots: tuple[CPSlot, ...] = ()
    """Connection-point requirements (223-style ontologies only)."""

    cp_constraints: tuple[CPConstraint, ...] = ()
    """Boolean connection layouts projected from nested SHACL shapes."""

    cls: type[Entity] | None = field(default=None, repr=False)
    """The Python class this info describes (set at registration)."""
