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

`objectrdf gen` compiles the extension into a Python package beside its base,
such as `objectrdf.watr.drinking_water`. Model authors import that package
like any other and never run the compiler themselves.

## When to write one

Most models need no extension. Plain WaTr or S223 equipment, `connect()`, and
`.port()` describe a one-off topology, and a
[Python `PropertySchema`](https://github.com/gtfierro/objectrdf/blob/main/docs/quantities.md#schemas-written-in-python)
captures a set of quantities used in one notebook or script.

Write an extension when the definition outlives one model:

| You want | Use |
| --- | --- |
| A topology for a single plant | Base classes, `connect()`, and `.port()` |
| Quantities that only one script or notebook needs | A Python `PropertySchema` |
| One equipment layout reused across many models | An extension class with named ports |
| Definitions that other tools read as RDF, or that validation should enforce | An extension |

The shapes in an extension are real SHACL. Validation enforces them, and any
RDF tool can read them. A Python schema exists only inside the program that
defines it.

## How it relates to the base

Extension classes are subclasses of base classes, in RDF and in Python. A
`ClarificationStage` is a `watr:SedimentationTank`, so code and queries written
for sedimentation tanks also find clarification stages. Enumerations, QUDT
terms, and the connection solver come from the base unchanged.

The extension's registry contains the base classes as well as its own, and its
bundled `_shapes.ttl` contains the base shapes as well as the extension's.
Validating a model that uses the extension checks both.

A saved model types each object with the extension class IRI and declares
`owl:imports` for the extension's ontology. A reader that resolves that import
learns the subclass links back to WaTr. For readers that cannot resolve the
import, `Model.export_ontology()` writes the extension ontologies the model uses.

## A worked example: drinking water

`objectrdf.watr.drinking_water` is compiled from
[`ontology/drinking-water.ttl`](https://github.com/gtfierro/objectrdf/blob/main/ontology/drinking-water.ttl).
It is a teaching configuration of conventional surface-water treatment,
following
[CDC's treatment overview](https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html).
Each of its five stages subclasses a WaTr class and fixes the stage's process,
objective, and connection points:

| Stage | Subclass of | Process | Objective | Connection points |
| --- | --- | --- | --- | --- |
| `CoagulationStage` | `CoagulationBasin` | Coagulation | Turbidity removal | `inlet`, `outlet` |
| `FlocculationStage` | `FlocculationBasin` | Flocculation | Turbidity removal | `inlet`, `outlet` |
| `ClarificationStage` | `SedimentationTank` | Settling | Clarification | `inlet`, `clarified_water`, `sludge` |
| `RapidSandFiltrationStage` | `RapidSandFilter` | Rapid sand filtration | Turbidity removal | `inlet`, `filtered_water`, `backwash_supply`, `backwash_waste` |
| `ChlorinationStage` | `ChlorinationUnit` | Chlorination | Disinfection | `inlet`, `outlet` |

Every point carries water except the clarifier's `sludge` outlet, which carries
sludge. The clarifier's shape in the source reads:

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

In Python, each `sh:name` becomes an attribute, and the required process and
objective are filled in when the stage is created:

```{code-cell} python3
from objectrdf import Model
from objectrdf.watr import SedimentationTank
from objectrdf.watr.drinking_water import ClarificationStage

print(ClarificationStage.describe_ports())

with Model("urn:example:extension#"):
    clarifier = ClarificationStage("clarifier")

print(isinstance(clarifier, SedimentationTank))
print(list(clarifier.has_process), list(clarifier.has_treatment_objective))
print(clarifier.sludge)
```

`clarifier.sludge` is a declared point; pass it to `connect()` to use that
outlet. Connecting the whole clarifier, as in `connect(clarifier, pump)`, is
ambiguous when the other end accepts both media: a WaTr `Pump` takes water or
sludge, so resolution asks you to name the outlet.

## Loading saved models

`Model.from_graph()` picks generated packages from the graph's `owl:imports`.
It recognizes the bundled extensions (`watr.drinking_water`, `watr.asm2d`,
`watr.seawater_ro`, and `s223.hvac`) without help. For an extension you
compiled yourself, pass its registry:

```python
import pumps

model = Model.from_graph("plant.ttl", registries=pumps.REGISTRY)
```

To write your own extension, follow
[Generate a domain API](../how-to/generate-domain-api.md). For everything the
compiler supports, see
[the SHACL configurations reference](https://github.com/gtfierro/objectrdf/blob/main/docs/shacl-configurations.md).
