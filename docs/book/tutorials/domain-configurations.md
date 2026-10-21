---
file_format: mystnb
kernelspec:
  name: python3
---

# Tutorial: use generated configurations and quantity schemas

Reusable domain definitions come from RDF and SHACL. Model authors import the
generated Python classes and supply equipment identities, values, and topology.
This tutorial builds two aerobic stages using the supplied ASM2d domain package.

## 1. Supply equipment and design values

`AerobicStage` already defines its processes, treatment objectives, roles, and
named water ports. `AerobicDesign` requires an oxygen transfer coefficient and
supplies a default volume of 1333 m³ from SHACL. The same immutable design can
be applied to several pieces of equipment; each receives independent properties.

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.watr.asm2d import AerobicStage, AerobicDesign, OxygenOutletState

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

assert model["first-volume"] is not model["second-volume"]
print("default volume:", design.volume)
print(AerobicStage.describe_ports())
```

Explicit quantities retain their numeric value and permitted compatible unit.
Bare numbers use their field's shape-declared default unit. For example,
`OxygenOutletState(oxygen_concentration=2.0)` means 2 g/m³. Use `describe()` to
inspect units, defaults, qualifications, and source shapes:

```{code-cell} python3
print(OxygenOutletState.describe())
```

The nominal aspect and static property capability come from the property shapes.
A static, observable, or actuatable capability describes what a property can do;
nominal or actual interpretation describes what its value means.

## 2. Resolve topology and validate the graph

`apply_properties(...)` also works on connection handles and concrete points.
It always attaches new properties to the exact subject supplied. The system
scope collects equipment and junctions, while `boundary(...)` identifies its
external points. A connection's name does not alter port matching.

```{code-cell} python3
resolved = model.resolve()
connection = resolved.connection(link)
print("connection:", connection.name, connection.medium)
print("system members:", len(resolved["treatment-system"].has_member))
print("boundaries:", len(resolved["treatment-system"].has_boundary_connection_point))
validation = model.validate()
assert validation.ok
print("conforms:", validation.ok)
```

The source shapes ship with the generated package, so validation uses the same
RDF requirements that produced the Python API. Use `model.save("train.ttl")`
to serialize the resolved graph.

## 3. Load the same configuration from RDF

The graph imports the ASM2d ontology, so loading it selects the `asm2d`
package, which also contains the WaTr base classes. Loading restores named
point references from their RDF facts and keeps values as written; it does not
fill in missing defaults.

```{code-cell} python3
graph = resolved.graph()
loaded = Model.from_graph(graph)
assert loaded["first"].outlet.medium is first.outlet.medium
assert set(loaded.graph()) == set(graph)
print("loaded outlet:", loaded["first"].outlet)
```

For new reusable definitions, follow [Generate a domain API](../how-to/generate-domain-api.md).
The full flowsheet examples are in `examples/watr/asm2d/` and
`examples/watr/seawater_ro/` in the repository.
