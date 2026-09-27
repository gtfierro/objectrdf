# Portable recipe classes: implementation plan

Status: implemented. This document records the design for reusable, typed
authoring classes whose definitions have the same meaning in Python, the
connection solver, and exported RDF. The first complete example is a coil with
air and chilled-water sides. The implementation and public usage are documented
in [recipes.md](recipes.md).

## Outcome and authoring contract

An extension author declares facts shared by every instance. A normal model
author instantiates the class and connects equipment without creating RDF
connection points by hand:

```python
class AirWaterCoil(ChilledWaterCoil):
    class_iri = "urn:example:recipes#AirWaterCoil"
    ontology_iri = "urn:example:recipes"
    air = ConnectionPoint.declare(
        count=2,
        medium=fixed(enums.Fluid_Air),
        direction=choose("in", "out"),
        label=default("Air connection"),
    )
    water = ConnectionPoint.declare(
        count=2,
        medium=fixed(enums.Water_ChilledWater),
        direction=choose("in", "out"),
    )

with Model("urn:example:building#") as model:
    coil = AirWaterCoil("coil-1")
    fan = Fan("supply-fan")
    chiller = Chiller("chiller")
    fan >> coil
    chiller >> coil
```

The class metadata is explicit because the recipe defines a portable RDF class.
Class-level policies and point declarations remain ordinary Python attributes.

The example above establishes two incoming flow intentions, but the inherited G36
`ChilledWaterCoil` shape also requires a connected `ChilledWaterValve`. A full
valid-model example must provide one and complete the outgoing paths. Use
`CoolingCoil` for isolated port tests and `ChilledWaterCoil` plus valve for
end-to-end validation tests. Never describe a graph that only resolves port
topology as fully conforming.

## Agreed design rules

1. **A named recipe subclass is portable.** It has an explicit RDF class IRI,
   `rdfs:subClassOf` its ontology parent, and an exportable SHACL shape. The
   generated graph imports the recipe ontology and its parent ontology. The
   class registers for `Model.from_graph()` hydration. A Python-only preset may
   be offered separately, but must not be presented as a portable class.
2. **A declaration is not an entity.** A class body runs before an instance or
   `Model` exists. `ConnectionPoint.declare(...)` returns a typed declaration
   descriptor. `ConnectionPoint(...)` remains construction of one concrete RDF
   entity. Do not overload ordinary entity construction based on ambient state.
3. **Policy strength is explicit.** `fixed(value)` is an invariant;
   `default(value)` initializes new instances and is replaceable;
   `choose(...)` restricts a value that is determined later. These rules apply
   to equipment properties and associated objects, not only port media. A
   property setter, solver, and validator must agree on fixed constraints.
4. **Unknown direction differs from bidirectional.** An undecided declaration
   can materialize as an inlet or outlet after connections determine it. A
   declared `BidirectionalConnectionPoint` remains that RDF class and permits
   flow either way. Do not represent uncertainty by asserting bidirectionality.
5. **Automatic connection is explainable.** `fan >> coil` and `chiller >> coil`
   match by direction, medium, role, capacity, and inherited constraints.
   Meaningfully distinct remaining candidates require an explicit point; no
   silent arbitrary routing. The resolved model identifies the selected point
   and reason, including when the author used `>>` rather than `connect()`.
6. **Python names are canonical per RDF predicate.** For S223 and WaTr point
   properties, use `medium`, `owner`, `connection`, and `paired_with` for
   `hasMedium`, `isConnectionPointOf`, `connectsThrough`, and
   `pairedConnectionPoint`. Apply the mapping in code generation so generated
   descriptors, constructors, recipes, examples, errors, and type hints agree.
   Keep the original predicate in `PropertySpec`/`.meta`. Do not globally strip
   `has_` or maintain two independent stores under old/new names. A separate
   friendly `media.Air` vocabulary is optional later; this work may use the
   existing typed `enums.Fluid_Air` constants.

## Declaration semantics and public objects

Implement a small typed policy model and a class-level descriptor, preferably
in a focused runtime module under `src/objectrdf/core/`. Avoid a metaclass
unless a descriptor and class decorator cannot express the behavior.

