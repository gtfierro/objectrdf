---
file_format: mystnb
kernelspec:
  name: python3
---

# Domain extensions

A domain extension is a small ontology layered on WaTr or S223. It declares
subclasses of base equipment and uses SHACL to fix what the base leaves open:

- which connection points the equipment has, with their direction, medium,
  count, and name;
- required processes, treatment objectives, and roles;
- defaults that the model author can replace;
- property schemas: groups of quantities with kinds, units, and bounds.

`plumb gen` compiles it into a package beside its base, such as
`plumb.watr.drinking_water`. Model authors just import it.

## When to write one

Write one when a definition outlives one model:

| You want | Use |
| --- | --- |
| A topology for a single plant | Base classes, `connect()`, and `.port()` |
| Quantities that only one script or notebook needs | A Python [`PropertySchema`](../how-to/define-property-sets.md) |
| One equipment layout reused across many models | An extension class with named ports |
| Definitions that other tools read as RDF, or that validation should enforce | An extension |

Extension shapes are SHACL: validation enforces them and any RDF tool reads
them. A Python schema exists only in its program.

## How it relates to the base

- Extension classes subclass base classes, in RDF and Python. Queries for
  `SedimentationTank` find a `ClarificationStage`.
- Enumerations, QUDT terms, and the solver come from the base unchanged.
- The registry and bundled `_shapes.ttl` include the base, so validation
  checks both.
- A saved model imports the extension's ontology. For readers that cannot
  resolve the import, `Model.export_ontology()` writes it out.

## A worked example: drinking water

`plumb.watr.drinking_water` is compiled from
[`ontology/drinking-water.ttl`](https://github.com/gtfierro/plumb/blob/main/ontology/drinking-water.ttl),
a teaching configuration of conventional surface-water treatment. Each stage
fixes its process, objective, and connection points:

| Stage | Subclass of | Process | Objective | Connection points |
| --- | --- | --- | --- | --- |
| `CoagulationStage` | `CoagulationBasin` | Coagulation | Turbidity removal | `inlet`, `outlet` |
| `FlocculationStage` | `FlocculationBasin` | Flocculation | Turbidity removal | `inlet`, `outlet` |
| `ClarificationStage` | `SedimentationTank` | Settling | Clarification | `inlet`, `clarified_water`, `sludge` |
| `RapidSandFiltrationStage` | `RapidSandFilter` | Rapid sand filtration | Turbidity removal | `inlet`, `filtered_water`, `backwash_supply`, `backwash_waste` |
| `ChlorinationStage` | `ChlorinationUnit` | Chlorination | Disinfection | `inlet`, `outlet` |

Every point carries water except the clarifier's `sludge` outlet. The
clarifier's source:

```turtle
dw:ClarificationStage a owl:Class ;
    rdfs:subClassOf watr:SedimentationTank ;
    rdfs:label "Clarification stage" .
dw:ClarificationStageShape a sh:NodeShape ;
    sh:targetClass dw:ClarificationStage ;
    sh:property [ sh:path watr:hasProcess ; sh:hasValue watr:Process-Settling ],
        [ sh:path watr:hasTreatmentObjective ;
          sh:hasValue watr:TreatmentObjective-Clarification ],
        [ sh:path s223:hasConnectionPoint ; sh:name "inlet" ;
          sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
          sh:qualifiedValueShape dw:Inlet ],
        [ sh:path s223:hasConnectionPoint ; sh:name "clarified_water" ;
          sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
          sh:qualifiedValueShape dw:ClarifiedWater ],
        [ sh:path s223:hasConnectionPoint ; sh:name "sludge" ;
          sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
          sh:qualifiedValueShape dw:Sludge ],
        [ sh:path s223:hasConnectionPoint ; sh:minCount 3 ; sh:maxCount 3 ] .
dw:Sludge sh:class s223:OutletConnectionPoint ;
    sh:property [ sh:path s223:hasMedium ; sh:hasValue watr:Fluid-Sludge ],
        [ sh:path rdfs:label ; sh:hasValue "sludge" ] .
```

Each `sh:name` becomes an attribute, and the process and objective are filled
in:

```{code-cell} python3
from plumb import Model
from plumb.watr import SedimentationTank
from plumb.watr.drinking_water import ClarificationStage

print(ClarificationStage.describe_ports())

with Model("urn:example:extension#"):
    clarifier = ClarificationStage("clarifier")

print(isinstance(clarifier, SedimentationTank))
print(list(clarifier.has_process), list(clarifier.has_treatment_objective))
print(clarifier.sludge)
```

Pass `clarifier.sludge` to `connect()` to use that outlet. `connect(clarifier,
pump)` is ambiguous, since a WaTr `Pump` takes water or sludge.

Next: [Generate a domain API](../how-to/generate-domain-api.md), and the
[extension compiler reference](../reference/extension-compiler.md).
