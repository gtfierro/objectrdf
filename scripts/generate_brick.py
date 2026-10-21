"""Regenerate plumb.brick from Brick 1.4 with its RealEstateCore, QUDT,
and other imports."""

from pathlib import Path

from ontoenv import OntoEnv

from plumb.gen import generate

ROOT = Path(__file__).resolve().parents[1]
BRICK_SOURCE = "https://brickschema.org/schema/1.4/Brick.ttl"
BRICK_IRI = "https://brickschema.org/schema/1.4/Brick"


def main() -> None:
    env = OntoEnv(temporary=True)
    try:
        env.add(BRICK_IRI)
        graph, _closure = env.get_closure(BRICK_IRI)
    finally:
        env.close()
    generate(graph, ROOT / "src" / "plumb" / "brick", name="Brick", source=BRICK_SOURCE)


if __name__ == "__main__":
    main()
