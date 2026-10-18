---
file_format: mystnb
kernelspec:
  name: python3
---

# Explore enumeration hierarchies

Generated enum values live in the package's `enums` module. They are
`EnumValue` objects with ontology IRIs, not Python classes. The WaTr module
also includes the S223 values it imports. The top level offers a small set of
branches; tab completion follows their children:

```{code-cell} python3
from objectrdf.watr import enums

print(dir(enums))
print(dir(enums.Substance))
```

Use a path such as `enums.Substance.Medium.Mix.Fluid.Water` to browse the
hierarchy. For a known value, `enums.values.Fluid_Water` offers a flat lookup.

## See a branch

Use `children` for the next level and `descendants` for all levels. `parent`
is the primary browsing path; `parents` includes every direct ontology parent
when a value belongs to more than one branch. These are values, so there is no
`.meta` step.

```{code-cell} python3
water = enums.Substance.Medium.Mix.Fluid.Water
assert water is enums.values.Fluid_Water
print([value.label for value in water.children])
print([value.iri for value in water.descendants])
print(water.parent.iri)

sludge = enums.values.Fluid_Sludge
print([value.iri for value in sludge.parents])
assert sludge.is_a(enums.values.Fluid_Water)
assert sludge.is_a(enums.values.Mix_Fluid)
```

`tree()` prints a subtree. Use `tree_text()` when you want the text to store,
display elsewhere, or search. `max_depth` bounds the display; `show_iris=True`
shows full RDF identifiers.

```{code-cell} python3
water.tree(max_depth=2)
rendered = water.tree_text(max_depth=1)
print("Fluid-Water" in rendered)
```

## Walk children in Python

This pattern is the same as for classes, except each node is an enum value:

```{code-cell} python3
def walk_values(value, max_depth, depth=0):
    yield value, depth
    if depth < max_depth:
        for child in value.children:
            yield from walk_values(child, max_depth, depth + 1)

for value, depth in walk_values(water, max_depth=2):
    print("  " * depth + (value.label or value.iri), value.iri)
```

## Select a value and check ancestry

For known values, use the flat constant from `enums.values` or follow the
branches. Bracket lookup searches within a subtree and can use a short child
name, a flat name, or a full IRI.

```{code-cell} python3
chilled = enums.values.Water_ChilledWater
assert enums.Substance.Medium.Mix.Fluid.Water.ChilledWater is chilled
assert water.ChilledWater is chilled
assert water["ChilledWater"] is chilled
assert enums.Substance.Medium["Water_ChilledWater"] is chilled
assert water[chilled.iri] is chilled

print(chilled.is_a(water))
print(chilled.parent is water)
```

If a short name matches more than one value in a subtree, bracket lookup
raises `KeyError` and lists the matching IRIs. Use a full flat name or IRI in
that case.

## Find all values

`EnumerationKind` is the root of the generated hierarchy. Its `descendants`
are the values available under that root. `dir(enums)` lists the top-level
branches, while `dir(enums.values)` lists every flat name.

```{code-cell} python3
print(len(enums.EnumerationKind.descendants), "enum descendants")
print("Water_ChilledWater" in dir(enums.values))
```

See the [class and enum catalog](../reference/catalog.md) and the
[S223 air path tutorial](../tutorials/s223-air-path.md) for enum values in a
connection.
