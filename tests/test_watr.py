"""WaTr reuses the S223 authoring and deferred-resolution machinery."""

import pytest
from rdflib import URIRef

from objectrdf import Model, connect
from objectrdf import watr
from objectrdf.watr import enums

W = "https://watermetadata.org/ontology/watr#"


@pytest.fixture
def m():
    with Model("urn:example/water#") as model:
        yield model


def test_extension_terms_keep_public_names():
    assert watr.ONTOLOGY.iri == "https://watermetadata.org/ontology/watr"
    assert watr.Pump.meta.iri == "https://watermetadata.org/ontology/watr#Pump"
    assert watr.Pump_2.meta.iri == "http://data.ashrae.org/standard223#Pump"
    # WaTr 0.3 pumps accept any Mix-Fluid (e.g. sludge), so they extend
    # s223:Equipment rather than s223:Pump, which admits only water, oil, or
    # refrigerant.
    assert not issubclass(watr.Pump, watr.Pump_2)
    assert issubclass(watr.Pump, watr.Equipment)


def test_latest_watr_terms_are_available():
    assert watr.MediaFiltrationUnit.meta.iri.endswith("#MediaFiltrationUnit")
    assert issubclass(watr.BeltFilterPress, watr.DewateringUnit)
    assert issubclass(watr.Process_ThermalHydrolysis, watr.Process_Hydrolysis)
    assert enums.values.ReducingAgent.iri.endswith("#ReducingAgent")


def test_class_implied_process_and_objective_are_filled_in(m):
    # WaTr's ClassDefaultsRule infers these in RDF; the generated classes
    # apply the same defaults so the authored model already carries them.
    clarifier = watr.Clarifier("clarifier")
    assert list(clarifier.has_process) == [watr.Process_Settling]
    assert list(clarifier.has_treatment_objective) == [
        watr.TreatmentObjective_Clarification
    ]
    # Only the unconnected outlets remain; nothing about process or objective.
    messages = [issue.message for issue in m.validate(infer=False).violations]
    assert messages
    assert not [text for text in messages if "rocess" in text or "bjective" in text]


def test_direct_watr_connection_point_shapes_are_compiled():
    slots = watr.Reactor._classinfo.cp_slots
    assert {(slot.direction, slot.medium) for slot in slots} >= {
        ("in", "http://data.ashrae.org/standard223#Mix-Fluid"),
        ("out", "http://data.ashrae.org/standard223#Mix-Fluid"),
    }
    constraint = watr.Clarifier._classinfo.cp_constraints[0]
    assert constraint.operator == "and"


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
    assert inlet_pipe.medium is enums.values.Fluid_Water
    assert outlet_pipe.medium is enums.values.Fluid_Water
    assert list(pump.has_connection_point) == []
    assert len(list(resolved[pump.name].has_connection_point)) == 2


def test_broad_watr_fluid_domain_can_be_narrowed_explicitly(m):
    source = watr.Tank("source")
    target = watr.Tank("target")
    handle = connect(source, target, medium=enums.values.Fluid_Sludge)

    connection = m.resolve().connection(handle)
    assert isinstance(connection, watr.Pipe)
    assert connection.medium is enums.values.Fluid_Sludge


def test_watr_connection_handle_stages_role_with_collection_api(m):
    handle = connect(
        watr.Tank("filter"),
        watr.Tank("backwash"),
        medium=enums.values.Fluid_Water,
    )
    handle.has_role.add(enums.values.Role_Backwash)

    assert enums.values.Role_Backwash in handle.has_role
    assert m.resolve().connection(handle).has_role == [enums.values.Role_Backwash]


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
    assert resolved.connection(inlet).medium is enums.values.Fluid_Water
    assert resolved.connection(outlet).medium is enums.values.Fluid_Water
    resolved_in = resolved["pxr-feed-in"]
    resolved_out = resolved["pxr-feed-out"]
    assert resolved_in.paired_with is resolved_out
    assert resolved_out.paired_with is resolved_in


def test_resolution_explains_paired_port_medium_propagation(m):
    source = watr.Tank("source")
    exchanger = watr.PressureExchanger("pxr")
    feed_in = exchanger.port(
        "pxr-feed-in",
        direction="in",
        medium=enums.values.Fluid_Sludge,
    )
    feed_out = exchanger.port("pxr-feed-out", direction="out")
    feed_in.pair(feed_out)
    handle = connect(feed_out, source.port("source-in", direction="in"))

    explanation = m.resolve().explain(handle)

    assert explanation.medium is enums.values.Fluid_Sludge
    assert explanation.medium_reason == "paired port"
    assert "paired with pxr-feed-in" in explanation.evidence[-1]
    assert str(explanation) == (
        "pxr-feed-out--source-in: pxr-feed-out -> source-in\n"
        "  medium: Fluid-Sludge (paired port)\n"
        "  - selected OutletConnectionPoint pxr-feed-out\n"
        "  - selected InletConnectionPoint source-in\n"
        "  - pxr-feed-out is paired with pxr-feed-in, whose medium is Fluid-Sludge"
    )


def test_prefixes_follow_namespaces_not_entity_order():
    def bindings(first, second):
        with Model("urn:example/order#") as model:
            first(f"a-{first.__name__}")
            second(f"b-{second.__name__}")
        graph = model.graph()
        return {
            prefix: str(namespace)
            for prefix, namespace in graph.namespaces()
            if prefix in {"s223", "watr"}
        }

    # watr.Pump_2 is s223:Pump, generated into the WaTr package.
    expected = {
        "s223": "http://data.ashrae.org/standard223#",
        "watr": "https://watermetadata.org/ontology/watr#",
    }
    assert bindings(watr.Pump_2, watr.Tank) == expected
    assert bindings(watr.Tank, watr.Pump_2) == expected


def test_from_graph_inference_uses_bundled_package_rules(m):
    # The model file carries no rules; inference must read the generated
    # package's bundled shapes, as validate() does.
    watr.Clarifier("clarifier")
    graph = m.graph()
    for predicate in ("hasProcess", "hasTreatmentObjective"):
        graph.remove((None, URIRef(f"{W}{predicate}"), None))

    plain = Model.from_graph(graph, registries=watr.REGISTRY)["clarifier"]
    assert isinstance(plain, watr.Clarifier)
    assert not list(plain.has_process)

    inferred = Model.from_graph(graph, registries=watr.REGISTRY, infer=True)
    clarifier = inferred["clarifier"]
    assert isinstance(clarifier, watr.Clarifier)
    assert watr.Process_Settling in clarifier.has_process
    assert watr.TreatmentObjective_Clarification in clarifier.has_treatment_objective
