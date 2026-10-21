---
file_format: mystnb
kernelspec:
  name: python3
---

# Add sensors and actuators

`.sensor()` adds a sensor and the property it observes. `.actuator()` adds a
command property and the actuator that carries it out. Both work on
equipment, named points, and connection handles.

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

## Add a sensor

Call `.sensor()` on what is measured. A turbidimeter on the filter outlet:

```{code-cell} python3
turbidimeter = sand_filter.filtered_water.sensor(
    "filter-effluent-turbidity",
    kind=quantity_kinds.Turbidity,
    unit=units.NTU,
)
turbidimeter, turbidimeter.observes
```

The sensor class is the most specific one the package defines for the
quantity kind: `TurbidityMeter`, `FlowSensor`, `ConcentrationSensor`,
`ConductivitySensor`, `TemperatureSensor`, or `PressureSensor` in WaTr. The
observed property is named `<name>-value`; `of_medium`, `of_substance`, and
`value` go to it.

## Measure a connection

A chlorine analyzer on a connection handle:

```{code-cell} python3
analyzer = finished.sensor(
    "chlorine-residual",
    kind=quantity_kinds.MassConcentration,
    unit=units.MilliGM_PER_L,
    of_substance=values.Constituent_ChlorineResidual,
)
analyzer.has_observation_location
```

Resolution replaces the handle with the concrete pipe.

## Choose the sensor class

A kind with no specific class gives a plain `Sensor`. Pass `sensor_class=`:

```{code-cell} python3
level = clearwell.sensor(
    "clearwell-level",
    kind=quantity_kinds.Length,
    unit=units.M,
    sensor_class=LevelSensor,
)
level
```

## Observe a status

An enumeration kind gives an `EnumeratedObservableProperty` instead of a
number:

```{code-cell} python3
running = high_service.sensor("high-service-running", kind=values.Binary_OnOff)
running.observes
```

## Add an actuator

`.actuator()` creates a `<name>-command` property and an `Actuator` that
`actuates` the equipment. Both are `actuated_by_property` the command:

```{code-cell} python3
speed = high_service.actuator(
    "high-service-speed", kind=quantity_kinds.Frequency, unit=units.HZ
)
start = high_service.actuator(
    "high-service-start", kind=values.Binary_OnOff, value=values.OnOff_Off
)
[command.name for command in high_service.actuated_by_property]
```

A quantity kind gives a `QuantifiableActuatableProperty`. An enumeration
kind gives an `EnumeratedActuatableProperty`; `value=` must be a member.

## Resolve and draw

```{code-cell} python3
resolved = model.compile()
analyzer = resolved["chlorine-residual"]
analyzer.has_observation_location is resolved.connection(finished)
```

The observed property takes the pipe's medium; see
[Attach quantities](attach-quantities.md):

```{code-cell} python3
analyzer.observes.of_medium
```

```{code-cell} python3
from objectrdf import flowsheet

flowsheet(resolved)
```

## Build a sensor by hand

`.sensor()` is shorthand for:

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

`has_observation_location` and `has_reference_location` accept handles,
ports, and named points. Other relations need concrete objects.
