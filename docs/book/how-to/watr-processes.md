---
file_format: mystnb
kernelspec:
  name: python3
---

# Author WaTr processes, objectives, and roles

Use the generated classes to name what a unit does, and an enum value to
record its role in your system. The
[vocabulary explanation](../explanation/watr-vocabulary.md) distinguishes
those from treatment objectives.

## Find the available terms

`Process` and `TreatmentObjective` are class hierarchies. You can inspect a
subtree and select a descendant by short name:

```{code-cell} python3
from objectrdf.watr import Process, TreatmentObjective, enums

print(Process.meta.tree(max_depth=1))
print(TreatmentObjective.meta.tree(max_depth=1))
assert Process.meta["Sedimentation"].meta.iri.endswith("Process-Sedimentation")
assert TreatmentObjective.meta["Thickening"].meta.iri.endswith(
    "TreatmentObjective-Thickening"
)
print(enums.values.Role_Primary.iri)
```

## Attach a process, objective, and role

Processes and objectives are generated class terms used directly. The role is
a generated enum value.
`has_process` is required by the current `UnitProcess` constructor even when
the ontology could infer a class-default process from RDF later.

```{code-cell} python3
from objectrdf import Model
from objectrdf.watr import (
    GravityThickener,
    Process_Sedimentation,
    TreatmentObjective_Thickening,
)

with Model("urn:example:thickening#") as model:
    thickener = GravityThickener(
        "primary-thickener",
        has_process=[Process_Sedimentation],
        has_treatment_objective=[TreatmentObjective_Thickening],
        has_role=[enums.values.Role_Primary],
    )

print(thickener.type)
print([process.__name__ for process in thickener.has_process])
print([objective.__name__ for objective in thickener.has_treatment_objective])
print([role.iri for role in thickener.has_role])
```

The class `GravityThickener` also carries a thickening objective in the
ontology's shapes. SHACL-AF inference can derive class defaults in the RDF
graph, but `resolve()` does not add them to the authored Python object. State
the intended objective explicitly when you want to inspect it on the object.

## Add an objective that depends on the installation

A sedimentation tank can record its process and intended outcome through the
same constructor API. The relationships are collections, so a unit can state
more than one process or objective.

```{code-cell} python3
from objectrdf.watr import (
    SedimentationTank,
    TreatmentObjective_Clarification,
)

with model:
    clarifier = SedimentationTank(
        "primary-clarifier",
        has_process=[Process_Sedimentation],
        has_treatment_objective=[TreatmentObjective_Clarification],
        has_role=[enums.values.Role_Primary],
    )

print([item.__name__ for item in clarifier.has_process])
print([item.meta.iri for item in clarifier.has_treatment_objective])
# model.save("treatment.ttl")
```

Both relations are serialized into RDF by `model.graph()` and `model.save()`.
For a system-level process, use the same `has_process` and
`has_treatment_objective` attributes on a generated `System` subclass.
