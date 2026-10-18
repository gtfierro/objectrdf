# ASM2d authoring API: design and implementation plan

Status: implemented. See [the supported compiler and runtime API](shacl-configurations.md)
and the [runnable ASM2d example](../examples/watr/asm2d/watertap_asm2d.py).
The design discussion below records the intended behavior; the supported
constructive SHACL subset and regeneration commands are documented separately.

See the [complete ASM2d example](asm2d-proposed-example.md) for the
model-authoring surface this plan should deliver.

The ASM2d example should express equipment, topology, and operating values
through supported library abstractions. Authors should not need local factory
functions, custom `__init__` methods, or wrappers around quantity creation to
make a flowsheet readable. Extension authors declare reusable domain concepts;
model authors instantiate them and supply values.

RDF ontology terms and SHACL shapes are the source of truth for domain
configurations, ports, quantity definitions, and defaults. Compile them into
ordinary Python classes and typed value schemas through the existing codegen
pipeline. Do not require a parallel Python recipe or dataclass declaration to
describe the same domain facts. This supersedes the earlier proposal to accept
Python recipe modules as compiler input.

This plan reuses the runtime machinery behind [portable recipes](recipes.md)
and replaces the overlapping property-bundle and stream-state conventions with
one typed property application mechanism. It preserves the equipment–port–
connection model and the compiler's commitment to statically visible Python.

### Model authors use supplied definitions

The normal model author imports supported equipment configurations and property
schemas from a shipped domain package. The ASM2d package must supply the
anaerobic, anoxic, and aerobic stage recipes, their ports, and their state and
design schemas. Creating an ASM2d model must not require defining a subclass,
choosing class/ontology IRIs, writing policy dictionaries, or running codegen.

Package maintainers and extension authors define reusable configurations in
RDF and SHACL. The compiler produces the importable Python surface. Advanced
users can supply additional shapes for new domain concepts, but common modeling
tasks must work through shipped definitions. Tutorial examples should lead
with constructing models; shape-authoring and code-generation details belong
in extension documentation.

## 1. Historical baseline and concrete problems

The current `build_model().resolve()` succeeds with 14 connections, three
boundary ports, and 99 resolved entities. Resolution establishes topology;
it does not establish full SHACL conformance or simulate ASM2d reactions.

Checks run while writing this plan on 2026-10-16, with no runtime changes:

- `uv run pytest`: 154 passed, one failed. The failure is
  `test_handle_collection_assignment_invalidates_resolution`: assigning a
  scalar enum to a collection raises `KeyError` through `EnumValue.__getitem__`
  instead of the expected `TypeError`.
- `uv run ruff check src tests examples`: passed.
- `uv run ty check src tests examples`: 51 diagnostics, including recipe point
  declarations inferred as `PointDeclaration` rather than instance references,
  and generated QUDT unit/kind arguments incompatible with `TermValue`.
- The proposed Python examples below compile syntactically, and local
  documentation links resolve. They specify new APIs and are not runnable
  implementation tests yet.

Record this baseline again before implementation. The recipe reference typing
and QUDT term compatibility issues directly affect the proposed public API;
resolve them through descriptors and generator types rather than casts in
model-author code.

At the time of the assessment, the implementation had these sources of friction:

- Top-level `connect(..., name=...)` creates fresh ports on bare equipment;
  the unnamed form negotiates existing and inferred points. Naming therefore
  changes endpoint selection.
- The 22 feed quantities repeat measurement metadata. `PropertyBundle`
  separates application from definition, but combines definitions, defaults,
  missing-value detection, binding, and overrides in one mutable object.
- Bundle parameters are discovered through `**values` and hyphen-to-underscore
  conversion. The type checker cannot identify missing or misspelled fields.
- `Entity.quantity`, `PortHandle.quantity`, `StreamState.quantity`, and the
  free QUDT helper differ in argument names and property-class selection.
- Process, objective, and role combinations repeat independently of bundles.
  Existing recipes can declare these policies and ports, but inherited
  generated constructor signatures do not yet reflect recipe defaults.
- The clarifier's water and TSS split fractions serialize with identical kind
  and unit metadata. Their component distinctions appear only in names and
  labels. Their interpretation also requires a splitting basis.
