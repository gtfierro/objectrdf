---
file_format: mystnb
kernelspec:
  name: python3
---

# Use a domain package

A domain package adds reusable equipment and property schemas on top of WaTr.
This tutorial builds two aerobic reactor stages with `plumb.watr.asm2d`,
the activated-sludge package.

## 1. Create the stages

`AerobicStage` fixes its processes, objectives, roles, and named `inlet` and
`outlet` ports:

```{code-cell} python3
from plumb import Model, connect
from plumb.qudt import QuantityAmount as Q, units
from plumb.watr.asm2d import AerobicStage, AerobicDesign, OxygenOutletState

print(AerobicStage.describe_ports())
```

Create two stages in a system:

```{code-cell} python3
with Model("urn:example:two-stages#") as model:
    with model.system("treatment-system") as system:
        first = AerobicStage("first")
        second = AerobicStage("second")
```

## 2. Apply design values

`AerobicDesign` is a property schema compiled from SHACL. It requires an
oxygen transfer coefficient and defaults the volume to 1333 m³:

```{code-cell} python3
print(AerobicDesign.describe())
```

Create one design and apply it to both stages. Each stage gets its own
properties:

```{code-cell} python3
design = AerobicDesign(oxygen_transfer_coefficient=Q(10.0, units.PER_HR))
first.apply_properties(design)
second.apply_properties(design)

model["first-volume"], model["second-volume"]
```

The volume was not given, so it takes the default:

```{code-cell} python3
design.volume
```

Set the oxygen concentration leaving each stage:

```{code-cell} python3
outlet_oxygen = OxygenOutletState(oxygen_concentration=Q(2.0, units.GM_PER_M3))
first_oxygen = first.outlet.apply_properties(outlet_oxygen)
second_oxygen = second.outlet.apply_properties(outlet_oxygen)

dict(first_oxygen)
```

A bare number uses the field's default unit:
`OxygenOutletState(oxygen_concentration=2.0)` means 2 g/m³. An explicit
`Q(...)` keeps its unit.

## 3. Connect the stages

Mark where flow enters and leaves the system, then connect the first stage to
the second:

```{code-cell} python3
system.boundary(first.inlet, second.outlet)
link = connect(first.outlet, second.inlet, name="interstage")
```

## 4. Resolve and validate

```{code-cell} python3
resolved = model.resolve()
connection = resolved.connection(link)
connection.name, connection.medium
```

```{code-cell} python3
model.validate().ok
```

Validation uses the shapes bundled with the package, the same ones the Python
classes were compiled from.

## 5. Load it back

The graph imports the ASM2d ontology, so `from_graph()` selects the package.
Loading keeps the values as written; it does not fill in defaults.

```{code-cell} python3
graph = resolved.graph()
loaded = Model.from_graph(graph)
loaded["first"]
```

```{code-cell} python3
loaded["first-volume"].has_value
```

## Next

- [Domain extensions](../explanation/domain-extensions.md) explains what a
  domain package is.
- [Generate a domain API](../how-to/generate-domain-api.md) writes one.
- `examples/watr/asm2d/` and `examples/watr/seawater_ro/` contain full
  flowsheets.
