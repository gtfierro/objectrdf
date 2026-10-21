"""Finding objects, containment navigation, and topology walks.

The semantics are recorded in ``docs/traversal.md``. In short: a class or
enum value used as a filter matches itself and anything narrower, ``exact()``
opts out, containment follows the registries' containment tables, and
``walk()`` follows the 223 connection vocabulary by predicate IRI so S223 and
WaTr models behave the same.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, cast

from .entity import Entity
from .enums import EnumValue
from .errors import ModelingError
from .relations import EnumValues, RelSet

if TYPE_CHECKING:
    from .model import Model

T = TypeVar("T")

Direction = Literal["downstream", "upstream"]

#: Keyword options of the find and walk methods. A generated property with
#: one of these names can only be filtered through ``attrs=``; the guard in
#: ``tests/test_traversal.py`` keeps the generated packages clear of them.
OPTION_NAMES = frozenset(
    {
        "recursive",
        "limit",
        "through",
        "descend",
        "include_connections",
        "max_hops",
        "direction",
        "attrs",
        "type",
    }
)


@dataclass(frozen=True, slots=True)
class Exact(Generic[T]):
    """A filter value that matches only itself, not anything narrower."""

    value: T

    def __repr__(self) -> str:
        return f"exact({self.value!r})"


def exact(value: T) -> Exact[T]:
    """Match ``value`` itself: the exact class, enum value, or object."""
    return Exact(value)


# -- filters ---------------------------------------------------------------


def type_matches(entity: object, entity_type: object) -> bool:
    """Apply the searched-type argument of a find method to ``entity``."""
    if entity_type is None:
        return isinstance(entity, Entity)
    if isinstance(entity_type, Exact):
        return type(entity) is entity_type.value
    if isinstance(entity_type, tuple):
        return any(type_matches(entity, item) for item in entity_type)
    return isinstance(entity, cast(type, entity_type))


def merge_filters(
    attributes: Mapping[str, object], attrs: Mapping[str, object] | None
) -> Mapping[str, object]:
    """Combine keyword filters with the ``attrs=`` escape hatch."""
    if not attrs:
        return attributes
    overlap = sorted(attributes.keys() & attrs.keys())
    if overlap:
        raise TypeError(f"filter {overlap[0]!r} given both as a keyword and in attrs")
    return {**attributes, **attrs}


def matches(entity: Entity, attributes: Mapping[str, object]) -> bool:
    """Apply BeautifulSoup-style attribute filters to an entity."""
    specs = type(entity)._effective_specs()
    for name, expected in attributes.items():
        actual: Any
        if name == "type":
            if not _type_attribute_matches(entity, expected):
                return False
            continue
        if name == "iri":
            actual = entity.meta.instance_iri
        else:
            try:
                actual = getattr(entity, name)
            except AttributeError:
                return False
        boolean = _is_boolean(specs.get(name)) or isinstance(actual, bool)
        if not value_matches(actual, expected, boolean=boolean):
            return False
    return True


def _type_attribute_matches(entity: Entity, expected: object) -> bool:
    """``type=``: class semantics on the entity's class; strings, regexes, and
    lists of them also match its Python class name."""
    cls = type(entity)
    if callable(expected) and not isinstance(expected, type):
        return value_matches(cls, expected)
    return value_matches(cls, expected) or value_matches(entity.type, expected)


def value_matches(actual: object, expected: object, *, boolean: bool = False) -> bool:
    """Apply one filter value to an attribute's current value."""
    if isinstance(expected, bool) and not boolean:
        if _is_collection(actual):
            return bool(len(cast(Any, actual))) is expected
        return (actual is not None) is expected
    if callable(expected) and not isinstance(expected, type):
        return bool(cast(Callable[[Any], object], expected)(actual))
    if _is_collection(actual):
        return any(_scalar_matches(item, expected) for item in cast(Any, actual))
    return _scalar_matches(actual, expected)


def _scalar_matches(value: object, expected: object) -> bool:
    if isinstance(expected, list):
        return any(_scalar_matches(value, item) for item in expected)
    if isinstance(expected, Exact):
        target = expected.value
        if isinstance(value, EnumValue) and isinstance(target, EnumValue):
            return value.iri == target.iri
        if isinstance(target, type) and not isinstance(value, type):
            return type(value) is target
        return value is target or value == target
    if isinstance(expected, re.Pattern):
        pattern = cast(re.Pattern[str], expected)
        return isinstance(value, str) and pattern.search(value) is not None
    if isinstance(expected, type):
        if isinstance(value, type):
            return issubclass(value, expected)
        return isinstance(value, expected)
    if isinstance(expected, EnumValue):
        return isinstance(value, EnumValue) and value.is_a(expected)
    return value == expected


