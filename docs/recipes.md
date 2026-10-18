# Portable recipe classes

For new domain packages, define configurations in RDF and SHACL and
[generate their Python API](shacl-configurations.md). The Python declarations
below remain available for compatibility and advanced authoring. The
[ASM2d example](asm2d-proposed-example.md) uses generated configurations.

An extension package can register a named recipe subclass with an RDF class
identity. Class level declarations describe shared equipment facts; each model
instance still receives its own entity and point references.
Set `class_iri` and `ontology_iri` on the subclass; `class_label` is optional.
Those attributes trigger registration and schema generation automatically.

```python
from objectrdf import Model, choose, default, fixed
from objectrdf.s223 import ChilledWaterCoil, ConnectionPoint, enums


class AirWaterCoil(ChilledWaterCoil):
    class_iri = "urn:example:recipes#AirWaterCoil"
    ontology_iri = "urn:example:recipes"
    air = ConnectionPoint.declare(
        count=2,
        medium=fixed(enums.values.Fluid_Air),
        direction=choose("in", "out"),
        label=default("Air connection"),
    )
    water = ConnectionPoint.declare(
        count=2,
        medium=fixed(enums.values.Water_ChilledWater),
        direction=choose("in", "out"),
    )


with Model("urn:example:building#") as model:
    coil = AirWaterCoil("coil-1")
```

`fixed(value)` is enforced when assigning a declared equipment property and is
exported as a SHACL value constraint when the value is RDF-observable.
`default(value)` initializes newly constructed instances and can be replaced.
`choose(...)` restricts assignment to its values. Mutable defaults are copied
for each entity. Graph hydration preserves the graph's current values instead
of applying defaults.

Use the class variable `property_policies` for generated equipment properties,
keyed by their canonical Python property name:

```python
class ChilledCoil(ChilledWaterCoil):
    class_iri = "urn:example:recipes#ChilledCoil"
    ontology_iri = "urn:example:recipes"
    property_policies = {"has_role": default([enums.values.Role_Cooling])}
```

This keeps policy declarations separate from generated property descriptors.

`ConnectionPoint.declare(...)` is a class declaration. It does not construct an
RDF entity. Instance access returns a `PointRef` for one point or a
`PointGroupRef` when `count` is greater than one. Pass either reference to
`connect()` or to `>>` when a connection must use that point or group
explicitly. After resolution, `resolved.point(ref)` returns a concrete point
or a tuple of concrete points.
Operator-authored links can be inspected with `resolved.explain(source, target)`
even when the `ConnectionHandle` from `connect()` was not retained.

The class is registered in the parent package's registry for graph hydration.
Its RDF class, parent link, ontology imports, and SHACL point counts are
available from `model.export_ontology()`; pass a file path to serialize that
schema as Turtle. `Model.graph()` records imports for both recipe and parent
ontologies.

For an end-to-end S223 model, honor inherited equipment requirements as well as
the declared port layout. In particular, the generated G36
`ChilledWaterCoil` shape also requires its valve and complete connection paths.
Use `CoolingCoil` for isolated port-layout checks and the valve-equipped coil
for full model validation.

See [`examples/s223/recipe_coil/`](../examples/s223/recipe_coil/) for a runnable
example that exports both an instance graph and the portable recipe schema.
It now imports the configuration generated from `ontology/hvac.ttl`; model
authors do not write the Python declarations shown above.
