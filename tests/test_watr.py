"""WaTr reuses the S223 authoring and deferred-resolution machinery."""

import pytest

from objectrdf import Model, connect
from objectrdf import watr
from objectrdf.watr import enums


@pytest.fixture
def m():
    with Model("urn:example/water#") as model:
        yield model


def test_extension_terms_keep_public_names():
    assert watr.ONTOLOGY.iri == "urn:nawi-water-ontology"
    assert watr.Pump.meta.iri == "urn:nawi-water-ontology#Pump"
    assert watr.Pump_2.meta.iri == "http://data.ashrae.org/standard223#Pump"
    assert issubclass(watr.Pump, watr.Pump_2)


def test_latest_watr_terms_are_available():
    assert watr.MediaFiltrationUnit.meta.iri.endswith("#MediaFiltrationUnit")
    assert issubclass(watr.BeltFilterPress, watr.DewateringUnit)
    assert issubclass(watr.Process_ThermalHydrolysis, watr.Process_Hydrolysis)
    assert enums.ReducingAgent.iri.endswith("#ReducingAgent")


def test_direct_watr_connection_point_shapes_are_compiled():
    slots = watr.Tank._classinfo.cp_slots
    assert {(slot.direction, slot.medium) for slot in slots} >= {
        ("in", "http://data.ashrae.org/standard223#Mix-Fluid"),
        ("out", "http://data.ashrae.org/standard223#Mix-Fluid"),
    }
    constraint = watr.SequencingBatchReactor._classinfo.cp_constraints[0]
    assert constraint.operator == "xone"


def test_watr_domains_prefer_coherent_medium_assignment(m):
    source = watr.Chiller("source")
    pump = watr.Pump("transfer-pump")
    tank = watr.Tank("product-tank")
    inlet = connect(source, pump)
    outlet = connect(pump, tank)

    assert m.check().complete
    resolved = m.resolve()
    inlet_pipe = resolved.connection(inlet)
    outlet_pipe = resolved.connection(outlet)

    assert isinstance(inlet_pipe, watr.Pipe)
    assert isinstance(outlet_pipe, watr.Pipe)
    assert inlet_pipe.has_medium is enums.Fluid_Water
    assert outlet_pipe.has_medium is enums.Fluid_Water
    assert list(pump.has_connection_point) == []
    assert len(list(resolved[pump.name].has_connection_point)) == 2


def test_broad_watr_fluid_domain_can_be_narrowed_explicitly(m):
    source = watr.Tank("source")
    target = watr.Tank("target")
    handle = connect(source, target, medium=enums.Fluid_Sludge)

    connection = m.resolve().connection(handle)
    assert isinstance(connection, watr.Pipe)
    assert connection.has_medium is enums.Fluid_Sludge


def test_watr_connection_handle_stages_role_with_collection_api(m):
    handle = connect(
        watr.Tank("filter"),
        watr.Tank("backwash"),
        medium=enums.Fluid_Water,
    )
    handle.has_role.add(enums.Role_Backwash)

    assert enums.Role_Backwash in handle.has_role
    assert m.resolve().connection(handle).has_role == [enums.Role_Backwash]


def test_named_paired_ports_propagate_medium_through_solver(m):
    source = watr.Chiller("source")
    exchanger = watr.PressureExchanger("pxr")
    target = watr.Tank("target")
    feed_in = exchanger.port("pxr-feed-in", direction="in")
    feed_out = exchanger.port("pxr-feed-out", direction="out")
    feed_in.pair(feed_out)

    inlet = connect(source, feed_in)
    outlet = connect(feed_out, target)

    resolved = m.resolve()
    assert resolved.connection(inlet).has_medium is enums.Fluid_Water
    assert resolved.connection(outlet).has_medium is enums.Fluid_Water
    resolved_in = resolved["pxr-feed-in"]
    resolved_out = resolved["pxr-feed-out"]
    assert resolved_in.paired_connection_point is resolved_out
    assert resolved_out.paired_connection_point is resolved_in


def test_resolution_explains_paired_port_medium_propagation(m):
    source = watr.Tank("source")
    exchanger = watr.PressureExchanger("pxr")
    feed_in = exchanger.port(
        "pxr-feed-in",
        direction="in",
        medium=enums.Fluid_Sludge,
    )
    feed_out = exchanger.port("pxr-feed-out", direction="out")
    feed_in.pair(feed_out)
    handle = connect(feed_out, source.port("source-in", direction="in"))

    explanation = m.resolve().explain(handle)

    assert explanation.medium is enums.Fluid_Sludge
    assert explanation.medium_reason == "paired port"
    assert "paired with pxr-feed-in" in explanation.evidence[-1]
