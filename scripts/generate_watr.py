"""Regenerate the local WaTr snapshot with its S223 and QUDT imports."""

from pathlib import Path
import subprocess
import sys

from ontoenv import OntoEnv
from rdflib import Graph

from objectrdf.gen import generate

ROOT = Path(__file__).resolve().parents[1]
WATR_SOURCE = ROOT / "ontology" / "watr-pr39-pr46.ttl"
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
        ROOT / "src" / "objectrdf" / "watr",
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
