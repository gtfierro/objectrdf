---
file_format: mystnb
kernelspec:
  name: python3
---

# Connect equipment

`connect(a, b)` records that flow goes from `a` to `b`. You do not create
pipes or connection points. When the model resolves, the solver picks the
points, the medium, and the connection class. See
[How connections are resolved](../explanation/connection-resolution.md).

## Read a class's port requirements

`describe_ports()` lists the connection points a class requires: direction,
count, and allowed media.

```{code-cell} python3
from plumb import Model, connect
from plumb.watr import GravityThickener, Pump, enums
from plumb.watr.drinking_water import ClarificationStage, RapidSandFiltrationStage

values = enums.values
print(Pump.describe_ports())
```

`"in"` is flow arriving at the equipment, `"out"` is flow leaving it, and
`"bi"` is either. A medium root admits everything beneath it. Domain classes
also list their named points:

```{code-cell} python3
print(ClarificationStage.describe_ports())
```

The same information is structured on `meta.port_contract`:

```{code-cell} python3
for slot in Pump.meta.port_contract.slots:
    print(slot.direction, slot.point_class.__name__, slot.min_count, slot.max_count)
```

## Connect and check

```{code-cell} python3
model = Model("urn:example:residuals#")
with model:
    clarifier = ClarificationStage("clarifier")
    sand_filter = RapidSandFiltrationStage("sand-filter")
    sludge_pump = Pump("sludge-pump")
    thickener = GravityThickener("thickener")

sludge = connect(clarifier, sludge_pump, name="sludge-draw")
report = model.check()
print(report.status)
for issue in report.issues:
    print(issue.message)
```

`check()` solves without building anything. It returns one of:

- `complete`: exactly one answer.
- `underconstrained`: more than one. Here the clarifier has a water and a
  sludge outlet, and a WaTr pump accepts either.
- `unsatisfiable`: none. The issues name the authored facts in conflict.

An underconstrained report is truthy; test `report.complete`. `resolve()`,
`graph()`, `save()`, and `validate()` raise `AmbiguousModelError` or
`UnsatisfiableModelError` instead of guessing.

## Add a hint

Add the narrowest fact you know. Here, the medium:

```{code-cell} python3
sludge.medium = values.Fluid_Sludge
connect(sludge_pump, thickener, name="sludge-to-thickener")
print(model.check().status)
```

The second connection needs no hint: the pump now carries sludge.

| Hint | Example |
| --- | --- |
| Medium | `connect(a, b, medium=...)` or `handle.medium = ...` |
| Named point | `connect(clarifier.clarified_water, ...)` |
| Declared port | `equipment.port("dosing", direction="in", medium=...)` |
| Connection class | `connect(a, b, connection=Pipe)` |

A named point selects that point outright:

```{code-cell} python3
connect(clarifier.clarified_water, sand_filter.inlet, name="clarified-water")
print(model.check().status)
```

`.port()` declares a point the shapes do not mention, with a stable name.
Its `medium=` overrides the class's medium domain.

`Tank(..., medium=[...])` records `s223:hasMedium` on the tank but does not
constrain its connections. Put the medium on the port or connection instead.

## Inspect the result

```{code-cell} python3
resolved = model.resolve()
resolved.explain(sludge)
```

The explanation gives the chosen points, the medium, and the reason. The same
values are on `.medium`, `.medium_reason`, and `.evidence`.

`resolved.connection(handle)` returns the concrete connection:

```{code-cell} python3
pipe = resolved.connection(sludge)
pipe, pipe.medium, list(pipe.connects_at)
```

Derived points and pipes exist only in the snapshot. Before resolution,
`equipment.ports` holds points that already exist and declared ports. After,
the snapshot's copy holds every concrete point:

```{code-cell} python3
list(sludge_pump.ports)
```

```{code-cell} python3
list(resolved["sludge-pump"].ports)
```

The snapshot can be walked along its pipes. `through=` follows only pipes
carrying one medium, here the sludge line:

```{code-cell} python3
start = resolved["clarifier"]
start.find_all_next(), start.find_all_next(through={"medium": values.Fluid_Sludge})
```

See [Query and edit saved models](query-loaded-models.md) for the other
search and walk methods.

Any edit to the model invalidates the snapshot.

## Describe a connection

Set properties on the handle. They are copied to the resolved connection:

```python
sludge.label = "Clarifier sludge draw"
spent = connect(sand_filter.backwash_waste, recovery_tank, name="spent-backwash")
spent.has_role.add(values.Role_Backwash)
```

Roles do not affect which medium the solver picks.

## Add more points

Shape requirements are minimums. Request an extra point with `ports="new"`:

```python
connect(source, mixer, ports="new")
```

Pair two ports that carry the same flow through a device. Pairing makes their
media equal and records `s223:pairedConnectionPoint`:

```python
feed_in = exchanger.port("feed-in", direction="in")
feed_out = exchanger.port("feed-out", direction="out")
feed_in.pair(feed_out)
```

## Group into a system

`model.system(name)` collects the equipment created inside it. `boundary()`
marks the points where the system meets the rest of the plant:

```{code-cell} python3
plant = Model("urn:example:plant#")
with plant:
    intake = Pump("intake-pump")
    with plant.system("treatment") as treatment:
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("sand-filter")

connect(intake, clarifier.inlet, name="raw-water")
connect(clarifier.clarified_water, sand_filter.inlet, name="clarified-water")
treatment.boundary(
    clarifier.sludge,
    sand_filter.filtered_water,
    sand_filter.backwash_supply,
    sand_filter.backwash_waste,
)

resolved = plant.resolve()
list(resolved["treatment"].has_boundary_connection_point)
```

A boundary point may connect to nothing in the model. Ports work too:
`intake.port("river", direction="in")`.

## Place in a space

Equipment created inside an open `PhysicalSpace` is located there with
`s223:hasPhysicalLocation`. A `DomainSpace` inside a `PhysicalSpace` is
enclosed by it. Spaces nest through `s223:contains`, exposed as `contains_`.
