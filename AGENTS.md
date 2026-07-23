# Repository Guidelines

## Project Structure & Module Organization

Python source uses a `src/` layout under `src/objectrdf/`. The stable runtime is
in `core/`, ontology compilation lives in `gen/`, and `cli.py` provides the
`objectrdf` command. Packages such as `brick/` and `s223/` are generated
compiler output; change generator logic or overlays and regenerate them instead
of hand-editing generated classes. Tests are in `tests/`, with shared toy
ontology classes in `tests/toy.py` and RDF inputs in `tests/fixtures/`. Runnable
examples live in `examples/`, while architecture and authoring documentation is
kept in `docs/` and `DESIGN.md`.

## Build, Test, and Development Commands

- `uv sync` installs Python 3.12+ dependencies and development tools from
  `uv.lock`.
- `uv run pytest` runs the complete test suite configured under `tests/`.
- `uv run ruff check src tests examples` checks style and common errors.
- `uv run ty check src tests examples` performs static type checking.
- `uv build` creates source and wheel distributions with the `uv_build`
  backend.
- `uv run objectrdf gen --file schema.ttl --name Example --out mypkg`
  compiles a local ontology. See `docs/codegen.md` before regenerating committed
  packages.

## Coding Style & Naming Conventions

Use four-space indentation, Ruff's 88-character line limit, and modern Python
3.12 type syntax (`T | None`, built-in generics). Add type annotations to public
APIs and concise docstrings where behavior is not obvious. Follow `snake_case`
for functions, variables, and generated property names; use `PascalCase` for
classes and `UPPER_CASE` for constants. Ruff intentionally excludes generated
ontology packages listed in `pyproject.toml`.

## Testing Guidelines

Tests use pytest. Name files `test_<area>.py` and test functions
`test_<behavior>()`. Keep focused unit tests near the affected subsystem and
put reusable RDF data in `tests/fixtures/`. For generator changes, test both
semantic output and deterministic regeneration. Run pytest, Ruff, and `ty`
before submitting a change; no numeric coverage threshold is currently set.

## Commit & Pull Request Guidelines

This repository currently has no commit history from which to infer a house
style. Use short, imperative subjects such as `Add inverse relation validation`
and keep each commit focused. Pull requests should explain the motivation and
observable behavior, list verification commands, link relevant issues, and
include generated diffs when ontology output changes. Update documentation or
examples when public APIs change; screenshots are only useful for visual output.
