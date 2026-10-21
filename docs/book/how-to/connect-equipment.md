---
file_format: mystnb
kernelspec:
  name: python3
---

# Connect equipment

`connect(a, b)` records that flow goes from `a` to `b`. You do not create pipes
or connection points yourself. When the model is resolved, the solver picks
the connection points, the medium, and the connection class (`Pipe` for
water). This page builds a clarifier's residuals line with WaTr equipment.

## Connect and check

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr import GravityThickener, Pump, enums
from objectrdf.watr.drinking_water import ClarificationStage, RapidSandFiltrationStage

values = enums.values
model = Model("urn:example:residuals#")
with model:
    clarifier = ClarificationStage("clarifier")
    sand_filter = RapidSandFiltrationStage("sand-filter")
    sludge_pump = Pump("sludge-pump")
    thickener = GravityThickener("thickener")

sludge = connect(clarifier, sludge_pump, name="sludge-draw")
print(model.check().status)
```

`check()` solves without building anything. `underconstrained` means more
than one valid answer: the clarifier has a water outlet and a sludge outlet,
and a WaTr pump accepts either. The issue says which connection is undecided:

```{code-cell} python3
for issue in model.check().issues:
    print(issue.message)
```

An underconstrained report is still truthy, so test `report.complete` or
`report.status` rather than `if report`. `resolve()`, `graph()`, `save()`, and
`validate()` refuse to guess: they raise `AmbiguousModelError`, or
`UnsatisfiableModelError` for a contradiction.

## Give the solver a hint

Add the narrowest fact you know. Here that is the medium of the connection,
either when it is created or later on the handle:

```{code-cell} python3
sludge.medium = values.Fluid_Sludge
connect(sludge_pump, thickener, name="sludge-to-thickener")
print(model.check().status)
```

The second connection needs no hint. Only the sludge medium fits both the
pump's outlet and the thickener's inlet once the pump carries sludge.

Other hints:

- **A named point.** Equipment from a domain package has named points, such
  as `clarifier.clarified_water` and `clarifier.sludge`. Connecting a named
  point selects it outright, as in the next cell.
- **A port.** `equipment.port(name, direction=..., medium=...)` declares a
  point that the shapes do not mention, such as a dosing inlet, with a
  stable name. Its `medium=` overrides the class's medium domain.
- **A neighbour.** Equipment with a fixed medium settles its connections, as
  the thickener did above.
- **A connection class.** `connect(a, b, connection=SomeConnection)`
  constrains the class that is created.

```{code-cell} python3
connect(clarifier.clarified_water, sand_filter.inlet, name="clarified-water")
print(model.check().status)
```

A medium on equipment itself, as in `Tank(..., medium=[...])`, records
`s223:hasMedium` on the tank but does not constrain its connections. To fix
what a tank receives, give its port or connection the medium.

## See what the solver chose

```{code-cell} python3
resolved = model.resolve()
resolved.explain(sludge)
```

The explanation lists the chosen points, the medium, and why: an explicit
connection or port, a paired port, an ontology constraint that left one
choice, or the solver's preference for fewer medium changes. The same values
are on `explanation.medium`, `.medium_reason`, and `.evidence`.
`resolved.connection(handle)` returns the concrete connection:

```{code-cell} python3
pipe = resolved.connection(sludge)
type(pipe).__name__, pipe.medium, [point.name for point in pipe.connects_at]
```

The authored model never gains the derived points and pipes. They exist in
the resolved snapshot, and any later edit to the model invalidates it.

## Describe the connection

Handles accept connection properties before the connection exists. Roles
and labels are copied to the resolved connection:

```python
sludge.label = "Clarifier sludge draw"
spent = connect(sand_filter.backwash_waste, recovery_tank, name="spent-backwash")
spent.has_role.add(values.Role_Backwash)
```

Collections on a handle work like collections on any object: use `.add()` for
one value, and assignment to replace them all. Roles describe the connection;
they do not affect which medium the solver picks.

## More points than the shapes require

Shape requirements are minimums. A `Clarifier` whose shapes list only
outlets still gets an inlet when something connects into it. To add a point
the shapes do not need, request one:

```python
connect(source, mixer, ports="new")
```

Ports on the two sides of equipment that carry the same flow, such as the
feed side of a heat exchanger, can be paired. Pairing makes their media equal
and records `s223:pairedConnectionPoint`:

```python
feed_in = exchanger.port("feed-in", direction="in")
feed_out = exchanger.port("feed-out", direction="out")
feed_in.pair(feed_out)
```

## Systems and boundaries

`model.system(name)` collects the equipment created inside it into an
`s223:System`. Connections that cross the system's edge give it boundary
connection points when the model resolves:

```{code-cell} python3
plant = Model("urn:example:plant#")
with plant:
    intake = Pump("intake-pump")
with plant, plant.system("treatment") as treatment:
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
sorted(point.name for point in resolved["treatment"].has_boundary_connection_point)
```

`boundary()` also names points that connect to nothing in the model, such as
the sludge outlet here: they are where the system meets the rest of the
plant. Ports work too, as in `intake.port("river", direction="in")`.

## Spaces

Equipment created inside an open `PhysicalSpace` is located there with
`s223:hasPhysicalLocation`. A `DomainSpace` (which needs `has_domain`) inside
a `PhysicalSpace` is enclosed by it. Spaces nest through `s223:contains`,
exposed as `contains_` because `contains()` is the containment method.
