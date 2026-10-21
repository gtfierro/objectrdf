# Contributing to plumb

## Set up

plumb needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
Graphviz is needed for the flowsheet tests and the book.

```bash
make setup          # install development and documentation dependencies
```

## Check a change

```bash
make check          # lint, format check, type checks, and tests
make docs-check     # build the book, running every code cell; warnings are errors
make dist-check     # build the wheel and sdist, check metadata, smoke-test the wheel
```

Use `make test TEST_ARGS="-q tests/test_named_points.py"` to select tests and
`make format` to format source. `make help` lists every target. CI runs the
same checks on every pull request.

Repository conventions (layout, style, naming, tests, commits) are in
[AGENTS.md](AGENTS.md). Internals are described in the
[contributor documentation](docs/index.md).

## Generated packages

`plumb.s223`, `plumb.watr`, `plumb.qudt`, `plumb.brick`, and the domain
packages are compiler output. Do not edit them by hand: change the generator
or an overlay in `src/plumb/gen/` and regenerate. See
[docs/codegen.md](docs/codegen.md) for the scripts, and include the generated
diff in the pull request.

## Pull requests

Explain the motivation and the observable behavior, list the commands you ran,
and add an entry under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md) for
anything a user would notice. Update the book or examples when a public API
changes.

## Release

Releases are published to [PyPI](https://pypi.org/project/plumb-rdf/) by the
[release workflow](.github/workflows/release.yml) when a GitHub release is
published. Nobody uploads by hand.

1. On an up-to-date `main` with green CI, set the new `version` in
   `pyproject.toml` and run `uv lock` so the lockfile records it. CI
   installs with `UV_LOCKED=1`, so a stale lockfile fails the release.
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`,
   add a fresh empty `## [Unreleased]` above it, and update the links at the
   bottom:

   ```markdown
   [Unreleased]: https://github.com/gtfierro/plumb/compare/vX.Y.Z...HEAD
   [X.Y.Z]: https://github.com/gtfierro/plumb/compare/vPREVIOUS...vX.Y.Z
   ```

3. Check, commit, tag, and push:

   ```bash
   make check docs-check dist-check
   git commit -am "Release X.Y.Z"
   git tag -a vX.Y.Z -m "plumb X.Y.Z"
   git push origin main vX.Y.Z
   ```

4. Publish a GitHub release from the tag, with that version's changelog
   section as the notes:

   ```bash
   awk '/^## \[X.Y.Z\]/{f=1;next} /^## \[/{f=0} f' CHANGELOG.md \
     | sed '/^\[.*\]: /d' > notes.md
   gh release create vX.Y.Z --title "plumb X.Y.Z" --notes-file notes.md --verify-tag
   ```

   Creating the release in the GitHub web UI works too.

The workflow then:

- runs lint, type checks, and tests;
- fails if the tag is not `v` followed by the `pyproject.toml` version;
- builds and checks the wheel and sdist;
- publishes them to PyPI through trusted publishing in the `pypi`
  environment;
- attaches them to the GitHub release.

Watch it with `gh run watch`, or under Actions on GitHub.

### Things to know

- **The workflow runs from the tagged commit.** Changes to
  `release.yml` only take effect for tags made after them.
- **If the workflow fails before publishing**, fix the problem on `main`,
  delete the GitHub release, move the tag to the fixed commit
  (`git tag -f -a vX.Y.Z -m "plumb X.Y.Z" && git push -f origin vX.Y.Z`),
  and create the release again. Re-running the failed run would build the
  old commit.
- **PyPI never accepts the same version twice**, even after a deletion. If
  a broken release reaches PyPI, yank it on PyPI and release the next patch
  version.
- **Trusted publishing** is configured on PyPI for project `plumb-rdf`,
  owner `gtfierro`, repository `plumb`, workflow `release.yml`, environment
  `pypi`. Renaming the workflow file or the environment breaks publishing
  until the PyPI side is updated to match.
- The book at <https://gtfierro.github.io/plumb/> deploys separately, from
  `main`, whenever the book, source, examples, or ontologies change.
