"""Integration tests against the committed generated Brick package."""

import pytest
from rdflib import RDF, URIRef

brick = pytest.importorskip("objectrdf.brick")

from objectrdf import Model  # noqa: E402

BRICK = "https://brickschema.org/schema/Brick#"


@pytest.fixture
def m():
    with Model("urn:test/bldg#") as model:
        yield model


def test_scale_and_hierarchy():
    assert len(brick.__all__) > 1000
    assert issubclass(brick.AHU, brick.HVAC_Equipment)
    assert issubclass(brick.AHU, brick.Equipment)
    assert issubclass(brick.Supply_Air_Temperature_Sensor, brick.Point)


def test_docstrings_come_from_the_ontology():
    assert "fan" in (brick.AHU.__doc__ or "").lower()
    assert brick.AHU.meta.iri == f"{BRICK}AHU"
    assert brick.AHU.meta.ontology.name == "Brick"


def test_feeds_operator_and_inverse(m):
    ahu = brick.AHU("ahu1")
    vav = brick.VAV("vav1")
    ahu >> vav
    assert vav in ahu.feeds
    assert ahu in vav.is_fed_by


def test_containment_negotiation(m):
    with brick.Building("b1") as building:
        with brick.Floor("f1") as floor:
            room = brick.Room("r1")
    assert floor in building.has_part
    assert room in floor.has_part

    with brick.Room("r2") as r2:
        ahu = brick.AHU("ahu1")
    assert r2 in ahu.has_location

    ahu.contains(brick.Supply_Fan("sf1"))
    assert m["sf1"] in ahu.has_part


def test_point_range_enforced(m):
    ahu = brick.AHU("ahu1")
    with pytest.raises(Exception, match="has_point expects Point"):
        ahu.has_point.add(brick.VAV("v"))  # deliberate wrong type


def test_serialization_produces_brick_triples(m):
    ahu = brick.AHU("ahu1")
    vav = brick.VAV("vav1")
    ahu >> vav
    g = m.graph()
    a = URIRef("urn:test/bldg#ahu1")
    assert (a, RDF.type, URIRef(f"{BRICK}AHU")) in g
    assert (a, URIRef(f"{BRICK}feeds"), URIRef("urn:test/bldg#vav1")) in g


def test_quickstart_example_runs(tmp_path):
    import runpy
    import shutil
    from pathlib import Path

    example = Path(__file__).parent.parent / "examples" / "brick_quickstart.py"
    target = tmp_path / "brick_quickstart.py"
    shutil.copy(example, target)
    runpy.run_path(str(target))
    assert (tmp_path / "bldg1.ttl").exists()
