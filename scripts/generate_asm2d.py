"""Regenerate the ASM2d domain API from its checked-in ontology and SHACL."""

from pathlib import Path

from rdflib import Graph

from plumb.gen import generate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "ontology" / "asm2d.ttl"
    generate(
        Graph().parse(source),
        ROOT / "src" / "plumb" / "watr" / "asm2d",
        name="ASM2d",
        source="ontology/asm2d.ttl",
    )


if __name__ == "__main__":
    main()
