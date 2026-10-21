# plumb

[![CI](https://github.com/gtfierro/objectrdf/actions/workflows/ci.yml/badge.svg)](https://github.com/gtfierro/objectrdf/actions/workflows/ci.yml)

Describe water and wastewater treatment plants as plain, typed Python and
get RDF that conforms to [WATR](https://github.com/DataDrivenCPS/water-ontology)
and [ASHRAE 223P](https://open223.info). No RDF in user code; real Turtle out.
[Brick](https://brickschema.org) building models use the same API.

Bundled ontologies: WATR v0.3.0.rc1 (a release candidate whose terms may still
change before 0.3.0), ASHRAE 223P (v1.0.0-2026), and Brick 1.4.2.

```python
from plumb import Model, connect, flowsheet
from plumb.qudt import quantity_kinds, units
from plumb.watr import Pump
from plumb.watr.drinking_water import ClarificationStage, CoagulationStage

with Model("urn:example:plant#") as model:
    intake = Pump("intake-pump")
    coagulation = CoagulationStage("coagulation")
    clarifier = ClarificationStage("clarifier")

raw_water = connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, clarifier.inlet, name="coagulated-water")
raw_water.sensor("raw-water-flow", kind=quantity_kinds.VolumeFlowRate, unit=units.M3_PER_DAY)

model.save("plant.ttl")      # connection points and pipes are worked out for you
print(model.validate())      # SHACL via shifty; errors name your objects
flowsheet(model).save("plant.svg")
```

The ontology classes are generated code, so editors and type checkers see
everything: completion, ontology definitions on hover, and type errors when a
link's range doesn't fit.

## Install and run the examples

Plumb requires Python 3.12 or newer. From a checkout of this repository,
install the project and its dependencies with
[uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Then run an example from the repository root:

```bash
uv run python examples/watr/treatment/watr_quickstart.py
uv run python examples/watr/asm2d/watertap_asm2d.py
uv run python examples/s223/ahu/s223_quickstart.py
uv run python examples/brick/quickstart/brick_quickstart.py
```

Each example prints a short summary and writes its generated Turtle file next
to the example script. See [examples/](examples/) for more scenarios.

- Documentation: [the learning book](docs/book/index.md) (tutorials, how-to
  guides, explanations, and API reference; build it with `make docs`)
- Start with [modelling a treatment train](docs/book/tutorials/watr-treatment.md)
  and [characterizing and instrumenting a plant](docs/book/tutorials/watr-instrumented-plant.md)
- Contributor documentation: [docs/index.md](docs/index.md)
- Design rationale and roadmap: [DESIGN.md](DESIGN.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- Examples organized by ontology: [examples/](examples/)

## Domain configurations and quantities

Reusable equipment layouts and property metadata are defined in RDF and SHACL.
The compiler generates typed configurations and immutable value schemas:

```python
from plumb.qudt import QuantityAmount as Q, units
from plumb.watr.asm2d import AerobicStage, AerobicDesign, OxygenOutletState

with Model("urn:example:reactor#") as model:
    reactor = AerobicStage("R5")
    reactor.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0))
    reactor.outlet.apply_properties(
        OxygenOutletState(oxygen_concentration=Q(1.91, units.GM_PER_M3))
    )
```

Bare values use shape-declared units; explicit quantities preserve their units.
The same `apply_properties(...)` API works on equipment, points, and connections.
Use `subject.quantity(...)` for individual values. `capability=` selects static,
observable, or actuatable properties; `has_aspect=` supplies their interpretation.

See [domain extensions](docs/book/explanation/domain-extensions.md), the
[ASM2d tutorial](docs/book/tutorials/domain-configurations.md), and the
[extension compiler reference](docs/book/reference/extension-compiler.md).
Regenerate the supplied domains with
`uv run python scripts/generate_example_domains.py`.

## Development

The Makefile wraps the standard development commands:

```bash
make setup          # install development and documentation dependencies
make check          # lint, type checks, and tests
make docs           # build the documentation and execute tutorials
make docs-open      # build and open the HTML documentation
make docs-check     # full documentation build; warnings are errors
make build          # source distribution and wheel, replacing dist/
make dist-check     # build, check metadata, and smoke-test the wheel
make regen          # regenerate the supplied domain packages from local SHACL
make help           # all available targets
```

Use `make test TEST_ARGS="-q tests/test_named_points.py"` to select tests.
`make format` formats source while excluding generated ontology output.
`make clean` removes documentation, build output, and tool caches.
Before uploading a release, run `make dist-check` and upload the files it
leaves in `dist/`.

To regenerate the committed ontology packages, see [docs/codegen.md](docs/codegen.md).
