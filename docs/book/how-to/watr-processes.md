---
file_format: mystnb
kernelspec:
  name: python3
---

# Set processes, objectives, and roles

A WaTr unit records what it does (`has_process`), what it is for
(`has_treatment_objective`), and its place in your system (`has_role`).
[The WaTr vocabulary](../explanation/watr-vocabulary.md) explains the
difference.

## Find the terms

Processes and objectives are class hierarchies. Roles are enum values.

```{code-cell} python3
from objectrdf.watr import Process, TreatmentObjective, enums

print(Process.meta.tree(max_depth=1))
print(TreatmentObjective.meta.tree(max_depth=1))
```

## Use the class defaults

When the class fixes a process or objective, the constructor fills it in. A
gravity thickener needs only its role:

```{code-cell} python3
from objectrdf import Model
from objectrdf.watr import GravityThickener

with Model("urn:example:thickening#") as model:
    thickener = GravityThickener("primary-thickener", has_role=[enums.values.Role_Primary])

list(thickener.has_process), list(thickener.has_treatment_objective), list(thickener.has_role)
```

A class that fixes no process, such as `DewateringUnit`, requires
`has_process`.

## Add an objective

A sedimentation tank always settles, but its objective depends on the
installation. State it; the process is still filled in:

```{code-cell} python3
from objectrdf.watr import SedimentationTank, TreatmentObjective_Clarification

with model:
    clarifier = SedimentationTank(
        "primary-clarifier",
        has_treatment_objective=[TreatmentObjective_Clarification],
    )

list(clarifier.has_process), list(clarifier.has_treatment_objective)
```

## Name a more specific process

A subclass of the default replaces it:

```{code-cell} python3
from objectrdf.watr import MediaFiltrationUnit, Process_RapidSandFiltration

with model:
    sand_filter = MediaFiltrationUnit(
        "sand-filter", has_process=[Process_RapidSandFiltration]
    )

list(sand_filter.has_process)
```

Systems take the same attributes.
