# Authoring models

## The Model

A `Model` owns a namespace and every entity you create. The idiomatic form is
the ambient `with` block — entities created inside it bind automatically:

```python
from objectrdf import Model

with Model("urn:example/bldg1#") as model:
    ahu = AHU("ahu1")            # IRI becomes urn:example/bldg1#ahu1
```

Outside a `with` block, pass `model=` explicitly. Local names must be unique
within a model; `model["ahu1"]` looks an entity back up.

The name is optional. When omitted, one is generated per model with an
increasing per-class index — `AHU()` names itself `ahu_1`, the next `ahu_2` —
skipping any names you've minted manually:

```python
with Model("urn:example/bldg1#"):
    vavs = [VAV() for _ in range(4)]   # vav_1 ... vav_4
```

`model.save("out.ttl")` serializes (format inferred from the extension);
`model.graph()` exposes the underlying `rdflib.Graph` as an escape hatch.
`model.compile()` resolves and validates by default, returning an immutable
snapshot. Use `model.compile(validate=False)` only when intentionally
inspecting or emitting a partial graph.

## Attributes: required vs optional

Everything the ontology's SHACL shapes say about a class becomes its
constructor signature and attributes:

- `minCount >= 1` → required keyword argument (your IDE flags the omission);
- `maxCount 1` → scalar attribute (`fan.has_location`, entity or `None`);
- otherwise → a set-like collection (`ahu.feeds.add(vav)`, iterable,
  assignment replaces contents).

Runtime checks mirror the static types, so users without a type checker get
the same errors, at construction/assignment time, in Python vocabulary:

```
RangeError: AHU.has_point expects Point, got VAV ('vav-101')
```

Every entity also has `name` (the local name), `label` (defaults to name,
serialized as `rdfs:label`), and `comment`.

## Inverses

Declared `owl:inverseOf` pairs are maintained automatically and in memory:
`ahu.feeds.add(vav)` makes `ahu in vav.is_fed_by` true immediately. Both
directions serialize (redundant but valid RDF).

## Containment

Two ways to say "X contains Y", one negotiation mechanism — the predicate is
chosen per (container class, child class) pair from a table the generated
package registers:

```python
with Building("b1"):
    with Floor("f2") as floor:
        Room("r201")                # floor hasPart r201
        with Room("r202") as room:
            VAV("vav-202")          # vav hasLocation r202 (innermost
                                    # compatible container wins)

floor.contains(Room("r203"), Room("r204"))
fan.contains(sensor, via="has_point")   # explicit escape hatch
```

Only entities opened with `with` join the ambient stack; creating a `Room`
doesn't make it a container until you enter its block (or call
`.contains()`).

For Brick: Location×Location → `hasPart`, Location×Equipment → the
equipment's `hasLocation`, Equipment×Equipment → `hasPart`,
{Equipment,Location}×Point → `hasPoint`.

If containers are open but none accepts the new entity's class, construction
raises `ContainmentError` (a floating entity is almost always a mistake);
create the entity outside the block to opt out. Ambiguity (two applicable
rules) also raises, telling you the exact `via=` call to write.

## Flow connections: `>>` and `<<`

`a >> b` records "a flows into b" using the package-defined property (Brick:
`feeds`) and **returns `b`**, so chains read along the flow:

```python
oad >> supply_fan >> vav >> zone
zone << vav                       # mirror; means vav >> zone
```

In the S223 and WaTr packages, these operators record deferred connection
intentions. Z3 selects connection points, media, and Connection subclasses
when the model is resolved or serialized. Use the functional form when you
need to provide or retain a medium constraint:

```python
flow = connect(pump_a, pump_b, medium=enums.Fluid_Water)
flow.medium = enums.Water_ChilledWater  # refine before resolution
```

See [Authoring 223P](s223.md#how-z3-resolution-works) for solver lifecycle,
ambiguity diagnostics, and all supported hint mechanisms.

## Validation

```python
report = model.validate()          # shapes from the generated package's source
report = model.validate("extra-shapes.ttl")
if not report:
    print(report)                  # violation: vav-101 (VAV) [hasPoint]: ...
```

Validation runs shifty (SHACL Core + SHACL-AF inference) against the exact
ontology graph bundled in each generated package and maps every result back
to the Python entity, so the message names your variables, not blank nodes.

Serialized models declare an `owl:Ontology` resource automatically. Its IRI
defaults to the model namespace without the trailing `#` or `/`, and it imports
the ontology packages and compiled vocabularies actually referenced by the
model:

```python
model = Model(
    "urn:example/building#",
    name="Example building",
    ontology_iri="urn:example/building-model",  # optional override
    imports=["urn:example/project-vocabulary"],  # optional additions
)
```

`owl:imports` uses a generated package's canonical ontology IRI when available
and its recorded source URL otherwise. Compiled QUDT terms carry their
provenance, so using a unit or quantity kind adds the QUDT import without
additional authoring syntax.

## Metadata: `.meta`

Ontology provenance is always one attribute away, on classes and instances:

```python
AHU.meta.iri          # https://brickschema.org/schema/Brick#AHU
AHU.meta.label        # "AHU"
AHU.meta.definition   # the skos:definition text (also in AHU.__doc__)
AHU.meta.ontology     # OntologyInfo(name='Brick', version=..., source=...)
AHU.meta.parents      # (HVAC_Equipment,)
AHU.meta.properties   # effective PropertySpecs (inherited + own)

ahu.meta.instance_iri # urn:example/bldg1#ahu1
ahu.meta.model        # the owning Model
```

`name`, `label`, `comment`, `meta`, `model`, and `contains` are reserved:
ontology properties that would collide are suffixed with `_` by the
generator's naming policy.
