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
assert Process.meta["Settling"].meta.iri.endswith("Process-Settling")
assert TreatmentObjective.meta["Thickening"].meta.iri.endswith(
    "TreatmentObjective-Thickening"
)
print(enums.values.Role_Primary.iri)
```

## Attach a process, objective, and role

Processes and objectives are generated class terms used directly. The role is
a generated enum value. When the class's shapes fix a process or objective,
the constructor fills it in, so a gravity thickener needs only its role:

```{code-cell} python3
from objectrdf import Model
from objectrdf.watr import GravityThickener

with Model("urn:example:thickening#") as model:
    thickener = GravityThickener(
        "primary-thickener",
        has_role=[enums.values.Role_Primary],
    )

print(thickener.type)
print([process.__name__ for process in thickener.has_process])
print([objective.__name__ for objective in thickener.has_treatment_objective])
print([role.iri for role in thickener.has_role])
```

These are the values WaTr's `ClassDefaultsRule` would infer in RDF. A
`UnitProcess` whose class fixes no process, such as a generic
`DewateringUnit`, still requires `has_process`.

## Add an objective that depends on the installation

A sedimentation tank always settles, but what it is operated for depends on
the installation. State that objective; the settling process is still filled
in. The relationships are collections, so a unit can state more than one
process or objective.

```{code-cell} python3
from objectrdf.watr import SedimentationTank, TreatmentObjective_Clarification

with model:
    clarifier = SedimentationTank(
        "primary-clarifier",
        has_treatment_objective=[TreatmentObjective_Clarification],
        has_role=[enums.values.Role_Primary],
    )

print([item.__name__ for item in clarifier.has_process])
print([item.meta.iri for item in clarifier.has_treatment_objective])
# model.save("treatment.ttl")
```

## Name a more specific process

A supplied process that is a subclass of the class default replaces it. A
media filter performs media filtration; a rapid sand filter is one kind:

```{code-cell} python3
from objectrdf.watr import MediaFiltrationUnit, Process_RapidSandFiltration

with model:
    sand_filter = MediaFiltrationUnit(
        "sand-filter",
        has_process=[Process_RapidSandFiltration],
    )

print([item.__name__ for item in sand_filter.has_process])
```

Both relations are serialized into RDF by `model.graph()` and `model.save()`.
For a system-level process, use the same `has_process` and
`has_treatment_objective` attributes on a generated `System` subclass.
