# Validate, save, and query a model

Use `compile()` when you want a resolved snapshot that has passed the bundled
SHACL shapes. For authored S223 and WaTr models, `validate()` resolves first,
then shifty runs SHACL validation with inference enabled by default.

```python
snapshot = model.compile()       # resolve, validate, return frozen snapshot
report = model.validate()        # detailed ValidationReport
if not report.ok:
    for issue in report.violations:
        print(issue.entity, issue.path, issue.message)
model.save("model.ttl")          # resolve and serialize
```

`report.issues` can also contain warnings and informational notices. They do
not make `report.ok` false. If you supply your own shapes, pass an
`rdflib.Graph` or Turtle file path: `model.validate("shapes.ttl")`. Pass
`infer=False` only when you deliberately want to check without SHACL-AF rule
inference. The solver's choices are separate from that inference step.

To open an objectrdf graph as typed objects, the loader reads its
`owl:imports` declarations and selects an installed generated package. The
graph also records the ontology version when the package has one. You can
iterate over all loaded entities without knowing their classes beforehand.
`infer=True` applies shifty's rules before hydration; it is opt-in for loading
because inference changes the graph being queried.

```python
from objectrdf import Model

loaded = Model.from_graph(
    "model.ttl",
    infer=True,
)
for entity in loaded:
    print(entity.name, entity.type, entity.meta.ontology.version)

for cls, instances in loaded.by_class().items():
    print(cls.__name__, len(instances), [item.name for item in instances])

from objectrdf.watr import Pump

pumps = loaded.find_all(Pump)
one_pump = loaded.find(Pump, label="Transfer pump")
```

`by_class()` groups by exact Python class. `find_all(Pump)` also includes
instances of Pump subclasses. To discover class names before importing them,
see the [class catalog](../reference/catalog.md).

For graphs without matching imports, or for custom generated packages, pass
the package's registry explicitly, for example
`registries=objectrdf.watr.drinking_water.REGISTRY` for the treatment tutorial.

Generated property edits on a loaded object update the model's RDF graph.
Unmodeled triples remain in `loaded.graph()`. Deferred `connect()` and system
scopes are currently for newly authored models; on a loaded graph, edit the
concrete connection and point objects. For more query examples, see
`docs/querying.md` in the repository.
