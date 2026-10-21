# ObjectRDF

ObjectRDF describes water and wastewater treatment plants as Python objects
and writes them out as RDF conforming to
[WaTr](https://github.com/DataDrivenCPS/water-ontology) and ASHRAE 223P.

- `objectrdf.watr` provides WaTr's equipment, processes, treatment objectives,
  media, and roles as typed classes and values.
- `connect()` records flow between equipment. The runtime chooses the
  connection points and pipes.
- `validate()` checks the model against the ontologies' SHACL shapes.
- `Model.from_graph()` loads saved RDF back as objects.

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
