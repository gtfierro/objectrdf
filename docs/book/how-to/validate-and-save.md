---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Validate and save

`validate()` checks the resolved RDF against the SHACL shapes bundled with
each package, using shifty. It applies S223's and WaTr's SHACL-AF rules first
and maps each result back to a Python object.

```{code-cell} python3
from plumb import Model, connect
from plumb.watr import Pump, Tank
from plumb.watr.drinking_water import ClarificationStage

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

The sludge tank has no connection point. Connect it:

```{code-cell} python3
connect(clarifier.sludge, sludge_tank, name="sludge-draw")
model.validate().ok
```

`report.issues` also holds warnings and informational notices, which do not
affect `report.ok`. An unconnected boundary point is a notice.

## Add your own shapes

Pass a Turtle path or an `rdflib.Graph`:

```python
model.validate("site-rules.ttl")
```

`infer=False` skips the SHACL-AF rules.

## Compile

`compile()` resolves, validates, and returns the snapshot, or raises
`ValidationError`:

```{code-cell} python3
resolved = model.compile()
resolved["sludge-draw"]
```

`compile(validate=False)` returns a snapshot without validating.

## Save

```{code-cell} python3
model.save("plant.ttl")
```

The format follows the extension. `save()` and `graph()` resolve but do not
validate. The file declares its ontologies with `owl:imports`, which is how
[loading](save-and-load.md) finds the packages.
