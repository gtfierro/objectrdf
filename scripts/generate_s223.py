"""Regenerate objectrdf.s223 from the published ASHRAE 223P document.

The document is compiled without its QUDT imports; quantity kinds and units
come from the separate ``objectrdf.qudt`` vocabulary package.
"""

from pathlib import Path

from rdflib import Graph

from objectrdf.gen import generate

ROOT = Path(__file__).resolve().parents[1]
S223_SOURCE = "https://open223.info/223p.ttl"


def main() -> None:
    generate(
        Graph().parse(S223_SOURCE, format="turtle"),
        ROOT / "src" / "objectrdf" / "s223",
        name="S223",
        source=S223_SOURCE,
    )


if __name__ == "__main__":
    main()
