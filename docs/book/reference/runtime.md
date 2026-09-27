# Runtime API reference

These signatures and docstrings are imported from the installed `objectrdf`
package during the book build. The [lifecycle](../explanation/lifecycle.md)
explains when to use each operation.

## Model

```{autoclass} objectrdf.Model
:members: system, from_graph, find, find_all, check, resolve, compile, graph, save, validate, export_ontology
```

## Connections and snapshots

```{autofunction} objectrdf.connect
```

```{autoclass} objectrdf.ConnectionHandle
:members: medium, connection_class, label, comment, assign
```

```{autoclass} objectrdf.ResolvedModel
:members: entities, connection, point, explain, graph
```

```{autoclass} objectrdf.ResolutionReport
:members: satisfiable, complete
```

```{autoclass} objectrdf.ResolutionExplanation
:members:
```

## Validation and errors

```{autoclass} objectrdf.ValidationReport
:members: violations
```

```{autoclass} objectrdf.core.Issue
:members:
```

```{autoexception} objectrdf.AmbiguousModelError
```

```{autoexception} objectrdf.UnsatisfiableModelError
```

```{autoexception} objectrdf.ValidationError
```
