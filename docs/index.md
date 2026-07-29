# objectrdf

Author RDF building models — Brick, ASHRAE 223P, WATR — as plain, typed
Python. No IRIs, no triples, no namespaces in user code; the RDF appears when
you call `model.save()`.

```python
from objectrdf import Model
from objectrdf.brick import AHU, VAV, Building, Floor, Room

with Model("urn:example/bldg1#") as model:
    with Building("bldg1"):
        with Floor("floor1"):
            room = Room("room101")

    ahu = AHU("ahu1", label="Main AHU")
    vav = VAV("vav-101")
    ahu >> vav                     # brick:feeds, negotiated by the library

model.save("bldg1.ttl")            # valid Brick Turtle
print(model.validate())            # SHACL validation (via shifty)
```

Because the ontology classes are *generated code* (not runtime magic), your
editor and type checker see everything: completion on `ahu.`, hover-docs
showing the ontology's own `skos:definition`, and a red squiggle when you
`feeds` something that can't be fed.

For 223P, one operator replaces the whole connection ceremony:

```python
from objectrdf.s223 import Damper, Fan

oad = Damper("oa-damper")   # shape-required connection points appear
oad >> Fan("supply-fan")    # media negotiated, Duct created, inverses set
```

## Documentation

- [Authoring models](authoring.md) — the Model, containment, `>>`, validation
- [Querying existing models](querying.md) — hydrate RDF as typed objects
- [Authoring 223P](s223.md) — enums, connection negotiation, 223 specifics
- [Authoring WaTr](watr.md) — water-treatment classes on the S223 topology model
- [Code generation](codegen.md) — how ontologies become Python packages
- [Architecture](architecture.md) — how the runtime works inside
- [DESIGN.md](../DESIGN.md) — the full design rationale and roadmap
- [Quantities and nominal stream state](quantities.md)
- [Current implementation roadmap](roadmap.md)

## Status

Phases 1–2 (see DESIGN.md §13): core runtime + compiler + generated Brick
1.4, 223P, and WaTr packages, including enum namespaces, deferred connection
compilation, and a mutable typed object view over existing RDF graphs.
BuildingMOTIF templates and broader round-trip coverage are subsequent phases.

## Development

```bash
uv sync            # install
uv run pytest      # tests
uv run ruff check src tests examples
uv run ty check src tests examples
```
