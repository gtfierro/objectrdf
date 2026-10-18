---
file_format: mystnb
kernelspec:
  name: python3
---

# Complete class catalog

Generated package classes are ordinary Python classes. Browse the ontology
hierarchy below, or use the alphabetical class index to find a class directly.
Each name in the hierarchy links to its index entry, which shows its direct
parents and ontology IRI. Both views are built from the installed S223 and
WaTr packages every time the book is built.

```python
from objectrdf.s223 import Equipment as S223Equipment
from objectrdf.watr import Equipment as WatrEquipment, Process

# Direct children and the full branch of the hierarchy:
S223Equipment.meta.subclasses
S223Equipment.meta.children
S223Equipment.meta.descendants
Process.meta.descendants
print(Process.meta.tree(max_depth=3))

# Every class available from a generated package:
WatrEquipment.meta.registry.classes
```

For example, the top of the WaTr process hierarchy renders as:

```{code-cell} python3
from objectrdf.watr import Process

print(Process.meta.tree(max_depth=2))
```

Depth in the hierarchy does not change the import path. For example, a
reverse-osmosis process is available directly from the WaTr package. For
dynamic lookup, use the parent class's ``meta`` view:

```{code-cell} python3
from objectrdf.watr import Process_ReverseOsmosis

process_cls = Process.meta["ReverseOsmosis"]
same_cls = Process.meta[
    "https://watermetadata.org/ontology/watr#Process-ReverseOsmosis"
]
assert process_cls is Process_ReverseOsmosis is same_cls
print(process_cls.__name__)
```

The lookup also accepts the full Python name, such as
``Process.meta["Process_ReverseOsmosis"]``. It raises ``KeyError`` for classes
outside the Process subtree.

`meta.children` and `meta.subclasses` give the same direct child classes;
`meta.descendants` includes every depth. `meta.parents` gives the direct bases
of a class. A class can have multiple parents, so the catalog lists all direct
parents. `meta.iri` distinguishes
same named ontology concepts that were given different Python names such as
`Damper` and `Damper_2`. A multiply inherited class appears under each parent
in `meta.tree()` and in the hierarchy below.

## Browse the class hierarchy

Expand a branch to step through its subclasses. A class with multiple direct
parents appears under each parent. Select any class name to jump to its entry
in the alphabetical index.

```{code-cell} python3
:tags: [hide-input]
from html import escape
from IPython.display import HTML, display
from objectrdf.s223 import Equipment as S223Equipment
from objectrdf.watr import Equipment as WatrEquipment

def class_anchor(package, cls):
    return f"{package}-class-{cls.__name__}"

def class_hierarchy(package, registry):
    classes = registry.classes
    children = {cls: [] for cls in classes}
    roots = []
    for cls in classes:
        parents = [parent for parent in cls.meta.parents if parent in children]
        if parents:
            for parent in parents:
                children[parent].append(cls)
        else:
            roots.append(cls)

    def branch(cls):
        link = (
            f'<a href="#{class_anchor(package, cls)}">'
            f'<code>{escape(cls.__name__)}</code></a>'
        )
        if not children[cls]:
            return f"<li>{link}</li>"
        descendants = "".join(branch(child) for child in children[cls])
        return f"<li><details><summary>{link}</summary><ul>{descendants}</ul></details></li>"

    return '<ul class="class-hierarchy">' + "".join(branch(cls) for cls in roots) + "</ul>"

display(HTML("""
<style>
.class-hierarchy, .class-hierarchy ul { list-style: none; padding-left: 1.3em; }
.class-hierarchy li { margin: 0.15em 0; }
.class-hierarchy summary { cursor: pointer; }
</style>
"""))
```

### S223 hierarchy

```{code-cell} python3
:tags: [hide-input]
display(HTML(class_hierarchy("s223", S223Equipment.meta.registry)))
```

### WaTr hierarchy

```{code-cell} python3
:tags: [hide-input]
display(HTML(class_hierarchy("watr", WatrEquipment.meta.registry)))
```

## Alphabetical class index

Every class is listed once here, including classes reachable through multiple
branches above. Use its Python name for a direct import from the package.

### S223

```{code-cell} python3
:tags: [hide-input]
def class_table(package, registry):
    rows = [
        "<table><thead><tr><th>Python class</th><th>Direct parents</th>"
        "<th>Ontology class IRI</th></tr></thead><tbody>"
    ]
    for cls in registry.classes:
        parents = ", ".join(
            f'<a href="#{class_anchor(package, parent)}">'
            f'{escape(parent.__name__)}</a>'
            for parent in cls.meta.parents
        ) or "—"
        rows.append(
            f'<tr id="{class_anchor(package, cls)}">'
            f"<td><code>{escape(cls.__name__)}</code></td>"
            f"<td>{parents}</td>"
            f"<td><code>{escape(cls.meta.iri)}</code></td></tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)

display(HTML(class_table("s223", S223Equipment.meta.registry)))
```

### WaTr

```{code-cell} python3
:tags: [hide-input]
display(HTML(class_table("watr", WatrEquipment.meta.registry)))
```

## Enumeration values

Enum values have their own hierarchy. Flat constants remain available from
the package's `enums.values` namespace, and each value exposes direct children,
descendants, a printable tree, and scoped lookup. Top-level `enums` exposes
the main branches, such as `Substance` and `Role`; `dir(enums.values)` lists
every flat name:

```{code-cell} python3
from objectrdf.watr import enums

print(dir(enums))
print(len(enums.EnumerationKind.descendants))
water = enums.Substance.Medium.Mix.Fluid.Water
print(water.tree_text(max_depth=2))
assert water["ChilledWater"] is enums.values.Water_ChilledWater
assert enums.Substance.Medium["Water_ChilledWater"] is enums.values.Water_ChilledWater
assert water[enums.values.Water_ChilledWater.iri] is enums.values.Water_ChilledWater
```
