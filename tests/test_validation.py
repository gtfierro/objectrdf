"""shifty-backed validation with issues mapped back to entities."""

import pytest
import rdflib
import toy

from objectrdf import Model, ValidationError

# Shapes for the toy ontology: a Meter must have at least one hasPoint.
TOY_SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix toy: <urn:toy#> .

toy:MeterShape a sh:NodeShape ;
    sh:targetClass toy:Meter ;
    sh:property [
        sh:path toy:hasPoint ;
        sh:minCount 1 ;
        sh:message "a Meter must observe at least one Point" ;
    ] .
"""


@pytest.fixture
def shapes():
    g = rdflib.Graph()
    g.parse(data=TOY_SHAPES, format="turtle")
    return g


def test_conforming_model(shapes):
    with Model("urn:ex/t#") as m:
        toy.Meter("m1", has_point=[toy.Sensor("s1")])
    report = m.validate(shapes)
    assert report
    assert report.issues == ()


def test_violation_maps_back_to_entity(shapes):
    with Model("urn:ex/t#") as m:
        s1 = toy.Sensor("s1")
        meter = toy.Meter("m1", has_point=[s1])
        # Constructor enforcement passed; break the invariant afterwards to
        # exercise validate() (the safety net for post-construction edits).
        meter.has_point.remove(s1)

    report = m.validate(shapes)
    assert not report
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.entity is meter
    assert "at least one Point" in issue.message
    assert issue.severity == "violation"
    # the rendered form names the entity, its class, and the property
    assert "m1 (Meter)" in str(issue)
    assert "hasPoint" in str(issue)


def test_report_str_conforms(shapes):
    with Model("urn:ex/t#") as m:
        toy.Meter("m1", has_point=[toy.Sensor("s1")])
    assert str(m.validate(shapes)) == "conforms"


def test_compile_validates_by_default(shapes):
    with Model("urn:ex/t#") as m:
        sensor = toy.Sensor("s1")
        meter = toy.Meter("m1", has_point=[sensor])
        meter.has_point.remove(sensor)

    with pytest.raises(ValidationError, match="does not conform") as exc:
        m.compile(shapes=shapes)
    assert exc.value.report is not None

    # Partial/diagnostic workflows can still request resolution alone.
    assert m.compile(validate=False)
