---
file_format: mystnb
kernelspec:
  name: python3
---

# Attach quantities and property sets

Values such as a design flow, a tank volume, or the turbidity of raw water are
S223 properties attached to equipment, points, or connections. Units and
quantity kinds are QUDT terms from `objectrdf.qudt`.

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

## One quantity

`.quantity()` creates a property with a value, unit, and quantity kind, and
attaches it:

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

The unit must match the quantity kind's dimensions:

```{code-cell} python3
try:
    clearwell.quantity("bad-volume", 5, unit=units.KiloGM, kind=quantity_kinds.Volume)
except ValueError as error:
    print(error)
```

`capability=` picks the property class: `"static"` (the default) for a fixed
value, `"observable"` for something measured, and `"actuatable"` for a
writable setpoint. It says nothing about interpretation, so add
`Aspect_Nominal` yourself for a nominal value. For a measured value that a
sensor reports, use [`.sensor()`](add-sensors-and-actuators.md).

A quantity on a stream describes what flows in it. Qualify it with the medium
and the substance:

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

`raw_water` is a connection handle, so the property moves to the concrete pipe
when the model resolves. Ports and named points accept quantities the same
way.

## A property set written in Python

Several quantities that always go together form a schema. Subclass
`PropertySchema` and declare each field with `quantity_field()`:

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

The class is a frozen, keyword-only dataclass. Bare numbers use the field's
unit. A `QuantityAmount` keeps its own unit if it is compatible, with no
conversion. Bounds and units are checked when you create the value:

```{code-cell} python3
try:
    InfluentQuality(flow_rate=-5, turbidity=18.0)
except ValueError as error:
    print(error)
```

`apply_properties()` attaches one property per field and returns them keyed by
field name:

```{code-cell} python3
influent = raw_water.apply_properties(
    InfluentQuality(flow_rate=40_000, turbidity=Q(18.0, units.NTU))
)
dict(influent)
```

Each application creates new properties named after the subject and field.
Use `prefix=` to choose a different stem. A name that is already taken makes
the whole application fail, leaving the model unchanged.

## A property set from an ontology

Domain packages compile property schemas from SHACL, so the definition is
shared RDF rather than Python. The ASM2d package defines the design values
of an aerobic reactor, with a default volume:

```{code-cell} python3
from objectrdf.watr.asm2d import AerobicDesign, AerobicStage

print(AerobicDesign.describe())
```

```{code-cell} python3
with model:
    reactor = AerobicStage("R5")
dict(reactor.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0)))
```

Write a schema in Python while you work out what you need, and move it to SHACL
when other models or tools need to share it. See
[Domain extensions](../explanation/domain-extensions.md).

## A plain value

S223's `Property` takes a literal directly. Use it when no QUDT quantity kind
fits. It carries less meaning than a quantity, so prefer `.quantity()` when you
can:

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

## What the ontologies cannot express yet

S223 and WaTr describe a nominal, untimed value on equipment or a stream: the
value, unit, quantity kind, medium, and substance. They cannot yet tell apart
several operating points or samples of the same stream. A distinct operating
point needs a companion ontology that defines:

- an operating-point class and how it relates to the connection;
- whether a state is nominal, calculated, measured, or constrained;
- time, scenario, or run identity and the validity interval;
- the cardinality and ownership of its properties;
- composition semantics, including the balance basis.

QUDT also has no quantity kind for reverse-osmosis water permeability
(`M-PER-SEC-PA`), which is why the example above uses a plain `Property`.
WaTr would need to define that kind before it can be a checked quantity.
