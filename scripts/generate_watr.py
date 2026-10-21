"""Regenerate plumb.watr from WaTr v0.3.0.rc1 with its S223 and QUDT imports.

`ontology/watr-0.3.0rc1.ttl` is the unmodified `watr.ttl` asset of
https://github.com/DataDrivenCPS/water-ontology/releases/tag/v0.3.0.rc1.
"""

from pathlib import Path
import subprocess
import sys

from ontoenv import OntoEnv
from rdflib import Graph

from plumb.gen import generate

ROOT = Path(__file__).resolve().parents[1]
WATR_SOURCE = ROOT / "ontology" / "watr-0.3.0rc1.ttl"
ASM2D_COMPONENTS = ROOT / "ontology" / "asm2d-components.ttl"
WATR_IRI = "https://watermetadata.org/ontology/watr"
S223_SOURCE = "https://open223.info/223p.ttl"


def main() -> None:
    merged = Graph()
    env = OntoEnv(temporary=True)
    try:
        env.add(str(WATR_SOURCE))
        env.add(S223_SOURCE)
        for source in (WATR_IRI, S223_SOURCE):
            graph, _closure = env.get_closure(source)
            merged += graph
    finally:
        env.close()
    # The example's model-component pools extend the local WaTr snapshot.
    merged.parse(ASM2D_COMPONENTS, format="turtle")
    generate(
        merged,
        ROOT / "src" / "plumb" / "watr",
        name="WATR",
        source=str(WATR_SOURCE.relative_to(ROOT)),
    )
    # Link the extension against the freshly emitted base in a new interpreter.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_example_domains.py")],
        check=True,
    )


if __name__ == "__main__":
    main()
