# Authoring WaTr models

`objectrdf.watr` is generated from the
WaTr [v0.3.0.rc1](../ontology/README.md) release candidate, with its S223 and
QUDT imports closure. Its ontology namespace is
`https://watermetadata.org/ontology/watr#`. It exposes WaTr treatment
equipment, processes, substances, and roles while reusing S223 connection
points and deferred Z3 resolution.

```python
from objectrdf import Model, connect
from objectrdf.watr.drinking_water import (
    ChlorinationStage,
    ClarificationStage,
    CoagulationStage,
    FlocculationStage,
    RapidSandFiltrationStage,
)

with Model("urn:example/treatment#") as model:
    with model.system("treatment-system") as system:
        coagulation = CoagulationStage("coagulation")
        flocculation = FlocculationStage("flocculation")
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("sand-filter")
        disinfection = ChlorinationStage("chlorination-contact")

        connect(coagulation.outlet, flocculation.inlet)
        connect(flocculation.outlet, clarifier.inlet)
        connect(clarifier.clarified_water, sand_filter.inlet)
        connect(sand_filter.filtered_water, disinfection.inlet)
        system.boundary(
            coagulation.inlet, disinfection.outlet, clarifier.sludge,
            sand_filter.backwash_supply, sand_filter.backwash_waste,
        )

resolved = model.compile()
```

This conventional surface-water sequence follows
[CDC's treatment overview](https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html).
The stages subclass WaTr's `CoagulationBasin`, `FlocculationBasin`,
`SedimentationTank`, `RapidSandFilter`, and `ChlorinationUnit`. Their process
terms, objectives, and named ports are generated from
[`ontology/drinking-water.ttl`](../ontology/drinking-water.ttl). The main path
carries water; sludge and intermittent filter backwash have separate boundary
ports. This schematic records treatment intent without calculating performance
or sizing. See the [executable tutorial](book/tutorials/watr-treatment.md).

Generic treatment equipment may still have several equal-best media. Constrain
such a connection at creation time or later through its handle. For example,
when connecting residuals equipment:

```python
from objectrdf.watr import enums

flow = connect(residuals_source, residuals_target)
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
    Process_Settling,
    SedimentationTank,
    TreatmentObjective_Clarification,
    enums,
)

with Model("urn:example:clarifier#") as treatment:
    clarifier = SedimentationTank(
        "clarifier",
        has_process=[Process_Settling],
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
properties through schema definitions or `subject.quantity(..., of_substance=...)`.

See
[`examples/watr/treatment/watr_quickstart.py`](../examples/watr/treatment/watr_quickstart.py)
for a complete serializing example and [Authoring 223P](s223.md) for handles,
snapshots, ambiguity, and validation behavior shared by both packages.
See [Quantities and property schemas](quantities.md) for compiled QUDT terms and
the boundary between ontology semantics and convenience authoring.

The [ASM2d example](../examples/watr/asm2d/README.md) writes a larger WaTr/S223
Turtle graph with seven biological reactors, a secondary clarifier, recycle
loops, process and objective metadata, and selected WaterTAP design values.
