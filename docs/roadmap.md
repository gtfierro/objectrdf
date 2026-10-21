# Implementation roadmap

## Completed in the current framework pass

- Strict `Model.compile(validate=True)` with local, reproducible shape bundles.
- Multiple-inheritance constructor unioning; punned terms remain reference
  instances rather than generated instantiable classes.
- Named ports, solver-level paired-port medium propagation, and concrete
  `pairedConnectionPoint` materialization.
- System member scopes and solver-derived boundary connection points.
- QUDT 3.4.0 unit and quantity-kind vocabularies compiled through ontoenv,
  QUDT quantity values, and concise quantity authoring.
- A nominal stream-state authoring view using existing S223/WaTr semantics.
- Per-connection solver explanations with authored and inferred evidence.
- BeautifulSoup-style traversal: narrowing filters with `exact()`,
  containment search, and topology walks with `through=` path filters
  ([traversal.md](traversal.md)).

## Deferred deliberately

- Logical/property-package translation. Revisit after the ontology-facing
  quantity and stream-state patterns settle.
- Source traceability/provenance for generated model facts. Revisit before
  adding interchange or translation workflows.
- A committed lockfile pinning the versions and hashes of each generated
  package's imports closure. Generation is byte-identical for an unchanged
  closure and each package bundles its compiled graph, but regenerating Brick,
  S223, or WaTr still resolves imports from the network.

## Later development line

A translator between S223/WaTr and WaterTAP is on the development timeline.
WaterTAP itself is not modeled by this framework today. Translation needs an
explicit mapping ontology or mapping package for unit models, ports, state
variables, assumptions, and provenance; free-text comments are not a semantic
translation contract.
