# Authoring WaTr models

`objectrdf.watr` is generated from the
[local WaTr snapshot](../ontology/README.md) combining upstream PRs 39 and 46,
with its S223 and QUDT imports closure. Its ontology namespace is
`https://watermetadata.org/ontology/watr#`. It exposes WaTr treatment
equipment, processes, substances, and roles while reusing S223 connection
points and deferred Z3 resolution.

```python
from objectrdf import Model, connect
from objectrdf.watr import Chiller, Pump, Tank

with Model("urn:example/treatment#") as model:
    source = Chiller("source")
    pump = Pump("transfer-pump")       # WaTr Pump
    product = Tank("product-tank")     # accepts the Mix-Fluid domain
    inlet = connect(source, pump)
    outlet = connect(pump, product)

resolved = model.resolve()
assert resolved.connection(inlet).medium is resolved.connection(outlet).medium
```

The source establishes `Fluid-Water`. Water is permitted by both pump ports
and by the tank's broad `Mix-Fluid` domain, so the optimizer ranks that
coherent assignment above unsupported alternatives. This is an assignment
preference, not a hard claim that every pump preserves medium. Generic
treatment equipment may still have several equal-best media. Constrain such a
component at creation time or later through its handle:

```python
from objectrdf.watr import enums

flow = connect(source, target)
flow.medium = enums.values.Fluid_Sludge
flow.has_role.add(enums.values.Role_Backwash)
```

You can also author a known WaTr/S223 ConnectionPoint with `medium`, or
connect broad-domain equipment to a device that already establishes a medium.
Connection handles expose multi-valued generated properties as staged
collections, so roles can be added before the concrete Connection exists.
See [Giving the solver media hints](s223.md#giving-the-solver-media-hints) for
all supported patterns and diagnostics.

## Describe treatment intent

WaTr separates the process a unit performs from the treatment objective it
achieves. Both are punned ontology class terms: pass the generated classes
directly to equipment or a system. An installation-specific role is an enum
value:

```python
from objectrdf.watr import (
    Process_Sedimentation,
    SedimentationTank,
    TreatmentObjective_Clarification,
    enums,
)

with Model("urn:example:clarifier#") as treatment:
    clarifier = SedimentationTank(
        "clarifier",
        has_process=[Process_Sedimentation],
        has_treatment_objective=[TreatmentObjective_Clarification],
        has_role=[enums.values.Role_Primary],
    )

print([item.__name__ for item in clarifier.has_treatment_objective])
```

Explore available process and objective subclasses through `Process.meta.tree()`
and `TreatmentObjective.meta.tree()`. The
[book guide](book/how-to/watr-processes.md) gives an executable example and
explains how ontology class defaults relate to authored properties.

When WaTr and S223 define the same local name, the WaTr class keeps the public
name (`Pump`) and the imported S223 class receives a deterministic suffix
(`Pump_2`). WaTr enumeration additions, such as `Fluid_Sludge` and
`Role_Backwash`, are available alongside S223 values in `objectrdf.watr.enums`.
These are punned named individuals, so use the exported instance directly
rather than constructing a class. Constituents such as
`Constituent_Salt` and `Constituent_SuspendedSolids` can qualify stream
properties through `stream_state(...).quantity(..., substance=...)`.

See
[`examples/watr/treatment/watr_quickstart.py`](../examples/watr/treatment/watr_quickstart.py)
for a complete serializing example and [Authoring 223P](s223.md) for handles,
snapshots, ambiguity, and validation behavior shared by both packages.
See [Quantities and stream state](quantities.md) for compiled QUDT terms and
the boundary between ontology semantics and convenience authoring.

The [ASM2d example](../examples/watr/asm2d/README.md) writes a larger WaTr/S223
Turtle graph with seven biological reactors, a secondary clarifier, recycle
loops, process and objective metadata, and selected WaterTAP design values.
