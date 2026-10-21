---
file_format: mystnb
kernelspec:
  name: python3
---

# Create objects and set attributes

A `Model` owns a namespace and the objects created in it. The examples use
WaTr; S223 works the same way.

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
properties stay in sync. An ontology property whose name collides with the
object API, such as `contains` or `walk`, gets a trailing underscore:
`contains_`.

## Next

- [Connect equipment](connect-equipment.md) joins objects with flow.
- [Group equipment into systems and spaces](organize-equipment.md) places
  objects inside others.
- [Validate a model](validate-a-model.md) checks the result against the
  shapes.
