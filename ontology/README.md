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

`watr-0.3.0rc1.ttl` is the unmodified `watr.ttl` asset of WaTr
[v0.3.0.rc1](https://github.com/DataDrivenCPS/water-ontology/releases/tag/v0.3.0.rc1)
(SHA-256 `9107996edff06fdfc7d7af524eedf51ca2837d72e6df03ffe5b21d45dda18110`),
a release candidate built from upstream `main`. It keeps the unversioned
`https://watermetadata.org/ontology/watr` ontology IRI with
`owl:versionInfo "0.3.rc1"`; its S223 and QUDT 3.3.0 imports remain imports
and are resolved through ontoenv at generation time.

The release states which subjects and objects `watr:hasProcess` and
`watr:hasTreatmentObjective` accept with SHACL target shapes
(`watr:ProcessBearerShape`, `watr:ProcessValueShape`, and
`watr:TreatmentObjectiveValueShape`). The compiler reads those shapes as the
properties' domains and ranges, so the generated package exposes
`has_process` and `has_treatment_objective` on equipment and systems without
local additions to the ontology. Their values are punned process and objective
class terms, passed as generated Python classes and serialized as ontology
IRIs.

Regenerate the Python package and bundled import closure with:

```bash
uv run python scripts/generate_watr.py
```

To move to a newer WaTr release, replace this file with the release's
`watr.ttl` asset, update `WATR_SOURCE` in `scripts/generate_watr.py`, and
regenerate.
