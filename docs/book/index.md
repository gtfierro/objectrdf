# Learn ObjectRDF

ObjectRDF lets you author ontology-backed RDF as Python objects. Its generated
S223 and WaTr packages supply classes and enum values; the runtime records
relations, resolves deferred connections, validates against SHACL, and emits
RDF.

Start with [an S223 air path](tutorials/s223-air-path.md), then build a
[WaTr treatment path](tutorials/watr-treatment.md). Each tutorial is an
executable MyST notebook page. Run the book build to see current output.

Use the task guides when you need to [diagnose a model](how-to/diagnose-resolution.md)
or [validate and query RDF](how-to/validate-and-query.md). The
[lifecycle explanation](explanation/lifecycle.md) shows where Z3 and shifty
act. The [runtime reference](reference/runtime.md) and
[ontology reference](reference/ontologies.md) are generated from Python
docstrings when the book builds.

From this repository's root:

```bash
uv sync --group docs
uv run --group docs jupyter-book build docs/book
```

The generated HTML is at `docs/book/_build/html/index.html`.
