# Learn ObjectRDF

ObjectRDF lets you author ontology-backed RDF as Python objects. Its generated
S223 and WaTr packages supply classes and enum values; the runtime records
relations, resolves deferred connections, validates against SHACL, and emits
RDF.

Start with [an S223 air path](tutorials/s223-air-path.md), then build a
[WaTr treatment path](tutorials/watr-treatment.md). Each tutorial is an
executable MyST notebook page. Run the book build to see current output.

Use the task guides to [explore classes](how-to/explore-classes.md),
[explore enums](how-to/explore-enums.md),
[inspect port requirements](how-to/inspect-port-contracts.md),
[diagnose a model](how-to/diagnose-resolution.md), or
[validate and query RDF](how-to/validate-and-query.md). The
[lifecycle explanation](explanation/lifecycle.md) shows where Z3 and shifty
act. The [runtime reference](reference/runtime.rst),
[ontology reference](reference/ontologies.rst), and
[complete class catalog](reference/catalog.md) are generated from Python
metadata when the book builds.

From this repository's root:

```bash
uv sync --group docs
uv run --group docs jupyter-book build docs/book
```

The generated HTML is at `docs/book/_build/html/index.html`.
