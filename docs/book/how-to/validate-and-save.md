---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Validate and save a model

Validation checks the resolved RDF against the SHACL shapes bundled with each
generated package, using shifty. It also applies the SHACL-AF rules that
carry S223's and WaTr's inferences, and maps every result back to your Python
objects.

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr import Pump, Tank
from objectrdf.watr.drinking_water import ClarificationStage

model = Model("urn:example:validate#")
with model:
    intake = Pump("intake-pump")
    clarifier = ClarificationStage("clarifier")
    sludge_tank = Tank("sludge-tank")
connect(intake, clarifier.inlet, name="raw-water")

report = model.validate()
report.ok
```

## Read the report

```{code-cell} python3
for issue in report.violations:
    print(issue.entity, issue.path)
    print("  ", issue.message)
```

The sludge tank has no connections, and WaTr requires every tank to have a
fluid connection point. `report.issues` also holds warnings and
informational notices, which do not make `report.ok` false. A boundary point
that connects to nothing, for example, is an informational notice.

```{code-cell} python3
connect(clarifier.sludge, sludge_tank, name="sludge-draw")
model.validate().ok
```

`validate()` resolves the model first, so an ambiguous or contradictory model
raises `AmbiguousModelError` or `UnsatisfiableModelError` before any shapes
run.

To check against your own shapes as well, pass a Turtle path or an
`rdflib.Graph`: `model.validate("site-rules.ttl")`. Pass `infer=False` only
when you deliberately want to validate without the SHACL-AF rules.

## Compile: resolve and validate in one step

`compile()` resolves, validates, and returns the frozen snapshot, or raises
`ValidationError` listing the violations:

```{code-cell} python3
resolved = model.compile()
resolved["sludge-draw"]
```

Use `compile(validate=False)` only when you need a partial model on purpose,
for example while diagnosing it.

## Save

```{code-cell} python3
model.save("plant.ttl")
```

The format comes from the file extension. `save()` and `graph()` resolve the
model but do not validate it, so run `validate()` or `compile()` first when
the file must conform. The saved graph declares the ontologies it uses with
`owl:imports`, which is how [loading it again](query-loaded-models.md)
finds the right packages.
