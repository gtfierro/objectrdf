"""Containment: `with` nesting, contains(), negotiation and its errors."""

import pytest
import toy

from objectrdf import Model
from objectrdf.core import ContainmentError


@pytest.fixture
def m():
    with Model("urn:ex/t#") as model:
        yield model


def test_with_nesting_builds_location_hierarchy(m):
    with toy.Location("site") as site:
        with toy.Location("floor1") as floor1:
            room = toy.Location("room101")
    assert floor1 in site.has_part
    assert room in floor1.has_part
    assert room not in site.has_part  # attached to innermost only


def test_equipment_in_location_scope_gets_has_location(m):
    with toy.Location("room101") as room:
        fan = toy.Fan("f1")
    # rule declares the edge lives on the child (equipment hasLocation room)
    assert fan.has_location is room


def test_point_attaches_to_innermost_compatible_container(m):
    with toy.Location("room101") as room:
        with toy.Fan("f1") as fan:
            sensor = toy.Sensor("s1")
    assert sensor in fan.has_point
    assert sensor not in room.has_point


def test_explicit_contains(m):
    floor1 = toy.Location("floor1")
    r1, r2 = toy.Location("r1"), toy.Location("r2")
    result = floor1.contains(r1, r2)
    assert result is floor1  # chains
    assert list(floor1.has_part) == [r1, r2]


def test_contains_via_escape_hatch(m):
    fan = toy.Fan("f1")
    sensor = toy.Sensor("s1")
    fan.contains(sensor, via="has_point")
    assert sensor in fan.has_point


def test_no_rule_raises_with_guidance(m):
    s1 = toy.Sensor("s1")
    s2 = toy.Sensor("s2")
    with pytest.raises(ContainmentError, match="no containment rule"):
        s1.contains(s2)


def test_incompatible_scope_raises(m):
    # A Location cannot be contained by Equipment: no rule for that pair.
    with toy.Fan("f1"):
        with pytest.raises(ContainmentError, match="no containment rule accepts"):
            toy.Location("room")


def test_ambiguous_rules_raise(m):
    table = toy._REGISTRY.containment
    table.register("Equipment", "Sensor", "feeds")  # nonsense second rule
    try:
        fan = toy.Fan("f1")
        sensor = toy.Sensor("s1")
        with pytest.raises(ContainmentError, match="more than one property"):
            fan.contains(sensor)
    finally:
        table.rules.pop()


def test_via_with_unknown_property_raises(m):
    fan = toy.Fan("f1")
    sensor = toy.Sensor("s1")
    with pytest.raises(ContainmentError, match="has a property named"):
        fan.contains(sensor, via="bogus")


def test_scope_is_cleaned_up_after_exit(m):
    with toy.Location("room"):
        pass
    # No ambient container anymore: sensors attach nowhere, silently.
    sensor = toy.Sensor("s1")
    assert sensor in m.entities
