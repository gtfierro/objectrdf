""">> and << flow-connection sugar."""

import pytest
import toy

from objectrdf import Model


@pytest.fixture
def m():
    with Model("urn:ex/t#") as model:
        yield model


def test_rshift_adds_feeds_and_returns_right_operand(m):
    a, b = toy.Fan("a"), toy.Fan("b")
    result = a >> b
    assert result is b
    assert b in a.feeds


def test_rshift_chains_along_flow(m):
    a, b, c = toy.Fan("a"), toy.Fan("b"), toy.Fan("c")
    a >> b >> c
    assert b in a.feeds
    assert c in b.feeds
    assert c not in a.feeds


def test_lshift_is_the_mirror(m):
    a, b, c = toy.Fan("a"), toy.Fan("b"), toy.Fan("c")
    a << b << c
    assert a in b.feeds
    assert b in c.feeds


def test_rshift_without_flow_property_raises(m):
    sensor = toy.Sensor("s")
    fan = toy.Fan("f")
    with pytest.raises(TypeError, match="does not participate in >>"):
        sensor >> fan
    with pytest.raises(TypeError, match="does not participate in <<"):
        fan << sensor