- `mode="nominal"` currently selects `QuantifiableProperty` without asserting
  `Aspect-Nominal`. Capability and nominal interpretation are separate facts.

## 2. Public abstractions

Use three complementary abstractions. They have different responsibilities
and do not introduce new simulation objects.

| Abstraction | Responsibility | RDF behavior |
| --- | --- | --- |
| `QuantityDefinition` | Compiled immutable metadata for one shape-defined numeric field | Creates no RDF by itself |
| `PropertySchema` | Generated typed, immutable values for a reusable group of property shapes | Applying it creates fresh property entities on a target |
| Equipment configuration | Generated equipment class and named port references derived from RDF/SHACL | Instances use the declared RDF class and satisfy its shapes |

`QuantityDefinition` is distinct from the existing core `PropertySpec`, which
describes an RDF predicate, and from QUDT `QuantityValue`, which is an RDF
entity. Do not reuse either name for a Python field declaration.

### Quantity definitions and typed schemas

Generate keyword-only frozen dataclasses or equivalent explicit constructors
from reusable property shapes. Their fields have real names, defaults, and
types visible to editors and type checkers. Runtime `QuantityDefinition`
metadata is generated from the same shapes; it is not a second authoritative
definition written by the package author.

For example, this proposed source fragment describes an outlet property group
and the dissolved-oxygen field it contains:

```turtle
@prefix ex: <urn:example:asm2d#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix s223: <http://data.ashrae.org/standard223#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix qk: <http://qudt.org/vocab/quantitykind/> .
@prefix unit: <http://qudt.org/vocab/unit/> .

ex:OxygenOutletStateShape a sh:NodeShape ;
    sh:property [
        sh:path s223:hasProperty ;
        sh:name "oxygen_concentration" ;
        sh:qualifiedMinCount 1 ;
        sh:qualifiedMaxCount 1 ;
        sh:qualifiedValueShape ex:DissolvedOxygenShape
    ] .

ex:DissolvedOxygenShape a sh:NodeShape ;
    sh:class s223:QuantifiableProperty ;
    sh:property [
        sh:path s223:hasValue ;
        sh:datatype xsd:double ;
        sh:minCount 1 ; sh:maxCount 1
    ], [
        sh:path qudt:hasQuantityKind ;
        sh:hasValue qk:MassConcentration ; sh:maxCount 1
    ], [
        sh:path qudt:hasUnit ;
        sh:defaultValue unit:GM-PER-M3 ;
        sh:minCount 1 ; sh:maxCount 1
    ], [
        sh:path s223:ofSubstance ;
        sh:hasValue s223:Constituent-DissolvedOxygen ; sh:maxCount 1
    ], [
        sh:path s223:ofMedium ;
        sh:hasValue s223:Fluid-Water ; sh:maxCount 1
    ], [
        sh:path s223:hasAspect ;
        sh:hasValue s223:Aspect-Nominal
    ] .
```

Compile the group to `OxygenOutletState(oxygen_concentration=...)` and attach
its properties to the group shape's focus node. This untargeted reusable shape
does not require oxygen on every outlet in an ontology; compose it into the
specific configuration's outlet shape where required. Its Python value schema
does not create a new RDF stream-state individual or invent an RDF class.

Declare `AerobicDesign` and the full influent group through the same pattern.
Reuse named quantity shapes with `sh:node` and grouped property shapes with
`sh:group` where appropriate. Volume's numeric default of 1333 m³ belongs in
the source shape as `sh:defaultValue`, not in a hand-maintained Python class.

Prefer standard SHACL structure, names, descriptions, ordering, and groups.
If export selection or a stable Python name cannot be derived unambiguously,
allow a small documented code-generation annotation vocabulary in RDF. Such
annotations control projection and naming only; they must not replace SHACL
constraints or conceal domain-specific facts in Python overlays. Preserve the
source shape IRI on every generated field for diagnostics and introspection.

The schema constructor binds values. There is no second bundle-binding step,
no positional "single missing value" rule, and no alternate string-keyed
override path. Use normal dataclass replacement when a new value set is
needed. All fields in the first implementation are scalar numeric quantities;
retain ordinary generated property construction for other property classes.

