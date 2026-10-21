---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Find objects in a model

Find objects by class and attribute, search what contains what, and follow
the flow from one piece of equipment to the next. The same methods work on an
authored model, a resolved snapshot, and a [loaded model](save-and-load.md).
To find a class to search for, see
[Find classes and values](find-classes-and-values.md).

## Build a model to search

A treatment train in a building, with a sludge branch off the clarifier:

```{code-cell} python3
from plumb import Model, connect
from plumb.watr import PhysicalSpace, Pump, Tank
from plumb.watr.drinking_water import (
    ClarificationStage,
    CoagulationStage,
    RapidSandFiltrationStage,
)

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

model = authored.resolve()
```

The resolved snapshot has the pipes and connection points the solver chose,
so everything below can be searched.

## Find by class and attribute

`find_all()` includes subclasses. A `ClarificationStage` is a
`SedimentationTank`:

```{code-cell} python3
from plumb.watr import SedimentationTank

model.find_all(SedimentationTank)
```

Keyword filters match attributes by equality or collection membership.
`find()` returns the first match or `None`:

```{code-cell} python3
from plumb.watr import Pipe, enums

model.find(Pump, label="Intake pump"), model.find_all(Pipe, medium=enums.values.Fluid_Sludge)
```

A class or enum value also matches anything narrower. Water and sludge are
both kinds of fluid, so filtering on `Mix_Fluid` finds every pipe. Wrap a
value in `exact()` to match only that value:

```{code-cell} python3
from plumb import exact

fluid = enums.values.Mix_Fluid
len(model.find_all(Pipe, medium=fluid)), model.find_all(Pipe, medium=exact(fluid))
```

Other filter values:

| Filter | Matches |
| --- | --- |
| `medium=[water, sludge]` | any of the values |
| `label=re.compile("^Intake")` | a regex search on strings |
| `has_role=True` / `False` | the attribute has a value / has none |
| `label=lambda s: "pump" in s` | the function returns true |
| `has_member=Pump` | a related object of that class |
| `type=Pipe`, `type="Pipe"` | the object's own class |

A tuple searches for several classes, `find_all((Pump, Tank))`, and
`limit=` stops early. `attrs={"name": value}` passes a filter whose name
clashes with an option such as `limit`.

Item lookup takes a local name or an IRI:

```{code-cell} python3
model["clarifier"] is model["urn:example:plant#clarifier"]
```

## Follow relations

Attributes lead to related objects:

```{code-cell} python3
pipe = model["clarified-water"]
for point in pipe.connects_at:
    print(point.owner.name, point.label)
```

## Search inside and above an object

Containment follows the package's containment rules, whichever side stores
the edge. Here each stage records `has_physical_location`, and the building
lists them as its contents:

```{code-cell} python3
building = model["treatment-building"]
building.contents
```

An object's `find_all()` searches what it contains, at any depth unless
`recursive=False`. `find_parent()` searches upward:

```{code-cell} python3
building.find_all(SedimentationTank), model["clarifier"].find_parent(PhysicalSpace)
```

`container` is the one direct container, or `None`. `containers` and
`find_parents()` go all the way up.

## Follow the flow

`find_next()` and `find_all_next()` follow connections downstream, nearest
first; `find_previous()` and `find_all_previous()` go upstream. Pipes and
connection points are stepped over:

```{code-cell} python3
model["intake-pump"].find_all_next()
```

```{code-cell} python3
model["sand-filter"].find_previous(Pump)
```

Keyword filters select the results. `through=` restricts the path instead:
only pipes carrying water, or anything narrower, are followed, so the
sludge branch is left out:

```{code-cell} python3
model["intake-pump"].find_all_next(through={"medium": enums.values.Fluid_Water})
```

`walk()` yields each step with its distance and the path taken:

```{code-cell} python3
for hop in model["intake-pump"].walk():
    print(hop.depth, hop.entity.name, [step.connection.name for step in hop.via])
```

| Option | Effect |
| --- | --- |
| `through={"type": Pipe}` | follow only these connections |
| `through=lambda crossing: ...` | decide per step |
| `descend=True` | also step into containers through `maps_to` points |
| `include_connections=True` | return pipes too |
| `max_hops=2` | stop after two steps |

Bidirectional points are crossed in either direction.
[An S223 air path](../tutorials/s223-air-path.md) shows `descend=True`.

## Where walks work

Walks follow concrete pipes and points. A resolved snapshot and a loaded
model have them. An authored model with `connect()` calls does not, so
walking it raises and names the fix:

```{code-cell} python3
try:
    authored["intake-pump"].find_all_next()
except Exception as error:
    print(type(error).__name__, error)
```

`find_all()` and containment searches work on authored models too.

## Query with SPARQL

For anything else, query the RDF. `graph()` returns a copy of it:

```{code-cell} python3
rows = model.graph().query(
    "SELECT ?pump WHERE { ?pump a <https://watermetadata.org/ontology/watr#Pump> }"
)
for row in rows:
    print(row.pump)
```
