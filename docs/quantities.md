# Quantities, values, and nominal stream state

## Simple fixed values

S223's `hasValue` accepts a literal directly. Use it when the ontology class
already supplies the meaning, or when no dimensionally correct QUDT quantity
kind exists:

```python
from objectrdf.watr import Property, enums

coefficient = Property(
    "water-permeability",
    label="Water permeability coefficient [m/(Pa·s)]",
    has_value=4.2e-12,
    has_aspect=[enums.Aspect_Nominal],
)
membrane.has_property.add(coefficient)
```

`has_value` may be a Python literal or a named RDF resource. It serializes
without an intermediate node:

```turtle
:water-permeability s223:hasValue 4.2e-12 .
```

Prefer `QuantifiableProperty` when a compatible quantity kind and unit are
known; the generic `Property` form intentionally carries less machine-readable
measurement semantics.

## QUDT-backed quantities

`objectrdf.qudt` compiles the QUDT 3.4.0 unit and quantity-kind individuals
through ontoenv. They are immutable reference terms, not locally minted
entities:

```python
from objectrdf.qudt import quantity, quantity_kinds, units

pressure = quantity(
    watr.QuantifiableProperty,
    "operating-pressure",
    7_000_000,
    units.PA,
    quantity_kinds.Pressure,
    of=pump,
    has_aspect=[enums.Aspect_Nominal],
)
```

This emits the compact ontology pattern: the S223/WaTr property carries a
scalar `hasValue` and identifies its QUDT quantity kind and unit. A
`QuantityValue` node remains available for graphs that specifically need that
QUDT form, but it is not required for a fixed S223 property value. If a QUDT
term is also declared as a class (punned), the compiled named individual is
still used; authoring never creates a new local unit or quantity-kind instance.
The helper returns the same generated property type passed as its first
argument, so both `s223.QuantifiableProperty` and
`watr.QuantifiableProperty` retain their package-specific static type.

## Medium and substance-qualified stream properties

For a nominal flow state, use a non-RDF authoring view. Its subject can be an
authored connection point or a deferred `ConnectionHandle`:

```python
from objectrdf.qudt import stream_state

state = stream_state(feed_out, medium=enums.Water_Seawater)
tds = state.quantity(
    watr.QuantifiableProperty,
    "influent-tds",
    35.0,
    units.GM_PER_L,
    quantity_kinds.MassConcentration,
    substance=enums.Constituent_Salt,
    has_aspect=[enums.Aspect_Nominal],
)
```

The helper stages the property on the deferred connection and qualifies it
with `ofMedium`. `substance=` similarly uses `ofSubstance`. It adds no
framework-specific RDF class. The example above therefore says that `tds` is
a nominal salt mass concentration of the seawater at `feed_out`; it does not
create a new stream-state individual or a simulation state.

Media, constituents, substances, and aspects are ontology individuals from
the package's `enums` module. If the needed substance does not exist, define it
in an ontology extension with the appropriate S223/WaTr parent and regenerate
the package. A Python-only ad hoc enum would have no portable RDF definition.

See
[`examples/watr/seawater_ro/watertap_seawater_ro_full.py`](../examples/watr/seawater_ro/watertap_seawater_ro_full.py)
for inlet composition, equipment design properties, residence times,
efficiencies, pressures, and UV parameters using these patterns.

## What belongs in the ontology

S223 and WaTr are sufficient for a nominal, untimed property of equipment or
a connection:

- the subject-to-property relation (`hasProperty`);
- numeric value, unit, and quantity kind (QUDT);
- medium and substance qualification (`ofMedium`, `ofSubstance`);
- connection topology and media.

They are not sufficient to distinguish several operating points or samples
for the same stream. A companion ontology is needed before the framework
should serialize a real `StreamState`. It should define:

- `StreamState` (or `OperatingPoint`) and the relation to its connection;
- whether a state is nominal, calculated, measured, or constrained;
- time/scenario/run identity and validity interval;
- cardinality and ownership of its properties;
- constituent/composition semantics, including balance basis;
- SHACL constraints tying property unit dimensions to quantity kinds.

The ergonomic API should remain a thin constructor for that ontology pattern.
It may infer names, create the QUDT value node, and stage facts on a deferred
handle; it should not invent process equations or WaterTAP semantics.

There is also a concrete vocabulary gap for reverse-osmosis water permeability:
QUDT 3.2.1 contains `M-PER-SEC-PA`, but no named quantity kind with the same
dimension vector. WaTr should define a water-permeability-coefficient quantity
kind before `objectrdf` offers typed convenience syntax for it. Until then, a
scalar S223 `Property` can preserve the value, but its unit cannot be expressed
as a validated `QuantifiableProperty` without asserting a false quantity kind.

This project models S223/WaTr graphs. A S223/WaTr-to-WaterTAP translation layer
is future work and is not part of the current authoring model.
