---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Query and edit saved models

`Model.from_graph()` loads RDF as the same typed Python objects you author
with. You can then find objects by class, follow their relations, edit them,
and save the result.

## Load a model

First save a small treatment model to load:

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr.drinking_water import (
    ClarificationStage,
    CoagulationStage,
    RapidSandFiltrationStage,
)
from objectrdf.watr import Pump

with Model("urn:example:plant#") as authored:
    intake = Pump("intake-pump", label="Intake pump")
    coagulation = CoagulationStage("coagulation")
    clarifier = ClarificationStage("clarifier")
    sand_filter = RapidSandFiltrationStage("sand-filter")
connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, clarifier.inlet, name="coagulated-water")
connect(clarifier.clarified_water, sand_filter.inlet, name="clarified-water")
authored.save("plant.ttl")
```

The saved graph's `owl:imports` names the packages it needs, so loading takes
just the file:

```{code-cell} python3
model = Model.from_graph("plant.ttl")
len(model)
```

`by_class()` groups the objects by their exact class:

```{code-cell} python3
for cls, objects in model.by_class().items():
    print(cls.__name__, [obj.name for obj in objects])
```

Loading reads the saved points and pipes as ordinary objects: the resolved
graph, not the `connect()` calls that produced it.

## Find objects

`find_all()` includes subclasses. The clarifier was saved as a drinking-water
`ClarificationStage`, and it is also a WaTr `SedimentationTank`:

```{code-cell} python3
from objectrdf.watr import SedimentationTank

model.find_all(SedimentationTank)
```

Keyword filters use attribute names. A value matches by equality, by
membership for collections, or through a function:

```{code-cell} python3
from objectrdf.watr import Pipe, enums

model.find(Pump, label="Intake pump"), model.find_all(Pipe, medium=enums.values.Fluid_Water)
```

`find()` returns the first match or `None`. Item lookup takes a local name or
a full IRI:

```{code-cell} python3
model["clarifier"] is model["urn:example:plant#clarifier"]
```

## Follow relations

From there, traversal is attribute access:

```{code-cell} python3
clarifier = model["clarifier"]
for point in clarifier.has_connection_point:
    pipe = point.connection
    print(point.name, point.medium.label, pipe.name if pipe else "-")
```

```{code-cell} python3
pipe = model["clarified-water"]
[point.owner.name for point in pipe.connects_at]
```

For graph-shaped questions that read better in SPARQL, query the RDF:

```{code-cell} python3
rows = model.graph().query(
    "SELECT ?pump WHERE { ?pump a <https://watermetadata.org/ontology/watr#Pump> }"
)
[str(row.pump) for row in rows]
```

`model.graph()` returns a copy, so a SPARQL update on it does not change the
model.

## Discover classes

You do not need to know the class names in advance. Each class's `.meta`
navigates the hierarchy:

```{code-cell} python3
from objectrdf.watr import Process

print(Process.meta.tree(max_depth=2))
```

`meta.children` lists direct subclasses, `meta.descendants` all of them, and
`meta[name_or_iri]` finds one within the branch:

```{code-cell} python3
Process.meta["Settling"], len(Process.meta.descendants)
```

Each package's `REGISTRY.classes` lists every class it defines, and the
[class catalog](../reference/catalog.md) lists every S223 and WaTr class. These
are Python classes, so `issubclass` and `isinstance` work as usual.

## Edit and save

Edits to a loaded object write through to its RDF graph:

```{code-cell} python3
from objectrdf.watr import Tank

clarifier.label = "Clarifier 1"
clarifier.has_role.add(enums.values.Role_Primary)
with model:
    Tank("sludge-tank")
model.save("plant-updated.ttl")
```

Only the triples behind generated attributes are replaced. Classes,
predicates, and values the package does not know about stay in the graph
untouched. If you pass an `rdflib.Graph` to `from_graph()`, that graph is
updated in place.

`connect()` and `model.system()` do not work on a loaded model yet, because
there is no solver step to place them. Edit the concrete pipes and points
instead:

```{code-cell} python3
try:
    connect(model["intake-pump"], model["sludge-tank"])
except Exception as error:
    print(type(error).__name__, error)
```

Changes made directly through rdflib after loading are not reflected in the
objects.

## Which packages load

`from_graph()` reads the graph's `owl:imports` and picks the installed
packages that match: Brick, S223, WaTr, QUDT, and the bundled domain packages
(`watr.drinking_water`, `watr.asm2d`, `watr.seawater_ro`, and `s223.hvac`).
When a package records a version, the version in the graph must match the
installed one.

For RDF without those imports, or for a package you compiled yourself, pass
the registries. A domain package's registry includes its base classes:

```python
from objectrdf import brick, s223

model = Model.from_graph("building.ttl", registries=[brick.REGISTRY, s223.REGISTRY])
```

RDF classes from none of the packages stay in the graph without becoming
Python objects. By default, a relation that points at such a resource raises
an error that names the missing registry. `strict=False` skips those values
instead.

## Load with inference

`infer=True` runs SHACL-AF rules before the objects are built. The rules come
from the selected packages' bundled shapes unless you pass `shapes=`:

```python
model = Model.from_graph("plant.ttl", infer=True)
```

Inference is off by default because it changes the graph you are querying.