def _is_collection(value: object) -> bool:
    return isinstance(value, (RelSet, EnumValues, list, tuple, set, frozenset))


def _is_boolean(spec: Any) -> bool:
    return spec is not None and spec.kind == "literal" and spec.datatype is bool


def select(
    candidates: Iterable[Any],
    entity_type: object,
    filters: Mapping[str, object],
    limit: int | None = None,
) -> list[Any]:
    """Candidates of ``entity_type`` matching ``filters``, at most ``limit``."""
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    found: list[Any] = []
    if limit == 0:
        return found
    for candidate in candidates:
        if type_matches(candidate, entity_type) and matches(candidate, filters):
            found.append(candidate)
            if limit is not None and len(found) >= limit:
                break
    return found


# -- per-model indexes -------------------------------------------------------


def _index(model: Model, kind: str, build: Callable[[Model], T]) -> T:
    """A derived index of ``model``, built on first use.

    The cache is a model attribute that ``Model._touch`` replaces on every
    edit, and that an ``_atomic`` rollback restores with the rest of the
    model's state, so a cached index always describes the current entities.
    """
    cache = model._traversal_indexes
    if kind not in cache:
        cache[kind] = build(model)
    return cache[kind]


def _order(model: Model) -> dict[Entity, int]:
    return {entity: index for index, entity in enumerate(model.entities)}


def _related(entity: Entity, prop: str) -> Iterator[Entity]:
    value = getattr(entity, prop, None)
    if isinstance(value, Entity):
        yield value
    elif isinstance(value, RelSet):
        yield from (item for item in value if isinstance(item, Entity))


# -- containment -------------------------------------------------------------


@dataclass
class _Containment:
    children: dict[Entity, list[Entity]] = field(default_factory=dict)
    parents: dict[Entity, list[Entity]] = field(default_factory=dict)


#: One containment rule as seen from the entity that stores the edge: the
#: property to read, the class its values must have, and whether the entity
#: is the container (``True``) or the child.
_Edge = tuple[str, type, bool]


def _build_containment(model: Model) -> _Containment:
    order = _order(model)
    registries: dict[int, Any] = {}
    for entity in model.entities:
        registry = entity.meta.registry
        registries.setdefault(id(registry), registry)
    rules: dict[tuple[type, type, str, str], None] = {}
    for registry in registries.values():
        for rule in registry.containment.rules:
            try:
                container = registry.resolve(rule.container)
                child = registry.resolve(rule.child)
            except KeyError:
                continue
            rules[(container, child, rule.prop, rule.edge_from)] = None

    edges_by_class: dict[type, list[_Edge]] = {}

    def edges(cls: type) -> list[_Edge]:
        found = edges_by_class.get(cls)
        if found is None:
            found = edges_by_class[cls] = [
                (prop, child, True)
                if edge_from == "container"
                else (prop, container, False)
                for container, child, prop, edge_from in rules
                if issubclass(cls, container if edge_from == "container" else child)
            ]
        return found

    children: defaultdict[Entity, dict[Entity, None]] = defaultdict(dict)
    parents: defaultdict[Entity, dict[Entity, None]] = defaultdict(dict)
    for entity in model.entities:
        for prop, other, is_container in edges(type(entity)):
            for value in _related(entity, prop):
                if (
                    value is entity
                    or value not in order
                    or not isinstance(value, other)
                ):
                    continue
                parent, child = (entity, value) if is_container else (value, entity)
                children[parent][child] = None
                parents[child][parent] = None
    return _Containment(
        {key: _sorted(values, order) for key, values in children.items()},
        {key: _sorted(values, order) for key, values in parents.items()},
    )


def _sorted(values: Iterable[Entity], order: Mapping[Entity, int]) -> list[Entity]:
    """Entities in model order; ones outside the model go last."""
    return sorted(values, key=lambda item: order.get(item, len(order)))


def _containment(entity: Entity) -> _Containment:
    return _index(entity.meta.model, "containment", _build_containment)