- `fixed(x)` records an exact authored value and a hard constraint. Assigning
  an incompatible value raises immediately. The solver uses it, and the
  exported shape validates it. Falsey values such as `0`, `False`, and `""`
  remain present values.
- `default(x)` initializes *new* instances only. An assignment replaces it
  after normal type/range checks. Copy mutable collections per instance.
  Hydrating an existing RDF graph must not silently fill a missing default or
  mutate the source graph.
- `choose(a, b, ...)` records allowed values without prematurely selecting
  one. The solver selects only when constraints make the choice unique. A
  remaining meaningful choice makes strict compilation fail with an action
  the author can take.
- Subclasses inherit declarations. They may narrow `choose` to `fixed` and
  override a `default`. Reject incompatible fixed facts at class definition.
  Check inherited ontology/SHACL restrictions as early as practical, then run
  full shape validation at compilation.
- A declaration of one point exposes a stable per-instance `PointRef`. A
  declaration with `count > 1` exposes a `PointGroupRef`. Use the current
  `PortHandle` internally if helpful, but do not expose an authored object
  whose Python class changes after resolution. `resolved.point(ref)` maps a
  single reference to its concrete connection point; a group maps to concrete
  points. The reference can constrain an explicit `connect()` call.
- Ports in one count group with identical declared facts are interchangeable.
  Solver permutations of them are one solution. Distinct names, roles,
  properties, or owner relationships make points meaningfully different;
  report ambiguity when such points still compete. Do not expose unstable
  list indices as semantic identities. If a user needs a named physical point,
  let them declare a separate named point.
- Use the same policy engine for non-port property values and links. Define a
  clear class-level declaration site for those properties without overriding
  generated Python descriptors. Even if the first example only fixes port
  medium and defaults a label, do not build a port-specific policy mechanism
  that cannot later express roles, quantity terms, or linked children.

Each recipe instance must expose its point references through descriptors or
model-owned storage. Do not attach plain `self.air` attributes during
`__init__`: snapshot cloning in `solver223._clone_model()` copies entity data
and relationships, not arbitrary instance attributes. Construction must be
atomic. If a recipe fails after reserving names, registering point references,
or linking child entities, restore the model and inverse links completely.
Recipe-created helper objects must not accidentally attach to an open spatial
containment scope. Reserved-name collisions must raise `ModelingError`, not a
raw `KeyError`.

## Resolver and connection behavior

Extend the authored-point representation in `core/resolution.py` and the
solver in `solver223.py`. Today `Entity.port()` requires `"in"`, `"out"`, or
`"bi"`; `_make_points()` assigns a corresponding concrete point class, and
`_components()` starts only from connection intentions. Recipe declarations
need an allowed-direction domain and must participate even if no connection
has yet been authored. Refactor components as needed so an unconnected recipe
does not silently disappear from compilation.

The solver must combine:

- source outlet and target inlet compatibility, including genuinely
  bidirectional points;
- exact/allowed media and enum hierarchy compatibility;
- inherited SHACL point counts and `and`/`or`/`xone` layouts;
- recipe point counts, allowed directions, roles, and point capacity;
- explicit `PointRef`/`PointGroupRef` endpoint selection and existing concrete
  points;
- fixed facts on the recipe class.

Track the selected named point and resolved direction as observable solver
choices. The current uniqueness check aggregates some choices by point class;
that is insufficient when two same-class points have different names or
properties. Canonicalize interchangeable points, but surface meaningful ties.
An explicit `connect(fan, coil.water)` must fail for incompatible medium and
must not leave a partial relation. `fan >> coil` may remain deferred until
`check()` or `compile()`, but the error must name the author-facing entities,
candidate points, and a concrete way to disambiguate. Extend explanation
lookup so users can inspect operator-authored links without having retained a
`ConnectionHandle`.

## Ontology export, validation, and hydration

The class decorator should validate metadata and register the class only
after its declarations pass checks. Avoid duplicate class IRIs and name
collisions in `Registry`. Store the recipe schema graph with the registry or
an associated package, and include it when `Model.validate()` gathers shapes.
Provide a documented export path for the extension ontology and shapes. Use
stable IRIs for generated shape nodes so repeated export is deterministic.

