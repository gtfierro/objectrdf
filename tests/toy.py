"""A tiny hand-written ontology package in the exact shape the compiler emits.

Used by the core runtime tests so they don't depend on the generator; also
serves as the reference for what generated code should look like. If the
emitter's output style changes, change this file to match.
"""

from __future__ import annotations

from objectrdf.core import (
    ClassInfo,
    Entity,
    Lit,
    OntologyInfo,
    PropertySpec,
    Registry,
    Rel,
    RelOne,
)

ONTOLOGY = OntologyInfo(name="Toy", iri="urn:toy", version="0.0.1")

_REGISTRY = Registry(ONTOLOGY)

_P_Equipment_feeds = PropertySpec(
    name="feeds",
    predicate="urn:toy#feeds",
    kind="object",
    label="feeds",
    definition="The subject delivers a flow to the object.",
    ranges=("Equipment",),
    inverse="fed_by",
)
_P_Equipment_fed_by = PropertySpec(
    name="fed_by",
    predicate="urn:toy#fedBy",
    kind="object",
    ranges=("Equipment",),
    inverse="feeds",
)
_P_Equipment_has_part = PropertySpec(
    name="has_part",
    predicate="urn:toy#hasPart",
    kind="object",
    ranges=("Equipment",),
)
_P_Equipment_has_location = PropertySpec(
    name="has_location",
    predicate="urn:toy#hasLocation",
    kind="object",
    ranges=("Location",),
    max_count=1,
)
_P_Equipment_has_point = PropertySpec(
    name="has_point",
    predicate="urn:toy#hasPoint",
    kind="object",
    ranges=("Point",),
)
_P_Equipment_rated_power = PropertySpec(
    name="rated_power",
    predicate="urn:toy#ratedPower",
    kind="literal",
    datatype=float,
    max_count=1,
)


class Equipment(Entity):
    """A toy equipment class.

    Ontology: Toy — urn:toy#Equipment
    """

    _classinfo = ClassInfo(
        iri="urn:toy#Equipment",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label="Equipment",
        definition="A toy equipment class.",
        properties=(
            _P_Equipment_feeds,
            _P_Equipment_fed_by,
            _P_Equipment_has_part,
            _P_Equipment_has_location,
            _P_Equipment_has_point,
            _P_Equipment_rated_power,
        ),
    )

    feeds: Rel[Equipment] = Rel(_P_Equipment_feeds)
    """The subject delivers a flow to the object. (toy:feeds)"""

    fed_by: Rel[Equipment] = Rel(_P_Equipment_fed_by)
    has_part: Rel[Equipment] = Rel(_P_Equipment_has_part)
    has_location: RelOne[Location] = RelOne(_P_Equipment_has_location)
    has_point: Rel[Point] = Rel(_P_Equipment_has_point)
    rated_power: Lit[float] = Lit(_P_Equipment_rated_power)


class Fan(Equipment):
    """A toy fan.

    Ontology: Toy — urn:toy#Fan
    """

    _classinfo = ClassInfo(
        iri="urn:toy#Fan",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label="Fan",
        definition="A device that moves air.",
    )


_P_Location_has_part = PropertySpec(
    name="has_part",
    predicate="urn:toy#hasPart",
    kind="object",
    ranges=("Location",),
)
_P_Location_has_point = PropertySpec(
    name="has_point",
    predicate="urn:toy#hasPoint",
    kind="object",
    ranges=("Point",),
)


class Location(Entity):
    """A toy location.

    Ontology: Toy — urn:toy#Location
    """

    _classinfo = ClassInfo(
        iri="urn:toy#Location",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label="Location",
        properties=(_P_Location_has_part, _P_Location_has_point),
    )

    has_part: Rel[Location] = Rel(_P_Location_has_part)
    has_point: Rel[Point] = Rel(_P_Location_has_point)


class Point(Entity):
    """A toy point (sensor/setpoint/etc)."""

    _classinfo = ClassInfo(
        iri="urn:toy#Point",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label="Point",
    )


class Sensor(Point):
    """A toy sensor."""

    _classinfo = ClassInfo(
        iri="urn:toy#Sensor",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label="Sensor",
    )


class Organizational(Entity):
    """An abstract/organizational class that must not be instantiated."""

    _classinfo = ClassInfo(
        iri="urn:toy#Organizational",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        abstract=True,
    )


_P_Meter_has_point = PropertySpec(
    name="has_point",
    predicate="urn:toy#hasPoint",
    kind="object",
    ranges=("Point",),
    required=True,
)


class Meter(Equipment):
    """A toy meter: narrows has_point to required (SHACL minCount 1)."""

    _classinfo = ClassInfo(
        iri="urn:toy#Meter",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label="Meter",
        properties=(_P_Meter_has_point,),
    )

    has_point: Rel[Point] = Rel(_P_Meter_has_point)


# -- UX registration (what generated overlay code emits) -------------------

Equipment._RSHIFT = "feeds"

_REGISTRY.containment.register("Location", "Location", "has_part")
_REGISTRY.containment.register(
    "Location", "Equipment", "has_location", edge_from="child"
)
_REGISTRY.containment.register("Equipment", "Equipment", "has_part")
_REGISTRY.containment.register("Equipment", "Point", "has_point")
_REGISTRY.containment.register("Location", "Point", "has_point")
