---
file_format: mystnb
kernelspec:
  name: python3
---

# Attach quantities

A value such as a tank volume or a raw-water turbidity is an S223 property on
equipment, a point, or a connection. Units and quantity kinds are QUDT terms
from `plumb.qudt`.

```{code-cell} python3
from plumb import Model, connect
from plumb.qudt import QuantityAmount as Q, quantity_kinds, units
from plumb.watr import Pump, Tank, enums
from plumb.watr.drinking_water import CoagulationStage

values = enums.values
model = Model("urn:example:quantities#")
with model:
    intake = Pump("intake-pump")
    coagulation = CoagulationStage("coagulation")
    clearwell = Tank("clearwell")
raw_water = connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, clearwell, name="coagulated-water")
```

## Attach one quantity

`.quantity()` creates and attaches a property with a value, unit, and kind:

```{code-cell} python3
volume = clearwell.quantity(
    "clearwell-volume",
    5_000,
    unit=units.M3,
    kind=quantity_kinds.Volume,
    has_aspect=[values.Aspect_Nominal],
)
volume, volume.has_value, volume.has_unit
```

The unit must match the kind's dimensions:

```{code-cell} python3
try:
    clearwell.quantity("bad-volume", 5, unit=units.KiloGM, kind=quantity_kinds.Volume)
except ValueError as error:
    print(error)
```

`capability=` picks the property class:

| Capability | Use |
| --- | --- |
| `"static"` (default) | a fixed value |
| `"observable"` | a measured value; see [`.sensor()`](add-sensors-and-actuators.md) |
| `"actuatable"` | a writable setpoint |

Add `Aspect_Nominal` yourself for a nominal value.

## Qualify a stream quantity

A quantity on a connection describes what flows in it. Name the medium and,
for a constituent, the substance:

```{code-cell} python3
toc = raw_water.quantity(
    "raw-organic-carbon",
    3.5,
    unit=units.MilliGM_PER_L,
    kind=quantity_kinds.MassConcentration,
    of_medium=values.Water_Freshwater,
    of_substance=values.Constituent_OrganicCarbon,
)
toc.of_medium, toc.of_substance
```

The property moves to the concrete pipe when the model resolves. Ports and
named points accept quantities the same way.

## The medium of a property

223P requires a property's `of_medium` to be compatible with the medium of
the pipe, point, or equipment it is on. Resolution uses that:

- Without `of_medium`, the property takes its host's resolved medium.
- With `of_medium`, the solver keeps the host's medium compatible, and
  `check()` reports a conflict.

`Water_Freshwater` above fits the raw-water pipe's `Fluid_Water`. `Fluid_Air`
would not; [How connections are resolved](../explanation/connection-resolution.md)
defines compatible media:

```{code-cell} python3
with Model("urn:example:conflict#") as other:
    stage = CoagulationStage("coagulation")
    sump = Tank("sump")
drain = connect(stage.outlet, sump, name="drain")
drain.quantity(
    "drain-temperature", 15, unit=units.DEG_C, kind=quantity_kinds.Temperature,
    of_medium=values.Fluid_Air,
)
report = other.check()
print(report.status)
print(report.issues[0].labels[-1])
```


## Attach a plain value

When no QUDT quantity kind fits, use S223's `Property` with a literal:

```{code-cell} python3
from plumb.watr import Property

permeability = Property(
    "water-permeability",
    label="Water permeability coefficient [m/(Pa·s)]",
    has_value=4.2e-12,
    has_aspect=[values.Aspect_Nominal],
    model=model,
)
coagulation.has_property.add(permeability)
```

QUDT has no kind for reverse-osmosis water permeability (`M-PER-SEC-PA`),
hence the plain `Property` above.

## Limits

S223 and WaTr describe one nominal, untimed value per property. They cannot
distinguish operating points, samples, or scenarios of the same stream. That
needs a companion ontology defining the operating point, its time or
scenario, whether a value is nominal, calculated, or measured, and the
composition basis.

## Next

[Define and apply property sets](define-property-sets.md) groups quantities
into a reusable schema.
