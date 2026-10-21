---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Model a treatment train

This tutorial models a conventional surface-water treatment train:
coagulation, flocculation, sedimentation, filtration, and disinfection
([CDC overview](https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html)).
You will connect the stages, mark the system boundary, explore the result,
save it, and load it again.

![Treatment train with sludge and filter backwash branches](../_static/treatment-train.svg)

The model records equipment, connectivity, and treatment intent. It does not
calculate removal, dose, or contact time.

## 1. Import the stages

`objectrdf.watr.drinking_water` provides one class per stage. Each subclasses
a WaTr equipment class and fixes its process, objective, and named ports.

| Stage | Class | WaTr parent |
| --- | --- | --- |
| Coagulation | `CoagulationStage` | `CoagulationBasin` |
| Flocculation | `FlocculationStage` | `FlocculationBasin` |
| Clarification | `ClarificationStage` | `SedimentationTank` |
| Filtration | `RapidSandFiltrationStage` | `RapidSandFilter` |
| Disinfection | `ChlorinationStage` | `ChlorinationUnit` |

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

## 2. Connect the stages

Connect named ports along the production path. The clarifier's `sludge`
outlet and the filter's backwash ports are separate points, so waste cannot
end up feeding the next stage.

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

`model.system()` groups the stages. `boundary()` marks the points where flow
crosses into or out of the system: raw water in, finished water out, sludge
out, and backwash water in and out.

## 3. Explore the result

`compile()` resolves the connections, validates the model, and returns a
snapshot. List each stage's process and objective:

```{code-cell} python3
resolved = model.compile()
plant = resolved["treatment-system"]

for stage in plant.has_member:
    print(f"{stage.name}: {stage.meta.label}")
    print("  processes:", ", ".join(p.meta.label for p in stage.has_process))
    print("  objectives:", ", ".join(o.meta.label for o in stage.has_treatment_objective))
```

Follow each outlet through its pipe to the next stage:

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

List the boundary points and their media:

```{code-cell} python3
for point in sorted(plant.has_boundary_connection_point, key=lambda item: item.name):
    direction = "IN" if isinstance(point, InletConnectionPoint) else "OUT"
    print(f"{direction:3} {point.owner.name}.{point.label}: {point.medium.label}")
```

Sludge is its own medium. Both filter outlets carry water and are told apart
by name.

## 4. Save and load

```{code-cell} python3
model.save("treatment.ttl")
```

The file imports the drinking-water ontology, so `from_graph()` selects the
right package. Query by the WaTr parent class:

```{code-cell} python3
loaded = Model.from_graph("treatment.ttl")
for tank in loaded.find_all(SedimentationTank):
    print(f"{tank.name}: {tank.type}")
    for outlet in tank.ports:
        if isinstance(outlet, OutletConnectionPoint):
            print(f"  {outlet.label}: {outlet.medium.label}")
```

## 5. Draw it

```{code-cell} python3
from objectrdf import flowsheet

flowsheet(loaded, title="Conventional treatment train")
```

Unconnected boundary points are drawn as feed and product terminals.

## Next

[Instrument a plant](watr-instrumented-plant.md) adds pumps, residuals
handling, an influent property set, sensors, and actuators to this train. The
script version is `examples/watr/treatment/watr_quickstart.py`.
