---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Plumb

Write water and wastewater treatment plant models in Python and get RDF that
conforms to [WaTr](https://github.com/DataDrivenCPS/water-ontology) and ASHRAE
223P.

A semantic model of a plant is useful to analytics, controls, and digital
twins, but writing one by hand is slow: every pipe needs connection points on
both ends, matching media, inverse links, and the right classes, and nothing
checks the result until a SHACL validator runs. Plumb lets you state what
the plant is. It fills in the rest and checks it as you go.

```{code-cell} python3
from plumb import Model, connect, flowsheet
from plumb.qudt import quantity_kinds, units
from plumb.watr import Pump
from plumb.watr.drinking_water import (
    ClarificationStage,
    CoagulationStage,
    RapidSandFiltrationStage,
)

with Model("urn:example:plant#") as model:
    intake = Pump("intake-pump")
    coagulation = CoagulationStage("coagulation")
    clarifier = ClarificationStage("clarifier")
    sand_filter = RapidSandFiltrationStage("sand-filter")

raw_water = connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, clarifier.inlet, name="coagulated-water")
settled = connect(clarifier.clarified_water, sand_filter.inlet, name="settled-water")

raw_water.quantity("raw-turbidity", 18.0, unit=units.NTU, kind=quantity_kinds.Turbidity)
settled.sensor("settled-turbidity", kind=quantity_kinds.Turbidity, unit=units.NTU)

model.save("plant.ttl")
flowsheet(model)
```

## Features

**Typed classes generated from the ontologies.** Every WaTr and 223P class,
process, medium, and role is a Python class or value, with editor completion,
type checking, and the ontology's definitions in its docstrings. Required
properties are required arguments.

**Connections inferred from the shapes.** `connect(a, b)` is enough. A solver
reads the SHACL shapes to choose connection points, media, and pipe classes,
and stops to ask when the model is ambiguous rather than guess.

**Validation in Python terms.** `validate()` runs the ontologies' own SHACL
shapes and rules, and reports each violation against the Python object that
caused it.

**Quantities, sensors, and actuators.** Values carry QUDT units and quantity
kinds, checked for dimensional consistency. `.sensor()` and `.actuator()`
add an instrument and its property in one call.

**Flow sheets.** `flowsheet()` draws any model, authored or loaded, with
processes, streams, and instruments.

**Load, query, and edit.** `Model.from_graph()` reads saved RDF back as the
same typed objects, chosen from the file's `owl:imports`.

**Domain packages.** Reusable equipment layouts and property sets are written
in SHACL and compiled into Python packages, such as
`plumb.watr.drinking_water` above.

## Start here

1. [Model a treatment train](tutorials/watr-treatment.md)
2. [Instrument a plant](tutorials/watr-instrumented-plant.md)
3. [Use a domain package](tutorials/domain-configurations.md)

The how-to guides each cover one task. Brick and 223P building models use the
same API; see [An S223 air path](tutorials/s223-air-path.md).

## Building the book

Every code cell runs when the book is built. From the repository root:

```bash
uv sync --group docs
uv run --group docs jupyter-book build docs/book
```

Open `docs/book/_build/html/index.html`.
