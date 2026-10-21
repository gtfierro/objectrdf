---
file_format: mystnb
kernelspec:
  name: python3
---

# Author a model

A `Model` owns a namespace and the objects created in it. The examples use
WaTr; Brick and S223 work the same way.

## Create objects

Objects created inside `with model:` join the model. The name becomes a local
name in the namespace:

```{code-cell} python3
from plumb import Model
from plumb.watr import Pump, SedimentationTank, Tank, enums

model = Model("urn:example:plant#")
with model:
    intake = Pump("intake-pump")
    clarifier = SedimentationTank("clarifier")

model["clarifier"]
```

Unnamed objects are numbered per class:

```{code-cell} python3
with model:
    spare = Pump()
    another_spare = Pump()
spare.name, another_spare.name
```

Outside a `with` block, pass `model=`:

```{code-cell} python3
clearwell = Tank("clearwell", model=model)
clearwell.meta.instance_iri
```

Methods on existing objects, such as `.port()` and `.sensor()`, use the
object's own model.

## Set attributes

A property the shapes require is a required keyword argument:

```{code-cell} python3
from plumb.watr import DomainSpace

try:
    DomainSpace("zone", model=model)
except TypeError as error:
    print(error)
```

A requirement that the class itself fixes is filled in. Every WaTr
sedimentation tank performs settling:

```{code-cell} python3
list(clarifier.has_process)
```

A property with at most one value is a plain attribute. Others are set-like
collections with `add()`, `remove()`, and `clear()`; assignment replaces the
contents and takes an iterable:

```{code-cell} python3
clearwell.label = "Clearwell"
clearwell.has_role.add(enums.values.Role_Storage)
clearwell.label, list(clearwell.has_role)
```

Values are type-checked when set:

```{code-cell} python3
from plumb.watr import Process_Settling

try:
    clearwell.has_role.add(Process_Settling)
except Exception as error:
    print(type(error).__name__, error)
```

Every object also has `name`, `type`, `label`, and `comment`. Inverse
properties stay in sync.

## Contain objects

An object opened with `with` becomes a container. Objects created inside are
linked with the predicate the ontology uses for that pair of classes:

```{code-cell} python3
from plumb.watr import PhysicalSpace

with model:
    with PhysicalSpace("filter-building"):
        backwash_pump = Pump("backwash-pump")

list(backwash_pump.has_physical_location)
```

- `container.contains(child)` does the same without a block.
- `via="property_name"` picks the predicate when more than one applies.
- A class the container cannot hold raises `ContainmentError`.
- `contents`, `find_all()`, and `find_parent()` search containment; see
  [Find objects in a model](find-objects.md).

## Connect objects

`connect(a, b)` records flow from `a` to `b` and returns a handle. `a >> b`
does the same and returns `b`. See [Connect equipment](connect-equipment.md).

```{code-cell} python3
from plumb import connect

raw_water = connect(intake, clarifier, name="raw-water")
raw_water
```

## Validate

```{code-cell} python3
model.validate()
```

WaTr requires every tank to have a connection point. Connect the clearwell:

```{code-cell} python3
connect(clarifier, clearwell, name="settled-water")
model.validate().ok
```

[Validate and save](validate-and-save.md) covers reports and saving.

## Set ontology metadata

The saved graph declares an `owl:Ontology` that imports every package the
model uses. Its IRI defaults to the namespace without the trailing `#` or
`/`. Override it, and add imports or prefixes, on the constructor:

```python
model = Model(
    "urn:example:plant#",
    name="Example plant",
    ontology_iri="urn:example:plant-model",
    imports=["urn:example:project-vocabulary"],
    prefixes={"qudt": "http://qudt.org/schema/qudt/"},
)
```

## Inspect a class

`.meta` gives a class's ontology provenance:

```{code-cell} python3
SedimentationTank.meta.iri, SedimentationTank.meta.label, SedimentationTank.meta.parents
```

```{code-cell} python3
print(SedimentationTank.meta.definition)
```

On an object, `meta.instance_iri` and `meta.model` identify it. An ontology
property whose name collides with the object API (`name`, `type`, `label`,
`comment`, `meta`, `model`, `contains`, `ports`, `describe_ports`) gets a
trailing underscore, such as `contains_`.

## Brick

Brick spaces nest through `rec:hasPart`, equipment is located with
`hasLocation`, and points attach with `hasPoint`. Brick 1.4's location classes
are the RealEstateCore ones (`Building`, `Room`, `Space`, `Site`, `Zone`);
the deprecated `brick:` classes have a `_2` suffix, such as `Building_2`.
