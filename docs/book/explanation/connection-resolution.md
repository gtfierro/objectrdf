---
file_format: mystnb
kernelspec:
  name: python3
---

# How connections are resolved

In S223 and WaTr, a connection is several RDF resources: a connection point on
each piece of equipment, a `Connection` such as a `Pipe` between them, the
medium of each, and the inverse links. `connect(a, b)` records only the
intention. Resolution fills in the rest, using constraints compiled from the
ontology's SHACL shapes and the Z3 solver.

## Connection points come from the shapes

A class's SHACL shapes say which connection points its instances need: how
many, in which direction, and carrying what medium. The compiler turns those
shapes into a port contract:

```{code-cell} python3
from objectrdf.watr import Clarifier

print(Clarifier.describe_ports())
```

Points with a fixed medium are created with the equipment. The rest stay
deferred until resolution, when the surrounding connections supply enough
information to choose them.

Shape requirements are minimums, not a closed list. A WaTr `Clarifier` whose
shapes list only outlets still gets an inlet when something connects into it.
A shape maximum on the total number of points still applies.

Within a direction the shapes do describe, the media they allow are a domain.
A connection into that side must carry one of them, which is how
`connect(damper, fan)` needs no `medium=`: every inlet of an S223 `Fan`
carries air. A port declared with `.port(..., medium=...)` overrides the
domain, for points the class shapes do not mention, such as a dosing or power
inlet.

Alternatives expressed with `sh:and`, `sh:or`, and `sh:xone` stay as nested
constraints, so the solver chooses a branch instead of the compiler picking
one in advance.

## What the solver decides

Each group of connected equipment is solved separately, and the result is
cached until the model changes. For each group, Z3 has variables for which
connection points exist, their classes, which point each connection uses, the
medium of each connection, and the connection class. The hard constraints
are:

- the shapes' minimum and maximum counts, and their `and`/`or`/`xone`
  structure;
- an outlet connects to an inlet (or a bidirectional point), and a point holds
  one connection;
- each point's medium is within its allowed domain, and a connection's
  medium matches both of its points;
- anything you stated: `medium=`, a named point or port, `connection=`, or a
  paired port.

Media form a hierarchy, so `Water_ChilledWater` satisfies a domain of
`Fluid_Water`, and a broad domain such as WaTr's `Mix_Fluid` accepts any
narrower fluid.

Among the valid answers, Z3 prefers fewer medium changes across equipment:
two ports on one piece of equipment prefer the same medium when their
domains overlap. This is a preference for the plausible reading, not a claim
that equipment preserves its medium. A valid answer can still change media
where other constraints call for it.

The connection class follows from the medium: water, gas, and oil give a
`Pipe`, and air gives a `Duct`, unless `connection=` says otherwise.

## Ambiguity is an error

If more than one answer remains after the preference, resolution stops with
`AmbiguousModelError` instead of choosing one. An isolated pump-to-pump
connection is the simplest case, since nothing says what flows through it.
A partial model may stay undecided while you author it (`check()` reports
`underconstrained`), but RDF is only written for a single interpretation.
Contradictory facts raise `UnsatisfiableModelError`, which lists the authored
facts that conflict.

Every decision can be inspected:

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

Nothing in `connect()` named a medium. The coagulation stage's inlet is a
point with a fixed water medium, reported as an explicit port, and the pump
accepts water. The resolved RDF has points on both sides, a `Pipe` with its
medium, and both directions of every inverse relation:

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

A SHACL `minCount 1` usually becomes a required constructor argument. Two
cases are exceptions. The first is a requirement the class's own shapes
satisfy, such as the settling process of every WaTr sedimentation tank,
which is filled in for you. The second is a cycle: an S223 `Junction`
requires a connection point, and every connection point requires its owner,
so no construction order could satisfy both. The compiler finds such cycles
and leaves the container's side to validation, so `Junction("j",
medium=...)` works and its points are added during resolution. The point
still requires its owner and medium up front.

## Where validation fits

Resolution and validation do different jobs. The solver fixes the topology and
media before any RDF exists. Validation then runs SHACL, through shifty, on
the resolved RDF, with the SHACL-AF rules that carry S223's and WaTr's
inferences. A resolved model produces no violations from the connection
pattern itself. A boundary point that connects to nothing appears as an
informational notice, which does not make the report fail. See
[how an authored model becomes RDF](lifecycle.md) for the whole sequence.
