# Code generation

objectrdf is a compiler: ontology + SHACL in, ordinary Python modules out.
Generated packages are real code (not stubs, not runtime metaclasses), so
editors, type checkers, and debuggers see exactly what runs.

## CLI

```bash
# from a local ontology file
objectrdf gen --file Brick.ttl --name Brick --out src/objectrdf/brick

# by IRI: ontoenv resolves and merges the owl:imports closure
objectrdf gen --iri https://brickschema.org/schema/1.4/Brick \
              --name Brick --out src/objectrdf/brick

# merge extra graphs (e.g. shapes shipped separately)
objectrdf gen --file core.ttl --extra shapes.ttl --name My --out mypkg
```

The output is a single `__init__.py` in the target directory. Regeneration
from the same input is byte-identical (tested), so ontology upgrades show up
as reviewable diffs.

## What maps to what

| Ontology | Generated Python |
|---|---|
| `owl:Class` / `rdfs:Class` | class (subclassing `Entity`) |
| `rdfs:subClassOf` | Python inheritance (`isinstance` mirrors subsumption) |
| `rdfs:label`, `skos:definition`/`rdfs:comment` | `meta` + class/attribute docstrings |
| property with `rdfs:domain`/`schema:domainIncludes` | descriptor on the domain class |
| `sh:property` with `sh:minCount >= 1` | required constructor kwarg |
| `sh:property` with `sh:maxCount 1` | scalar attribute (`RelOne`/`Lit`) |
| `sh:class` / `sh:datatype` / `rdfs:range` | type annotation + runtime check |
| `owl:inverseOf` | automatic inverse maintenance |
| `owl:equivalentProperty` | canonicalized to the ontology's primary namespace |

Properties whose SHACL path is not a plain IRI and constraints that cannot be
expressed constructively still apply at `model.validate()` time. For 223-style
connection points, nested `sh:and`, `sh:or`, and `sh:xone` shapes are preserved
as recursive solver metadata. Nested `sh:or` values on `hasMedium` become slot
medium domains. Branches containing only validation constraints are marked
opaque rather than incorrectly flattened into required slots.

## Solver translation boundary

SHACL Core connection-point structure compiles directly to Z3. Constraints
that exist only as SHACL-SPARQL remain validation-only.

Media likelihood comes from the ontology's permitted-media domains, not a
class-specific preservation flag. For every pair of active ports on an entity,
the optimizer adds an affinity preference only when their compiled domains
overlap. Extension authors therefore influence assignment by publishing
accurate `hasMedium` constraints on qualified ConnectionPoint shapes. Hard
equality exists only across the two endpoints of a Connection.

The `connection_classes` overlay mapping is separate: it maps a resolved
medium or ancestor to the resource to materialize, such as `Fluid-Water` →
`Pipe`. Model authors can add instance-level evidence with `medium=`,
`handle.medium`, or authored ConnectionPoints as described in [Authoring
223P](s223.md#giving-the-solver-media-hints).

**Final solver TODO:** implement a bounded SHACL-SPARQL-to-Z3 translator for
basic graph patterns, equality/inequality, `EXISTS`/`NOT EXISTS`, `UNION`,
subclass paths, and constituent-medium compatibility. Unsupported queries
must remain validation-only. Translated constraints must also distinguish hard
requirements from ranking evidence.

## Naming policy

- Classes keep their IRI local name (`Air_Handling_Unit` stays as-is).
- Properties snake_case their local name (`hasPoint` → `has_point`).
- Collisions with reserved Entity API (`name`, `label`, `comment`, `meta`,
  `model`, `contains`) or keywords get a trailing `_`.
- Distinct IRIs mapping to one name are suffixed `_2`, `_3`, ... in sorted-IRI
  order (deterministic).
- When several namespaces declare the "same" property (Brick bundles
  RealEstateCore), `owl:equivalentProperty` groups are collapsed to the
  primary namespace's member — models serialize with `brick:isPointOf`, not
  `rec:isPointOf`.

## Inheritance repair (MRO)

RDF permits parent combinations Python's C3 linearization rejects. At
generation time each parent tuple is repaired: redundant ancestors dropped,
parents ordered most-derived-first, and — only if C3 still fails — trailing
parents pruned. Pruned links remain visible through `meta.iri`/RDF; they just
don't contribute to the Python MRO.

## UX overlays

Operator sugar and containment rules are *policy*, not ontology fact, so they
live in overlays (`objectrdf/gen/overlays.py`), keyed by ontology name. An
overlay entry that doesn't resolve against a given ontology version is
skipped with a comment in the generated file, so one overlay can serve many
versions. Pass `--no-overlay` to disable, or supply your own
`Overlay` via the Python API (`objectrdf.gen.compile_source`).

## Regenerating the committed packages

```bash
curl -sLO https://brickschema.org/schema/1.4/Brick.ttl
uv run objectrdf gen --file Brick.ttl --name Brick --out src/objectrdf/brick
uv run pytest tests/test_brick.py
```

WaTr is compiled from its extension graph plus the S223 imports closure. The
WaTr overlay gives extension terms priority when names collide and installs
the same deferred connection solver:

```bash
uv run objectrdf gen --file water.ttl --extra 223p.ttl \
  --name WATR --out src/objectrdf/watr \
  --source https://watermetadata.org/water.ttl
uv run pytest tests/test_watr.py
```

A committed lockfile of the imports closure (via ontoenv) is planned; see
DESIGN.md §9.
