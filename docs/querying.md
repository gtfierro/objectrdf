# Querying existing models

`Model.from_graph()` turns resources in an existing RDF graph into the same
generated Python classes used for authoring:

For graphs saved by objectrdf, `owl:imports` on the model ontology identifies
the generated package. The loader discovers built-in packages, including the
bundled domain configurations (`watr.drinking_water`, `watr.asm2d`,
`watr.seawater_ro`, and `s223.hvac`), and checks the recorded
`owl:versionInfo` against the installed package when available:

```python
from objectrdf import Model

model = Model.from_graph("building.ttl")
for entity in model:
    print(entity.name, entity.type, entity.meta.ontology.version)
```

You can then import a class when you want typed filtering:

```python
from objectrdf.brick import Fan

supply_fan = model.find(Fan, label="Supply fan")
if supply_fan is not None:
    downstream = list(supply_fan.feeds)
```

## Discovering classes and instances

Each generated package exports `REGISTRY`, which lists all its classes without
requiring you to choose one first. A domain package's registry contains both
the extension and its linked base types:

```python
from objectrdf.watr import drinking_water

loaded = Model.from_graph("treatment.ttl", registries=drinking_water.REGISTRY)
for cls in drinking_water.REGISTRY.classes:
    print(cls.__name__, cls.meta.iri)
```

Use the domain registry for graphs containing its configurations;
`objectrdf.watr.REGISTRY` covers the base WaTr vocabulary alone. For graphs
combining independent packages, pass a list of registries as shown below.

Use a class's `.meta` to inspect its direct parents or children, or find every
descendant in a particular branch:

```python
from objectrdf import s223
from objectrdf.s223 import Equipment as S223Equipment
from objectrdf.watr import Equipment as WatrEquipment, Process

all_s223_classes = s223.REGISTRY.classes
direct_equipment_types = S223Equipment.meta.children
all_equipment_types = WatrEquipment.meta.descendants
all_process_types = Process.meta.descendants
print(Process.meta.tree(max_depth=3))

for cls in all_process_types:
    print(cls.__name__, cls.meta.iri)
```

These are Python classes, so `issubclass`, `__mro__`, and `isinstance` work as
usual. `meta.children` (also available as `meta.subclasses`) lists direct
children; `meta.descendants` includes
all depths. Multiple inheritance can give a class more than one direct parent.
The [book catalog](book/reference/catalog.md) lists every S223 and WaTr class.

Classes are exported directly from the package, regardless of hierarchy depth:

```python
from objectrdf.watr import Process_ReverseOsmosis

by_name = Process.meta["ReverseOsmosis"]
by_iri = Process.meta[
    "https://watermetadata.org/ontology/watr#Process-ReverseOsmosis"
]
assert by_name is by_iri is Process_ReverseOsmosis
```

This lookup is scoped to descendants of `Process`; it raises `KeyError` for
unrelated classes. Direct imports remain useful for editor completion and
static typing.

For a loaded or newly authored model, `by_class()` groups current objects by
their **exact** Python class and preserves their order in the model:

```python
inventory = model.by_class()
for cls, objects in inventory.items():
    print(cls.__name__, len(objects), [obj.name for obj in objects])
```

The keys are actual classes, so `inventory.get(Fan, [])` works after importing
`Fan`. Use `find_all(Fan)` when you want fans *and subclasses* of `Fan`.
`by_class()` describes the model's current concrete entities. Deferred ports
and connections appear in a resolved snapshot after `model.resolve()`.

For RDF without a matching `owl:imports` declaration, or for a custom
generated package, pass its registry explicitly. Multiple registries are
accepted:

```python
from objectrdf import brick, s223

model = Model.from_graph(
    graph,
    registries=[
        brick.REGISTRY,
        s223.REGISTRY,
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
from objectrdf import s223

model = Model.from_graph(
    graph,
    registries=s223.REGISTRY,
    infer=True,
    shapes="building-shapes.ttl",
)
```

When `shapes` is omitted, shifty looks for rules in the data graph itself.
Inference is opt-in because it changes the graph being queried.