The exported schema needs the recipe `owl:Class`, `rdfs:subClassOf` parent,
`owl:Ontology` declaration, and imports of parent ontologies. Translate fixed
facts to applicable SHACL constraints (`sh:hasValue` where appropriate),
allowed choices to `sh:in`/`sh:or`, and point groups to qualified counts over
`hasConnectionPoint`, point type/direction, and medium. Defaults must not be
SHACL requirements. Preserve the inherited G36 and base S223 shapes during
validation. If individual Python slot names cannot be distinguished in RDF,
export the shared RDF-observable count/constraints. For a truly distinct slot,
require a portable distinguishing role, type, or predicate rather than
claiming a Python name alone is an RDF invariant.

`Model._graph_unresolved()` currently emits one `rdf:type` from the nearest
`ClassInfo`. Ensure recipe instances emit their recipe class IRI and the model
imports both the extension ontology and its base dependency closure. In
`Model.from_graph()`, registry lookup should pick the recipe Python class from
that IRI. Rebuild accessible point references from RDF-observable facts; do
not use constructor defaults to alter a loaded graph. If an expected named
point cannot be identified uniquely, report that ambiguity rather than
assigning one arbitrarily. Test graph edits and re-save, including RDF outside
the generated projection.

## Code changes and migration

Likely touch points: `core/entity.py`, `core/meta.py`, `core/model.py`,
`core/resolution.py`, `core/query.py`, `core/validation.py`, `core/relations.py`,
`solver223.py`, `gen/naming.py`, `gen/schema.py`, `gen/emit.py`, and
`gen/overlays.py`. Add a focused recipe/declaration module rather than
growing `Entity` or the solver with unrelated policy types.

Change generator logic or overlays and regenerate `brick/`, `s223/`, and
`watr/` as appropriate; never hand-edit generated classes. Verify that the
same pinned ontology input produces a byte-identical regeneration before
accepting generated diffs. Apply predicate renames throughout runtime,
tests, docs, and examples. Any short-lived compatibility aliases must share
the canonical descriptor and emit one RDF predicate; new documentation and
code should use only canonical Python names. Do not change unrelated Brick
property names. Preserve the current user edits in
`examples/watr/treatment/watr_quickstart.py` and the untracked `.DS_Store`.

At plan creation, the baseline review found 139 passing tests. Ruff had one
unused import in the already-edited WaTr quickstart. `ty` had 38 diagnostics
in WaTr quantity examples because generated `Unit`/`QuantityKind` constructor
types differ from compiled QUDT `TermValue` constants. Record the baseline
again before editing; do not hide new type errors in the recipe API. Fixing the
QUDT mismatch is worthwhile but separate from the recipe feature unless a
shared generator change resolves it naturally.

## Delivery sequence and verification

1. Lock down public types, policy semantics, and per-predicate naming in a
   small test fixture. Demonstrate class-definition conflicts, falsey fixed
   values, per-instance defaults, and inherited narrowing.
2. Add point declarations and stable references. Verify construction,
   containment suppression, rollback, cloning, and direct versus loaded graph
   behavior before involving the solver.
3. Extend solver matching and explanation. Test both `fan >> coil` and
   `chiller >> coil`, explicit point/group endpoints, incompatible media,
   unknown direction, actual bidirectional points, symmetry, and meaningful
   same-medium ambiguity.
4. Add ontology/schema export, local validation, and hydration. Compare the
   generated graph to its exported shape with shifty; round-trip through
   `Model.from_graph()` using the recipe registry. Test the valve obligation
   separately from port layout.
5. Regenerate affected packages, update the quickstart/docs, then run
   `uv run pytest`, `uv run ruff check src tests examples`,
   `uv run ty check src tests examples`, and `uv build`. Report any remaining
   baseline diagnostics and generated diffs.

Completion means an author can instantiate one portable recipe class, connect
air and chilled-water equipment without manually creating points, inspect
which points were selected, receive clear errors for unresolved or invalid
connections, export a validating ontology/shape, and load the graph back into
the same recipe class. Keep broader template ingestion, WaterTAP translation,
and a full general-purpose property DSL outside this first implementation.
