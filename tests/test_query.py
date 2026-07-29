"""Loading RDF graphs as generated objects and querying them."""

import pytest
import toy
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

from objectrdf import Model, ModelingError, connect

EX = Namespace("urn:example#")
TOY = Namespace("urn:toy#")


def _graph() -> Graph:
    graph = Graph()
    graph.add((EX.fan, RDF.type, TOY.Fan))
    graph.add((EX.fan, RDF.type, TOY.Equipment))
    graph.add((EX.fan, RDFS.label, Literal("Supply fan")))
    graph.add((EX.fan, TOY.feeds, EX.pump))
    graph.add((EX.fan, TOY.ratedPower, Literal(7.5)))
    graph.add((EX.pump, RDF.type, TOY.Equipment))
    graph.add((EX.pump, RDFS.label, Literal("Primary pump")))
    return graph


def test_from_graph_hydrates_generated_objects_and_relationships():
    model = Model.from_graph(_graph(), registries=toy.Fan.meta.registry)

    fan = model["fan"]
    pump = model["urn:example#pump"]
    assert isinstance(fan, toy.Fan)
    assert isinstance(pump, toy.Equipment)
    assert fan.label == "Supply fan"
    assert fan.rated_power == 7.5
    assert list(fan.feeds) == [pump]


def test_find_all_includes_subclasses_and_filters_attributes():
    model = Model.from_graph(_graph(), registries=toy.Fan.meta.registry)
    pump = model["pump"]

    assert model.find_all(toy.Fan) == [model["fan"]]
    assert model.find_all(toy.Equipment, feeds=pump) == [model["fan"]]
    assert model.find(toy.Equipment, label="Primary pump") is pump
    assert model.find(toy.Sensor) is None
    assert model.find_all(toy.Equipment, label=lambda value: "pump" in value) == [
        pump
    ]


def test_loaded_object_edits_write_through_and_preserve_unmodeled_rdf():
    source = _graph()
    source.add((EX.unknown, URIRef("urn:unmodeled"), Literal("kept")))
    model = Model.from_graph(source, registries=toy.Fan.meta.registry)

    fan = model["fan"]
    assert isinstance(fan, toy.Fan)
    fan.label = "Changed"
    fan.comment = "Retrofitted"
    fan.rated_power = 9.0

    graph = model.graph()
    assert (EX.fan, RDFS.label, Literal("Supply fan")) not in graph
    assert (EX.fan, RDFS.label, Literal("Changed")) in graph
    assert (EX.fan, RDFS.comment, Literal("Retrofitted")) in graph
    assert (EX.fan, TOY.ratedPower, Literal(7.5)) not in graph
    assert (EX.fan, TOY.ratedPower, Literal(9.0)) in graph
    assert (EX.unknown, URIRef("urn:unmodeled"), Literal("kept")) in graph
    assert (EX.fan, RDFS.label, Literal("Changed")) in source


def test_loaded_relationship_edits_and_new_objects_write_through():
    model = Model.from_graph(_graph(), registries=toy.Fan.meta.registry)
    fan = model["fan"]
    pump = model["pump"]
    assert isinstance(fan, toy.Fan)
    assert isinstance(pump, toy.Equipment)

    extra = toy.Equipment("secondary-pump", model=model)
    fan.feeds.add(extra)
    fan.feeds.remove(pump)

    graph = model.graph()
    extra_iri = URIRef("urn:example#secondary-pump")
    assert extra.meta.instance_iri == str(extra_iri)
    assert (extra_iri, RDF.type, TOY.Equipment) in graph
    assert (EX.fan, TOY.feeds, extra_iri) in graph
    assert (extra_iri, TOY.fedBy, EX.fan) in graph
    assert (EX.fan, TOY.feeds, EX.pump) not in graph


def test_failed_new_object_construction_rolls_back_graph_triples():
    model = Model.from_graph(_graph(), registries=toy.Fan.meta.registry)

    with pytest.raises(ModelingError, match="missing required"):
        toy.Meter("bad-meter", model=model)

    assert list(model.graph().triples((EX["bad-meter"], None, None))) == []


def test_lenient_loading_preserves_an_unprojected_known_predicate():
    source = _graph()
    source.add((EX.fan, TOY.hasPart, EX.external))
    model = Model.from_graph(
        source,
        registries=toy.Fan.meta.registry,
        strict=False,
    )

    model["fan"].label = "Changed"

    assert (EX.fan, TOY.hasPart, EX.external) in model.graph()


def test_unknown_object_target_names_the_missing_registry():
    graph = _graph()
    graph.add((EX.fan, TOY.hasPart, EX.external))

    with pytest.raises(ModelingError, match="include its registry"):
        Model.from_graph(graph, registries=toy.Fan.meta.registry)


def test_incompatible_known_types_are_rejected():
    graph = Graph()
    graph.add((EX.item, RDF.type, TOY.Fan))
    graph.add((EX.item, RDF.type, TOY.Location))

    with pytest.raises(ModelingError, match="incompatible generated Python types"):
        Model.from_graph(graph, registries=toy.Fan.meta.registry)


def test_shifty_inference_runs_before_relationships_are_hydrated():
    graph = Graph().parse(
        data="""
            @prefix ex: <urn:example#> .
            @prefix toy: <urn:toy#> .
            ex:fan a toy:Fan .
            ex:pump a toy:Equipment .
        """,
        format="turtle",
    )
    shapes = Graph().parse(
        data="""
            @prefix ex: <urn:example#> .
            @prefix toy: <urn:toy#> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .

            ex:FanShape a sh:NodeShape ;
                sh:targetClass toy:Fan ;
                sh:rule [
                    a sh:TripleRule ;
                    sh:subject sh:this ;
                    sh:predicate toy:feeds ;
                    sh:object ex:pump
                ] .
        """,
        format="turtle",
    )

    model = Model.from_graph(
        graph,
        registries=toy.Fan.meta.registry,
        infer=True,
        shapes=shapes,
    )

    fan = model["fan"]
    assert isinstance(fan, toy.Fan)
    assert list(fan.feeds) == [model["pump"]]
    assert (EX.fan, TOY.feeds, EX.pump) in graph


def test_loaded_graph_can_be_validated_without_authoring_resolution():
    shapes = Graph().parse(
        data="""
            @prefix toy: <urn:toy#> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .

            toy:FanShape a sh:NodeShape ;
                sh:targetClass toy:Fan ;
                sh:property [
                    sh:path toy:hasLocation ;
                    sh:minCount 1
                ] .
        """,
        format="turtle",
    )
    model = Model.from_graph(_graph(), registries=toy.Fan.meta.registry)

    report = model.validate(shapes, infer=False)

    assert not report
    assert report.violations[0].entity is model["fan"]


def test_graph_backed_model_rejects_uncommitted_solver_intentions():
    from objectrdf.watr import Pump, Tank

    graph = Graph()
    graph.add((EX.pump, RDF.type, URIRef(Pump.meta.iri)))
    graph.add((EX.tank, RDF.type, URIRef(Tank.meta.iri)))
    model = Model.from_graph(graph, registries=Pump.meta.registry)

    with pytest.raises(ModelingError, match="cannot yet be added"):
        connect(model["pump"], model["tank"])