def contents(entity: Entity) -> tuple[Entity, ...]:
    """Entities directly contained by ``entity``, in model order."""
    return tuple(_containment(entity).children.get(entity, ()))


def descendants(entity: Entity) -> Iterator[Entity]:
    """Everything ``entity`` contains, depth-first, each entity once."""
    children = _containment(entity).children
    seen = {entity}
    stack = list(reversed(children.get(entity, ())))
    while stack:
        item = stack.pop()
        if item in seen:
            continue
        seen.add(item)
        yield item
        stack.extend(reversed(children.get(item, ())))


def container(entity: Entity) -> Entity | None:
    """The single direct container of ``entity``, or ``None``."""
    parents = _containment(entity).parents.get(entity, ())
    if len(parents) > 1:
        names = ", ".join(parent.name for parent in parents)
        raise ModelingError(
            f"{entity.name} has {len(parents)} containers ({names}); "
            f"use containers or find_parents()"
        )
    return parents[0] if parents else None


def containers(entity: Entity) -> Iterator[Entity]:
    """Every container of ``entity``, nearest first, each once."""
    parents = _containment(entity).parents
    seen = {entity}
    frontier = list(parents.get(entity, ()))
    while frontier:
        following: list[Entity] = []
        for item in frontier:
            if item in seen:
                continue
            seen.add(item)
            yield item
            following.extend(parents.get(item, ()))
        frontier = following


# -- topology ----------------------------------------------------------------

_S223 = "http://data.ashrae.org/standard223#"
_HAS_POINT = {_S223 + "hasConnectionPoint", _S223 + "hasOptionalConnectionPoint"}
_POINT_OF = _S223 + "isConnectionPointOf"
_THROUGH = _S223 + "connectsThrough"
_AT = _S223 + "connectsAt"
_MAPS_TO = _S223 + "mapsTo"
_BOUNDARY = _S223 + "hasBoundaryConnectionPoint"
_MEMBER = _S223 + "hasMember"
_POINT_CLASSES = {
    _S223 + "ConnectionPoint": "bi",
    _S223 + "BidirectionalConnectionPoint": "bi",
    _S223 + "InletConnectionPoint": "in",
    _S223 + "OutletConnectionPoint": "out",
}
_EXITS = {"downstream": {"out", "bi"}, "upstream": {"in", "bi"}}
_ENTRIES = {"downstream": {"in", "bi"}, "upstream": {"out", "bi"}}


@dataclass(frozen=True, slots=True)
class Crossing:
    """One step of a walk.

    ``connection`` is the pipe or connection crossed, or ``None`` for a
    ``maps_to`` step into or out of a container. ``exit`` is ``None`` only
    for the first step of a walk that starts on a connection.
    """

    exit: Entity | None
    connection: Entity | None
    entry: Entity


@dataclass(frozen=True, slots=True)
class Hop:
    """An entity reached by a walk, its distance, and the path taken."""

    entity: Entity
    depth: int
    via: tuple[Crossing, ...]


@dataclass
class _Topology:
    order: dict[Entity, int]
    direction: dict[Entity, str] = field(default_factory=dict)
    owner: dict[Entity, Entity] = field(default_factory=dict)
    points: dict[Entity, list[Entity]] = field(default_factory=dict)
    connections: dict[Entity, list[Entity]] = field(default_factory=dict)
    on_connection: dict[Entity, list[Entity]] = field(default_factory=dict)
    maps_to: dict[Entity, list[Entity]] = field(default_factory=dict)
    mapped_from: dict[Entity, list[Entity]] = field(default_factory=dict)
    boundary: dict[Entity, list[Entity]] = field(default_factory=dict)
    boundary_of: dict[Entity, list[Entity]] = field(default_factory=dict)
    direct_members: dict[Entity, list[Entity]] = field(default_factory=dict)
    _members: dict[Entity, frozenset[Entity]] = field(default_factory=dict)

    def members(self, system: Entity) -> frozenset[Entity]:
        """Members of ``system`` at any depth of nested systems."""
        cached = self._members.get(system)
        if cached is None:
            found: set[Entity] = set()
            stack = list(self.direct_members.get(system, ()))
            while stack:
                item = stack.pop()
                if item not in found:
                    found.add(item)
                    stack.extend(self.direct_members.get(item, ()))
            cached = self._members[system] = frozenset(found)
        return cached


