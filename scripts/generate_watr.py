"""Regenerate WaTr with its S223 import closure through ontoenv."""

from ontoenv import OntoEnv
from rdflib import Graph

from objectrdf.gen import generate

WATR_SOURCE = "https://watermetadata.org/water.ttl"
S223_SOURCE = "https://open223.info/223p.ttl"


def main() -> None:
    merged = Graph()
    env = OntoEnv(temporary=True)
    try:
        for source in (WATR_SOURCE, S223_SOURCE):
            env.add(source)
            graph, _closure = env.get_closure(source)
            merged += graph
    finally:
        env.close()
    generate(
        merged,
        "src/objectrdf/watr",
        name="WATR",
        source=WATR_SOURCE,
    )


if __name__ == "__main__":
    main()
