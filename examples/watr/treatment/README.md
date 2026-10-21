# Conventional surface-water treatment

This example models five WaTr treatment units:

![Treatment train with sludge and filter backwash branches](../../../docs/book/_static/treatment-train.svg)

The sequence follows [CDC's overview of water treatment](https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html).
Coagulation and flocculation prepare particles for settling; clarification
withdraws sludge, sand filtration removes remaining particles, and the final
stage has the objective of disinfection.

Run from the repository root:

```bash
uv run python examples/watr/treatment/watr_quickstart.py
```

The script compiles and validates the model, then writes `treatment.ttl` beside
it. It creates five equipment members, four internal water pipes, and five
system boundary points: raw-water inlet, finished-water outlet, sludge outlet,
backwash supply inlet, and spent-backwash outlet. Backwashing is an intermittent
operation; the graph describes its paths without scheduling it.

The Python stage classes come from `plumb.watr.drinking_water`, generated
from [`ontology/drinking-water.ttl`](../../../ontology/drinking-water.ttl).
That source selects existing WaTr equipment classes, process terms, treatment
objectives, and named ports. Edit the source and run `make regen` to regenerate
the package. The [executable tutorial](../../../docs/book/tutorials/watr-treatment.md)
walks through authoring, inspection, and graph loading.

This is a treatment schematic, with chemical-feed equipment, backwash controls,
and residuals handling outside its boundary. It does not size equipment or
calculate removal efficiency, dose, or contact time. Water uses the broad
`Fluid_Water` medium; a treatment objective does not assert water quality.
