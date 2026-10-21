---
file_format: mystnb
kernelspec:
  name: python3
---

# Author a model

A `Model` owns a namespace and every object you create in it. The examples
use WaTr equipment. Brick and S223 work the same way.

## Create objects

Objects created inside `with model:` join that model. Each name becomes a local
name in the model's namespace:

```{code-cell} python3
from objectrdf import Model
from objectrdf.watr import Pump, SedimentationTank, Tank, enums

model = Model("urn:example:plant#")
with model:
    intake = Pump("intake-pump")
    clarifier = SedimentationTank("clarifier")

model["clarifier"]
```

The name is optional. Unnamed objects are numbered per class, skipping names
already in use:

```{code-cell} python3
with model:
    spares = [Pump() for _ in range(2)]
[pump.name for pump in spares]
```

Outside a `with` block, pass `model=`:

```{code-cell} python3
clearwell = Tank("clearwell", model=model)
clearwell.meta.instance_iri
```

Methods on existing objects, such as `connect()`, `.port()`, and `.sensor()`,
use the object's own model and need no `with` block.

## Required and optional attributes

The SHACL shapes for a class become its constructor signature. A required
property is a required keyword argument:

```{code-cell} python3
from objectrdf.watr import DomainSpace

try:
    DomainSpace("zone", model=model)
except TypeError as error:
    print(error)
```

A requirement that the class's own shapes satisfy is filled in instead. Every
WaTr sedimentation tank performs settling:

```{code-cell} python3
list(clarifier.has_process)
```

Pass a more specific process to replace the default. See
[WaTr processes and objectives](watr-processes.md).

Properties with at most one value are plain attributes. Others are set-like
collections with `add()`, `remove()`, and `clear()`. Assignment replaces the
contents and takes an iterable, even for one value:

```{code-cell} python3
clearwell.label = "Clearwell"
clearwell.has_role.add(enums.values.Role_Storage)
clearwell.label, list(clearwell.has_role)
```

Values are checked when you set them, with errors in Python terms:

```{code-cell} python3
from objectrdf.watr import Process_Settling

try:
    clearwell.has_role.add(Process_Settling)
except Exception as error:
    print(type(error).__name__, error)
```

Every object also has `name`, `type`, `label` (serialized as `rdfs:label`, and
defaulting to the name), and `comment`. Declared inverse properties stay in
sync: adding a connection point to equipment sets the point's `owner`.

## Containment

Opening an object with `with` makes it a container. Objects created inside
are linked with the predicate the ontology uses for that pair of classes:

```{code-cell} python3
from objectrdf.watr import PhysicalSpace

with model:
    with PhysicalSpace("filter-building"):
        backwash_pump = Pump("backwash-pump")

list(backwash_pump.has_physical_location)
```

`container.contains(child, ...)` does the same without a block, and
`via="property_name"` picks the predicate when more than one applies. If an
open container cannot hold the new object's class, construction raises
`ContainmentError`. Create the object outside the block instead.

In Brick, spaces contain spaces through `rec:hasPart`, equipment is located
with `hasLocation`, and points attach with `hasPoint`. Brick 1.4's location
classes are the RealEstateCore ones (`Building`, `Room`, `Space`, `Site`,
`Zone`). The deprecated `brick:` classes remain available with a `_2` suffix,
such as `Building_2`.

## Flow connections

`connect(a, b)` records that flow goes from `a` to `b`. Its result is a
handle you can refine before the model is resolved. `a >> b` records the same
intention and returns `b` for chaining. See
[Connect equipment](connect-equipment.md).

```{code-cell} python3
from objectrdf import connect

raw_water = connect(intake, clarifier, name="raw-water")
raw_water
```

## Save, inspect, and validate

`model.save("plant.ttl")` writes the RDF, with the format taken from the
extension. `model.graph()` returns the `rdflib.Graph`. Both resolve deferred
connections first; see [validate and save](validate-and-save.md) for
`validate()` and `compile()`.

```{code-cell} python3
report = model.validate()
report
```

WaTr requires every tank to have a fluid connection point, and nothing is
connected to the clearwell yet. Connecting it fixes the violation:

```{code-cell} python3
connect(clarifier, clearwell, name="settled-water")
model.validate().ok
```

The graph declares an `owl:Ontology` for the model that imports every
ontology package and vocabulary the model uses. The ontology IRI defaults to
the namespace without its trailing `#` or `/`. To set a name, a different IRI,
extra imports, or Turtle prefixes:

```python
model = Model(
    "urn:example:plant#",
    name="Example plant",
    ontology_iri="urn:example:plant-model",
    imports=["urn:example:project-vocabulary"],
    prefixes={"qudt": "http://qudt.org/schema/qudt/"},
)
```

The empty prefix is reserved for the model namespace.

## Ontology metadata

`.meta` gives a class's or object's ontology provenance:

```{code-cell} python3
SedimentationTank.meta.iri, SedimentationTank.meta.label, SedimentationTank.meta.parents
```

```{code-cell} python3
print(SedimentationTank.meta.definition)
```

`meta.ontology` names the source ontology and version, `meta.properties` lists
the generated properties, and `describe_ports()` shows the connection points
the shapes require. On an object, `meta.instance_iri` and `meta.model` identify
it. `name`, `type`, `label`, `comment`, `meta`, `model`, `contains`, `ports`,
and `describe_ports` are reserved, so an ontology property with one of those
names gets a trailing underscore, such as `contains_`.
