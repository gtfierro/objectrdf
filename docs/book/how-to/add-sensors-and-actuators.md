---
file_format: mystnb
kernelspec:
  name: python3
---

# Add sensors and actuators

`.sensor()` adds a sensor and the quantity it observes in one call. `.actuator()`
adds a command to a piece of equipment and the actuator that carries it out.
Both work on equipment, on connections that have not been resolved yet, and
on named points.

## A small filter train

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.qudt import quantity_kinds, units
from objectrdf.watr import LevelSensor, Pump, Tank, enums
from objectrdf.watr.drinking_water import ChlorinationStage, RapidSandFiltrationStage

values = enums.values
model = Model("urn:example:instruments#")
with model:
    sand_filter = RapidSandFiltrationStage("sand-filter")
    chlorination = ChlorinationStage("chlorine-contact")
    clearwell = Tank("clearwell")
    high_service = Pump("high-service-pump")

connect(sand_filter.filtered_water, chlorination.inlet, name="filtered-water")
connect(chlorination.outlet, clearwell, name="disinfected-water")
finished = connect(clearwell, high_service, name="finished-water")
```

## Sensors

Call `.sensor()` on what the sensor measures. A turbidimeter on the filter's
outlet:

```{code-cell} python3
turbidimeter = sand_filter.filtered_water.sensor(
    "filter-effluent-turbidity",
    kind=quantity_kinds.Turbidity,
    unit=units.NTU,
    of_medium=values.Fluid_Water,
)
turbidimeter, turbidimeter.observes
```

The sensor class comes from the quantity kind, using the most specific class
the package defines. WaTr gives `TurbidityMeter` for turbidity,
`FlowSensor` for flow rates, `ConcentrationSensor` for concentrations, and
`ConductivitySensor`, `TemperatureSensor`, and `PressureSensor` for theirs.
The observed property is a `QuantifiableObservableProperty` named
`<name>-value`. Keywords such as `of_medium`, `of_substance`, and `value` go
to that property.

A chlorine analyzer on a connection that does not exist yet:

```{code-cell} python3
analyzer = finished.sensor(
    "chlorine-residual",
    kind=quantity_kinds.MassConcentration,
    unit=units.MilliGM_PER_L,
    of_medium=values.Fluid_Water,
    of_substance=values.Constituent_ChlorineResidual,
)
analyzer.has_observation_location
```

The location is the connection handle for now. Resolution replaces it with the
concrete pipe.

When the quantity kind has no specific sensor class, you get a plain `Sensor`.
Pass `sensor_class=` to choose one, such as a level sensor that measures a
length:

```{code-cell} python3
level = clearwell.sensor(
    "clearwell-level",
    kind=quantity_kinds.Length,
    unit=units.M,
    sensor_class=LevelSensor,
)
level
```

An enumeration kind makes a status reading instead of a number, observed by
an `EnumeratedObservableProperty`:

```{code-cell} python3
running = high_service.sensor("high-service-running", kind=values.Binary_OnOff)
running.observes
```

## Actuators

`.actuator()` creates an actuatable `<name>-command` property and an `Actuator`
named `name` that `actuates` the equipment. The equipment and the actuator are
both `actuated_by_property` the command:

```{code-cell} python3
speed = high_service.actuator(
    "high-service-speed", kind=quantity_kinds.Frequency, unit=units.HZ
)
start = high_service.actuator(
    "high-service-start", kind=values.Binary_OnOff, value=values.OnOff_Off
)
[command.name for command in high_service.actuated_by_property]
```

A quantity kind with a unit makes a `QuantifiableActuatableProperty`, such as
a speed or position setpoint. An enumeration kind makes an
`EnumeratedActuatableProperty`, and `value=` must be one of its members.

## After resolution

```{code-cell} python3
resolved = model.compile()
analyzer = resolved["chlorine-residual"]
analyzer.has_observation_location is resolved.connection(finished)
```

```{code-cell} python3
from objectrdf import flowsheet

flowsheet(resolved)
```

## Building one by hand

`.sensor()` is shorthand. The same sensor written out in full:

```python
from objectrdf.watr import TurbidityMeter

turbidity = filtered.quantity(
    "filtered-turbidity-value",
    0.1,
    unit=units.NTU,
    kind=quantity_kinds.Turbidity,
    capability="observable",
)
TurbidityMeter(
    "filtered-turbidity",
    has_observation_location=filtered,
    observes=turbidity,
)
```

`has_observation_location` and `has_reference_location` accept connection
handles, ports, and named points. Other relations take concrete objects only.
