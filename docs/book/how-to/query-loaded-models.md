---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Query and edit saved models

`Model.from_graph()` loads RDF as typed Python objects. Find them by class,
follow their relations, edit them, and save the result.

## Load a model

Save a small model to load:

```{code-cell} python3
from plumb import Model, connect
from plumb.watr.drinking_water import (
    ClarificationStage,
    CoagulationStage,
    RapidSandFiltrationStage,
)
from plumb.watr import Pump

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

The file's `owl:imports` names the packages it needs:

```{code-cell} python3
model = Model.from_graph("plant.ttl")
len(model)
```

`by_class()` groups objects by exact class:

```{code-cell} python3
model.by_class()
```

Points and pipes load as ordinary objects, not as `connect()` calls.

## Find objects

`find_all()` includes subclasses. A `ClarificationStage` is a
`SedimentationTank`:

```{code-cell} python3
from plumb.watr import SedimentationTank

model.find_all(SedimentationTank)
```

Keyword filters match attributes by equality, collection membership, or a
function:

```{code-cell} python3
from plumb.watr import Pipe, enums

model.find(Pump, label="Intake pump"), model.find_all(Pipe, medium=enums.values.Fluid_Water)
```

`find()` returns the first match or `None`. Item lookup takes a local name or
an IRI:

```{code-cell} python3
model["clarifier"] is model["urn:example:plant#clarifier"]
```

To find a class to search for, see [Find classes and values](find-classes-and-values.md).

## Follow relations

Traversal is attribute access:

```{code-cell} python3
clarifier = model["clarifier"]
list(clarifier.has_connection_point)
```

```{code-cell} python3
pipe = model["clarified-water"]
for point in pipe.connects_at:
    print(point.owner.name, point.label)
```

Or query the RDF with SPARQL:

```{code-cell} python3
rows = model.graph().query(
    "SELECT ?pump WHERE { ?pump a <https://watermetadata.org/ontology/watr#Pump> }"
)
for row in rows:
    print(row.pump)
```

`model.graph()` returns a copy; updating it does not change the model.

## Edit and save

Edits write through to the graph:

```{code-cell} python3
from plumb.watr import Tank

clarifier.label = "Clarifier 1"
clarifier.has_role.add(enums.values.Role_Primary)
with model:
    Tank("sludge-tank")
model.save("plant-updated.ttl")
```

Only triples behind generated attributes change; unknown triples stay. A
graph passed to `from_graph()` is updated in place. Edits made through rdflib
after loading are not seen by the objects.

`connect()` and `model.system()` do not work on a loaded model. Edit the
concrete pipes and points instead:

```{code-cell} python3
try:
    connect(model["intake-pump"], model["sludge-tank"])
except Exception as error:
    print(type(error).__name__, error)
```

## Which packages load

`from_graph()` matches the graph's `owl:imports` against the installed
packages: Brick, S223, WaTr, QUDT, and the bundled domain packages
(`watr.drinking_water`, `watr.asm2d`, `watr.seawater_ro`, `s223.hvac`).
Versions must match.

For RDF without imports, or a package you compiled, pass registries. A domain
registry includes its base classes:

```python
from plumb import brick, s223

model = Model.from_graph("building.ttl", registries=[brick.REGISTRY, s223.REGISTRY])
```

Resources of unknown classes stay in the graph but are not loaded. A relation
to one raises an error naming the missing registry; `strict=False` skips it.

## Load with inference

`infer=True` runs the packages' SHACL-AF rules before loading. Pass
`shapes=` for other rules:

```python
model = Model.from_graph("plant.ttl", infer=True)
```

Inference is off by default because it changes the graph.
