# Generate domain APIs from SHACL

Domain configurations and property schemas are defined in RDF and SHACL, then
compiled into ordinary typed Python. Model authors import the generated package;
model code supplies values and topology while reusable definitions remain in RDF.

The complete example is [ASM2d](asm2d-example.md). Its source is
[ontology/asm2d.ttl](../ontology/asm2d.ttl), and its generated package is
`objectrdf.watr.asm2d`.

The [seawater RO example](../examples/watr/seawater_ro/README.md) uses
`objectrdf.watr.seawater_ro`, generated from `ontology/seawater-ro.ttl`.
The [surface-water treatment tutorial](book/tutorials/watr-treatment.md) uses
`objectrdf.watr.drinking_water`, generated from `ontology/drinking-water.ttl`.
The S223 examples share `objectrdf.s223.hvac`, generated from
`ontology/hvac.ttl`. Run `uv run python scripts/generate_example_domains.py`
to regenerate all four packages offline.

## Compile an extension

Identify the installed base package with a code-generation annotation on the
extension ontology:

```turtle
@prefix ex: <urn:example:domain#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix codegen: <https://w3id.org/objectrdf/codegen#> .

ex: a owl:Ontology ;
    owl:imports <https://watermetadata.org/ontology/watr> ;
    codegen:baseModule "objectrdf.watr" .
```

Use the existing compiler interface:

```bash
uv run objectrdf gen --file ontology/asm2d.ttl --name ASM2d \
    --source ontology/asm2d.ttl --out src/objectrdf/watr/asm2d
# Equivalent repository command:
uv run python scripts/generate_asm2d.py
```

The extension reuses the installed base's classes and enumeration values.
The package exports `REGISTRY`, including base and extension types for graph
loading; for example, `registries=objectrdf.watr.drinking_water.REGISTRY`.
Graphs saved by objectrdf import the extension's ontology, so the bundled
domains are found without `registries=`; a domain compiled elsewhere still
needs it.
The package carries the exact source shapes in `_shapes.ttl`; generation
canonicalizes blank nodes and is deterministic across fresh RDF parses.

## Equipment classes and ports

Declare a domain class with `owl:Class` and `rdfs:subClassOf`, and target it
with a node shape. The generator supports one constructive parent per extension
class, including another class in the same extension. It emits an explicit
constructor with typed inherited properties.

`sh:hasValue` supplies required constants on new instances. For a collection,
these are required members: callers can supply additional valid values.
`sh:defaultValue` supplies a replaceable default on new instances only. `sh:in`
restricts choices. Contradictory bounds, defaults, or inherited choices are
reported during compilation. Graph hydration preserves the graph as written;
it does not fill missing defaults or required values.

Named ports are qualified shapes over `s223:hasConnectionPoint`, with:

- A `sh:name` that becomes the Python reference, such as `inlet` or `feed_water`.
- An inlet, outlet, or bidirectional `sh:class`.
- An exact `sh:hasValue` medium and equal positive qualified minimum/maximum counts.
- Portable distinguishing facts for same-direction ports. ASM2d uses fixed
  RDF labels declared in those shapes.

One point exposes a typed `PointRef`; a group exposes a `PointGroupRef`.
Use these in `connect(...)` and inspect them through `resolved.point(ref)` or
the resolved equipment's named reference. The original RDF facts identify the
points after graph hydration; ambiguous matching raises an error.

```python
from objectrdf import Model, connect
from objectrdf.watr.asm2d import AerobicStage

with Model("urn:example:train#") as model:
    r5 = AerobicStage("R5")
    r6 = AerobicStage("R6")
    connect(r5.outlet, r6.inlet, name="stream8")
```

This constructs topology; the complete configuration also requires the design
and outlet properties specified by its shapes before full SHACL validation.
`describe_ports()` includes the named port counts and media compiled from RDF.

## Property groups and value schemas

Mark a reusable node shape with
`codegen:projection codegen:PropertySchema`. Its fields are property shapes
over `s223:hasProperty`, each with a stable `sh:qualifiedValueShape` IRI,
qualified minimum/maximum count of one, and a readable `sh:name`.

The quantity value shape supplies its property class, numeric `hasValue`
datatype/count, QUDT kind, unit, and substance/medium/aspect constraints. Reuse
shapes through `sh:node` and `sh:and`. The current numeric projection supports
double, float, and decimal inputs as Python numbers; fields are scalar and
required unless a value default is declared. Supported numeric checks include
inclusive minimum/maximum bounds and finite `sh:in` values.

A fixed `rdfs:label` on a quantity is preserved by the projection. It can
distinguish properties with the same quantity kind, such as membrane channel
height and stage width, so qualified cardinality checks identify the intended
field. Generated configurations also inherit the base package's containment
rules and work inside ordinary equipment `with` scopes.

```python
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.watr.asm2d import AerobicDesign, OxygenOutletState

r5.apply_properties(AerobicDesign(oxygen_transfer_coefficient=10.0))
r5.outlet.apply_properties(
    OxygenOutletState(oxygen_concentration=Q(0.00191, units.KiloGM_PER_M3))
)
```

These classes have generated keyword-only frozen dataclass constructors.
`AerobicDesign` takes its default volume of 1333 m³ from SHACL. Bare numbers
use shape-declared units; explicit `QuantityAmount` values retain their
numeric value and permitted compatible unit. There is no implicit conversion.
`sh:hasValue` plus a singleton unit constraint fixes the unit; `sh:defaultValue`
does not. Unit choices in `sh:in` and compiled QUDT dimension vectors are checked
before model mutation. Unknown compatibility produces an explicit error.

The same `apply_properties(...)` operation works on equipment, authored and
hydrated points, and connection handles. Each application creates independent
property entities on that exact subject. It returns a read-only `PropertySet`
keyed by the Python field names. Names derive from the target and field; use
`prefix=` to choose an alternate stem. Duplicate names fail, and a failed
application rolls back all entities, links, and model revisions. A new prefix
does not create a time or scenario context or relax the source shapes.

`describe()` shows field notation, units, required/default values, and source
shape provenance. `skos:notation` preserves symbols such as `S_NH4` while
descriptive names such as `ammonia_ammonium_nitrogen` form the Python API.

## Projection annotations and boundaries

The annotation vocabulary is small:

| Annotation | Purpose |
| --- | --- |
| `codegen:baseModule` | Installed Python package providing linked base types |
| `codegen:projection codegen:PropertySchema` | Export a reusable property group as typed values |
| `codegen:pythonName` | Optional explicit generated class/field name |
| `codegen:localName` | Optional RDF local name for a property, independent of its Python keyword |

Domain requirements stay in SHACL. Annotations select projections and names;
they do not replace constraints. Complex paths, disjunctive constructive layouts,
and unlinked parents produce compiler diagnostics. Full validation uses the
original shapes, including constraints outside the constructive projection.
The compiler is not a general SHACL-SPARQL object-construction engine.
