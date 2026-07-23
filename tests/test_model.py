"""Model lifecycle: ambient binding, IRI minting, lookup, serialization."""

import pytest
import toy
from rdflib import OWL, RDF, RDFS, Literal, URIRef

from objectrdf import Model, ModelingError


def test_entities_require_an_active_model():
    with pytest.raises(ModelingError, match="no active Model"):
        toy.Fan("f1")


def test_ambient_model_binds_entities():
    with Model("urn:ex/bldg#") as m:
        fan = toy.Fan("f1")
    assert fan in m.entities
    assert m["f1"] is fan


def test_explicit_model_kwarg():
    m = Model("urn:ex/bldg#")
    fan = toy.Fan("f1", model=m)
    assert fan in m.entities


def test_namespace_gets_separator_appended():
    m = Model("urn:ex/bldg")
    fan = toy.Fan("f1", model=m)
    assert fan.meta.instance_iri == "urn:ex/bldg#f1"


def test_explicit_prefixes_are_bound_to_graph():
    with Model(
        "urn:ex/bldg#",
        prefixes={"qudt": "http://qudt.org/schema/qudt/"},
    ) as m:
        toy.Fan("f1")

    namespaces = {prefix: str(namespace) for prefix, namespace in m.graph().namespaces()}
    assert namespaces["qudt"] == "http://qudt.org/schema/qudt/"


def test_default_prefix_is_reserved_for_model_namespace():
    with pytest.raises(ValueError, match="default prefix is reserved"):
        Model("urn:ex/bldg#", prefixes={"": "urn:other#"})


def test_duplicate_names_rejected():
    with Model("urn:ex/bldg#") as m:
        toy.Fan("f1")
        with pytest.raises(ModelingError, match="already exists"):
            toy.Fan("f1")
    assert len(m) == 1


def test_auto_names_increment_per_class():
    with Model("urn:ex/bldg#") as m:
        f1 = toy.Fan()
        f2 = toy.Fan()
        s1 = toy.Sensor()
    assert f1.name == "fan_1"
    assert f2.name == "fan_2"
    assert s1.name == "sensor_1"  # counters are per class-name prefix
    assert m["fan_2"] is f2
    assert f1.label == "fan_1"  # label still defaults to the name


def test_auto_names_skip_taken_names():
    with Model("urn:ex/bldg#"):
        toy.Fan("fan_1")  # user-minted name occupying the first slot
        auto = toy.Fan()
    assert auto.name == "fan_2"


def test_auto_name_prefix_is_snake_cased():
    with Model("urn:ex/bldg#"):
        meter = toy.Meter(has_point=[toy.Sensor()])
    assert meter.name == "meter_1"


def test_unknown_name_lookup_raises():
    m = Model("urn:ex/bldg#")
    with pytest.raises(KeyError, match="no entity named"):
        m["nope"]


def test_nested_models_restore_outer():
    with Model("urn:outer#") as outer:
        with Model("urn:inner#"):
            inner_fan = toy.Fan("f1")
        outer_fan = toy.Fan("f2")
    assert inner_fan.meta.instance_iri.startswith("urn:inner#")
    assert outer_fan in outer.entities


def test_graph_emits_types_labels_and_edges():
    with Model("urn:ex/bldg#") as m:
        fan = toy.Fan("f1", label="Supply Fan", comment="rooftop")
        pump = toy.Equipment("p1")
        fan.feeds.add(pump)
        fan.rated_power = 1.5

    g = m.graph()
    f1 = URIRef("urn:ex/bldg#f1")
    p1 = URIRef("urn:ex/bldg#p1")
    assert (f1, RDF.type, URIRef("urn:toy#Fan")) in g
    assert (f1, RDFS.label, Literal("Supply Fan")) in g
    assert (f1, RDFS.comment, Literal("rooftop")) in g
    assert (f1, URIRef("urn:toy#feeds"), p1) in g
    assert (f1, URIRef("urn:toy#ratedPower"), Literal(1.5)) in g
    # label defaults to the local name
    assert (p1, RDFS.label, Literal("p1")) in g


def test_graph_declares_instance_ontology_and_imports_dependencies():
    with Model(
        "urn:ex/bldg#",
        name="Example building",
        imports=["urn:manual-dependency"],
    ) as m:
        toy.Fan("f1")

    g = m.graph()
    ontology = URIRef("urn:ex/bldg")
    assert (ontology, RDF.type, OWL.Ontology) in g
    assert (ontology, RDFS.label, Literal("Example building")) in g
    assert (ontology, OWL.imports, URIRef("urn:toy")) in g
    assert (ontology, OWL.imports, URIRef("urn:manual-dependency")) in g


def test_model_accepts_explicit_ontology_iri():
    with Model(
        "urn:ex/instances#",
        ontology_iri="urn:ex/model",
    ) as m:
        toy.Fan("f1")

    assert (URIRef("urn:ex/model"), RDF.type, OWL.Ontology) in m.graph()


def test_save_roundtrip(tmp_path):
    with Model("urn:ex/bldg#") as m:
        toy.Fan("f1")
    out = tmp_path / "model.ttl"
    m.save(out)
    import rdflib

    g = rdflib.Graph()
    g.parse(out)
    assert (URIRef("urn:ex/bldg#f1"), RDF.type, URIRef("urn:toy#Fan")) in g
