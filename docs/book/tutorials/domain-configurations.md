---
file_format: mystnb
kernelspec:
  name: python3
---

# Use a domain package

A domain package adds reusable equipment and property schemas on top of WaTr.
This tutorial builds two aerobic reactor stages with `objectrdf.watr.asm2d`,
the activated-sludge package.

## 1. Create the stages

`AerobicStage` fixes its processes, objectives, roles, and named `inlet` and
`outlet` ports:

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.watr.asm2d import AerobicStage, AerobicDesign, OxygenOutletState

print(AerobicStage.describe_ports())
```

## 2. Apply design values

`AerobicDesign` is a property schema compiled from SHACL. It requires an
oxygen transfer coefficient and defaults the volume to 1333 m³:

```{code-cell} python3
print(AerobicDesign.describe())
```

Apply one design to both stages. Each stage gets its own properties:

```{code-cell} python3
with Model("urn:example:two-stages#") as model:
    with model.system("treatment-system") as system:
        first = AerobicStage("first")
        second = AerobicStage("second")
        design = AerobicDesign(oxygen_transfer_coefficient=Q(10.0, units.PER_HR))
        for stage in (first, second):
            stage.apply_properties(design)
            stage.outlet.apply_properties(
                OxygenOutletState(oxygen_concentration=Q(2.0, units.GM_PER_M3))
            )
        link = connect(first.outlet, second.inlet, name="interstage")
        system.boundary(first.inlet, second.outlet)

model["first-volume"] is not model["second-volume"], design.volume
```

A bare number uses the field's default unit:
`OxygenOutletState(oxygen_concentration=2.0)` means 2 g/m³. An explicit
`Q(...)` keeps its unit.

## 3. Resolve and validate

```{code-cell} python3
resolved = model.resolve()
connection = resolved.connection(link)
print("connection:", connection.name, connection.medium)
print("boundaries:", len(resolved["treatment-system"].has_boundary_connection_point))
print("conforms:", model.validate().ok)
```

Validation uses the shapes bundled with the package, the same ones the Python
classes were compiled from.

## 4. Load it back

The graph imports the ASM2d ontology, so `from_graph()` selects the package.
Loading keeps the values as written; it does not fill in defaults.

```{code-cell} python3
graph = resolved.graph()
loaded = Model.from_graph(graph)
print(loaded["first"].outlet)
print(set(loaded.graph()) == set(graph))
```

## Next

- [Domain extensions](../explanation/domain-extensions.md) explains what a
  domain package is.
- [Generate a domain API](../how-to/generate-domain-api.md) writes one.
- `examples/watr/asm2d/` and `examples/watr/seawater_ro/` contain full
  flowsheets.
