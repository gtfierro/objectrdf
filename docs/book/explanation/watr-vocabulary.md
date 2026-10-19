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

Some processes and objectives are fixed by the equipment class. For example,
every `GravityThickener` performs settling to thicken sludge. WaTr's
`ClassDefaultsRule` infers these in RDF, and the generated constructors apply
the same defaults: `GravityThickener("thickener")` already has
`Process_Settling` and `TreatmentObjective_Thickening`. A default is added
only when you have not supplied that term or a subclass of it, so
`MediaFiltrationUnit(has_process=[Process_RapidSandFiltration])` does not also
get the generic `Process_MediaFiltration`.

`ProcessObjectiveRule` adds the objective a process declares
(`Process-Chlorination` implies disinfection). That rule is not applied to
Python objects: `model.validate(infer=True)` uses it during validation, and
`Model.from_graph(..., infer=True)` applies it before loading an RDF graph. A
role depends on the installation and is never supplied by these rules.

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
