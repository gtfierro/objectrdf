"""QUDT compiled terms and S223 quantity authoring."""

from typing import Any

from rdflib import OWL, Literal, URIRef

from objectrdf import Model, connect, s223
from objectrdf.qudt import (
    quantity,
    quantity_kinds,
    stream_state,
    units,
)
from objectrdf.s223 import enums

QUDT = "http://qudt.org/schema/qudt/"


def test_compiled_qudt_terms_are_external_instances():
    assert units.PA.iri == "http://qudt.org/vocab/unit/PA"
    assert units.PA.is_instance_of(f"{QUDT}Unit")
    assert quantity_kinds.Pressure.is_instance_of(f"{QUDT}QuantityKind")


def test_quantity_helper_emits_s223_qudt_pattern():
    with Model("urn:test/quantity#") as model:
        pump = s223.Pump("pump")
        pressure = quantity(
            s223.QuantifiableProperty,
            "operating-pressure",
            7_000_000,
            units.PA,
            quantity_kinds.Pressure,
            of=pump,
        )

    assert pressure.has_value == 7_000_000
    graph = model.graph()
    pressure_iri = URIRef("urn:test/quantity#operating-pressure")
    assert (
        pressure_iri,
        URIRef(f"{QUDT}hasUnit"),
        URIRef(units.PA.iri),
    ) in graph
    assert (
        pressure_iri,
        URIRef(f"{QUDT}hasQuantityKind"),
        URIRef(quantity_kinds.Pressure.iri),
    ) in graph
    assert (
        pressure_iri,
        URIRef("http://data.ashrae.org/standard223#hasValue"),
        Literal(7_000_000),
    ) in graph
    assert (
        URIRef("urn:test/quantity"),
        OWL.imports,
        URIRef("http://qudt.org/3.4.0/qudt-all"),
    ) in graph


def test_quantifiable_property_accepts_simple_fixed_value():
    with Model("urn:test/simple-value#") as model:
        constructor: Any = s223.QuantifiableProperty
        prop = constructor(
            "salt-fraction",
            has_quantity_kind=quantity_kinds.MassFraction,
            has_unit=units.PERCENT,
            has_value=15,
        )

    assert prop.has_value == 15
    assert (
        URIRef("urn:test/simple-value#salt-fraction"),
        URIRef("http://data.ashrae.org/standard223#hasValue"),
        Literal(15),
    ) in model.graph()


def test_stream_state_stages_medium_qualified_property_on_connection():
    with Model("urn:test/stream#") as model:
        handle = connect(s223.Chiller("source"), s223.Pump("pump"))
        state = stream_state(handle, medium=enums.Fluid_Water)
        flow = state.quantity(
            s223.QuantifiableProperty,
            "design-flow",
            0.25,
            units.M3_PER_SEC,
            quantity_kinds.VolumeFlowRate,
        )

    connection = model.resolve().connection(handle)
    assert flow.of_medium is enums.Fluid_Water
    assert {prop.name for prop in connection.has_property} == {"design-flow"}
