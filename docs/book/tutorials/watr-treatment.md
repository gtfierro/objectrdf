---
file_format: mystnb
kernelspec:
  name: python3
---

# Tutorial: make a WaTr treatment path

WaTr equipment uses the S223 connection model. Here a water source feeds a
transfer pump and then a tank. You will see how a constrained neighbor helps
the solver select a medium for a more general component.

## 1. Author the path

Import equipment and enums from the same generated package. `Pump` here is
the WaTr class; the package also contains imported S223 classes.

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr import Chiller, Pump, Tank, enums

with Model("urn:example:treatment#") as model:
    source = Chiller("water-source")
    pump = Pump("transfer-pump")
    tank = Tank("product-tank")
    inlet = connect(source, pump)
    outlet = connect(pump, tank)

print(model.check().status)
```

The chiller constrains the first link to water. Water is allowed at both pump
ports and at the tank, so the resolver prefers a coherent assignment. That
preference is a ranking among valid assignments, not a claim that all pumps
must preserve media.

## 2. Inspect the selected links

```{code-cell} python3
resolved = model.resolve()
for handle in (inlet, outlet):
    connection = resolved.connection(handle)
    explanation = resolved.explain(handle)
    print(handle.name, connection.type, connection.medium)
    print("  reason:", explanation.medium_reason)

assert resolved.connection(inlet).medium is enums.values.Fluid_Water
assert resolved.connection(outlet).medium is enums.values.Fluid_Water
```

## 3. Add metadata before compiling

Connection handles can stage generated properties before a concrete `Pipe`
exists. Mutating a handle invalidates the cached snapshot; a new `resolve()`
reflects the edit.

```{code-cell} python3
inlet.label = "Water supply"
inlet.has_role.add(enums.values.Role_Supply)
updated = model.resolve()
assert updated is not resolved
print(updated.connection(inlet).label)
```

Use `model.compile()` for a strict resolution and SHACL validation checkpoint,
or `model.save("treatment.ttl")` to serialize the resolved graph. See the
[diagnostic guide](../how-to/diagnose-resolution.md) if a larger treatment
path has more than one valid medium assignment.

## 4. Load without listing classes

The serialized graph declares its WaTr import and version. `from_graph()`
uses that metadata to select the installed package. Iterate through the loaded
objects to discover their names and types; import `Pump` only when you want
typed filtering.

```{code-cell} python3
loaded = Model.from_graph(model.graph())
print(loaded["transfer-pump"].type)
print(loaded["transfer-pump"].meta.ontology.version)
assert loaded["transfer-pump"].type == "Pump"
```