Schema metadata and values must be validated before any model mutation.
Required fields and wrong constructor keywords are also checked statically.
Do not claim that generated annotations statically check dimensions; they check
the Python input type, while runtime metadata checks validate the quantity
definition and any explicitly supplied unit. Support integer literals as
numeric values and reject booleans and non-finite numbers.

### Units at definition and value sites

A bare number always uses its field's shape-declared default unit. Thus
`AerobicDesign(oxygen_transfer_coefficient=10.0)` means 10 h⁻¹; a concentration
field declared in g/m³ interprets `1.91` as 1.91 g/m³. Units must appear in
field documentation and schema descriptions, and survive RDF export. Never
infer units from a number's magnitude or from the calling model.

Also provide an immutable, model-independent `QuantityAmount(value, unit)`
value type for explicit input. It creates no RDF node. For example:

```python
design = AerobicDesign(
    oxygen_transfer_coefficient=QuantityAmount(10.0, units.PER_HR),
)
oxygen = OxygenOutletState(
    oxygen_concentration=QuantityAmount(0.00191, units.KiloGM_PER_M3),
)
```

Check explicit units against the field's declared meaning. Preserve the
supplied numeric value and compatible unit in the RDF property; do not silently
convert the numeric value to the default unit. This allows source values in
kg/m³ and author values in g/m³ to retain their meaning without a conversion
service. Compile the unit/kind compatibility metadata needed for this check
from the existing QUDT inputs; reject incompatible units and report unknown
compatibility explicitly. Dimensional compatibility is a check on an explicit
kind, not a way to infer the property's meaning.

Respect the source unit constraint. `sh:hasValue` plus `sh:maxCount 1` fixes
the serialized unit and prohibits a different explicit unit. A default unit
declared with `sh:defaultValue` permits another unit if the shape's actual
constraints allow it and compatibility is known. Default annotations do not
by themselves perform dimensional validation; compile applicable QUDT checks
and express required cross-unit compatibility in the extension's shapes so
Python and RDF validation agree.

The plain-number form remains a convenience for a schema with documented
default units. Use explicit amounts when importing values from another model
or when the units are less obvious. Library declarations and generated types
must expose both supported forms without an author-written wrapper. Automatic
unit conversion remains outside this implementation.

