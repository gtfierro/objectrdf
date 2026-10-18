# What the new WaTr vocabulary means

This package uses the local WaTr snapshot in `ontology/watr-pr39-pr46.ttl`,
assembled from water-ontology PRs 39 and 46. The snapshot keeps WaTr's 0.2
ontology IRI, but includes proposed changes that are not yet a published
release.

## Equipment, process, objective, and role

These four descriptions answer different questions about one unit:

| Question | RDF relation | Example |
| --- | --- | --- |
| What kind of equipment is it? | `rdf:type` | `watr:GravityThickener` |
| What activity does it perform? | `watr:hasProcess` | `watr:Process-Sedimentation` |
| What result is it intended to achieve? | `watr:hasTreatmentObjective` | `watr:TreatmentObjective-Thickening` |
| How is it used in this system? | `s223:hasRole` | `watr:Role-Primary` |

A sedimentation tank can clarify water, while a gravity thickener uses the
same settling process to thicken sludge. The process describes the mechanism;
the objective describes the intended outcome. A role such as `Role-Primary`
describes its place in a particular treatment system.

The generated `objectrdf.watr` module exposes the `Process` and
`TreatmentObjective` class hierarchies. Equipment and systems have
`has_process` and `has_treatment_objective` properties, which accept the
corresponding generated classes as punned ontology terms. These relations
serialize the ontology class IRIs directly, without creating named process or
objective objects. Roles are enum values in
`objectrdf.watr.enums` and can be passed to `has_role`. The
[authoring guide](../how-to/watr-processes.md) shows all three together.

The ontology's SHACL-AF class-default rules can infer processes and objectives
fixed by an equipment class. For example, `GravityThickener` implies
sedimentation and thickening. `model.validate(infer=True)` uses those rules
during validation, but does not add inferred relationships to the authored
Python objects. `Model.from_graph(..., infer=True)` applies inference before
loading an RDF graph. A role depends on the installation and is never supplied
by these class-default rules. In the current Python API, constructors may still
require an explicit `has_process` argument even when the RDF rules can infer
it.

## Aqueous media and constituents

PR 46 models freshwater with an H₂O constituent and seawater, brackish water,
and brine with H₂O and NaCl constituents. S223 can use a shared constituent
to treat those media as compatible at connections. This establishes
compatibility; it does not assert equal composition or enforce a material
balance. `Fluid-Sludge` belongs beneath both `Fluid-Water` and `Mix-Fluid`.
The Python enum value therefore has two entries in `.parents`, and `.is_a()`
recognizes both branches.

The bundled shapes also check percentage compositions. A composition whose
stated lower percentages exceed 100% violates
`CompositionPercentageShape`. If exactly one constituent percentage is
missing and the others determine a nonnegative remainder,
`CompositionComplementRule` can infer that value. A range or multiple missing
values does not determine one remainder. These are SHACL validation and
inference rules; selecting a medium with `connect(..., medium=...)` does not
calculate composition.

See [Explore enumeration hierarchies](../how-to/explore-enums.md) to inspect
the media branches in Python, and [Inspect port requirements](../how-to/inspect-port-contracts.md)
to see which media a particular equipment class permits.
