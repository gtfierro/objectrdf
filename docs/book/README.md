# Plumb learning book

This [Jupyter Book](https://jupyterbook.org/v1/) follows the Diátaxis layout:
hands-on tutorials, task guides, an explanation of the lifecycle, and an
API reference rendered from Python docstrings by Sphinx autodoc.

From the repository root, with Python 3.12 or newer:

```bash
make setup
make docs
```

Open `docs/book/_build/html/index.html`. The tutorials use MyST executable
code cells. The book build executes them, so the examples and their output
track the current implementation. Build from the repository root so relative
paths in the commands above work as written.

Use `make docs-open` to build and open the HTML in your default browser,
`make docs-rebuild` for a full rebuild, and `make docs-check` to treat warnings
as errors. `make docs-clean` removes generated documentation and notebook
caches. Pass extra Jupyter Book options with `DOCS_ARGS`, for example
`make docs DOCS_ARGS="--all"`.

The book has its own configuration in `_config.yml` and navigation in
`_toc.yml`. Edit source pages under `tutorials/`, `how-to/`, `explanation/`,
and `reference/`. The reference directives import the installed package at
build time; update docstrings or add a directive when public APIs change.