def _point_direction(entity: Entity) -> str | None:
    found: str | None = None
    for klass in type(entity).__mro__:
        info = klass.__dict__.get("_classinfo")
        if info is None:
            continue
        direction = _POINT_CLASSES.get(info.iri)
        if direction is not None and direction != "bi":
            return direction
        found = found or direction
    return found


def _build_topology(model: Model) -> _Topology:
    order = _order(model)
    topology = _Topology(order)
    links: defaultdict[str, defaultdict[Entity, dict[Entity, None]]] = defaultdict(
        lambda: defaultdict(dict)
    )

    def add(kind: str, key: Entity, value: Entity) -> None:
        links[kind][key][value] = None

    for entity in model.entities:
        direction = _point_direction(entity)
        if direction is not None:
            topology.direction[entity] = direction
        for spec, value in entity._property_values():
            if not isinstance(value, Entity):
                continue
            predicate = spec.predicate
            if predicate in _HAS_POINT:
                topology.owner.setdefault(value, entity)
                add("points", entity, value)
            elif predicate == _POINT_OF:
                topology.owner.setdefault(entity, value)
                add("points", value, entity)
            elif predicate == _THROUGH:
                add("connections", entity, value)
                add("on_connection", value, entity)
            elif predicate == _AT:
                add("on_connection", entity, value)
                add("connections", value, entity)
            elif predicate == _MAPS_TO:
                add("maps_to", entity, value)
                add("mapped_from", value, entity)
            elif predicate == _BOUNDARY:
                add("boundary", entity, value)
                add("boundary_of", value, entity)
            elif predicate == _MEMBER:
                add("direct_members", entity, value)
    for kind, mapping in links.items():
        setattr(
            topology,
            kind,
            {key: _sorted(values, order) for key, values in mapping.items()},
        )
    return topology


def walk(
    start: Entity,
    direction: Direction = "downstream",
    *,
    through: Mapping[str, object] | Callable[[Crossing], object] | None = None,
    descend: bool = False,
    include_connections: bool = False,
    max_hops: int | None = None,
) -> Iterator[Hop]:
    """Breadth-first walk of the connection graph from ``start``."""
    if direction not in _EXITS:
        raise ValueError("direction must be 'downstream' or 'upstream'")
    if max_hops is not None and max_hops < 0:
        raise ValueError("max_hops must be non-negative")
    model = start.meta.model
    if not model._frozen and (model._connection_intents or model._port_intents):
        raise ModelingError(
            "this model has connections that are not resolved yet; walk the "
            "resolved snapshot instead: model.resolve()[name].walk(...)"
        )
    return _Walk(
        _index(model, "topology", _build_topology),
        direction,
        through,
        descend=descend,
        include_connections=include_connections,
        max_hops=max_hops,
    ).run(start)


#: A pending step: ("exit", point) leaves through a point; ("enter", point,
#: inner) steps through ``maps_to`` from a container point to an inner one.
_Step = tuple[str, Entity, Entity | None, tuple[Crossing, ...]]


