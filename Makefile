.DEFAULT_GOAL := help

UV ?= uv
TEST_ARGS ?=
DOCS_ARGS ?=

PYTHON_PATHS := src tests examples
DOCS_DIR := docs/book
FORMAT_EXCLUDE := src/objectrdf/qudt/units.py,src/objectrdf/qudt/quantity_kinds.py

.PHONY: help setup check test lint typecheck format build docs docs-rebuild \
	docs-check docs-open docs-clean regen clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install project, development, and documentation dependencies
	$(UV) sync --group docs

check: lint typecheck test ## Run lint, type checks, and tests

test: ## Run tests (override TEST_ARGS to select tests or options)
	$(UV) run pytest $(TEST_ARGS)

lint: ## Check Python style and common errors
	$(UV) run ruff check $(PYTHON_PATHS)

typecheck: ## Check Python types
	$(UV) run ty check $(PYTHON_PATHS)

format: ## Format Python source, excluding generated ontology output
	$(UV) run ruff format --extend-exclude '$(FORMAT_EXCLUDE)' $(PYTHON_PATHS)

build: ## Build the source distribution and wheel in dist/
	$(UV) build

docs: ## Build HTML documentation and execute tutorial notebooks
	$(UV) run --group docs jupyter-book build $(DOCS_DIR) $(DOCS_ARGS)

docs-rebuild: ## Rebuild all documentation pages
	$(UV) run --group docs jupyter-book build $(DOCS_DIR) --all $(DOCS_ARGS)

docs-check: ## Rebuild documentation with warnings treated as errors
	$(UV) run --group docs jupyter-book build $(DOCS_DIR) --all --warningiserror $(DOCS_ARGS)

docs-open: docs ## Build documentation and open it in the default browser
	$(UV) run --group docs python -c 'from pathlib import Path; import webbrowser; webbrowser.open(Path("$(DOCS_DIR)/_build/html/index.html").resolve().as_uri())'

docs-clean: ## Remove generated documentation and notebook caches
	$(UV) run --group docs jupyter-book clean $(DOCS_DIR) --all

regen: ## Regenerate supplied domain packages from local SHACL
	$(UV) run python scripts/generate_example_domains.py

clean: docs-clean ## Remove documentation, build output, and tool caches
	rm -rf build dist .pytest_cache .ruff_cache
