# Generate a domain API from RDF and SHACL

Use an ontology extension when several models share equipment roles, named ports,
or quantity metadata. Maintain those definitions in RDF and SHACL, then generate
the Python package. Model authors import it without running the compiler.

## Declare the base package and equipment

Save this source as `pumps.ttl`. The annotation identifies the installed base
package. Ontology classes supply identity and inheritance; SHACL supplies required
members, defaults, cardinalities, and point layouts.

```turtle
@prefix ex: <urn:example:pumps#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix s223: <http://data.ashrae.org/standard223#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix kind: <http://qudt.org/vocab/quantitykind/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix codegen: <https://w3id.org/objectrdf/codegen#> .

ex: a owl:Ontology ;
    owl:imports <http://data.ashrae.org/standard223/1.0/model/all> ;
    codegen:baseModule "objectrdf.s223" .

ex:SupplyPump a owl:Class ; rdfs:subClassOf s223:Pump .
ex:SupplyPumpShape a sh:NodeShape ; sh:targetClass ex:SupplyPump ;
    sh:node ex:PressureDesignShape ;
    sh:property [ sh:path s223:hasRole ; sh:hasValue s223:Role-Supply ],
        [ sh:path s223:hasConnectionPoint ; sh:name "inlet" ;
          sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
          sh:qualifiedValueShape ex:Inlet ],
        [ sh:path s223:hasConnectionPoint ; sh:name "outlet" ;
          sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
          sh:qualifiedValueShape ex:Outlet ],
        [ sh:path s223:hasConnectionPoint ; sh:minCount 2 ; sh:maxCount 2 ] .
ex:Inlet sh:class s223:InletConnectionPoint ;
    sh:property [ sh:path s223:hasMedium ; sh:hasValue s223:Fluid-Water ],
        [ sh:path rdfs:label ; sh:hasValue "inlet" ] .
ex:Outlet sh:class s223:OutletConnectionPoint ;
    sh:property [ sh:path s223:hasMedium ; sh:hasValue s223:Fluid-Water ],
        [ sh:path rdfs:label ; sh:hasValue "outlet" ] .

ex:PressureDesignShape a sh:NodeShape ;
    codegen:projection codegen:PropertySchema ;
    codegen:pythonName "PressureDesign" ;
    sh:property [ sh:path s223:hasProperty ; sh:name "pressure" ;
        sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ;
        sh:qualifiedValueShape ex:Pressure ] .
ex:Pressure sh:class s223:QuantifiableProperty ;
    sh:property [ sh:path s223:hasValue ; sh:datatype xsd:double ;
                  sh:minCount 1 ; sh:maxCount 1 ; sh:minInclusive 0.0 ],
        [ sh:path qudt:hasQuantityKind ; sh:hasValue kind:Pressure ],
        [ sh:path qudt:hasUnit ; sh:defaultValue unit:PA ;
          sh:in (unit:PA unit:KiloPA unit:BAR) ],
        [ sh:path s223:hasAspect ; sh:hasValue s223:Aspect-Nominal ] .
```

`sh:hasValue` on a collection supplies required members while allowing additional
valid values. `sh:defaultValue` supplies a replaceable default on new instances.
Use `sh:in` for finite choices. Named ports need a fixed direction, medium,
positive exact count, and distinguishing facts when several ports share a
medium and direction. Fixed labels provide those facts in this example.

## Compile and use the package

Run from the directory containing `pumps.ttl`:

```bash
objectrdf gen --file pumps.ttl --name Pumps --out pumps
```

The generated package contains typed constructors and frozen quantity schemas,
plus the exact source shapes used for validation:

```python
from objectrdf import Model
from objectrdf.qudt import QuantityAmount as Q, units
from pumps import SupplyPump, PressureDesign

with Model("urn:example:plant#") as model:
    pump = SupplyPump("pump")
    pump.apply_properties(PressureDesign(pressure=Q(7.0, units.BAR)))

assert model.validate().ok
```

A bare pressure value uses Pa, the source default. Explicit values preserve their
units without conversion. For several fields with the same quantity kind, use
source constraints such as fixed labels to distinguish their qualified shapes.
`describe()` displays units, defaults, and provenance.

## Load saved models

A saved model declares `owl:imports` for `urn:example:pumps#`. `Model.from_graph()`
only recognizes the extensions bundled with objectrdf from their imports, so
pass your package's registry when loading:

```python
from objectrdf import Model
import pumps

model.save("plant.ttl")
loaded = Model.from_graph("plant.ttl", registries=pumps.REGISTRY)
assert isinstance(loaded["pump"], SupplyPump)
```

The registry includes the base package's classes, so equipment from the base
in the same graph loads too.

## Limits

The compiler supports one constructive parent per extension class, including
local inheritance, shape composition through `sh:node` and `sh:and`, scalar
quantity fields, and inclusive numeric bounds. Complex paths and disjunctive
constructive layouts produce diagnostics. Full validation still uses the original
shapes, including constraints outside the constructive projection.

The repository sources `ontology/asm2d.ttl`, `ontology/seawater-ro.ttl`,
`ontology/drinking-water.ttl`, and `ontology/hvac.ttl` regenerate with:

```bash
uv run python scripts/generate_example_domains.py
```