Source check on 2026-10-18 found a correction required in the existing example:
[WaterTAP's flowsheet](https://github.com/watertap-org/watertap/blob/main/watertap/flowsheets/activated_sludge/ASM2D_flowsheet.py)
sets the initial R5/R6/R7 oxygen concentrations to 0.00191/0.00260/0.00320 in
the [property package's kg/m³ units](https://github.com/watertap-org/watertap/blob/main/watertap/property_models/unit_specific/activated_sludge/asm2d_properties.py).
Our current bundle uses g/m³ with those same numbers. Correct these to
1.91/2.60/3.20 g/m³, or preserve the original numbers with explicit kg/m³ units.
These source oxygen values are initialization conditions that WaterTAP later
unfixes when fixing KLa; do not describe them as results calculated by this
example. The plan's usage sketches below use the corrected g/m³ values.

The full `ASM2dState` declares all 22 current feed fields. Shared concentration
definitions carry `of_medium`; each component field specifies its exact pool.
Alkalinity has its own amount-concentration definition and no `of_substance`.
Do not collapse COD-, nitrogen-, or phosphorus-based pools into pure chemical
species simply because they share a mass-concentration unit. Preserve the
existing ontology terms and their documentation.

The complete feed application becomes a declaration of values in the schema's
documented units. This is the same operation used for reactor design and outlet
conditions:

```python
influent = ASM2dState(
    flow_rate=18446.0,
    temperature=298.15,
    pressure=101325.0,
    s_o2=1e-6,
    s_f=30.0,
    s_a=20.0,
    s_nh4=16.0,
    s_no3=1e-6,
    s_po4=3.6,
    s_i=30.0,
    s_n2=1e-6,
    x_i=25.0,
    x_s=125.0,
    x_h=30.0,
    x_pao=1e-6,
    x_pp=1e-6,
    x_pha=1e-6,
    x_aut=1e-6,
    x_meoh=1e-6,
    x_mep=1e-6,
    x_tss=180.0,
    alkalinity=7.0,
)
mx1_feed_water.apply_properties(influent, prefix="feed")
```

### One application operation

The primary operation is:

```python
r5.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0))
r5.outlet.apply_properties(OxygenOutletState(oxygen_concentration=1.91))
```

Provide the same typed `apply_properties(schema, *, prefix=None)` contract on
eligible concrete entities, `PortHandle`, recipe `PointRef`, and
`ConnectionHandle`. Applying to a point attaches to that point; applying to a
connection attaches to the connection. Never relocate properties between
these subjects as an ergonomic shortcut.

Return a `PropertySet` implementing `Mapping[str, Entity]`, keyed by canonical
schema field names. Do not promise statically typed dynamic attribute access
on the returned property entities. The schema's numeric values and the
created RDF properties are separate objects with separate lifecycles.

Application rules:

- The schema and definitions are model-independent immutable Python values.
- Each application creates independent, model-owned property entities.
- Default names derive deterministically from target identity and field name.
  Python parameter names never depend on serialized RDF names. Explicit
  `local_name` and `prefix` control RDF naming, not field lookup.
- Applying twice with colliding names raises an error. A distinct prefix
  creates distinct properties; it does not establish scenario or time identity.
- Validate every field, target, and reserved name before committing. Any later
  failure rolls back all created entities, links, reservations, and revisions.
- Deferred targets retain stable identity and stage attachment until
  resolution. Concrete and graph-backed targets use the same validation rules
  where edits are already supported. Do not broaden graph-backed topology
  editing as part of this feature.
- Schema descriptions show units, kind, qualifications, aspects, defaults,
  and required fields, derived from the source RDF and SHACL. Preserve source
  documentation in schema export; Python grouping metadata does not create
  extra model-instance resources.

Keep `target.quantity(name, value, *, unit, kind, ...)` as the explicit one-off
operation. Both scalar creation and schema application use one internal
property-construction path. Canonical qualification arguments are `of_medium`
and `of_substance`. Property capability is `capability="static"`,
`"observable"`, or `"actuatable"`; aspects are independent metadata. Static
does not imply nominal, and observable does not imply actual. ASM2d's nominal
definitions explicitly assert `Aspect-Nominal`.

The existing free QUDT helper remains the lower-level operation for choosing
an explicit generated property class. `StreamState` must not remain a separate
property builder with different argument names: migrate its qualification
behavior into definitions, with a temporary forwarding adapter if needed.

## 3. Equipment configurations compiled from RDF and SHACL

Define the anaerobic, anoxic, and aerobic configurations as ontology classes
with SHACL shapes. A generic aeration basin must not acquire ASM2d-specific
nitrification facts; those belong to the domain-specific subclass and shape.
Keep physical equipment type, process, objective, and operating role distinct.

For example, the source for an aerobic stage can include the following. This
fragment illustrates required process values and an inlet; the complete shape
also declares the outlet, roles, objectives, and applicable property groups.

```turtle
@prefix ex: <urn:example:asm2d#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix s223: <http://data.ashrae.org/standard223#> .
@prefix watr: <https://watermetadata.org/ontology/watr#> .

ex:AerobicStage a owl:Class ;
    rdfs:subClassOf watr:AerationBasin .

ex:AerobicStageShape a sh:NodeShape ;
    sh:targetClass ex:AerobicStage ;
    sh:property [
        sh:path watr:hasProcess ;
        sh:hasValue watr:Process-Nitrification
    ], [
        sh:path watr:hasProcess ;
        sh:hasValue watr:Process-Aeration
    ], [
        sh:path s223:hasConnectionPoint ;
        sh:name "inlet" ;
        sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
        sh:qualifiedValueShape [
            sh:class s223:InletConnectionPoint ;
            sh:property [
                sh:path s223:hasMedium ;
                sh:hasValue s223:Fluid-Water ; sh:maxCount 1
            ]
        ]
    ] .
```

Extend the existing `gen/schema.py` intermediate representation and emitter
to compile these shapes into explicit constructors and typed point descriptors.
Reuse the existing recipe runtime for constrained values and stable references
where appropriate. Do not add a separate `--recipes declarations.py` compiler
input or require handwritten Python configurations. Existing Python recipe
support can remain for compatibility; the new domain package uses RDF inputs.

Use the existing `--file`, `--extra`, and `--iri` workflow. Resolve imports and
base-package references so generated extension types inherit the installed
WaTr classes instead of emitting incompatible duplicate base registries. If
base-package linking needs additional compiler configuration, make it generic;
do not encode ASM2d facts in a Python overlay. Ship generated modules so a
model author needs only imports and constructors.

### Shape semantics and construction rules

The compiler must distinguish constraints from authoring defaults:

| RDF/SHACL source | Generated behavior |
| --- | --- |
| Class/subclass declarations and `sh:targetClass` | RDF class identity, Python inheritance, and applicable constraints |
| `sh:hasValue` | Ensure the required value is present during construction; preserve validation semantics |
| `sh:defaultValue` | Replaceable authoring default on new instances; not a validation constraint |
| `sh:in` | Allowed values; do not pick one arbitrarily |
| Cardinality, class, and datatype constraints | Required fields, scalar/collection types, and runtime checks |
| Qualified point shapes | Typed named point/group references and solver constraints |
| Labels, descriptions, names, order, and groups | Documentation and a deterministic Python projection |

`sh:hasValue` on a collection requires membership, not exact equality of the
whole collection. The two process constraints above permit additional
processes unless another constraint forbids them. Do not compile them as
`fixed([Nitrification, Aeration])` and silently prohibit valid extra values.
A singleton becomes fixed only when the other constraints establish that
interpretation. These distinctions follow the
[SHACL constraint semantics](https://www.w3.org/TR/shacl/#HasValueConstraintComponent)
and its [default-value annotation](https://www.w3.org/TR/shacl/#defaultValue).

Construction of supported shapes may supply unambiguous required constants and
create required child properties/ports. This is objectrdf's constructive
projection of the shapes, not behavior provided by SHACL validation itself.
Required variable numeric values still come from the author. `sh:defaultValue`
must never fill missing values on graph hydration, and an invalid default or
contradictory inherited shape must produce a compiler diagnostic.

Unsupported or ambiguous shapes remain validation constraints with explicit
generation diagnostics. Never claim that arbitrary SHACL-SPARQL is a recipe
for creating objects. Compile only the supported constructive subset; use the
original shapes for full validation. Keep generated field-to-shape provenance
so errors point to the source RDF rather than a generated Python policy table.

An unambiguous required process value must allow `AerobicStage("R5")` without
forcing an author to repeat `has_process`. If the shape permits additional
values, retain the typed additive input or relationship operations. Constructor
defaults and required arguments must be derived from effective inherited
constraints. Descriptors and point methods must pass `ty` without casts or
`Any` in the example. A single generated `PointRef` supports property-schema
application just like `PortHandle`; interchangeable point groups retain their
existing matching semantics.

The target flowsheet pattern is:

```python
r5 = AerobicStage("R5", label="Aerobic reactor 5")
r5.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0))
r5.outlet.apply_properties(OxygenOutletState(oxygen_concentration=1.91))

r6 = AerobicStage("R6", label="Aerobic reactor 6")
r6.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0))
r6.outlet.apply_properties(OxygenOutletState(oxygen_concentration=2.60))

connect(r5.outlet, r6.inlet, name="stream8", medium=water)
```

Equipment construction and properties deliberately remain separate statements
with the same library operations for every equipment type. Avoid a special
ASM2d constructor that forwards arbitrary kwargs into hidden property calls.
No custom factory or `__init__` is required from an extension author.

Class and ontology IRIs come from the RDF input. Schema export preserves the
source shapes and imports; it must not reconstruct a weaker approximation
from Python policies. Numeric defaults remain annotations rather than new
SHACL invariants. If a named port cannot be reconstructed uniquely from portable
RDF facts, hydration must report ambiguity; its local Python name is not a
portable distinguishing role.

## 4. Connection names and allocation are independent

Adopt `connect(..., ports="match")` as the default for named and unnamed
connections. `>>` uses the same matching policy. Matching considers existing,
declared, and shape-derived points, directions, media, capacity, and inherited
constraints. Meaningfully distinct candidates require an explicit point;
interchangeable point permutations do not create false ambiguity.

Support `ports="new"` for authors who explicitly need fresh points on bare
equipment. Explicit point endpoints remain exact references under either
policy; only bare equipment endpoints allocate fresh points. Fresh allocation
must obey recipe and ontology point counts and cannot bypass a fixed layout.
Changing only `name` must never change the selection policy or satisfiability.

Keep port identities independent of connection names. Derive allocated port
names from their owning equipment and a deterministic allocation identifier;
use explicit named ports when stable domain identity matters. The implementation
must document allocation ordering and test deterministic regeneration.

Migrate ASM2d branches and boundaries to explicit recipe or authored ports.
Straight sections can use matching where their endpoints are unambiguous.
Do not add a flowsheet-specific connection helper to hide `ports="new"`.
An ambiguous result should name candidate points and show the explicit
endpoint selection needed to resolve it.

## 5. System membership and boundaries

Use the existing `model.system(...)` scope to collect equipment membership.
Extend its scope object with typed `boundary(...)` staging, so the author can
declare boundaries while the system is being built rather than retrieving
`.entity` afterward. The final `System` owns the same explicit boundary links.

```python
with model:
    with model.system("ASM2d-system", label="WaterTAP ASM2d") as system:
        # Construct equipment, apply schemas, and connect the treatment train.
        system.boundary(mx1_feed_water, cl1_effluent, sp2_waste)
```

Equipment properties and ports must not be collected as equipment members.
Membership and boundary staging must roll back on failed scope exit. Preserve
the current explicit interpretation of the feed, effluent, and waste as system
ports; do not introduce dummy boundary equipment.

## 6. Split semantics must survive RDF export

Represent the clarifier's H2O fraction with the H2O constituent and its TSS
fraction with the suspended-solids constituent, both qualified by water.
Retain the overall-flow interpretation of SP1 and SP2 separately from a
component-specific split.

Component identity alone does not say whether a fraction refers to inlet
component mass flow, volume flow, concentration, or another denominator.
Define an explicit split-fraction property type and split-basis vocabulary in
the local ontology extension, with documentation and shapes. Confirm the
appropriate existing predicates and source meaning before choosing the final
terms. Use an extension term where the current ontology lacks the relation;
never reinterpret a unit or label as a machine-readable basis.

Compile the extension through the existing generator. Its schema must require
the applicable basis and component qualifications. A split-fraction definition
selects that property class through the shared quantity-construction path;
schemas must therefore support an explicit property class when the default
quantifiable class is insufficient. The definition still validates compatible
kind, unit, and qualifications.

This work describes the documented split parameters; it does not enforce a
mass balance, infer unspecified complementary fractions, or calculate stream
composition. Do not apply a whole-flow sum-to-one rule to unrelated component
fractions.

## 7. Delivery sequence and verification

Each step produces usable library behavior and focused tests. Do not mark the
work complete after adding convenience aliases or only rewriting the example.

1. **Capture baseline and lock the public contract.** Record pytest, Ruff, and
   `ty` results against the current working tree. Add RDF/SHACL fixtures for
   quantity groups, stage classes, required collection members, defaults,
   choices, and ports, plus expected generated APIs. Preserve user changes.
2. **Extend shape extraction and the compiler IR.** Capture effective inherited
   constants, defaults, allowed values, qualified property groups, point names,
   QUDT compatibility metadata, and source-shape provenance. Validate source
   fixtures and diagnose unsupported constructive cases. Test that collection
   membership is not compiled as exact equality, defaults do not become hard
   constraints, and a shape edit changes generated Python without manual edits.
3. **Generate typed value schemas and unify property application.** Emit explicit
   typed schema constructors and immutable quantity metadata from the IR. Add
   generic runtime value validation, `QuantityAmount`, deterministic names,
   and `PropertySet`. Implement the shared creation/application path for
   entities, ports, point references, and connections. Test required fields,
   defaults, falsey values, explicit units, invalid terms, property independence,
   exact attachment subjects, rollback, cloning, and supported graph edits.
   Verify capability and aspect triples independently. Add typing fixtures
   for valid and deliberately invalid constructor calls.
4. **Generate equipment configurations and port descriptors.** Extend the same
   RDF-to-Python emitter with shape-derived constructor values and typed point
   references. Reuse runtime recipe machinery without maintaining Python domain
   definitions. Test inheritance, required/additional collection members,
   defaults, choices, base-package linking, original-shape validation, hydration,
   and byte-identical regeneration. Use the existing RDF CLI inputs.
5. **Correct connection allocation and system scopes.** Remove the name-based
   allocation branch, add explicit allocation policy, and support boundary
   staging on system scopes. Test named/unnamed equivalence, `>>` equivalence,
   explicit endpoints, fresh allocation, fixed counts, meaningful ambiguity,
   distinct ports on branches, deterministic names, and failure rollback.
6. **Add split semantics and migrate ASM2d.** Add and compile required ontology
   terms and shapes, including source-defined stage configurations and quantity
   groups. Replace the mutable bundle module with generated schemas and stage
   classes, and ship them as supported domain imports. Supply all 22 feed values through
   the typed state constructor. Use the same operations for all seven reactors,
   preserve stream names and the physical meaning of source values, correct the
   outlet-oxygen unit mismatch, and remove the manual system-member list. Test
   the equivalent kg/m³ and g/m³ representations against the source values.
7. **Migrate public examples and retire overlapping APIs.** Update the seawater
   RO examples and documentation to the canonical property arguments and
   capability/aspect semantics. Provide forwarding compatibility only where
   useful, with a documented removal boundary. Generated packages must change
   through generator logic or overlays, followed by deterministic regeneration.
8. **Run release checks.** Run `uv run pytest`,
   `uv run ruff check src tests examples`, `uv run ty check src tests examples`,
   and `uv build`. Run the documented example commands and RDF/SHACL generation
   twice. Report any pre-existing diagnostics separately from new failures.

Likely implementation touch points include `core/property_bundle.py`, new
property-definition/schema modules, `core/entity.py`, `core/resolution.py`,
`core/recipes.py`, `core/model.py`, `qudt/__init__.py`, top-level `connect`,
`solver223.py`, and `gen/`. Changes to generated vocabulary APIs must
also reserve new library method names through the generator's naming rules.
Keep the existing recipe plan as historical documentation; update `recipes.md`
and `codegen.md` to describe RDF/SHACL configuration authoring and the generated
API. Do not present Python recipe definitions as the primary domain source.

## 8. Acceptance criteria

- ASM2d uses supported schemas, recipes, and target operations without custom
  authoring factories, wrappers, handwritten constructors, or typing escapes.
- A normal model author can import the supplied configurations and build the
  model without writing recipe declarations or running the compiler.
- The configurations, property groups, defaults, qualifications, and units
  originate in RDF/SHACL. Changing the source shapes and regenerating updates
  the typed Python API without editing a parallel Python domain definition.
- Source shapes validate the emitted RDF, and generated metadata retains their
  provenance. SHACL defaults, membership constraints, choices, and cardinalities
  retain their actual semantics in constructors and runtime checks.
- Shared measurement metadata and equipment constraints are each declared once.
  The example's varying values are readable keyword arguments.
- Changing a connection's name does not change endpoint allocation policy,
  satisfiability, or selected equipment/ports apart from connection identity.
- The graph retains all 14 named connections, the original equipment, three
  explicit boundary ports, 22 feed values, reactor sizes, KLa values, outlet
  oxygen values, pump pressure, and documented split parameters.
- Bare numeric inputs use documented schema units; explicit amounts preserve
  their compatible units. Corrected outlet oxygen values retain WaterTAP's
  physical meaning rather than the current example's factor-of-1,000 error.
- A machine can distinguish the water and TSS split parameters by their RDF
  semantics without parsing resource names or labels.
- Nominal definitions emit nominal aspects. Property capability remains a
  separate, correctly typed fact.
- Recipe schema export and graph hydration preserve RDF-observable meaning.
  New recipe types and more explicit semantics are expected graph changes;
  do not require raw Turtle text or the old total entity count to stay equal.
- Regeneration is deterministic, public examples type-check, and documented
  shape validation succeeds. If inherited ontology constraints expose a
  modeling issue, resolve it explicitly rather than weakening validation.

Time/scenario identity, automatic unit conversion, reaction solving, mass
balance solving, WaterTAP translation, a general-purpose property expression
language, and a separate flowsheet framework are outside this plan.
