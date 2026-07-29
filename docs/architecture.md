# Architecture

```
user script
    │  plain typed Python                     existing RDF graph
    ▼
generated package (objectrdf.brick, ...)      ← output of objectrdf.gen
    │  classes, PropertySpecs, registries          │
    │                                              ▼
    │                                      query hydration (core/query.py)
    ▼
runtime core (objectrdf.core)
    │  Entity / Model / descriptors / deferred intentions
    ▼
Z3 resolution (objectrdf.solver223)
    │  immutable compiled snapshot
    ▼
rdflib (serialization) · shifty (SHACL) · ontoenv (imports resolution)
```

## Runtime core (`src/objectrdf/core/`)

- **`meta.py`** — the data generated code instantiates: `OntologyInfo`,
  `PropertySpec` (one attribute: predicate, kind, ranges, cardinality,
  inverse), `ClassInfo` (per-class provenance), and the per-package
  `Registry` that resolves string range names to classes at runtime.
- **`entity.py`** — the `Entity` base. Construction binds to the ambient
  `Model`, applies constructor kwargs through descriptors, enforces required
  properties, then attaches to any open containment scope; any failure after
  binding unbinds (no ghost entities). `.meta` serves `ClassMetaView` /
  `InstanceMetaView`. `>>`/`<<` read the class's `_RSHIFT` property.
- **`relations.py`** — descriptors covering object relations, literals,
  enumeration values, compiled vocabulary terms, and unconstrained scalar
  values. `ValueOne` implements predicates such as S223 `hasValue`, accepting
  either a Python literal or named RDF resource without forcing a wrapper
  node. All descriptors range-check with the same semantics as the generated
  annotations. Inverse edges are mirrored by writing directly into the
  partner's store (no recursion).
- **`containment.py`** — the ambient `with` stack (a `ContextVar`) plus the
  per-package `ContainmentTable`; `attach()` walks the stack innermost-first
  and applies the first matching rule, raising with guidance otherwise.
- **`model.py`** — namespace, IRI minting, name uniqueness, entity lookup,
  revision tracking, resolution caching, and the only rdflib-touching
  serializer. It also exposes typed selection and tracked mutation over loaded
  graphs.
  Serialization and validation of authored models operate on resolved
  snapshots; output graphs declare an `owl:Ontology` and import the generated
  packages and compiled vocabularies they reference.
- **`query.py`** — optionally runs shifty inference, chooses the most-specific
  generated class for each typed RDF resource, hydrates generated attributes,
  and implements the `find`/`find_all` filter semantics. Generated attribute
  changes replace their managed triples while unmodeled RDF is preserved.
- **`resolution.py`** — stable authored `ConnectionHandle`s, staged generated
  property collections, and the `ResolutionReport`/`ResolvedModel` public API.
- **`validation.py`** — runs shifty, then translates the standard SHACL
  report graph into `Issue`s that reference entities and attribute names.

Design invariant: **user-facing errors speak Python** (class names, attribute
names, entity names), and where the fix is mechanical the message contains
the exact code to write.

## Compiler (`src/objectrdf/gen/`)

Three stages, strictly separated:

1. **`schema.py`** — all RDF interpretation. Produces a plain-dataclass IR:
   classes (topologically ordered, MRO-repaired), properties (domain- and
   SHACL-derived, predicates canonicalized over `owl:equivalentProperty`).
2. **`emit.py`** — a dumb renderer of the IR. Emits aliased runtime imports
   (so ontology names like RealEstateCore's `Entity` can't shadow the base),
   specs, classes with docstrings from the ontology text, and explicit typed
   `__init__` methods wherever a class changes the property set.
3. **`overlays.py`** — per-ontology UX hints (rshift property, containment
   rules), applied at the end of the module with unresolvable entries
   skipped-with-comment.

`tests/toy.py` is a hand-written module in exactly the emitter's shape; the
core test suite runs against it so runtime and compiler stay independently
testable. `tests/test_gen.py` compiles `tests/fixtures/mini.ttl` and asserts
behavior (including that emitted code passes `ty check` and that generation
is deterministic).

## The 223 layer

- **`core/enums.py`** — `EnumValue` constants for punned enumeration
  hierarchies, with `is_a()` walking the parent chain; generated packages
  ship them in an `enums` submodule and register them with the Registry.
- **`connect223.py`** — the connection front end (`S223Connector`),
  installed on the generated `Connectable` root by overlay code. It has two
  jobs: `on_create` materializes shape-required connection points the moment
  equipment is constructed when a slot has one fixed medium, and `connect`
  records a deferred intention.
- **`solver223.py`** — partitions intentions by shared endpoints, encodes
  shape alternatives, cardinality, class, and permitted-media constraints in
  Z3, then ranks valid assignments by domain overlap. It checks uniqueness,
  caches unchanged component plans, and materializes derived objects in an
  immutable clone. Unsatisfiable cores refer back to authored handles and
  entities.
- **Compiler additions** — metaclass-aware class collection (223 types
  classes with `s223:Class`/`s223:AbstractClass`), `s223:inverseOf`
  handling, the punned enum-subtree carve-out, scalar `hasValue` recognition,
  CP-slot extraction, and the
  medium-domain extraction, and the mutually-required-cycle demotion
  documented in [s223.md](s223.md).

## Later phases

- BuildingMOTIF templates as generated subclasses; `as_template()` export;
- blank-node hydration and refresh after direct rdflib mutations.
