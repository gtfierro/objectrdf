# objectrdf

Author RDF building models — [Brick](https://brickschema.org),
[ASHRAE 223P](https://open223.info), [WATR](https://watermetadata.org) — as
plain, typed Python. No RDF in user code; real Turtle out.

```python
from objectrdf import Model
from objectrdf.brick import AHU, VAV, Building, Floor, Room

with Model("urn:example/bldg1#") as model:
    with Building("bldg1"):
        with Floor("floor1"):
            Room("room101")

    ahu = AHU("ahu1", label="Main AHU")
    ahu >> VAV("vav-101")          # brick:feeds

model.save("bldg1.ttl")
print(model.validate())            # SHACL via shifty, errors name your objects
```

The ontology classes are generated code, so editors and type checkers see
everything: completion, ontology definitions on hover, and type errors when a
link's range doesn't fit.

- Docs: [docs/index.md](docs/index.md)
- Query existing RDF as typed objects: [docs/querying.md](docs/querying.md)
- Z3 resolution and media hints: [docs/s223.md](docs/s223.md#giving-the-solver-media-hints)
- Quantities, scalar values, and stream composition:
  [docs/quantities.md](docs/quantities.md)
- Design rationale and roadmap: [DESIGN.md](DESIGN.md)
- Examples organized by ontology: [examples/](examples/)
- Brick quickstart:
  [examples/brick/quickstart/brick_quickstart.py](examples/brick/quickstart/brick_quickstart.py)
- WaTr treatment example:
  [examples/watr/treatment/watr_quickstart.py](examples/watr/treatment/watr_quickstart.py)

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests examples
uv run ty check src tests examples
```

Regenerate the Brick package: see [docs/codegen.md](docs/codegen.md).
