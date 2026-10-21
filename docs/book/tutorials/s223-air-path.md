---
file_format: mystnb
kernelspec:
  name: python3
---

# An S223 air path

The API is the same for 223P building systems. This tutorial connects a
damper to a fan, inspects the chosen connection, and validates the RDF.

## 1. Create and connect

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.s223 import Damper, Fan, enums

with Model("urn:example:air-path#") as model:
    damper = Damper("outside-air-damper")
    fan = Fan("supply-fan")
    air_link = connect(damper, fan)

print(damper.name, fan.name, air_link.name)
```

`damper >> fan` also records the connection, but returns the fan for
chaining.

## 2. Resolve

`check()` reports whether one interpretation exists. `resolve()` returns a
frozen snapshot with the chosen points and connection:

```{code-cell} python3
print(model.check().status)

resolved = model.resolve()
connection = resolved.connection(air_link)
explanation = resolved.explain(air_link)
print(connection.type, connection.medium)
print(explanation.source_point, "->", explanation.target_point)
```

The connection is a `Duct` because the medium is air. The snapshot holds the
derived points; the authored model does not:

```{code-cell} python3
print("authored:", len(model), "resolved:", len(resolved))
print("fan ports before:", [point.name for point in fan.ports])
print("fan ports after:", [point.name for point in resolved[fan.name].ports])
```

## 3. Validate

```{code-cell} python3
validation = model.validate()
print("conforms:", validation.ok, "issues:", len(validation.issues))
print("triples:", len(model.graph()))
```

`examples/s223/ahu/s223_quickstart.py` is a larger air and water example.
