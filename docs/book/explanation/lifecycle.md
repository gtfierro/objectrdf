# How an authored model becomes RDF

An authored `Model` is a mutable collection of typed Python entities and
deferred intentions. Generated ontology packages supply class signatures,
property descriptors, enum individuals, metadata, and compiled SHACL
constraints. The compiler produces those packages ahead of time; ordinary
model scripts import them without compiling an ontology again.

```text
generated classes → authored entities and handles → check() → resolve()
                                                         ├─→ graph()/save() → RDF
                                                         └─→ validate()/compile()
                                                              → shifty → report
```

## Authoring and resolution

Inside `with Model(namespace)`, constructors bind entities to the model.
Descriptors check property values against generated ranges and keep inverse
relationships synchronized. The model holds the authored entities; a call to
`connect(a, b)` records flow direction and returns a `ConnectionHandle`.
Some fixed-medium points are created during construction; other point
requirements can remain deferred. You can add
medium hints, roles, labels, and other connection properties to the handle.

`check()` asks the Z3 resolver whether constraints admit a complete,
unambiguous graph. It reports `complete`, `underconstrained`, or
`unsatisfiable`; an underconstrained report is still satisfiable. The
constraints come from authored facts and compiled SHACL point layouts,
cardinality, class requirements, and permitted media. The solver ranks valid
media assignments using overlap between a device's port domains. This
ranking does not express physical conservation of a medium.

`resolve()` selects concrete connection points and connection subclasses,
creates inverse relationships, and returns a frozen `ResolvedModel`. A handle
still points to the authored intention; `resolved.connection(handle)` maps it
to the concrete entity. `resolved.explain(handle)` records the selected
endpoints, medium, and evidence. The authored model is not filled with derived
entities. A later authored edit invalidates its cached snapshot.

## SHACL inference and validation

Z3 resolution and SHACL inference have different jobs. Z3 chooses the
connection topology and media before RDF is emitted. shifty runs SHACL Core
validation and, by default, SHACL-AF forward rules against the resolved RDF
and shapes bundled with the generated packages. Thus `model.validate()` is
the operation that runs shifty; `model.resolve()` alone does not. Validation
returns a `ValidationReport` whose issues map focus IRIs back to Python
entities when possible. Informational notices can coexist with `ok=True`.

`model.compile()` calls `resolve()` and then `validate()` by default. It raises
`ValidationError` for violations and returns the frozen snapshot on success.
`graph()` and `save()` resolve and serialize, but do not validate. An
`owl:Ontology` declaration and imports for referenced packages are emitted
with authored models.

## Loading existing RDF

`Model.from_graph()` follows a separate path: it can run shifty inference
before hydrating typed objects when `infer=True`. A loaded model is backed by
its graph; edits to generated attributes replace their managed triples while
preserving other RDF. The default is `infer=False`, since rule inference can
add triples to the queried graph. New deferred S223 or WaTr connections and
system scopes are not supported on a loaded model.

[How connections are resolved](connection-resolution.md) covers the solver's
constraints. For the runtime and compiler internals, see `docs/architecture.md`
in the repository.
