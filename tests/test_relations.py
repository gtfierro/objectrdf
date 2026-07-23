"""Typed relationship descriptors: RelSet, RelOne, Lit, inverse upkeep."""

import pytest
import toy

from objectrdf import Model, ModelingError
from objectrdf.core import RangeError


@pytest.fixture
def m():
    with Model("urn:ex/t#") as model:
        yield model


def test_add_and_iterate(m):
    a, b, c = toy.Fan("a"), toy.Fan("b"), toy.Fan("c")
    a.feeds.add(b, c)
    assert list(a.feeds) == [b, c]
    assert b in a.feeds
    assert len(a.feeds) == 2


def test_add_deduplicates(m):
    a, b = toy.Fan("a"), toy.Fan("b")
    a.feeds.add(b)
    a.feeds.add(b)
    assert len(a.feeds) == 1


def test_range_violation_raises(m):
    a = toy.Fan("a")
    pt = toy.Sensor("s")
    with pytest.raises(RangeError, match="feeds expects Equipment"):
        a.feeds.add(pt)  # ty: ignore[invalid-argument-type]  # deliberate: runtime must mirror


def test_non_entity_value_raises(m):
    a = toy.Fan("a")
    with pytest.raises(RangeError, match="links entities"):
        a.feeds.add("not-an-entity")  # ty: ignore[invalid-argument-type]  # deliberate


def test_constructor_kwargs_assign_relations(m):
    b = toy.Fan("b")
    a = toy.Fan("a", feeds=[b], rated_power=2.0)
    assert list(a.feeds) == [b]
    assert a.rated_power == 2.0


def test_unknown_constructor_kwarg_raises(m):
    with pytest.raises(ModelingError, match="no property 'nope'"):
        toy.Fan("a", nope=1)


def test_inverse_is_maintained(m):
    a, b = toy.Fan("a"), toy.Fan("b")
    a.feeds.add(b)
    assert list(b.fed_by) == [a]
    # and symmetrically from the other declared direction
    c = toy.Fan("c")
    c.fed_by.add(a)
    assert c in a.feeds


def test_remove_unlinks_inverse(m):
    a, b = toy.Fan("a"), toy.Fan("b")
    a.feeds.add(b)
    a.feeds.remove(b)
    assert list(b.fed_by) == []


def test_assignment_replaces_contents(m):
    a, b, c = toy.Fan("a"), toy.Fan("b"), toy.Fan("c")
    a.feeds = [b]
    a.feeds = [c]
    assert list(a.feeds) == [c]
    assert list(b.fed_by) == []  # old edge fully retracted


def test_relone_set_get_and_range(m):
    fan = toy.Fan("f")
    loc = toy.Location("room")
    fan.has_location = loc
    assert fan.has_location is loc
    with pytest.raises(RangeError):
        fan.has_location = toy.Fan("g")  # ty: ignore[invalid-assignment]  # deliberate


def test_literal_type_enforcement(m):
    fan = toy.Fan("f")
    fan.rated_power = 3  # int accepted where float expected
    assert fan.rated_power == 3
    with pytest.raises(RangeError, match="expects float"):
        fan.rated_power = "big"  # ty: ignore[invalid-assignment]  # deliberate
    with pytest.raises(RangeError):
        fan.rated_power = True  # bool is not a number here
