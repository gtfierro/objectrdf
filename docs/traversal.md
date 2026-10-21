# Traversal API

How objects in a model are found and how the model is walked. The API borrows
BeautifulSoup's shape (`find`, `find_all`, `find_parent`, `find_next`, ...)
but not its tree assumptions: plumb models are graphs. Containment gives a
tree-like view; connections give a directed flow graph, and the two are walked
by separate methods.

User-facing documentation is in
[Query and edit saved models](book/how-to/query-loaded-models.md). This page
records the semantics and the decisions behind them.

## One matching rule

Everything that names a type or a value matches itself **and anything
narrower**:

| Where | Given | Matches when |
|---|---|---|
| searched type (positional) | a class | `isinstance(entity, cls)` |
| searched type | a tuple of classes | any of them matches |
| `object` property filter | a class | some related entity is an instance |
| `class` property filter | a class | the value is a subclass |
| `enum` property filter | an `EnumValue` | the value `is_a` it |
| `type` pseudo-attribute | a class | `issubclass(type(entity), cls)` |

`exact(value)` opts out per value: identity or equality only, and for classes
the exact class. It is a wrapper rather than an `exact=True` flag so that it
can be mixed inside one query (`medium=[exact(Fluid_Water), Fluid_Air]`) and
because every keyword option risks shadowing a generated attribute name (see
[Reserved names](#reserved-names)).

Mixture media are not narrower than their constituents under `is_a`; use a
callable such as `lambda m: m.compatible_with(Fluid_Water)` for that.

## Filter values

Keyword filters (`**attributes`) are applied to each candidate with
`plumb.core.query.matches`. A filter value may be:

- a plain value: equality (`label="Intake pump"`);
- a class or `EnumValue`: the narrowing rule above;
- `exact(value)`: identity or equality; `exact(cls)` against a related
  entity means that entity's class is exactly `cls`;
- a list: any of its items matches (items may be any filter value except a
  list or callable);
- a compiled `re.Pattern`: `pattern.search(value)` on `str` values; other
  values never match;
- `True` / `False`: the attribute has a value / has none (non-empty
  collection, not `None`). On `xsd:boolean` literal properties, and whenever
  the attribute currently holds a `bool`, booleans are compared as values
  instead;
- a callable (not a class): called with the attribute's current value.

On a multi-valued attribute (`RelSet`, `EnumValues`, tuples, lists, sets),
value, class, enum, `exact` and regex filters match when **some member**
matches; `True`/`False` test emptiness; callables receive the whole
collection, as before.

`iri` and `type` are pseudo-attributes. `iri` compares the instance IRI;
`type` applies class semantics to the entity's own class; strings, regexes,
and lists of them also match `Entity.type`, the Python class name
(`type=["Duct", "Pipe"]`, `type=re.compile("Coil$")`).

`attrs={"name": filter}` passes filters whose names collide with a method's
own keyword options, as in BeautifulSoup.

## Containment

Containment is whatever the registry's `ContainmentTable` says, read in the
container → child direction regardless of which side stores the edge
(`edge_from="container"` rules such as `contains_`, `edge_from="child"` rules
such as `has_physical_location`). Connection points and pipes are not
containment; they are reached through attributes or the topology walk.

```python
ahu.contents          # direct children, model order
ahu.descendants       # depth-first, deduplicated, cycle-safe
damper.container      # the one direct container, None, or ModelingError if several
damper.containers     # all ancestors, nearest first (breadth-first)

ahu.find_all(Damper, recursive=True, limit=None, **filters)
ahu.find(Damper, **filters)
damper.find_parent(AirHandlingUnit, **filters)
damper.find_parents(System, **filters)
```

The rules of every registry used in the model are consulted, so mixed Brick
and S223 models work. The index is built on first use and kept on the model;
`Model._touch`, which every authored or write-through edit calls, drops it,
and an `_atomic` rollback restores the index that matched the restored
state.

## Topology

### Primitive

```python
entity.walk(
    direction="downstream",       # or "upstream"
    *,
    through=None,                 # Mapping[str, Filter] | Callable[[Crossing], object]
    descend=False,
    include_connections=False,
    max_hops=None,
) -> Iterator[Hop]
```

`Hop(entity, depth, via)` records what was reached, its BFS distance, and the
`Crossing(exit, connection, entry)` steps taken. `connection` is `None` for a
`maps_to` step.

BeautifulSoup-shaped wrappers sit on `walk()`:

```python
find_next / find_all_next          # direction="downstream"
find_previous / find_all_previous  # direction="upstream"
```

They take `(entity_type=None, /, *, through, descend, include_connections,
max_hops, limit, attrs, **filters)`. Keyword filters apply to **results**;
`through` applies to **the path**.

### Graph

The walk reads the 223 vocabulary by predicate IRI, so S223 and WaTr (which
reuses those predicates) behave the same:

- `hasConnectionPoint` / `isConnectionPointOf`: point ownership;
- `connectsThrough` / `connectsAt`: point–connection incidence;
- `mapsTo`: an internal point standing for its container's point;
- `hasBoundaryConnectionPoint`, `hasMember`: system boundaries and membership.

Both directions of each inverse pair are indexed, so a graph that states only
one side still walks. Point direction comes from the point's class:
inlets are entries downstream and exits upstream, outlets the reverse, and
`BidirectionalConnectionPoint` (or a point of no specific direction) is both,
in either walk direction. In loops or runs of bidirectional points the
downstream and upstream result sets can overlap; a visited set on points keeps
the walk finite.

### Steps

From a node, the walk leaves through its *exit* points. From an exit point
`p`:

1. through `p`'s connection `c` to every other point `q` on `c` that is an
   *entry* for this direction, arriving at `q`'s owner;
2. if `p` `maps_to` a container point `P`, to `P`, which then counts as an
   exit point of the container. Leaving a container this way happens even
   with `descend=False`: a walk that starts inside a box has to get out.

Arriving at `q` on equipment `Y`:

- `Y` is yielded;
- the walk continues from all of `Y`'s other exit points, as if `Y` were a
  single node;
- with `descend=True` it also continues from the internal points that map to
  `q` (their owners are yielded one crossing deeper).

Because descending only adds steps, `descend=True` finds everything
`descend=False` finds, at the same depths, however incomplete a container's
internal model is. Internal paths that rejoin the outside through `maps_to`
reach places already visited by passing through, so they add internal
equipment but never move outside results deeper.

Systems are an overlay, not part of the physical path. The walk always goes
through their members; a system is yielded when the walk arrives at one of its
boundary points from equipment outside it.

### `through=`

A crossing that fails `through` is pruned: the walk does not continue past it.
The mapping form uses the filter vocabulary above and is checked against the
crossing's connection (the pipe carries the medium); `maps_to` crossings
always pass. The callable form receives the whole `Crossing`.

```python
intake.find_all_next(Tank, through={"medium": Fluid_Water})
intake.walk(through={"type": Pipe, "medium": Fluid_Water})
```

### Results and order

The start entity is never yielded. Connections are yielded only with
`include_connections=True`, at the depth of the crossing that uses them.
Results are ordered by BFS depth (crossings, including `maps_to` steps), then
by model insertion order. Loaded models are created in sorted-IRI order, so an
authored model and its reloaded copy may order ties differently.

`max_hops` bounds depth. `limit` stops after that many results.

### Authored models

Connections authored with `connect()` or `>>` stay intentions until
resolution, so walking an authored model with pending intentions raises
`ModelingError`. Walk the resolved snapshot instead:

```python
snapshot = model.resolve()
snapshot["intake-pump"].find_all_next(Tank)
```

## Reserved names

New `Entity` methods are added to the generator's `naming.RESERVED`, so a
future ontology property with the same name is generated with a trailing `_`.

Keyword options cannot be renamed that way, because they are shared with the
attribute filters. `tests/test_traversal.py` fails if any generated property
name equals `recursive`, `limit`, `through`, `descend`,
`include_connections`, `max_hops`, `direction`, `attrs`, or `type`. On such a
failure, rename the option; until then, `attrs=` reaches the attribute.
`max_depth` was rejected for this reason: WaTr's `BalancedTree` has a
`max_depth` property.
