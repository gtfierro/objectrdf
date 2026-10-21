---
file_format: mystnb
kernelspec:
  name: python3
---

# Group equipment into systems and spaces

Place equipment in a room, group it into a system that meets the rest of the
plant at a few points, or put components inside a larger piece of equipment.

## Place equipment in a space

An object opened with `with` becomes a container. Objects created inside are
linked with the predicate the ontology uses for that pair of classes:

```{code-cell} python3
from plumb import Model, connect
from plumb.watr import PhysicalSpace, Pump
from plumb.watr.drinking_water import ClarificationStage, RapidSandFiltrationStage

model = Model("urn:example:plant#")
with model:
    with PhysicalSpace("filter-building") as building:
        backwash_pump = Pump("backwash-pump")

list(backwash_pump.has_physical_location)
```

Equipment in a `PhysicalSpace` is located there with
`s223:hasPhysicalLocation`. A `DomainSpace` inside a `PhysicalSpace` is
enclosed by it, and spaces nest through `s223:contains`, exposed as
`contains_`.

- `container.contains(child)` does the same without a block.
- `via="property_name"` picks the predicate when more than one applies.
- A class the container cannot hold raises `ContainmentError`.

## Group equipment into a system

`model.system(name)` collects the equipment created inside it into an S223
`System`. `boundary()` marks the points where the system meets the rest of
the plant:

```{code-cell} python3
with model:
    intake = Pump("intake-pump")
    with model.system("treatment") as treatment:
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
resolved = model.resolve()
list(resolved["treatment"].has_boundary_connection_point)
```

A connection that crosses into the system, such as the raw-water pipe, makes
its point a boundary point when the model resolves. A boundary point may also
connect to nothing in the model; it is then a feed or product of the system.
Ports work too: `intake.port("river", direction="in")`.

## Put components inside equipment

Equipment can contain equipment. A damper and fan created inside an air
handling unit are its parts:

```{code-cell} python3
from plumb.s223 import AirHandlingUnit, Damper, Fan

with Model("urn:example:air#") as air:
    with AirHandlingUnit("ahu") as ahu:
        damper = Damper("outside-air-damper")
        fan = Fan("supply-fan")
    zone_damper = Damper("zone-damper")
connect(damper, fan)
connect(ahu, zone_damper, name="supply-duct")
list(ahu.contains_)
```

The AHU's own inlet and outlet stand for points on its parts. `maps_to` says
which, so a walk can step through the AHU to the parts behind its ports:

```{code-cell} python3
air["outside-air-damper-in"].maps_to = air["ahu-in"]
air["supply-fan-out"].maps_to = air["ahu-out"]
air.resolve()["zone-damper"].find_all_previous(descend=True)
```

`maps_to` is set on concrete points, so it works for points the equipment
creates when it is constructed, such as `ahu-in` here. Ports that exist only
after resolution cannot be mapped yet.

## Find what contains what

`contents`, `find_all()`, and `find_parent()` search containment, and
`descend=True` walks into containers. See
[Find objects in a model](find-objects.md).
