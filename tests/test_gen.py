"""The compiler: fixture ontology -> generated module -> working classes."""

import importlib.util
import sys
from pathlib import Path

import pytest
import rdflib

from objectrdf import Model, ModelingError
from objectrdf.gen import compile_modules, compile_source, extract, generate
from objectrdf.gen.overlays import Overlay

FIXTURE = Path(__file__).parent / "fixtures" / "mini.ttl"

MINI_OVERLAY = Overlay(
    rshift={"Equipment": "feeds"},
    containment=(
        ("Equipment", "Sensor", "has_sensor", "container"),
        # deliberately references a class this ontology doesn't define:
        ("Zone", "Equipment", "has_location", "child"),
    ),
)

BOOLEAN_CP_TTL = """
@prefix mini: <urn:boolean#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

<urn:boolean> a owl:Ontology .

mini:Coil a owl:Class, sh:NodeShape ;
    sh:xone (
        [ sh:and (
            [ sh:property [
                sh:path mini:hasConnectionPoint ;
                sh:qualifiedValueShape [
                    sh:class mini:InletConnectionPoint ;
                    sh:node [ sh:property [
                        sh:path mini:hasMedium ;
                        sh:class mini:Fluid-Air
                    ] ]
                ] ;
                sh:qualifiedMinCount 1 ;
                sh:qualifiedMaxCount 1
            ] ]
            [ sh:or (
                [ sh:property [
                    sh:path mini:hasConnectionPoint ;
                    sh:qualifiedValueShape [
                        sh:class mini:OutletConnectionPoint ;
                        sh:node [ sh:property [
                            sh:path mini:hasMedium ;
                            sh:class mini:Fluid-Air
                        ] ]
                    ] ;
                    sh:qualifiedMinCount 1
                ] ]
                [ sh:property [
                    sh:path mini:hasConnectionPoint ;
                    sh:qualifiedValueShape [
                        sh:class mini:OutletConnectionPoint ;
                        sh:node [ sh:property [
                            sh:path mini:hasMedium ;
                            sh:class mini:Fluid-Water
                        ] ]
                    ] ;
                    sh:qualifiedMinCount 1
                ] ]
                [ sh:property [
                    sh:path mini:label ;
                    sh:minCount 1
                ] ]
            ) ]
        ) ]
        [ sh:property [
            sh:path mini:hasConnectionPoint ;
            sh:qualifiedValueShape [
                sh:class mini:BidirectionalConnectionPoint ;
                sh:node [ sh:property [
                    sh:path mini:hasMedium ;
                    sh:class mini:Medium-ThermalContact
                ] ]
            ] ;
            sh:qualifiedMinCount 2 ;
            sh:qualifiedMaxCount 3
        ] ]
    ) .

mini:Pump a owl:Class, sh:NodeShape ;
    sh:property [
        sh:path mini:hasConnectionPoint ;
        sh:qualifiedValueShape [
            sh:class mini:OutletConnectionPoint ;
            sh:node [ sh:property [
                sh:path mini:hasMedium ;
                sh:or (
                    [ sh:class mini:Fluid-Water ]
                    [ sh:class mini:Fluid-Air ]
                )
            ] ]
        ] ;
        sh:qualifiedMinCount 1
    ] .

# WaTr places the nested medium constraint directly on the qualified shape.
mini:Tank a owl:Class, sh:NodeShape ;
    sh:property [
        sh:path mini:hasConnectionPoint ;
        sh:qualifiedValueShape [
            sh:class mini:InletConnectionPoint ;
            sh:property [
                sh:path mini:hasMedium ;
                sh:class mini:Fluid-Water
            ]
        ] ;
        sh:qualifiedMinCount 1
    ] .

mini:InletConnectionPoint a owl:Class .
mini:OutletConnectionPoint a owl:Class .
mini:BidirectionalConnectionPoint a owl:Class .
mini:EnumerationKind a owl:Class .
mini:Fluid-Air a owl:Class ; rdfs:subClassOf mini:EnumerationKind .
mini:Fluid-Water a owl:Class ; rdfs:subClassOf mini:EnumerationKind .
mini:Medium-ThermalContact a owl:Class ;
    rdfs:subClassOf mini:EnumerationKind .
"""


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    """Compile the fixture ontology and import the generated package."""
    graph = rdflib.Graph()
    graph.parse(FIXTURE)
    out = tmp_path_factory.mktemp("gen") / "mini"
    target = generate(
        graph, out, name="Mini", source=str(FIXTURE), overlay=MINI_OVERLAY
    )
    spec = importlib.util.spec_from_file_location("generated_mini", target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["generated_mini"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def m():
    with Model("urn:ex/site#") as model:
        yield model


def test_class_hierarchy(mini):
    assert issubclass(mini.Fan, mini.Equipment)
    assert issubclass(mini.ExhaustFan, mini.Fan)


def test_ontology_info(mini):
    assert mini.ONTOLOGY.name == "Mini"
    assert mini.ONTOLOGY.iri == "urn:mini"
    assert mini.ONTOLOGY.version == "1.2.3"
    assert mini.ONTOLOGY.source == str(FIXTURE)
    assert Path(mini.__file__).with_name("_shapes.ttl").exists()


def test_docstrings_carry_ontology_documentation(mini):
    assert "Moves air using rotating blades." in mini.Fan.__doc__
    assert "urn:mini#Fan" in mini.Fan.__doc__  # provenance in the docstring
    # rdfs:comment is the fallback when skos:definition is absent
    assert "Measures a physical quantity." in mini.Sensor.__doc__


def test_meta_matches_docstrings(mini):
    assert mini.Fan.meta.definition == "Moves air using rotating blades."
    assert mini.Fan.meta.label == "Fan"
    assert mini.Fan.meta.ontology.version == "1.2.3"


def test_property_names_are_snake_cased(mini, m):
    fan = mini.Fan("f1", has_sensor=[mini.Sensor("s1")])
    assert hasattr(fan, "is_fed_by")
    assert hasattr(fan, "rated_power")


def test_shacl_min_count_becomes_required(mini, m):
    # The generated signature itself rejects the omission (this is what the
    # IDE/type checker sees too)...
    with pytest.raises(TypeError, match="has_sensor"):
        mini.Fan("f1")
    # ...and the runtime net still catches an explicitly-empty collection.
    with pytest.raises(ModelingError, match="missing required property: has_sensor"):
        mini.Fan("f1", has_sensor=[])
    import inspect

    param = inspect.signature(mini.Fan.__init__).parameters["has_sensor"]
    assert param.default is inspect.Parameter.empty


def test_shacl_max_count_one_becomes_scalar(mini, m):
    fan = mini.Fan("f1", has_sensor=[mini.Sensor("s1")])
    system = mini.System("sys1")
    fan.part_of_system = system
    assert fan.part_of_system is system


def test_generated_init_allows_omitting_name(mini, m):
    fan = mini.Fan(has_sensor=[mini.Sensor()])
    assert fan.name == "fan_1"
    assert m["sensor_1"] in fan.has_sensor


def test_plain_equipment_is_unconstrained(mini, m):
    eq = mini.Equipment("e1")  # no SHACL narrowing on the parent
    assert list(eq.has_sensor) == []


def test_inverse_maintained_from_owl_inverse_of(mini, m):
    a = mini.Equipment("a")
    b = mini.Equipment("b")
    a.feeds.add(b)
    assert a in b.is_fed_by


def test_overlay_rshift_and_containment(mini, m):
    a = mini.Equipment("a")
    b = mini.Equipment("b")
    a >> b
    assert b in a.feeds
    with mini.Fan("f1", has_sensor=[mini.Sensor("seed")]) as fan:
        s2 = mini.Sensor("s2")
    assert s2 in fan.has_sensor


def test_overlay_entries_for_missing_classes_are_skipped(mini):
    source = Path(mini.__file__).read_text()
    assert "# skipped: containment Zone/Equipment" in source


def test_serialization_uses_ontology_predicates(mini, m):
    from rdflib import Literal, URIRef

    mini.Fan("f1", has_sensor=[mini.Sensor("s1")], rated_power=0.75)
    g = m.graph()
    f1 = URIRef("urn:ex/site#f1")
    assert (f1, URIRef("urn:mini#hasSensor"), URIRef("urn:ex/site#s1")) in g
    assert (f1, URIRef("urn:mini#ratedPower"), Literal(0.75)) in g


def test_generation_is_deterministic():
    graph = rdflib.Graph()
    graph.parse(FIXTURE)
    one = compile_source(graph, name="Mini", source="x", overlay=MINI_OVERLAY)
    two = compile_source(graph, name="Mini", source="x", overlay=MINI_OVERLAY)
    assert one == two


def test_punned_enum_is_emitted_only_as_reference_instance():
    graph = rdflib.Graph().parse(
        data=BOOLEAN_CP_TTL
        + """
            @prefix mini: <urn:boolean#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            mini:Fluid-Air a owl:NamedIndividual, mini:EnumerationKind .
        """,
        format="turtle",
    )
    modules = compile_modules(
        graph,
        name="Boolean",
        overlay=Overlay(enum_root="urn:boolean#EnumerationKind"),
    )

    assert "class Fluid_Air" not in modules["__init__.py"]
    assert "Fluid_Air = _EnumValue(" in modules["enums.py"]


def test_multiple_inheritance_constructor_unions_parent_properties():
    graph = rdflib.Graph().parse(
        data="""
            @prefix ex: <urn:mi#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            <urn:mi> a owl:Ontology .
            ex:A a owl:Class .
            ex:B a owl:Class .
            ex:C a owl:Class ; rdfs:subClassOf ex:A, ex:B .
            ex:a a owl:DatatypeProperty ; rdfs:domain ex:A .
            ex:b a owl:DatatypeProperty ; rdfs:domain ex:B .
        """,
        format="turtle",
    )
    source = compile_source(graph, name="MI", overlay=None)
    c_source = source.split("class C(A, B):", 1)[1]

    assert "def __init__(" in c_source
    signature = c_source.split("def __init__(", 1)[1].split(") -> None:", 1)[0]
    assert "a:" in signature
    assert "b:" in signature


def test_has_value_is_scalar_and_sparql_shape_does_not_loosen_it():
    graph = rdflib.Graph().parse(
        data="""
            @prefix ex: <urn:value#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            <urn:value> a owl:Ontology .
            ex:Property a owl:Class, sh:NodeShape ;
                sh:property [
                    sh:path <http://data.ashrae.org/standard223#hasValue> ;
                    sh:maxCount 1
                ] .
            ex:QuantifiableProperty a owl:Class, sh:NodeShape ;
                rdfs:subClassOf ex:Property ;
                sh:property [
                    sh:path <http://data.ashrae.org/standard223#hasValue> ;
                    sh:message "SPARQL-only semantic constraint"
                ] .
        """,
        format="turtle",
    )
    ir = extract(graph, name="Value")
    prop = next(item for item in ir.classes if item.name == "Property")
    quantifiable = next(
        item for item in ir.classes if item.name == "QuantifiableProperty"
    )

    has_value = next(item for item in prop.own_props if item.name == "has_value")
    assert has_value.kind == "value"
    assert has_value.max_count == 1
    assert all(item.name != "has_value" for item in quantifiable.own_props)


def test_boolean_shacl_connection_constraints_are_preserved():
    graph = rdflib.Graph().parse(data=BOOLEAN_CP_TTL, format="turtle")
    ir = extract(
        graph,
        name="Boolean",
        enum_root="urn:boolean#EnumerationKind",
    )
    coil = next(cls for cls in ir.classes if cls.name == "Coil")

    assert coil.cp_slots == []  # alternatives must not become unconditional
    assert len(coil.cp_constraints) == 1
    xone = coil.cp_constraints[0]
    assert xone.operator == "xone"
    assert [child.operator for child in xone.children] == ["and", "slot"]

    inlet, outlets = xone.children[0].children
    assert inlet.slot is not None
    assert inlet.slot.direction == "in"
    assert inlet.slot.medium == "urn:boolean#Fluid-Air"
    assert inlet.slot.max_count == 1
    assert outlets.operator == "or"
    assert [child.operator for child in outlets.children] == [
        "slot",
        "slot",
        "opaque",
    ]
    assert [child.slot.medium for child in outlets.children if child.slot] == [
        "urn:boolean#Fluid-Air",
        "urn:boolean#Fluid-Water",
    ]

    bidirectional = xone.children[1].slot
    assert bidirectional is not None
    assert bidirectional.direction == "bi"
    assert bidirectional.min_count == 2
    assert bidirectional.max_count == 3


def test_boolean_connection_constraints_are_emitted():
    graph = rdflib.Graph().parse(data=BOOLEAN_CP_TTL, format="turtle")
    source = compile_source(
        graph,
        name="Boolean",
        overlay=Overlay(enum_root="urn:boolean#EnumerationKind"),
    )

    assert "cp_constraints=(" in source
    assert "_CPConstraint(operator='xone'" in source
    assert "_CPConstraint(operator='and'" in source
    assert "_CPConstraint(operator='or'" in source
    assert "_CPConstraint(operator='opaque')" in source
    assert "max_count=3" in source
    compile(source, "<generated boolean ontology>", "exec")


def test_nested_medium_or_becomes_slot_domain():
    graph = rdflib.Graph().parse(data=BOOLEAN_CP_TTL, format="turtle")
    ir = extract(
        graph,
        name="Boolean",
        enum_root="urn:boolean#EnumerationKind",
    )
    pump = next(cls for cls in ir.classes if cls.name == "Pump")

    assert len(pump.cp_slots) == 1
    assert pump.cp_slots[0].medium is None
    assert pump.cp_slots[0].medium_options == (
        "urn:boolean#Fluid-Air",
        "urn:boolean#Fluid-Water",
    )


def test_direct_qualified_shape_medium_is_extracted():
    graph = rdflib.Graph().parse(data=BOOLEAN_CP_TTL, format="turtle")
    ir = extract(
        graph,
        name="Boolean",
        enum_root="urn:boolean#EnumerationKind",
    )
    tank = next(cls for cls in ir.classes if cls.name == "Tank")

    assert len(tank.cp_slots) == 1
    assert tank.cp_slots[0].medium == "urn:boolean#Fluid-Water"


def test_extension_namespace_wins_name_collisions_and_identity():
    graph = rdflib.Graph().parse(
        data="""
            @prefix base: <urn:base#> .
            @prefix ext: <urn:extension#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            <urn:base> a owl:Ontology .
            <urn:extension> a owl:Ontology .
            base:Pump a owl:Class .
            ext:Pump a owl:Class ; rdfs:subClassOf base:Pump .
        """,
        format="turtle",
    )
    ir = extract(
        graph,
        name="Extension",
        ontology_iri="urn:extension",
        primary_namespace="urn:extension#",
    )

    names = {cls.iri: cls.name for cls in ir.classes}
    assert ir.ontology_iri == "urn:extension"
    assert names["urn:extension#Pump"] == "Pump"
    assert names["urn:base#Pump"] == "Pump_2"


def test_generated_source_type_checks(mini, tmp_path):
    """The emitted module must satisfy the type checker, not just run."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "ty", "check", mini.__file__],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, result.stdout + result.stderr
