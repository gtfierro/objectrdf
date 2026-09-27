# Diagnose an S223 or WaTr connection

Use this when `resolve()` reports ambiguity or an impossible connection.

1. Keep the handle returned by `connect(source, target)`. It identifies the
   authored link before any RDF connection exists.
2. Call `report = model.check()` and inspect `report.status` and
   `report.issues`. Test `report.complete` when you need one concrete graph;
   `bool(report)` also accepts an underconstrained model.
3. If the status is `underconstrained`, add a fact you know: pass
   `medium=enums.values.Fluid_Water` to `connect()`, set `handle.medium`, choose an
   explicit port with `equipment.port(...)`, or constrain the connection class
   with `connection=`. An adjacent device with a fixed medium can also resolve
   the choice.
4. If the status is `unsatisfiable`, read the issue labels to find the authored
   constraints in conflict. Check flow direction, point capacity, allowed
   media, and the requested connection class.
5. Once complete, call `resolved = model.resolve()` and
   `resolved.explain(handle)` to see the selected endpoints and why the medium
   was chosen.

```python
from objectrdf import Model, connect
from objectrdf.watr import Chiller, Pump, enums

with Model("urn:example:diagnosis#") as model:
    source = Chiller("source")
    pump = Pump("pump")
    link = connect(source, pump)

report = model.check()
if not report.complete:
    for issue in report.issues:
        print(issue.message, issue.labels)
    link.medium = enums.values.Fluid_Water

resolved = model.resolve()
print(resolved.explain(link).medium_reason)
```

## List an instance's ports

`instance.ports` includes connection points that already exist and any named
deferred ports created with `instance.port(...)`. Before resolution, a general
piece of equipment may have no points yet because the solver still needs to
choose their medium or direction.

```python
print([(port.name, port.medium) for port in pump.ports])

snapshot = model.resolve()
resolved_pump = snapshot[pump.name]
print([(point.name, point.medium) for point in resolved_pump.ports])
```

For S223 and WaTr equipment, `list(instance.has_connection_point)` gives only
the concrete connection point objects currently attached to that instance.
On a loaded RDF model, those concrete points are available immediately.

`resolve()`, `graph()`, `save()`, and `validate()` require a complete assignment
for authored models. They raise `AmbiguousModelError` or
`UnsatisfiableModelError` when the solver cannot produce one.

For a known point on a particular device, use `device.port("supply", "out",
medium=enums.values.Fluid_Water)` and connect that port. The
repository's `docs/s223.md` guide describes port pairing and media hints
in more detail.
