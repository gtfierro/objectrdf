"""UX overlays: per-ontology hints the compiler cannot derive from shapes.

An overlay contributes the pieces of the authoring experience that are policy
rather than ontology fact: which property ``>>`` means for a class family,
and which property realizes "X contains Y" for each class pair. Entries that
don't resolve against a particular ontology version are skipped at emit time
(with a comment in the generated file), so overlays can be written once
against the union of versions.

Overlays are keyed by lowercased ontology name; ``for_ontology`` also accepts
a custom overlay object for extension ontologies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: (container class, child class, property, edge owner: "container"|"child")
ContainmentRuleSpec = tuple[str, str, str, str]


@dataclass(frozen=True)
class Overlay:
    """UX hints for one ontology."""

    rshift: dict[str, str] = field(default_factory=dict)
    """class name -> property that ``>>`` adds to (e.g. Equipment feeds)."""

    containment: tuple[ContainmentRuleSpec, ...] = ()
    """Negotiation table rows for ``with`` scopes and ``contains()``."""

    enum_root: str | None = None
    """IRI of a punned enumeration root (223 EnumerationKind): its subtree
    becomes EnumValue constants in a generated ``enums`` module instead of
    entity classes."""

    ontology_iri: str | None = None
    """Ontology node to use for package identity when an imports closure
    contains several ``owl:Ontology`` declarations."""

    primary_namespace: str | None = None
    """Namespace whose terms retain unsuffixed Python names on collisions."""

    connector: bool = False
    """Install the 223-style connection-point negotiator on Connectable."""

    connection_classes: dict[str, str] = field(default_factory=dict)
    """medium enum IRI (or ancestor) -> Connection subclass name, used by
    the negotiator to pick Duct/Pipe/... from the resolved medium."""

BRICK = Overlay(
    rshift={"Equipment": "feeds"},
    containment=(
        # Spatial hierarchy composes via hasPart.
        ("Location", "Location", "has_part", "container"),
        # Equipment placed in a location: the edge lives on the equipment.
        ("Location", "Equipment", "has_location", "child"),
        # Assemblies: equipment within equipment.
        ("Equipment", "Equipment", "has_part", "container"),
        # Points attach to whatever hosts them.
        ("Equipment", "Point", "has_point", "container"),
        ("Location", "Point", "has_point", "container"),
    ),
    ontology_iri="https://brickschema.org/schema/1.4/Brick",
)

_S223_NS = "http://data.ashrae.org/standard223#"

S223 = Overlay(
    containment=(
        # Spatial hierarchy: physical spaces nest via s223:contains. (The
        # attribute is `contains_` — the trailing underscore avoids the
        # Entity.contains() method — but the negotiated `with`/.contains()
        # UX is the intended surface anyway.)
        ("PhysicalSpace", "PhysicalSpace", "contains_", "container"),
        # A physical space encloses the domain spaces (zones) within it.
        ("PhysicalSpace", "DomainSpace", "encloses", "container"),
        # Equipment placed in a space: the edge lives on the equipment.
        ("PhysicalSpace", "Equipment", "has_physical_location", "child"),
        # Assemblies: equipment within equipment.
        ("Equipment", "Equipment", "contains_", "container"),
    ),
    enum_root=f"{_S223_NS}EnumerationKind",
    ontology_iri="http://data.ashrae.org/standard223/1.0/model/all",
    connector=True,
    connection_classes={
        f"{_S223_NS}Fluid-Air": "Duct",
        f"{_S223_NS}Fluid-Water": "Pipe",
        f"{_S223_NS}Fluid-NaturalGas": "Pipe",
        f"{_S223_NS}Fluid-Oil": "Pipe",
    },
)

_WATR_NS = "urn:nawi-water-ontology#"

WATR = Overlay(
    containment=S223.containment,
    enum_root=S223.enum_root,
    ontology_iri="urn:nawi-water-ontology",
    primary_namespace=_WATR_NS,
    connector=True,
    connection_classes={
        **S223.connection_classes,
        f"{_S223_NS}Mix-Fluid": "Pipe",
    },
)

#: Built-in overlays by lowercased ontology name.
BUILTIN: dict[str, Overlay] = {"brick": BRICK, "s223": S223, "watr": WATR}


def for_ontology(name: str) -> Overlay | None:
    """The built-in overlay for an ontology name, if any."""
    return BUILTIN.get(name.lower())
