# What the new WaTr vocabulary means

This package is generated from WaTr
[v0.3.0.rc1](https://github.com/DataDrivenCPS/water-ontology/releases/tag/v0.3.0.rc1),
vendored unmodified as `ontology/watr-0.3.0rc1.ttl`. It is a release
candidate, so terms may still change before WaTr 0.3.0.

## Equipment, process, objective, and role

These four descriptions answer different questions about one unit:

| Question | RDF relation | Example |
| --- | --- | --- |
| What kind of equipment is it? | `rdf:type` | `watr:GravityThickener` |
| What activity does it perform? | `watr:hasProcess` | `watr:Process-Settling` |
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
settling, and `ProcessObjectiveRule` adds the objective a process declares
(`Process-Chlorination` implies disinfection). `model.validate(infer=True)` uses those rules
during validation, but does not add inferred relationships to the authored
Python objects. `Model.from_graph(..., infer=True)` applies inference before
loading an RDF graph. A role depends on the installation and is never supplied
by these class-default rules. In the current Python API, constructors may still
require an explicit `has_process` argument even when the RDF rules can infer
it.

## Aqueous media and constituents

WaTr 0.3 models freshwater with an H₂O constituent and seawater, brackish water,
and brine with H₂O and NaCl constituents. S223 can use a shared constituent
to treat those media as compatible at connections. This establishes
compatibility; it does not assert equal composition or enforce a material
balance. `Fluid-Sludge` is a `Mix-Fluid` composed of water and solids, not a
kind of `Fluid-Water`, so a sludge port does not accept a water-only
connection.

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
