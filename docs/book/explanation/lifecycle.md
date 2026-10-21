# Model lifecycle

```text
generated classes → authored model → check() → resolve() → graph() / save()
                                                         └→ validate() / compile()
```

## Generate

The compiler turns an ontology and its SHACL shapes into a Python package
ahead of time. Model scripts import the package; they never run the compiler.

## Author

An authored `Model` is mutable. Constructors check required properties,
attributes check their values, and inverse relations stay in sync.
`connect()` records an intention and returns a handle. Points the shapes fix
are created with the equipment; the rest wait for resolution.

## Resolve

`check()` asks the Z3 solver whether the model has exactly one
interpretation. `resolve()` builds it: a frozen `ResolvedModel` with every
connection point, connection, and inverse relation. The authored model is not
changed, and any later edit invalidates the snapshot. See
[How connections are resolved](connection-resolution.md).

`find_all()` works on any model, but walks such as `find_all_next()` follow
concrete pipes and points. An authored model gets those only from
resolution, so walk the snapshot (`model.resolve()["pump"].find_all_next()`);
walking an authored model with unresolved connections raises
`ModelingError`.

## Validate

`validate()` runs shifty on the resolved RDF: SHACL-AF rules, then SHACL Core
validation, against the shapes bundled with each package. `compile()`
resolves and validates in one call. `graph()` and `save()` resolve but do not
validate.

## Load

`Model.from_graph()` builds objects from existing RDF. A loaded model is
backed by its graph, and edits write through to it. It has no resolution
step, so `connect()` and `model.system()` are unavailable, but its pipes and
points are concrete, so it can be searched and walked directly.

The internals are in `docs/architecture.md` in the repository.
