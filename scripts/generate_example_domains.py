"""Regenerate example domain packages from their checked-in RDF and SHACL."""

from pathlib import Path

from rdflib import Graph

from plumb.gen import generate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for filename, name, package in (
        ("asm2d.ttl", "ASM2d", "watr/asm2d"),
        ("seawater-ro.ttl", "SeawaterRO", "watr/seawater_ro"),
        ("drinking-water.ttl", "DrinkingWater", "watr/drinking_water"),
        ("hvac.ttl", "HVAC", "s223/hvac"),
    ):
        source = ROOT / "ontology" / filename
        generate(
            Graph().parse(source),
            ROOT / "src" / "plumb" / package,
            name=name,
            source=str(source.relative_to(ROOT)),
        )


if __name__ == "__main__":
    main()
