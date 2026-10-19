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

The main output is `__init__.py` in the target directory. Regeneration
from the same input is byte-identical (tested), so ontology upgrades show up
as reviewable diffs.

When the source has a punned enum hierarchy, generation also writes
`enums.py`. Its top level exports the root and major branches for interactive
completion, such as `enums.Substance.Medium`. Every generated value is also
available under its flat Python name in `enums.values`, such as
`enums.values.Fluid_Water`. Each hierarchy node exposes its direct children
through attribute completion.

## What maps to what

### Domain configurations and property schemas

An extension ontology can identify an installed base package using
`codegen:baseModule`. Its SHACL shapes then compile into typed equipment
configurations with named ports, required values, replaceable defaults, and
immutable quantity schemas. The same CLI accepts these extensions:

```bash
objectrdf gen --file ontology/asm2d.ttl --name ASM2d \
    --source ontology/asm2d.ttl --out src/objectrdf/watr/asm2d
```

See [SHACL configurations](shacl-configurations.md) for source annotations,
supported constructive constraints, and regeneration. Domain authors maintain
RDF and SHACL; model authors import the generated classes.

### Ontology classes and properties

| Ontology | Generated Python |
|---|---|
| `owl:Class` / `rdfs:Class` | class (subclassing `Entity`) |
| `rdfs:subClassOf` | Python inheritance (`isinstance` mirrors subsumption) |
| `rdfs:label`, `skos:definition`/`rdfs:comment` | `meta` + class/attribute docstrings |
| property with `rdfs:domain`/`schema:domainIncludes` | descriptor on the domain class |
| `sh:property` with `sh:minCount >= 1` | required constructor kwarg |
| `sh:qualifiedValueShape [sh:class C]` with `sh:qualifiedMinCount >= 1` on an overlay `class_properties` predicate | class default: `C` is added unless the author supplies `C` or a subclass, and the kwarg becomes optional |
| `sh:property` with `sh:maxCount 1` | scalar attribute (`RelOne`/`Lit`) |
| `sh:class` / `sh:datatype` / `rdfs:range` | type annotation + runtime check |
| untyped declaration of a predicate that is enum-valued wherever it is typed | enum collection accepting any member |
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
- S223 point predicates have canonical Python names: `hasMedium` → `medium`,
  `isConnectionPointOf` → `owner`, `connectsThrough` → `connection`, and
  `pairedConnectionPoint` → `paired_with`. The mapping is scoped to the S223
  IRIs; equivalent local names in Brick and other ontologies keep their normal
  snake_case names. `PropertySpec.predicate` always retains the RDF predicate.
- Generated classes expose only the canonical S223 spellings.
- Collisions with reserved Entity API (`name`, `label`, `comment`, `meta`,
  `model`, `contains`) or keywords get a trailing `_`.
- Distinct IRIs mapping to one name are suffixed `_2`, `_3`, ... in sorted-IRI
  order (deterministic). An `owl:deprecated` term is suffixed before a current
  one, so Brick 1.4's `Building` is `rec:Building` and the deprecated
  `brick:Building` is `Building_2`.
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
uv run python scripts/generate_brick.py
uv run pytest tests/test_brick.py
```

The script bundles Brick's RealEstateCore, QUDT, and other imports into
`_shapes.ttl` through ontoenv. S223 is compiled from the published 223P
document alone, since units and quantity kinds come from `objectrdf.qudt`:

```bash
uv run python scripts/generate_s223.py
```

Base-package generation first relabels blank nodes from their content and
sorts the input triples, so the output does not depend on how an imports
closure happened to be assembled. Regenerating against unchanged upstream
documents is byte-identical.

WaTr is compiled from the checked-in
[v0.3.0.rc1 release](../ontology/README.md) plus its S223 and QUDT imports.
The complete graph is saved in the generated package's `_shapes.ttl`.
The WaTr overlay gives extension terms priority when names collide and
installs the same deferred connection solver:

```bash
uv run python scripts/generate_watr.py
```

The snapshot carries WaTr's 0.2 ontology IRI and version metadata. The
combined PR content is local and is not a published release.
