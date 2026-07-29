# Querying existing models

`Model.from_graph()` turns resources in an existing RDF graph into the same
generated Python classes used for authoring:

```python
from objectrdf import Model
from objectrdf.brick import Equipment, Fan

model = Model.from_graph(
    "building.ttl",
    registries=Equipment.meta.registry,
)

supply_fan = model.find(Fan, label="Supply fan")
if supply_fan is not None:
    downstream = list(supply_fan.feeds)
```

Pass one registry for each generated ontology package represented in the data:

```python
from objectrdf.brick import Equipment as BrickEquipment
from objectrdf.s223 import Equipment as S223Equipment

model = Model.from_graph(
    graph,
    registries=[
        BrickEquipment.meta.registry,
        S223Equipment.meta.registry,
    ],
)
```

Unknown RDF classes remain in `model.graph()` but are not exposed as Python
objects. In strict mode (the default), an object property pointing to a
resource whose generated type is unavailable raises an error suggesting that
its registry be included.

## Selection and traversal

`find_all()` includes instances of subclasses and returns a normal list.
`find()` returns the first match or `None`. Keyword filters use generated
attribute names:

```python
fans = model.find_all(Fan)
large_fans = model.find_all(
    Fan,
    weight=lambda value: value is not None and value > 100,
)
feeding_vav = model.find(Fan, feeds=model["vav-101"])
```

For a multi-valued relationship such as `feeds`, a filter checks membership.
After selection, traversal uses ordinary typed attributes and Python
collections. Full instance IRIs and collision-free local names both work with
item lookup:

```python
fan = model["supply-fan"]
same_fan = model["urn:example#supply-fan"]
points = list(fan.has_point)
```

## Editing

Loaded objects use the normal generated descriptors, so changes write through
to the backing RDF graph:

```python
from objectrdf.brick import VAV

fan.label = "Retrofitted supply fan"
fan.feeds.remove(model["old-vav"])

new_vav = VAV("new-vav", model=model)
fan.feeds.add(new_vav)

model.save("building-updated.ttl")
```

Objectrdf replaces only the triples represented by generated attributes.
Unknown classes, predicates, and values skipped with `strict=False` remain
untouched. When `from_graph()` receives an `rdflib.Graph`, that same graph is
updated in place; `model.graph()` returns a copy suitable for SPARQL or other
escape-hatch reads. For file inputs, the model owns the parsed graph and
`save()` writes the result.

Graph-to-object synchronization happens during `from_graph()`; subsequent
direct edits made through rdflib are not automatically reflected back into
already hydrated objects.

Deferred S223/WaTr connection and system intentions are not accepted on a
graph-backed model yet. Existing concrete `Connection`, `ConnectionPoint`,
and `System` objects and their generated relationships are editable normally.
This avoids silently treating a solver intention as though it had already
been committed to the backing graph.

For graph-shaped queries that are clearer in SPARQL, use the preserved RDF
graph directly:

```python
rows = model.graph().query("SELECT ?x WHERE { ?x a <urn:example#MyType> }")
```

## Inference

Pass `infer=True` to run shifty's SHACL-AF forward-chaining rules before
objects and relationships are hydrated:

```python
model = Model.from_graph(
    graph,
    registries=Equipment.meta.registry,
    infer=True,
    shapes="building-shapes.ttl",
)
```

When `shapes` is omitted, shifty looks for rules in the data graph itself.
Inference is opt-in because it changes the graph being queried.
