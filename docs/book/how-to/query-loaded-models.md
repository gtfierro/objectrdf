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
from plumb.watr import PhysicalSpace, Pump, Tank

with Model("urn:example:plant#") as authored:
    with PhysicalSpace("treatment-building"):
        intake = Pump("intake-pump", label="Intake pump")
        coagulation = CoagulationStage("coagulation")
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("sand-filter")
    holding = Tank("sludge-holding")
connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, clarifier.inlet, name="coagulated-water")
connect(clarifier.clarified_water, sand_filter.inlet, name="clarified-water")
connect(clarifier.sludge, holding, name="sludge-line")
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

A class or enum value also matches anything narrower, so `Fluid_Water`
matches seawater and hot water too. Wrap a value in `exact()` to match only
that value. Lists mean any of, compiled regexes search strings, and
`True`/`False` test whether an attribute has a value:

```{code-cell} python3
import re
from plumb import exact

(
    len(model.find_all(Pipe, medium=enums.values.Fluid_Water)),
    model.find_all(Pipe, medium=exact(enums.values.Fluid_Sludge)),
    model.find_all(Pump, label=re.compile("^Intake")),
)
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

## Search inside and above an object

Containment comes from the package's containment rules, whichever side
stores the edge. Here each stage records `has_physical_location`, and the
building still lists them as its contents:

```{code-cell} python3
building = model["treatment-building"]
building.contents
```

An entity's `find_all()` searches what it contains, at any depth unless
`recursive=False`. `find_parent()` searches upward:

```{code-cell} python3
building.find_all(SedimentationTank), model["clarifier"].find_parent(PhysicalSpace)
```

`container` is the one direct container (or `None`); `containers` and
`find_parents()` go all the way up.

## Follow the flow

`find_next()` and `find_all_next()` follow connections downstream,
nearest first; `find_previous()` and `find_all_previous()` go upstream.
Pipes and connection points are stepped over:

```{code-cell} python3
model["intake-pump"].find_all_next()
```

```{code-cell} python3
model["sand-filter"].find_previous(Pump)
```

Keyword filters select the results. `through=` restricts the path instead:
here only pipes carrying water, or anything narrower, are followed, so the
sludge branch is left out:

```{code-cell} python3
model["intake-pump"].find_all_next(through={"medium": enums.values.Fluid_Water})
```

`walk()` yields each step with its distance and the path taken:

```{code-cell} python3
for hop in model["intake-pump"].walk():
    print(hop.depth, hop.entity.name, [step.connection.name for step in hop.via])
```

Equipment is a single node unless `descend=True`, which steps into
containers through their `maps_to` points. `include_connections=True` also
returns pipes. Bidirectional points are crossed in either direction. A model
authored with `connect()` walks only after resolution:
`model.resolve()["intake-pump"].find_all_next()`.

## Query with SPARQL

`model.graph()` returns the RDF for SPARQL queries:

```{code-cell} python3
rows = model.graph().query(
    "SELECT ?pump WHERE { ?pump a <https://watermetadata.org/ontology/watr#Pump> }"
)
for row in rows:
    print(row.pump)
```

The graph is a copy; updating it does not change the model.

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
