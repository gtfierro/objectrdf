# Learn ObjectRDF

ObjectRDF lets you describe water and wastewater treatment plants as Python
objects and write them out as RDF that conforms to the
[WaTr](https://github.com/DataDrivenCPS/water-ontology) and ASHRAE 223P ontologies. The generated
`objectrdf.watr` package gives you WaTr's equipment, processes, treatment
objectives, media, and roles as typed classes and values. The runtime works
out the connection points and pipes between equipment, validates the model
against the ontologies' SHACL shapes, and loads saved RDF back as objects.

```python
from objectrdf import Model, connect
from objectrdf.watr import Pump
from objectrdf.watr.drinking_water import ClarificationStage, CoagulationStage

with Model("urn:example:plant#") as model:
    intake = Pump("intake-pump")
    coagulation = CoagulationStage("coagulation")
    clarifier = ClarificationStage("clarifier")

connect(intake, coagulation.inlet)
connect(coagulation.outlet, clarifier.inlet)
model.save("plant.ttl")
```

## Where to start

1. [Model a treatment train](tutorials/watr-treatment.md): stages, named
   points, system boundaries, saving, loading, and drawing the flow sheet.
2. [Characterize and instrument a plant](tutorials/watr-instrumented-plant.md):
   pumps and residuals, an influent property set, sensors, actuators, and a
   flow sheet.
3. [Use generated configurations](tutorials/domain-configurations.md): the
   ASM2d activated-sludge package and its property schemas.

The task guides cover [authoring](how-to/author-a-model.md),
[connecting equipment](how-to/connect-equipment.md),
[quantities and property sets](how-to/attach-quantities.md),
[sensors and actuators](how-to/add-sensors-and-actuators.md),
[processes and objectives](how-to/watr-processes.md),
[flow sheets](how-to/draw-a-flowsheet.md),
[validation](how-to/validate-and-save.md), and
[querying saved models](how-to/query-loaded-models.md). To package reusable
equipment layouts and property sets for your own models, read
[domain extensions](explanation/domain-extensions.md), then
[generate a domain API](how-to/generate-domain-api.md).

The same API works for 223P building systems and for Brick;
[the S223 air path](tutorials/s223-air-path.md) is a short example.

Every code cell in this book runs when the book is built, so the output you
see is what the current version produces. From the repository root:

```bash
uv sync --group docs
uv run --group docs jupyter-book build docs/book
```

The generated HTML is at `docs/book/_build/html/index.html`.
