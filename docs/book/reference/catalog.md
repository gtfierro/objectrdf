---
file_format: mystnb
kernelspec:
  name: python3
---

# Class catalog

Every S223 and WaTr class, generated from the installed packages at build
time. To browse in Python, see
[Find classes and values](../how-to/find-classes-and-values.md).

## Browse the class hierarchy

Expand a branch to step through its subclasses. A class with multiple direct
parents appears under each parent. Select any class name to jump to its entry
in the alphabetical index.

```{code-cell} python3
:tags: [hide-input]
from html import escape
from IPython.display import HTML, display
from objectrdf import s223, watr

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
display(HTML(class_hierarchy("s223", s223.REGISTRY)))
```

### WaTr hierarchy

```{code-cell} python3
:tags: [hide-input]
display(HTML(class_hierarchy("watr", watr.REGISTRY)))
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

display(HTML(class_table("s223", s223.REGISTRY)))
```

### WaTr

```{code-cell} python3
:tags: [hide-input]
display(HTML(class_table("watr", watr.REGISTRY)))
```
