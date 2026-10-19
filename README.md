# objectrdf

[![CI](https://github.com/gtfierro/objectrdf/actions/workflows/ci.yml/badge.svg)](https://github.com/gtfierro/objectrdf/actions/workflows/ci.yml)

Author RDF building models — [Brick](https://brickschema.org),
[ASHRAE 223P](https://open223.info), [WATR](https://watermetadata.org) — as
plain, typed Python. No RDF in user code; real Turtle out.

Bundled ontologies: Brick 1.4.2, ASHRAE 223P (v1.0.0-2026), and WATR
v0.3.0.rc1, a WATR release candidate whose terms may still change before
0.3.0.

```python
from objectrdf import Model
from objectrdf.brick import AHU, VAV, Building, Level, Room

with Model("urn:example/bldg1#") as model:
    with Building("bldg1"):
        with Level("floor1"):
            Room("room101")

    ahu = AHU("ahu1", label="Main AHU")
    ahu >> VAV("vav-101")          # brick:feeds

model.save("bldg1.ttl")
print(model.validate())            # SHACL via shifty, errors name your objects
```

The ontology classes are generated code, so editors and type checkers see
everything: completion, ontology definitions on hover, and type errors when a
link's range doesn't fit.

## Install and run the examples

Objectrdf requires Python 3.12 or newer. From a checkout of this repository,
install the project and its dependencies with
[uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Then run an example from the repository root:

```bash
uv run python examples/brick/quickstart/brick_quickstart.py
uv run python examples/s223/ahu/s223_quickstart.py
uv run python examples/watr/treatment/watr_quickstart.py
uv run python examples/watr/asm2d/watertap_asm2d.py
```

Each example prints a short summary and writes its generated Turtle file next
to the example script. See [examples/](examples/) for more scenarios.

- Docs: [docs/index.md](docs/index.md)
- Learning book: [docs/book/](docs/book/README.md) (tutorials, guides,
  lifecycle explanation, generated API reference)
- Query existing RDF as typed objects: [docs/querying.md](docs/querying.md)
- Z3 resolution and media hints: [docs/s223.md](docs/s223.md#giving-the-solver-media-hints)
- Quantities, scalar values, and stream composition:
  [docs/quantities.md](docs/quantities.md)
- Design rationale and roadmap: [DESIGN.md](DESIGN.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- Examples organized by ontology: [examples/](examples/)
- Brick quickstart:
  [examples/brick/quickstart/brick_quickstart.py](examples/brick/quickstart/brick_quickstart.py)
- WaTr treatment example:
  [examples/watr/treatment/watr_quickstart.py](examples/watr/treatment/watr_quickstart.py)

## Domain configurations and quantities

Reusable equipment layouts and property metadata are defined in RDF and SHACL.
The compiler generates typed configurations and immutable value schemas:

```python
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.watr.asm2d import AerobicStage, AerobicDesign, OxygenOutletState

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

See [the configuration guide](docs/shacl-configurations.md) and the
[ASM2d example](docs/asm2d-example.md). Regenerate the supplied domains with
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

Regenerate the Brick package: see [docs/codegen.md](docs/codegen.md).