class _Walk:
    def __init__(
        self,
        topology: _Topology,
        direction: Direction,
        through: Mapping[str, object] | Callable[[Crossing], object] | None,
        *,
        descend: bool,
        include_connections: bool,
        max_hops: int | None,
    ) -> None:
        self.topology = topology
        self.exits = _EXITS[direction]
        self.entries = _ENTRIES[direction]
        self.filters: Mapping[str, object] | None = None
        self.predicate: Callable[[Crossing], object] | None = None
        if isinstance(through, Mapping):
            self.filters = cast(Mapping[str, object], through)
        else:
            self.predicate = through
        self.descend = descend
        self.include_connections = include_connections
        self.max_hops = max_hops
        self.left: set[Entity] = set()
        self.entered: set[Entity] = set()
        self.reached: set[Entity] = set()

    def run(self, start: Entity) -> Iterator[Hop]:
        if self.max_hops == 0:
            return
        topology = self.topology
        self.reached.add(start)
        steps: list[_Step] = []
        hops: list[Hop] = []
        if start in topology.direction:
            if topology.direction[start] in self.exits:
                steps.append(("exit", start, None, ()))
            else:
                self.entered.add(start)
                steps.extend(self._through(start, ()))
        elif start in topology.on_connection:
            for point in topology.on_connection[start]:
                if topology.direction.get(point) in self.entries:
                    self._cross(Crossing(None, start, point), (), 1, hops, steps)
        else:
            points = topology.boundary.get(start) or topology.points.get(start, ())
            steps.extend(
                ("exit", point, None, ())
                for point in points
                if topology.direction.get(point) in self.exits
            )
        depth = 1
        if hops:
            yield from self._ordered(hops)
            depth = 2
        while steps and (self.max_hops is None or depth <= self.max_hops):
            hops = []
            following: list[_Step] = []
            for kind, point, inner, via in sorted(
                steps, key=lambda step: topology.order.get(step[2] or step[1], 0)
            ):
                if kind == "exit":
                    if point in self.left:
                        continue
                    self.left.add(point)
                    self._leave(point, via, depth, hops, following)
                elif inner is not None:
                    self._cross(
                        Crossing(point, None, inner), via, depth, hops, following
                    )
            yield from self._ordered(hops)
            steps = following
            depth += 1

    def _ordered(self, hops: list[Hop]) -> list[Hop]:
        order = self.topology.order
        return sorted(hops, key=lambda hop: order.get(hop.entity, len(order)))

    def _allowed(self, crossing: Crossing) -> bool:
        if self.predicate is not None:
            return bool(self.predicate(crossing))
        if self.filters is None or crossing.connection is None:
            return True
        return matches(crossing.connection, self.filters)

    def _leave(
        self,
        point: Entity,
        via: tuple[Crossing, ...],
        depth: int,
        hops: list[Hop],
        following: list[_Step],
    ) -> None:
        topology = self.topology
        for connection in topology.connections.get(point, ()):
            for other in topology.on_connection.get(connection, ()):
                if other is point or topology.direction.get(other) not in self.entries:
                    continue
                self._cross(
                    Crossing(point, connection, other), via, depth, hops, following
                )
        for outer in topology.maps_to.get(point, ()):
            crossing = Crossing(point, None, outer)
            if self._allowed(crossing):
                following.append(("exit", outer, None, via + (crossing,)))

    def _cross(
        self,
        crossing: Crossing,
        via: tuple[Crossing, ...],
        depth: int,
        hops: list[Hop],
        following: list[_Step],
    ) -> None:
        if not self._allowed(crossing):
            return
        path = via + (crossing,)
        connection = crossing.connection
        if (
            self.include_connections
            and connection is not None
            and connection not in self.reached
        ):
            self.reached.add(connection)
            hops.append(Hop(connection, depth, path))
        point = crossing.entry
        if point in self.entered:
            return
        self.entered.add(point)
        topology = self.topology
        owner = topology.owner.get(point)
        if owner is not None:
            self._reach(owner, depth, path, hops)
        previous = topology.owner.get(crossing.exit) if crossing.exit else None
        for system in topology.boundary_of.get(point, ()):
            if previous is None or previous not in topology.members(system):
                self._reach(system, depth, path, hops)
        following.extend(self._through(point, path))

    def _reach(
        self, entity: Entity, depth: int, path: tuple[Crossing, ...], hops: list[Hop]
    ) -> None:
        if entity not in self.reached:
            self.reached.add(entity)
            hops.append(Hop(entity, depth, path))

    def _through(self, point: Entity, path: tuple[Crossing, ...]) -> list[_Step]:
        """Continue from an entry point: past its owner, and with ``descend``
        also into the container through the points mapped to it.

        Passing through even when descending keeps ``descend=True`` a strict
        superset of ``descend=False``, at the same depths, however complete
        the container's internal model is.
        """
        topology = self.topology
        steps: list[_Step] = []
        if self.descend:
            steps.extend(
                ("enter", point, item, path)
                for item in topology.mapped_from.get(point, ())
            )
        owner = topology.owner.get(point)
        if owner is not None:
            steps.extend(
                ("exit", other, None, path)
                for other in topology.points.get(owner, ())
                if other is not point and topology.direction.get(other) in self.exits
            )
        return steps


def find_along(
    start: Entity,
    direction: Direction,
    entity_type: object,
    filters: Mapping[str, object],
    *,
    limit: int | None,
    **options: Any,
) -> list[Entity]:
    """Results of a walk that match a type and filters, nearest first."""
    hops = walk(start, direction, **options)
    return select((hop.entity for hop in hops), entity_type, filters, limit)
