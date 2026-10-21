"""Regenerate plumb.s223 from the published ASHRAE 223P document.

The document is compiled without its QUDT imports; quantity kinds and units
come from the separate ``plumb.qudt`` vocabulary package.
"""

from pathlib import Path
import subprocess
import sys

from rdflib import Graph

from plumb.gen import generate

ROOT = Path(__file__).resolve().parents[1]
S223_SOURCE = "https://open223.info/223p.ttl"


def main() -> None:
    generate(
        Graph().parse(S223_SOURCE, format="turtle"),
        ROOT / "src" / "plumb" / "s223",
        name="S223",
        source=S223_SOURCE,
    )
    # Link the extension against the freshly emitted base in a new interpreter.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_example_domains.py")],
        check=True,
    )


if __name__ == "__main__":
    main()
