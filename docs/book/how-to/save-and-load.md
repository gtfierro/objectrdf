---
file_format: mystnb
kernelspec:
  name: python3
mystnb:
  execution_in_temp: true
---

# Save, load, and edit models

Save a model as RDF, load RDF back as the same typed objects, edit them, and
save again. Loading needs to know which generated packages, or registries,
describe the classes in the file; this page covers how they are chosen and
how to pass your own.

## Save

```{code-cell} python3
from plumb import Model, connect
from plumb.watr import Pump, Tank
from plumb.watr.drinking_water import ClarificationStage, CoagulationStage

with Model("urn:example:plant#") as authored:
    intake = Pump("intake-pump", label="Intake pump")
    coagulation = CoagulationStage("coagulation")
    clarifier = ClarificationStage("clarifier")
    holding = Tank("sludge-holding")
connect(intake, coagulation.inlet, name="raw-water")
connect(coagulation.outlet, clarifier.inlet, name="coagulated-water")
connect(clarifier.sludge, holding, name="sludge-line")

authored.save("plant.ttl")
```

`save()` resolves the model and writes the snapshot. The format follows the
extension: `.ttl`, `.nt`, `.xml` or `.rdf`, or `.jsonld`; `format=`
overrides it. `graph()` returns the same RDF as an rdflib graph. Neither
validates; see [Validate a model](validate-a-model.md).

The file declares an `owl:Ontology` that imports each ontology it uses, and
records the installed version of each one that declares a version:

```{code-cell} python3
from rdflib import OWL

graph = authored.graph()
for _, _, dependency in graph.triples((None, OWL.imports, None)):
    print(dependency, graph.value(dependency, OWL.versionInfo))
```

Loading reads these imports to choose packages.

## Set ontology metadata

The ontology's IRI defaults to the namespace without the trailing `#` or
`/`. Set it, a label, extra imports, and prefixes on the constructor:

```python
model = Model(
    "urn:example:plant#",
    name="Example plant",
    ontology_iri="urn:example:plant-model",
    imports=["urn:example:project-vocabulary"],
    prefixes={"qudt": "http://qudt.org/schema/qudt/"},
)
```

## Share with tools that cannot resolve imports

A model that uses a domain package, such as drinking water, imports that
package's ontology by IRI. A reader that cannot fetch it can be given the
schema alongside the model. `export_ontology()` writes the schema of each
domain package the model uses: its classes, their parents, and its imports:

```{code-cell} python3
schema = authored.export_ontology("plant-schema.ttl")
len(schema)
```

## Load

`Model.from_graph()` takes a path, URL, or rdflib graph:

```{code-cell} python3
model = Model.from_graph("plant.ttl")
model.by_class()
```

Every resource with a generated class becomes an object of the most
specific class. Points and pipes load as ordinary objects, not as
`connect()` calls. Named ports come back, so `model["clarifier"].sludge`
works as it did when authored. Instance IRIs keep their namespace, which is
inferred from the resources unless you pass `namespace=`.

## How packages are chosen

Each installed package registers its classes in a registry. `from_graph()`
matches the graph's `owl:imports` against the installed packages:

| Package | Imports it matches |
| --- | --- |
| `plumb.s223`, `plumb.watr`, `plumb.qudt` | the ontology's IRI |
| `plumb.watr.drinking_water`, `.asm2d`, `.seawater_ro`, `plumb.s223.hvac` | the extension's IRI |

A domain package's registry includes its base classes, so when a graph
imports both WaTr and drinking water, the drinking-water registry is used and
covers both.

The imported version must match the installed package, so a file saved by a
different ontology release is not read with the wrong classes:

```{code-cell} python3
from rdflib import Graph, Literal, URIRef

old = Graph().parse("plant.ttl")
watr = URIRef("https://watermetadata.org/ontology/watr")
old.set((watr, OWL.versionInfo, Literal("0.1")))
try:
    Model.from_graph(old)
except ValueError as error:
    print(error)
```

## Pass registries

RDF without imports, or using a package you [compiled
yourself](generate-domain-api.md), needs `registries=`:

```{code-cell} python3
bare = Graph().parse("plant.ttl")
bare.remove((None, OWL.imports, None))
try:
    Model.from_graph(bare)
except ValueError as error:
    print(error)
```

```{code-cell} python3
from plumb.watr import drinking_water

model = Model.from_graph(bare, registries=drinking_water.REGISTRY)
type(model["clarifier"]).__name__
```

Pass a list for several, such as `[watr.REGISTRY, s223.hvac.REGISTRY]`. Every
generated package exposes `REGISTRY`, and a compiled package's registry
includes the classes it extends.

## Unknown classes and malformed data

Resources whose classes no registry knows stay in the graph but are not
loaded as objects. A generated attribute that points at one raises, because
the object would be incomplete:

```{code-cell} python3
from rdflib import RDF, Namespace

EX = Namespace("urn:example:plant#")
S223 = Namespace("http://data.ashrae.org/standard223#")
extended = Graph().parse("plant.ttl")
extended.add((EX.mystery, RDF.type, URIRef("urn:other#Gadget")))
extended.add((EX.clarifier, S223.contains, EX.mystery))
try:
    Model.from_graph(extended)
except Exception as error:
    print(type(error).__name__, error)
```

The fix is usually the missing registry. `strict=False` skips such values
instead, along with resources whose types conflict, several values for a
single-valued attribute, and named ports that cannot be identified. Skipped
triples stay in the graph.

```{code-cell} python3
model = Model.from_graph(extended, strict=False)
"mystery" in [entity.name for entity in model], (EX.mystery, None, None) in model.graph()
```

## Load with inference

`infer=True` runs the packages' SHACL-AF rules before loading, so facts the
rules derive become attributes. Pass `shapes=` for other rules:

```python
model = Model.from_graph("plant.ttl", infer=True)
```

Inference is off by default because it adds triples to the graph.

## Edit and save

A loaded model is backed by its graph, and edits write through to it:

```{code-cell} python3
from plumb.watr import enums

model = Model.from_graph("plant.ttl")
clarifier = model["clarifier"]
clarifier.label = "Clarifier 1"
clarifier.has_role.add(enums.values.Role_Primary)
with model:
    Tank("sludge-tank")
model.save("plant-updated.ttl")
```

Only the triples behind generated attributes change; everything else in the
graph stays. A graph passed to `from_graph()` is updated in place. Edits
made through rdflib after loading are not seen by the objects.

A loaded model has no resolution step, so `connect()` and `model.system()`
do not work on it. Edit the concrete pipes and points instead:

```{code-cell} python3
try:
    connect(model["intake-pump"], model["sludge-tank"])
except Exception as error:
    print(type(error).__name__, error)
```

## Search what you loaded

Search, containment, and flow walks work on a loaded model directly:

```{code-cell} python3
model["intake-pump"].find_all_next()
```

See [Find objects in a model](find-objects.md).
