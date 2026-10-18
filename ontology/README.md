# Local WaTr ontology snapshot

`asm2d.ttl` defines the ASM2d equipment configurations, named ports, property
groups, defaults, units, and split bases in RDF and SHACL. Regenerate its Python
package with `uv run python scripts/generate_asm2d.py`. See
[the compiler guide](../docs/shacl-configurations.md). `asm2d-components.ttl`
adds the component pools used by the WaTr base package.

`seawater-ro.ttl` defines reusable RO and pretreatment process configurations,
branched port layouts, and quantity schemas for feed, membrane, pumps, storage,
pressure recovery, permeate pressure, and UV. `hvac.ttl` defines the air/water
cooling coil shared by the S223 examples.

`drinking-water.ttl` defines a conventional surface-water treatment train using
WaTr coagulation, flocculation, sedimentation, sand filtration, and chlorination
equipment and processes. Its stage configurations include separate sludge and
filter backwash ports. The sequence follows
[CDC's treatment overview](https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html);
the port layouts are this repository's teaching configuration. All four domain
packages regenerate offline with `uv run python scripts/generate_example_domains.py`.

`qudt-catalog-extras.ttl` preserves reference terms from the pinned QUDT catalog
that are absent from WaTr's bundled import closure. It is included by
`scripts/generate_qudt.py`, including its offline `--file` regeneration path.

`watr-pr39-pr46.ttl` is the compiled WaTr document used to generate
`objectrdf.watr`. It combines the still-open
[water-ontology PR 46](https://github.com/DataDrivenCPS/water-ontology/pull/46)
and [PR 39](https://github.com/DataDrivenCPS/water-ontology/pull/39) on top of
upstream `main`.

The local source checkout is at `/private/tmp/objectrdf-water-ontology`, branch
`objectrdf-pr39-pr46`, merge commit `b0e8d67`. Its inputs were:

- upstream `main`: `41dcff240d850be24c0548dec0f73dbe18e8d7cc`
- PR 46: `b3829f85d43aaa0afa7d6405983c86d3ad774d64`
- PR 39: `1fb2285fbaed4086424bf87c8e7a069ef163d767`

PR 39 was based on the older `urn:nawi-water-ontology` namespace. Its ontology
modules were moved to the current `https://watermetadata.org/ontology/watr#`
term namespace and `https://watermetadata.org/ontology/modules/` module IRIs.
The merged source keeps PR 46's aqueous composition rules and PR 39's later
equipment process requirements, including its broader Filter and reverse
osmosis process counts. The upstream compiler produced this document with
`make build-ontology`; its external S223 and QUDT imports remain imports.

The local source adds six `schema:domainIncludes` and `schema:rangeIncludes`
triples to `watr:hasProcess` and `watr:hasTreatmentObjective`. They describe
their equipment/system subjects and process/objective values for code
generation without adding OWL domain or range entailments. The generated
package therefore exposes `has_process` and `has_treatment_objective` on
equipment and systems. Their values are punned process and objective class
terms, passed as generated Python classes and serialized as ontology IRIs.
The WaTr SHACL shapes remain the authority for validation.
The local snapshot also accepts either `rdfs:comment` or `skos:definition` as
the definition of a WaTr class. The upstream `watr:Class` shape required only
`rdfs:comment`, although the new punned process and objective terms are
defined with `skos:definition`.

Regenerate the Python package and bundled import closure from this checked-in
snapshot with:

```bash
uv run python scripts/generate_watr.py
```

The document retains the upstream WaTr 0.2 ontology IRI and version metadata,
but this combination is a local development snapshot, not a published WaTr
release.
