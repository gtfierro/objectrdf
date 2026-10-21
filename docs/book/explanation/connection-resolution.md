---
file_format: mystnb
kernelspec:
  name: python3
---

# How connections are resolved

In S223 and WaTr, one connection is several resources: a connection point on
each side, a `Connection` such as a `Pipe`, their media, and inverse links.
`connect(a, b)` records only the intention. Resolution builds the rest with
the Z3 solver, using constraints compiled from the SHACL shapes.

## Points come from the shapes

A class's shapes say which points it needs: how many, which direction, and
which media. The compiler turns them into a port contract:

```{code-cell} python3
from objectrdf.watr import Clarifier

print(Clarifier.describe_ports())
```

- Points with a fixed medium are created with the equipment. The rest wait
  for resolution.
- Requirements are minimums. A `Clarifier` whose shapes list only outlets
  still gets an inlet when something connects into it. A maximum on the total
  still applies.
- The allowed media on a side form a domain. Every S223 `Fan` inlet carries
  air, so `connect(damper, fan)` needs no `medium=`.
- A port declared with `.port(..., medium=...)` overrides the domain.
- `sh:and`, `sh:or`, and `sh:xone` stay as alternatives for the solver to
  choose between.

## What the solver decides

Each group of connected equipment is solved separately and cached until the
model changes. Z3 chooses which points exist, their classes, which point each
connection uses, each connection's medium, and the connection class, subject
to:

- the shapes' minimum and maximum counts, and their `and`/`or`/`xone`
  structure;
- an outlet connects to an inlet (or a bidirectional point), and a point holds
  one connection;
- each point's medium is within its allowed domain, and a connection's
  medium matches both of its points;
- anything you stated: `medium=`, a named point or port, `connection=`, or a
  paired port.

Media form a hierarchy: `Water_ChilledWater` satisfies a `Fluid_Water`
domain.

Among valid answers, Z3 prefers fewer medium changes: two ports on one device
prefer the same medium when their domains overlap. This is a preference, not
a claim that equipment preserves its medium.

The medium picks the connection class: water, gas, and oil give a `Pipe`,
and air a `Duct`, unless `connection=` says otherwise.

## Ambiguity is an error

If more than one answer remains, resolution raises `AmbiguousModelError`
rather than choose. A lone pump-to-pump connection is the simplest case:
nothing says what flows. A model may be undecided while you author it, but
RDF is only written for one interpretation. Contradictions raise
`UnsatisfiableModelError`, listing the conflicting facts.

`explain()` shows each decision:

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr import Pump
from objectrdf.watr.drinking_water import CoagulationStage

with Model("urn:example:resolution#") as model:
    pump = Pump("intake-pump")
    coagulation = CoagulationStage("coagulation")
raw_water = connect(pump, coagulation, name="raw-water")

resolved = model.resolve()
resolved.explain(raw_water)
```

No medium was given. The coagulation inlet has a fixed water medium, and the
pump accepts water. The resolved RDF:

```{code-cell} python3
import rdflib

graph = resolved.graph()
pipe = resolved.connection(raw_water)
subjects = {pipe.meta.instance_iri, *(p.meta.instance_iri for p in pipe.connects_at)}
excerpt = rdflib.Graph()
excerpt.namespace_manager = graph.namespace_manager
for triple in graph:
    if str(triple[0]) in subjects:
        excerpt.add(triple)
print(excerpt.serialize(format="turtle").split("\n\n", 1)[1])
```

## Required properties that require each other

A SHACL `minCount 1` usually becomes a required constructor argument, with
two exceptions:

- A requirement the class itself fixes, such as a sedimentation tank's
  settling process, is filled in.
- A cycle is left to validation. An S223 `Junction` requires a connection
  point, and a point requires its owner, so `Junction("j", medium=...)` works
  and its points are added during resolution.

## Where validation fits

The solver fixes topology and media before RDF exists. Validation then checks
the RDF with shifty. A resolved model has no violations from its connection
pattern. See [Model lifecycle](lifecycle.md).
