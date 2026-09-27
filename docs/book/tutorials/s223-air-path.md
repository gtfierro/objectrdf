---
file_format: mystnb
kernelspec:
  name: python3
---

# Tutorial: make an S223 air path

You will create a damper and a fan, connect them in the direction of airflow,
inspect the selected connection, and read the resulting RDF. Work through the
cells in order. This page runs during the book build.

## 1. Create equipment in a model

A model owns entity names and mints IRIs in its namespace. S223 classes come
from generated Python code. `enums.values.Fluid_Air` is an ontology individual, not
a class to instantiate.

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.s223 import Damper, Fan, enums

with Model("urn:example:air-path#") as model:
    damper = Damper("outside-air-damper")
    fan = Fan("supply-fan")
    air_link = connect(damper, fan)

print(damper.name, fan.name, air_link.name)
```

`connect()` records an intention and returns a stable handle. The shorter
`damper >> fan` also records a connection, but returns the fan so you can
chain flows.

## 2. Check and resolve

`check()` describes whether a complete interpretation is available. `resolve()`
creates an immutable snapshot containing the selected points and connection.
Fixed-medium points required by these equipment shapes may already have been
created during construction; resolution adds the concrete link and any
remaining points to the snapshot.

```{code-cell} python3
report = model.check()
print(report.status)
assert report.complete

resolved = model.resolve()
connection = resolved.connection(air_link)
explanation = resolved.explain(air_link)
print(connection.type, connection.medium)
print(explanation.source_point, "->", explanation.target_point)
assert connection.medium is enums.values.Fluid_Air
```

The connection is a `Duct` because the selected medium is air. The snapshot
also contains connection points, ownership links, and inverse relations.
Compare the authored and resolved counts:

```{code-cell} python3
print("authored:", len(model), "resolved:", len(resolved))
print("fan ports before resolution:", [point.name for point in fan.ports])
print("fan ports in snapshot:", [point.name for point in resolved[fan.name].ports])
```

## 3. Inspect RDF and validate

`graph()` resolves automatically. It returns an `rdflib.Graph`, so you can
inspect triples without writing a file. `validate()` uses the bundled ontology
shapes through shifty and may include informational notices for unconnected
boundary points.

```{code-cell} python3
from rdflib import RDF, URIRef

graph = model.graph()
assert (URIRef(connection.meta.instance_iri), RDF.type, URIRef(connection.meta.iri)) in graph
validation = model.validate()
print("conforms:", validation.ok, "issues:", len(validation.issues))
print("triples:", len(graph))
```

To save the graph in your own script, call `model.save("air-path.ttl")`.
For a larger air and water example with a reusable coil, see
`examples/s223/ahu/s223_quickstart.py` in the repository.
