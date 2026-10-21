---
file_format: mystnb
kernelspec:
  name: python3
---

# Attach quantities and property sets

A value such as a tank volume or a raw-water turbidity is an S223 property on
equipment, a point, or a connection. Units and quantity kinds are QUDT terms
from `objectrdf.qudt`.

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.qudt import QuantityAmount as Q, quantity_kinds, units
from objectrdf.watr import Pump, Tank, enums
from objectrdf.watr.drinking_water import CoagulationStage

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

## Define a property set in Python

Subclass `PropertySchema` and declare each field with `quantity_field()`:

```{code-cell} python3
from objectrdf import PropertySchema, quantity_field


class InfluentQuality(PropertySchema):
    """Raw surface-water quality at the plant intake."""

    flow_rate: float | Q = quantity_field(
        kind=quantity_kinds.VolumeFlowRate,
        unit=units.M3_PER_DAY,
        label="Raw-water flow",
        of_medium=values.Water_Freshwater,
        aspects=(values.Aspect_Nominal,),
        minimum=0,
    )
    turbidity: float | Q = quantity_field(
        kind=quantity_kinds.Turbidity,
        unit=units.NTU,
        label="Raw-water turbidity",
        of_medium=values.Water_Freshwater,
        aspects=(values.Aspect_Nominal,),
        minimum=0,
    )
    temperature: float | Q = quantity_field(
        kind=quantity_kinds.Temperature,
        unit=units.DEG_C,
        label="Raw-water temperature",
        of_medium=values.Water_Freshwater,
        aspects=(values.Aspect_Nominal,),
        default=12.0,
    )


print(InfluentQuality.describe())
```

The class is a frozen, keyword-only dataclass. A bare number uses the
field's unit. A `QuantityAmount` keeps its own compatible unit; nothing is
converted. Bounds and units are checked on creation:

```{code-cell} python3
try:
    InfluentQuality(flow_rate=-5, turbidity=18.0)
except ValueError as error:
    print(error)
```

## Apply a property set

`apply_properties()` attaches one property per field and returns them by
field name:

```{code-cell} python3
influent = raw_water.apply_properties(
    InfluentQuality(flow_rate=40_000, turbidity=Q(18.0, units.NTU))
)
dict(influent)
```

Properties are named `<subject>-<field>`; `prefix=` changes the stem. If a
name is taken, nothing is applied.

## Use a property set from an ontology

Domain packages compile property schemas from SHACL. ASM2d defines an
aerobic reactor's design values:

```{code-cell} python3
from objectrdf.watr.asm2d import AerobicDesign, AerobicStage

print(AerobicDesign.describe())
```

```{code-cell} python3
with model:
    reactor = AerobicStage("R5")
dict(reactor.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0)))
```

Start a schema in Python. Move it to SHACL when other models or tools need
it; see [Domain extensions](../explanation/domain-extensions.md).

## Attach a plain value

When no QUDT quantity kind fits, use S223's `Property` with a literal:

```{code-cell} python3
from objectrdf.watr import Property

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
