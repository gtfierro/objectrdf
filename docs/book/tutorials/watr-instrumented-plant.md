---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Instrument a plant

This tutorial extends [the treatment train](watr-treatment.md) into a plant
with pumps, a clearwell, sludge thickening, and filter backwash. You will
describe the raw water, add sensors and actuators, and draw the result.

## 1. Describe the influent

A property schema is a group of quantities. Each field has a QUDT quantity
kind, a unit, and the medium it describes.

```{code-cell} python3
from objectrdf import Model, PropertySchema, connect, flowsheet, quantity_field
from objectrdf.qudt import QuantityAmount as Q, quantity_kinds, units
from objectrdf.watr import GravityThickener, LevelSensor, Pump, Tank, enums
from objectrdf.watr.drinking_water import (
    ChlorinationStage,
    ClarificationStage,
    CoagulationStage,
    FlocculationStage,
    RapidSandFiltrationStage,
)

values = enums.values


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
    organic_carbon: float | Q = quantity_field(
        kind=quantity_kinds.MassConcentration,
        unit=units.MilliGM_PER_L,
        label="Total organic carbon",
        of_medium=values.Water_Freshwater,
        of_substance=values.Constituent_OrganicCarbon,
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


raw = InfluentQuality(flow_rate=40_000, turbidity=Q(18.0, units.NTU), organic_carbon=3.5)
raw
```

Bare numbers take the field's unit. Omitted fields take their default.
Units and bounds are checked on creation:

```{code-cell} python3
try:
    InfluentQuality(flow_rate=40_000, turbidity=Q(18.0, units.KiloGM), organic_carbon=3.5)
except ValueError as error:
    print(error)
```

## 2. Create the equipment

The stages come from `drinking_water`. Pumps, tanks, and the thickener are
plain WaTr classes.

```{code-cell} python3
model = Model("urn:example:surface-water#")

with model:
    with model.system("plant"):
        intake = Pump("raw-water-pump")
        coagulation = CoagulationStage("coagulation")
        flocculation = FlocculationStage("flocculation")
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("sand-filter")
        chlorination = ChlorinationStage("chlorine-contact")
        clearwell = Tank("clearwell", has_role=[values.Role_Storage])
        high_service = Pump("high-service-pump")

        sludge_pump = Pump("sludge-pump")
        thickener = GravityThickener("thickener")
        backwash_pump = Pump("backwash-pump")
        backwash_tank = Tank("backwash-recovery", has_role=[values.Role_Backwash])
```

The thickener's process and objective come from its class:

```{code-cell} python3
list(thickener.has_process), list(thickener.has_treatment_objective)
```

## 3. Connect the main path

Named points select stage ports. For a whole pump or tank, the solver picks
the point.

```{code-cell} python3
raw_water = connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, flocculation.inlet, name="coagulated-water")
connect(flocculation.outlet, clarifier.inlet, name="flocculated-water")
connect(clarifier.clarified_water, sand_filter.inlet, name="clarified-water")
connect(sand_filter.filtered_water, chlorination.inlet, name="filtered-water")
connect(chlorination.outlet, clearwell, name="disinfected-water")
finished = connect(clearwell, high_service, name="finished-water")
print(model.check().status)
```

## 4. Add residuals and backwash

The sludge line needs a medium. A WaTr pump accepts water or sludge, so
nothing else says which one flows.

```{code-cell} python3
connect(clarifier.sludge, sludge_pump, name="sludge-draw", medium=values.Fluid_Sludge)
connect(sludge_pump, thickener, name="sludge-to-thickener", medium=values.Fluid_Sludge)
connect(clearwell, backwash_pump, name="backwash-draw")
connect(backwash_pump, sand_filter.backwash_supply, name="backwash-supply")
connect(sand_filter.backwash_waste, backwash_tank, name="spent-backwash")
print(model.check().status)
```

Mark where the plant meets the outside. These ports connect to nothing in
the model:

```{code-cell} python3
model["plant"].boundary(
    intake.port("raw-water-suction", direction="in"),
    high_service.port("distribution", direction="out"),
    thickener.port("thickened-sludge", direction="out", medium=values.Fluid_Sludge),
    thickener.port("thickener-supernatant", direction="out", medium=values.Fluid_Water),
)
```

## 5. Characterize the influent

Attach the property set to the raw-water connection:

```{code-cell} python3
influent = raw_water.apply_properties(raw)
dict(influent)
```

```{code-cell} python3
turbidity = influent["turbidity"]
turbidity.has_value, turbidity.has_unit, turbidity.of_medium
```

## 6. Add instruments

Call `.sensor()` on what is measured. Each observed property takes the
medium of the pipe or point it is on.

```{code-cell} python3
raw_water.sensor(
    "raw-water-flow", kind=quantity_kinds.VolumeFlowRate, unit=units.M3_PER_DAY
)
sand_filter.filtered_water.sensor(
    "filter-effluent-turbidity", kind=quantity_kinds.Turbidity, unit=units.NTU
)
finished.sensor(
    "chlorine-residual",
    kind=quantity_kinds.MassConcentration,
    unit=units.MilliGM_PER_L,
    of_substance=values.Constituent_ChlorineResidual,
)
clearwell.sensor(
    "clearwell-level", kind=quantity_kinds.Length, unit=units.M, sensor_class=LevelSensor
)
```

Give the high-service pump a speed command and an on/off command:

```{code-cell} python3
high_service.actuator("high-service-speed", kind=quantity_kinds.Frequency, unit=units.HZ)
high_service.actuator(
    "high-service-start", kind=values.Binary_OnOff, value=values.OnOff_Off
)
list(high_service.actuated_by_property)
```

## 7. Resolve, validate, and draw

```{code-cell} python3
resolved = model.compile()
resolved.explain(finished)
```

The clearwell feeds two pumps. `explain()` shows which outlet each
connection uses.

The chlorine analyzer was attached to the `finished` handle. In the snapshot,
its location is the concrete pipe:

```{code-cell} python3
analyzer = resolved["chlorine-residual"]
analyzer.has_observation_location
```

```{code-cell} python3
flowsheet(resolved, title="Surface-water treatment plant")
```

Save it:

```{code-cell} python3
model.save("plant.ttl")
```

## Next

- [Attach quantities and property sets](../how-to/attach-quantities.md)
- [Add sensors and actuators](../how-to/add-sensors-and-actuators.md)
- [Query and edit saved models](../how-to/query-loaded-models.md)
