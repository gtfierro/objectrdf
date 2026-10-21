---
file_format: mystnb
kernelspec:
  name: python3
---

# Explore class hierarchies

Start from a class in the generated package you are using. The examples here
use WaTr's `Process` branch; the same API works for `Equipment` in WaTr or
S223. Classes are ordinary Python types, so you can import and pass them to
`Model.find_all()` once you know which one you need.

## See the branch

`children` gives direct subclasses. `descendants` gives all depths. Both are
tuples of Python classes; use `.meta` on each class to inspect ontology facts.

```{code-cell} python3
from objectrdf.watr import Process

print([cls.__name__ for cls in Process.meta.children])
print(len(Process.meta.descendants), "process descendants")
print(Process.meta.tree(max_depth=2))
```

`meta.tree()` returns text, so call `print()` to display it. A class can have
multiple parents and may appear more than once in the rendered hierarchy.

## Walk children in Python

Use `children` when you want to do something at each level. This walk yields
the starting class first, then its children, to the requested depth:

```{code-cell} python3
def walk_classes(cls, max_depth, depth=0):
    yield cls, depth
    if depth < max_depth:
        for child in cls.meta.children:
            yield from walk_classes(child, max_depth, depth + 1)

for cls, depth in walk_classes(Process, max_depth=2):
    print("  " * depth + cls.__name__, cls.meta.iri)
```

The hierarchy is a directed graph when classes have multiple parents, so a
walk through each parent's children can visit the same class more than once.
If you want each class once, iterate over `Process.meta.descendants` instead.

## Navigate up or select a deep class

`parents` contains direct Python bases with ontology metadata. The Python
inheritance checks `issubclass()` and `isinstance()` work as usual.

```{code-cell} python3
from objectrdf.watr import Process_ReverseOsmosis

print([cls.__name__ for cls in Process_ReverseOsmosis.meta.parents])
print(issubclass(Process_ReverseOsmosis, Process))

selected = Process.meta["ReverseOsmosis"]
assert selected is Process_ReverseOsmosis
print(selected.meta.label, selected.meta.iri)
```

`Process.meta[...]` also accepts the full Python name or ontology class IRI.
The lookup stays within the Process subtree and raises `KeyError` for an
unrelated class. Direct imports are useful when you want editor completion or
static type checking.

## Find every available class

Each generated package exports its own `REGISTRY`, so you can browse available
classes without selecting a class first. A domain package's registry includes its generated
configurations and linked base types. The base registry remains unchanged.

```{code-cell} python3
from objectrdf import watr

registry = watr.REGISTRY
print(len(registry.classes), "registered classes")
print(registry.resolve("Process_ReverseOsmosis") is Process_ReverseOsmosis)
```

For a searchable list with direct parents and class IRIs, use the
[class catalog](../reference/catalog.md). To inspect instances of these
classes in a loaded model, use the [query guide](validate-and-save.md).
