# objectrdf — Design

An object-oriented authoring layer for RDF building/water models (Brick, ASHRAE 223P, WATR).
Practitioners write plain Python against typed classes; RDF is produced behind the scenes.
No IRIs, no triples, no namespaces in user code.

Inspired by (and inverting) [semantic_objects](https://github.com/lazlop/semantic_objects):
that project authors Python dataclasses and generates SHACL from them. Here the ontology +
SHACL is the source of truth and the Python surface is synthesized from it.

---

## 1. The central architectural decision: compile, don't conjure

The requirements "synthesize classes dynamically from RDF" and "type annotations everywhere
so LSPs and type checkers work" are in direct tension. Anything built at runtime with
metaclasses/`type()` is invisible to pyright/mypy and to editor completion.

**Decision: objectrdf is a compiler.** A codegen pipeline reads the ontology (+ SHACL shapes,
+ optionally BuildingMOTIF templates) and emits ordinary Python modules — real `.py` files,
not `.pyi` stubs, so the static view and runtime behavior cannot drift apart. Precedent:
protobuf, sqlacodegen, OpenAPI generators.

```
ontology.ttl ─┐
shapes.ttl  ──┼─▶  objectrdf-gen  ─▶  generated package (brick/, s223/, watr/)
templates/  ──┘                          │
                                         ▼
                    small stable runtime (objectrdf core)
                    Model, Entity, Relation, connection negotiation,
                    rdflib serialization, pyshacl validation
```

Consequences:

- Ship pre-generated, versioned packages: `objectrdf.brick` (Brick 1.4.x),
  `objectrdf.s223` (223P 1.0), `objectrdf.watr`. Users `pip install objectrdf[brick]`
  and import; they never run the generator unless they have a custom extension ontology.
- Ontology upgrades become reviewable diffs of generated code.
- The generator is also a public CLI for extension ontologies and site-specific templates:
  `objectrdf gen --ontology myext.ttl --base objectrdf.s223 -o mysite/`.
- Generated code is deliberately boring and declarative — thin classes over runtime
  descriptors — so it's greppable and debuggable.

## 2. Class synthesis rules

### Hierarchy
- `rdfs:subClassOf` → Python inheritance. Brick's tree maps cleanly; where RDF has multiple
  superclasses, use Python multiple inheritance with a C3-safe ordering; if a cycle or
  un-linearizable diamond appears, flatten to the primary parent and record the rest as
  runtime metadata (still emitted as extra `rdf:type`/subclass semantics in output RDF).
- Python `isinstance()` therefore mirrors ontology subsumption — this is what makes the
  type system enforce e.g. `feeds: Equipment` for all AHU subclasses for free.
- Abstract/organizational classes (e.g. Brick's `Class` roots, 223 `Connectable`) are
  generated but marked abstract where instantiation makes no sense.

### Properties from SHACL
223 classes *are* node shapes; Brick 1.4 ships shapes as well. For each `sh:property`:

| SHACL | Python |
|---|---|
| `minCount >= 1` | required, keyword-only constructor arg |
| `minCount` absent/0 | optional, defaults to `None`/empty |
| `maxCount 1` | scalar attribute `T \| None` |
| no `maxCount` | typed collection `RelSet[T]` |
| `sh:class C` | annotation is the generated class for `C` |
| `sh:datatype` | mapped Python literal type (`float`, `str`, `datetime`…) |
| `sh:in` / EnumerationKind | generated enum-like namespace (see §5) |
| `sh:or` | `Union[...]` annotation |
| qualified shapes (223 connection-point counts) | consumed by the connection negotiator (§6), not surfaced as attributes |

Attribute names come from `rdfs:label`/`skos:prefLabel`, snake_cased, with a deterministic
collision policy (suffix by property namespace prefix on conflict). Original IRI, label,
and definition live in metadata and in the generated docstring — so hover-docs in the
editor show the ontology's own definitions.

### Required vs optional surface
Two candidate UXs:

1. **Flat (recommended):** everything is an attribute; required ones are required
   keyword-only constructor args, optional ones default to `None`. The constructor
   signature *is* the documentation of what's mandatory, and the type checker enforces it
   at the call site (`AHU(...)` missing a required arg is a red squiggle).
2. **`obj.optional.foo` sub-namespace:** keeps tab-completion on the instance short.
   Cost: every property access decision requires knowing its cardinality class; refactors
   when an ontology version changes a `minCount` break user code syntactically.

**Decided: flat.** "Is this required" is a constructor-time concern, not a
navigation-time concern. If instance completion noise becomes real, mitigate with
`__dir__` ordering and doc grouping rather than a namespace split.

## 3. Typed relationships

Relationships are typed descriptors generated from the property's SHACL/schema:

```python
class Equipment(Entity):
    feeds: RelSet[Equipment]        # brick:feeds, domain/range from shapes
    has_part: RelSet[Equipment]
    has_point: RelSet[Point]
```

- `ahu.feeds.add(vav)` — `add` is typed `(Equipment) -> None`; passing a `Room` is a
  static type error *and* a runtime `TypeError` (runtime double-checks via isinstance,
  since not everyone runs a checker).
- Constructor sugar: `AHU("ahu1", feeds=[vav1, vav2])`.
- Where a subclass's shapes narrow a range (qualified constraints), the generated subclass
  re-declares the descriptor with the narrower parameter — checkers see the narrowing.
- Inverse maintenance: `vav.fed_by` reflects automatically (both views over one edge store
  owned by the Model).

## 4. The Model (session) object

```python
from objectrdf import Model
from objectrdf.brick import AHU, VAV, Supply_Fan

with Model("urn:ex/bldg1#") as m:
    fan = Supply_Fan("sf1", label="Supply Fan 1")
    ahu = AHU("ahu1", has_part=[fan])
    vav = VAV("vav1", fed_by=[ahu])

m.save("bldg1.ttl")          # rdflib under the hood; user never sees it
report = m.validate()        # shifty, errors mapped back to Python objects
```

- Entities bind to the ambient model (contextvar) so authoring code stays clean;
  `Model.add()` / `model=` kwarg exist for explicit style and for library code.
- The first constructor arg is the local name; the model's namespace makes the IRI.
  `label` defaults from the name.
- `m.graph` exposes the rdflib Graph for escape hatches, but nothing in the happy path
  needs it.
- `m.validate()` runs the ontology's shapes (via shifty, §9) and translates violation reports into messages
  referencing Python identifiers ("`vav1` (VAV): missing required `has_point` of type
  `Supply_Air_Flow_Sensor`"), not blank nodes and IRIs.
- Round-tripping (loading an existing TTL into objects) is explicitly **out of scope for
  v1** — authoring first — but the edge-store design shouldn't preclude it.

## 5. Enumerations (223 EnumerationKind, QUDT units)

223's punned enumeration hierarchy (`s223:Medium-Air`, `s223:Water-ChilledWater`, roles,
aspects) becomes generated constant namespaces that preserve the hierarchy:

```python
from objectrdf.s223.enums import Medium, Role
Medium.Water.ChilledWater      # usable anywhere a Medium is expected
```

Hierarchy-aware compatibility (`ChilledWater` *is a* `Water`) is used by the
connection negotiator and by validation. QUDT units and quantity kinds are
compiled named-individual references rather than locally minted entities:
`quantity(Property, "temperature", 72.5, units.DEG_F,
quantity_kinds.Temperature)`. See `docs/quantities.md`.

## 6. The 223 connection model: negotiation + operators

The pain: manually authoring `Connectable → ConnectionPoint → Connection → ConnectionPoint
→ Connectable` plus media and directions. The abstraction: **users connect equipment;
the library works out the plumbing.**

```python
from objectrdf.s223 import Damper, Fan, VAV
from objectrdf.s223.enums import Medium

oad = Damper("oa-damper")
sf  = Fan("supply-fan")
vav = VAV("vav-101")

oad >> sf >> vav      # creates ConnectionPoints (if needed), Connections, media, directions
```

Negotiation algorithm for `a >> b`:
1. Candidate pairs = (outlet-capable CPs of `a`) × (inlet-capable CPs of `b`), including
   CPs *required by shape but not yet instantiated* (223 shapes say a Fan must have an
   air inlet and outlet — the negotiator can materialize them).
2. Filter by medium compatibility using the enum hierarchy; prefer unbound CPs over bound.
3. Exactly one candidate → create/reuse CPs, create the `Connection`, set medium,
   directions, `connectsThrough`, etc.
4. Zero candidates → error explaining media/directions available on each side.
   More than one → error listing the candidates *and the exact code to disambiguate*.

Disambiguation and access to the underlying pieces:

```python
chiller.outlet(Medium.Water.ChilledWater) >> pump          # pick CP by medium
connect(ahu, vav, medium=Medium.Air)                       # functional form; returns the Connection
c = connect(sf, vav)
c.observes(FlowSensor("sf-flow"))                          # sensors on connections/CPs stay reachable
```

- **Decided:** `>>` returns its right operand so chains read left-to-right along the flow
  direction; `<<` is the mirror. When you need the `Connection` object itself, use
  `connect()`.
- Connection class (Duct/Pipe/Wire) is inferred from medium with an override kwarg.
- Brick gets the same operators as sugar for `feeds` (`ahu >> vav` ≡ `ahu.feeds.add(vav)`),
  so muscle memory transfers across ontologies; WATR reuses the 223 machinery outright.

## 7. Containment

Containment (spatial hierarchy, part-of, equipment location) gets the same treatment as
connections: users express *what contains what*, and the right predicate is negotiated
from the (container type, containee type) pair.

Two syntaxes, same edge:

```python
# 1. Context-manager nesting — reads like the hierarchy it builds
with Site("campus") as site:
    with Building("b1"):
        with Floor("f2") as f2:
            r201 = Room("r201")
            vav  = VAV("vav-201")          # equipment created in a Room scope → located there

# 2. Explicit — for after-the-fact or programmatic construction
f2.contains(Room("r202"), Room("r203"))
site.contains(chiller_plant)
```

- Entering an entity's `with` block pushes it onto an ambient containment stack
  (same contextvar mechanism as `Model`); entities constructed inside are attached to the
  innermost compatible container.
- Predicate negotiation is table-driven per ontology, derived from the shapes:
  Brick `Location`×`Location` → `hasPart`, `Location`×`Equipment` → `hasLocation`
  (inverse edge), `Equipment`×`Equipment` → `hasPart`; 223 space/space, space/equipment,
  and domain-space enclosure map to their respective 223 predicates. Ambiguity or
  incompatibility errors follow the connection-negotiator style: say what was tried,
  show the code that disambiguates (`f2.contains(vav, via=Brick.hasLocation)` escape
  hatch, still no raw RDF in the common path).
- `contains()` is variadic, returns the container for chaining, and accepts the same
  entities the constructor `contains=[...]` kwarg does.

## 8. Class & instance metadata hooks

Every generated class carries its ontology provenance, reachable without touching RDF
but exposing it faithfully for tooling that wants it:

```python
AHU.meta.iri          # "https://brickschema.org/schema/Brick#AHU" (str)
AHU.meta.label        # rdfs:label
AHU.meta.definition   # skos:definition / rdfs:comment text
AHU.meta.ontology     # OntologyInfo(name="Brick", version="1.4.2", iri=..., source=...)
AHU.meta.parents      # direct ontology superclasses (as Python classes)
AHU.meta.properties   # PropertySpec list: name, predicate IRI, cardinality, range, source shape
AHU.meta.shape        # the SHACL shape(s) governing this class (as text/graph on demand)
```

- `meta` is a class-level descriptor that also works on instances; instances add
  `x.meta.cls`, `x.meta.iri` (the minted instance IRI), and `x.meta.model`.
- Instance conveniences stay top-level: `x.name` (local name), `x.label` (settable,
  defaults from name), `x.comment`.
- `name`, `label`, `comment`, and `meta` are **reserved names**; ontology properties that
  snake_case onto them get mangled per the collision policy (§12). Everything in `meta`
  is what the docstring generator uses, so hover-docs, `help()`, and `meta` never
  disagree.

## 9. Toolchain: ontoenv + shifty

Both the generator and the runtime lean on two existing tools:

**[ontoenv](https://ontoenv.gtf.fyi)** — ontology dependency resolution for the compiler.
`objectrdf gen` takes ontology IRIs, not file paths; ontoenv resolves the `owl:imports`
closure (Brick→ref schemas, 223→QUDT, extensions→base ontologies), caches it, and makes
codegen reproducible. A lockfile (pinned versions/hashes of the closure) is committed
next to the generated packages so regeneration is a verifiable no-op. Wishlist if needed:
first-class lockfile support in ontoenv itself.

**[shifty](https://shifty.gtf.fyi)** (via `pyshifty`) — SHACL validation *and* SHACL-AF
inference. This is load-bearing for 223, where normative semantics live in `sh:rule`s
(connection-point closure, `connected`/`connectedTo` derivation, medium assignment):

- `m.validate()` → shifty validation over the generated model + ontology shapes, report
  translated to Python-object terms.
- `m.infer()` (or automatically inside `validate()`) → run rules to fixed point; users
  author the minimal asserted graph, inference materializes the rest. `m.save()` gains
  `inferred=False|True` to control which graph is emitted.
- At **codegen time**, shifty computes effective flattened shapes per class (inherited +
  rule-implied constraints), so the negotiation tables and property specs come from the
  post-inference view of the ontology rather than hand-rolled shape walking.
- The WASM build opens a later door: in-browser "Python you write / TTL you get" docs
  playground with live validation.

Candidate shifty feature asks (will file as they firm up): a structured (JSON) validation
report with focus node + source shape + result path for clean mapping back to Python
objects; targeted validation (given focus nodes only) for fast feedback in the authoring
loop; an API to expose the compiled/flattened per-class property constraints so the
codegen doesn't re-derive them.

## 10. BuildingMOTIF templates as classes

A template whose `name` parameter targets class `C` generates a subclass of `C`:

```python
# from a template library for a site/project
class MakeupAirUnit(s223.AirHandlingUnit):     # template 'makeup-air-unit'
    def __init__(self, name, *, sf: Fan | None = None, ...):  # template params
        ...
```

- Template params → constructor args (typed from the param's shape/class in the body).
- Instantiating expands the template body into the model; dependencies resolve
  recursively; unfilled optional params can be filled later (`mau.fill(...)`).
- Inverse direction also falls out of the design: every generated class knows its shape,
  so `MakeupAirUnit.as_template()` can emit a MOTIF template — keeping objectrdf
  interoperable with the existing MOTIF ecosystem rather than parallel to it.
- The generator accepts template libraries as an input alongside ontologies, so a site's
  `templates/` directory becomes a typed Python module.

## 11. Package layout & stack

```
objectrdf/
  core/            # Entity, Model, RelSet, descriptors, edge store
  connect/         # 223 negotiation engine (medium/direction resolution)
  gen/             # the compiler: ontology+SHACL+templates -> python modules
  brick/           # generated (committed, versioned)
  s223/            # generated
  watr/            # generated
  cli.py           # objectrdf gen ...
```

- uv project, `ruff`, `ty`/pyright in CI **run against the generated packages and the
  example scripts** — the examples are the real test of the typing story.
- rdflib for graph construction/serialization (oxrdflib as optional accelerator),
  pyshifty for validation + inference, ontoenv for ontology resolution in the compiler.
- Generated-code snapshot tests: regenerating from pinned ontology versions must be a
  no-op diff.

## 12. Known hard problems (tracked, not hand-waved)

- **Name mangling collisions** after snake_casing labels across namespaces — needs a
  deterministic, documented policy.
- **MRO** for multi-parent RDF classes — flattening policy must be stable across
  ontology releases or generated code churns.
- **SHACL expressivity**: `sh:or`/`sh:xone` over shapes, closed shapes, SPARQL-based
  constraints — v1 maps the tractable subset, passes the rest through to
  `m.validate()` so nothing is silently lost.
- **223 inferred vs asserted** triples (e.g. `connected` closure): emit asserted-only,
  rely on reasoning downstream; document which profile the output targets.
- **Chained `>>` with junctions/tees** (one outlet feeding two inlets) — chains cover the
  linear case; fan-out uses explicit `connect()` or `a >> (b, c)` later.

## 13. Phasing

1. **Core + Brick** (simpler graph model, no connection negotiation): compiler (on
   ontoenv), Entity/Model/RelSet, flat attribute UX, containment contexts, `meta` hooks,
   serialization, shifty-backed validation mapping. Deliverable: the Brick authoring
   example above runs and type-checks.
2. **223 + WATR**: enumeration namespaces, connection negotiation, `>>`/`connect()`,
   QUDT-backed properties, rule-based inference on save/validate.
3. **Templates**: MOTIF template ingestion → generated subclasses; `as_template()` export.
4. **Polish**: round-trip loading, error-message UX, docs site with side-by-side
   "Python you write / TTL you get" panes.
