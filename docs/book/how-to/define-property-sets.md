---
file_format: mystnb
kernelspec:
  name: python3
---

# Define and apply property sets

A property set, or schema, is a reusable group of quantities: each field has
a QUDT quantity kind, a unit, a medium, and optional bounds and default.
Define one in Python for a single program, or use one compiled from an
ontology. [Attach quantities](attach-quantities.md) covers single values.

```{code-cell} python3
from plumb import Model, connect
from plumb.qudt import QuantityAmount as Q, quantity_kinds, units
from plumb.watr import Pump, enums
from plumb.watr.drinking_water import CoagulationStage

values = enums.values

model = Model("urn:example:property-sets#")
with model:
    intake = Pump("intake-pump")
    coagulation = CoagulationStage("coagulation")
raw_water = connect(intake, coagulation.inlet, name="raw-water")
```

## Define a schema in Python

Subclass `PropertySchema` and declare each field with `quantity_field()`:

```{code-cell} python3
from plumb import PropertySchema, quantity_field


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

## Apply a schema

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

## Use a schema from an ontology

Domain packages compile property schemas from SHACL. ASM2d defines an
aerobic reactor's design values:

```{code-cell} python3
from plumb.watr.asm2d import AerobicDesign, AerobicStage

print(AerobicDesign.describe())
```

```{code-cell} python3
with model:
    reactor = AerobicStage("R5")
dict(reactor.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0)))
```

Start a schema in Python. Move it to SHACL when other models or tools need
it; see [Domain extensions](../explanation/domain-extensions.md).
