# Examples

Examples are grouped first by ontology and then by scenario. Each scenario
directory contains its runnable Python and related inputs or generated RDF.

## Brick

- [`brick/quickstart/`](brick/quickstart/) — a small building, HVAC equipment,
  zones, points, and Brick `feeds` relationships.

## ASHRAE 223P

- [`s223/ahu/`](s223/ahu/) — an air handler with air and chilled-water
  connection topology.

## WaTr

- [`watr/treatment/`](watr/treatment/) — a compact chiller, pump, and tank
  treatment path.
- [`watr/seawater_ro/`](watr/seawater_ro/) — a full seawater reverse-osmosis
  system with nominal stream and equipment properties.
- [`watr/seawater_ro_pretreatment/`](watr/seawater_ro_pretreatment/) —
  seawater pretreatment stages.
- [`watr/epanet_anytown/`](watr/epanet_anytown/) — the Anytown EPANET input,
  converter, generated WaTr graph, and a directly authored topology example.
- [`watr/distribution_network/`](watr/distribution_network/) — a small,
  directly authored distribution loop with hydraulic and water-quality
  sensors.
