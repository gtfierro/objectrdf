# Quantities and property schemas

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
    has_aspect=[enums.values.Aspect_Nominal],
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

When the subject has `hasProperty`, call `quantity` on it to use its package's
`QuantifiableProperty` class and attach the property in one step:

```python
from objectrdf.qudt import quantity_kinds, units

pressure = pump.quantity(
    "operating-pressure",
    7_000_000,
    unit=units.PA,
    kind=quantity_kinds.Pressure,
    has_aspect=[enums.values.Aspect_Nominal],
)
```

`pressure` is a named `QuantifiableProperty` object in the model, linked from
`pump` by `hasProperty`. The default `capability="static"` selects
`QuantifiableProperty`. Use `capability="observable"` for an observed value or
`capability="actuatable"` for a writable value that can trigger actuation.
Capability is independent of interpretation: add `Aspect_Nominal` explicitly
for a nominal value. Observable properties do not imply an actual aspect.

```python
reading = pump.quantity(
    "discharge-pressure",
    7_000_000,
    unit=units.PA,
    kind=quantity_kinds.Pressure,
    capability="observable",
)
```

The same method works on a concrete `ConnectionPoint`. A deferred port from
`equipment.port(...)` can also accept a quantity; the property attaches to
the concrete connection point when the model resolves:

```python
outlet = pump.port("pump-out", direction="out")
outlet.quantity(
    "outlet-pressure",
    7_000_000,
    unit=units.PA,
    kind=quantity_kinds.Pressure,
)
```

This emits the compact ontology pattern: the S223/WaTr property carries a
scalar `hasValue` and identifies its QUDT quantity kind and unit. A
`QuantityValue` node remains available for graphs that specifically need that
QUDT form, but it is not required for a fixed S223 property value. If a QUDT
term is also declared as a class (punned), the compiled named individual is
still used; authoring never creates a new local unit or quantity-kind instance.

## Reusable schemas from RDF and SHACL

Define reusable quantity metadata and defaults in SHACL, then generate typed,
immutable value schemas. Model authors supply values and apply the schema:

```python
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.watr.asm2d import AerobicDesign, OxygenOutletState

design = AerobicDesign(oxygen_transfer_coefficient=10.0)
r5.apply_properties(design)
r6.apply_properties(design)
r5.outlet.apply_properties(
    OxygenOutletState(oxygen_concentration=Q(0.00191, units.KiloGM_PER_M3))
)
```

Each application creates separate RDF property entities. `AerobicDesign`'s
volume default and the default units come from SHACL. Explicit quantities retain
their value and permitted compatible unit without implicit conversion.
`describe()` lists fields, units, defaults, qualifications, and source shapes.

The same `apply_properties(...)` method works on equipment, points, and connection
handles. It returns a read-only `PropertySet` keyed by field name. `prefix=`
chooses a different naming stem; duplicate names fail atomically. Attach a value
to the point or connection it describes, rather than moving it onto equipment.

See [SHACL configurations](shacl-configurations.md) for schema authoring and
[ASM2d](asm2d-example.md) for a complete model. Use `capability=` and explicit
aspects for individual quantities. Property schemas obtain both their property
class and their aspects from SHACL.

## Schemas written in Python

A schema does not have to come from SHACL. Subclass `PropertySchema` and
declare each field with `quantity_field()`; the class becomes a frozen,
keyword-only dataclass with the same validation, `describe()`, and
`apply_properties()` behavior as a generated schema:

```python
from objectrdf import PropertySchema, quantity_field
from objectrdf.qudt import QuantityAmount as Q, quantity_kinds, units

class InfluentQuality(PropertySchema):
    """Raw surface-water quality at the plant intake."""

    flow_rate: float | Q = quantity_field(
        kind=quantity_kinds.VolumeFlowRate,
        unit=units.M3_PER_DAY,
        of_medium=enums.values.Water_Freshwater,
        minimum=0,
    )
    turbidity: float | Q = quantity_field(
        kind=quantity_kinds.Turbidity, unit=units.NTU, minimum=0
    )
    temperature: float | Q = quantity_field(
        kind=quantity_kinds.Temperature, unit=units.DEG_C, default=12.0
    )

raw_water.apply_properties(InfluentQuality(flow_rate=40_000, turbidity=18.0))
```

`unit` is the default for bare numbers; `of_medium`, `of_substance`,
`aspects`, `minimum`, `maximum`, and `allowed_units` mirror what a SHACL
property shape supplies. Move a schema into SHACL when other tools or
packages need to share it.

## Medium and substance qualifications

A scalar quantity can identify its medium, substance, and interpretation directly:

```python
feed.outlet.quantity(
    "influent-tds",
    Q(35.0, units.GM_PER_L),
    kind=quantity_kinds.MassConcentration,
    of_medium=enums.values.Water_Seawater,
    of_substance=enums.values.Constituent_Salt,
    has_aspect=[enums.values.Aspect_Nominal],
)
```

Media, constituents, substances, and aspects are ontology individuals from the
package's `enums` module. Add missing terms in an ontology extension and
regenerate its package. The model does not create a separate stream-state
individual for these properties.

See [the seawater RO example](../examples/watr/seawater_ro/watertap_seawater_ro_full.py)
for generated schemas covering composition, equipment design, pressures,
residence times, efficiencies, and UV parameters.

## What belongs in the ontology

S223 and WaTr are sufficient for a nominal, untimed property of equipment or
a connection:

- the subject-to-property relation (`hasProperty`);
- numeric value, unit, and quantity kind (QUDT);
- medium and substance qualification (`ofMedium`, `ofSubstance`);
- connection topology and media.

They are not sufficient to distinguish several operating points or samples
for the same stream. A companion ontology is needed before the framework
should serialize a distinct operating point. It should define:

- an operating-point class and its relation to the connection;
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
