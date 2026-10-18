---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Tutorial: model a conventional water treatment train

Build a surface-water treatment train using WaTr's treatment equipment and
process vocabulary. The sequence follows the conventional steps described in
[CDC's treatment overview](https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html):
coagulation, flocculation, sedimentation, filtration, and disinfection.

![Treatment train with sludge and filter backwash branches](../_static/treatment-train.svg)

| Stage | WaTr equipment class | Purpose in this train |
| --- | --- | --- |
| Coagulation | `CoagulationBasin` | Add coagulant to destabilize suspended particles. |
| Flocculation | `FlocculationBasin` | Mix gently so particles form larger flocs. |
| Clarification | `SedimentationTank` | Settle flocs; withdraw sludge separately. |
| Filtration | `RapidSandFilter` | Remove remaining suspended particles through sand media. |
| Chlorination and contact | `ChlorinationUnit` | Dose chlorine and provide a contact stage for disinfection. |

This is an equipment and connectivity model. It records treatment intent;
it does not calculate removal efficiency, chlorine dose, or contact time.
Chemical-feed equipment, filter-cleaning controls, and residuals handling sit
outside the model boundary.

## 1. Import the treatment configurations

The configurations below subclass the WaTr equipment in the table. Their
processes, treatment objectives, and named ports come from
`ontology/drinking-water.ttl`, compiled into `objectrdf.watr.drinking_water`.
Model authors import these definitions rather than writing Python subclasses
or port-selection helpers.

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr import (
    InletConnectionPoint,
    OutletConnectionPoint,
    SedimentationTank,
)
from objectrdf.watr.drinking_water import (
    ChlorinationStage,
    ClarificationStage,
    CoagulationStage,
    FlocculationStage,
    RapidSandFiltrationStage,
)
```

## 2. Author the train and its boundaries

Connect explicit named ports along the production path. The clarifier has a
separate sludge outlet. The filter has distinct production and backwash ports,
so its waste cannot accidentally become the supply to disinfection.

```{code-cell} python3
with Model("urn:example/treatment#") as model:
    with model.system("treatment-system") as system:
        coagulation = CoagulationStage("coagulation")
        flocculation = FlocculationStage("flocculation")
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("sand-filter")
        disinfection = ChlorinationStage("chlorination-contact")

        connect(coagulation.outlet, flocculation.inlet, name="coagulated-water")
        connect(flocculation.outlet, clarifier.inlet, name="flocculated-water")
        connect(
            clarifier.clarified_water, sand_filter.inlet, name="clarified-water"
        )
        connect(
            sand_filter.filtered_water, disinfection.inlet, name="filtered-water"
        )

        system.boundary(
            coagulation.inlet,
            disinfection.outlet,
            clarifier.sludge,
            sand_filter.backwash_supply,
            sand_filter.backwash_waste,
        )
```

The system scope collects five treatment units. Its five boundary points
represent raw water entering, finished water leaving, sludge withdrawal,
clean backwash water entering, and spent backwash leaving. Boundary points
connect to the surrounding plant without adding placeholder equipment.

Backwashing is an intermittent cleaning operation. These ports describe
available paths; they do not imply that production and backwashing run
simultaneously. The external clean-water supply and waste handling are left
outside this train.

## 3. Explore the treatment train

`compile()` resolves the connections and validates the model against its SHACL
shapes. Use the resulting snapshot to explore the equipment and its connections.

Start with the system's members: what treatment does each unit perform, and
what is it intended to achieve? The process and objective labels come from WaTr.

```{code-cell} python3
resolved = model.compile()
plant = resolved["treatment-system"]

for stage in plant.has_member:
    print(f"{stage.name}: {stage.meta.label}")
    print("  processes:", ", ".join(p.meta.label for p in stage.has_process))
    print("  objectives:", ", ".join(o.meta.label for o in stage.has_treatment_objective))
```

Next, discover how these units are connected, without supplying the sequence
of stages or the connection handles used during authoring. Follow each outlet
through its pipe to the receiving unit's inlet. A boundary outlet has no
internal pipe, so it does not lead to another unit in this model.

```{code-cell} python3
for stage in plant.has_member:
    for outlet in stage.ports:
        if not isinstance(outlet, OutletConnectionPoint) or outlet.connection is None:
            continue
        pipe = outlet.connection
        for inlet in pipe.connects_at:
            if isinstance(inlet, InletConnectionPoint):
                print(
                    f"{stage.name}.{outlet.label} → "
                    f"{inlet.owner.name}.{inlet.label} via {pipe.name}"
                )
```

This reveals that clarified water feeds the sand filter and filtered water
feeds the chlorination stage. Sludge and spent backwash do not feed another
treatment stage here. To find their exit points, inspect the system boundary:
which flows enter or leave, at which unit, and carrying what medium?

```{code-cell} python3
for point in sorted(plant.has_boundary_connection_point, key=lambda item: item.name):
    direction = "IN" if isinstance(point, InletConnectionPoint) else "OUT"
    print(f"{direction:3} {point.owner.name}.{point.label}: {point.medium.label}")
```

The report separates the raw-water inlet from the backwash supply inlet, and
the finished-water outlet from the sludge and backwash waste outlets. It also
shows sludge as a distinct medium, while the two filter outlets both carry
water. Their named ports identify their different purposes.

Water remains the broad `Fluid_Water` medium throughout the main path. A
`TreatmentObjective_Disinfection` term expresses the purpose of the final
stage; it does not assert a measured water quality or treatment outcome.

## 4. Save the model as RDF

Write the resolved RDF to `treatment.ttl` in the current working directory:

```{code-cell} python3
model.save("treatment.ttl")
```

The file contains the equipment, processes, treatment objectives, connections,
and system boundaries, ready to share or load in another session.

## 5. Load and explore the saved model

Pass the domain package's `REGISTRY` to load all its types, including the WaTr
base classes. You do not need to choose an equipment class to obtain the registry.
For example, retrieve settling tanks by their WaTr equipment class, even though
the saved objects use the more specific
`ClarificationStage` configuration, and report their outlet streams.

```{code-cell} python3
from objectrdf.watr import drinking_water

loaded = Model.from_graph("treatment.ttl", registries=drinking_water.REGISTRY)
for tank in loaded.find_all(SedimentationTank):
    print(f"{tank.name}: {tank.type}")
    for outlet in tank.ports:
        if isinstance(outlet, OutletConnectionPoint):
            print(f"  {outlet.label}: {outlet.medium.label}")
```

Run the complete serializing example with
`uv run python examples/watr/treatment/watr_quickstart.py`. To change the
reusable stages, edit their RDF/SHACL source and run `make regen`.
Continue with [WaTr processes and objectives](../how-to/watr-processes.md)
or [domain configurations and quantity schemas](domain-configurations.md).
