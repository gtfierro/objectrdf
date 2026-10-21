"""Regenerate the pinned QUDT reference vocabularies through ontoenv."""

from pathlib import Path
import argparse

from ontoenv import OntoEnv
from rdflib import Graph

from plumb.gen.vocabulary import emit_vocabulary_module

QUDT_VERSION = "3.4.0"
QUDT_ALL = f"http://qudt.org/{QUDT_VERSION}/qudt-all"
QUDT = "http://qudt.org/schema/qudt/"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "plumb" / "qudt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="use a bundled RDF closure offline")
    args = parser.parse_args()
    if args.file is not None:
        graph = Graph().parse(args.file)
    else:
        env = OntoEnv(temporary=True)
        try:
            env.add(QUDT_ALL)
            graph, _closure = env.get_closure(QUDT_ALL)
        finally:
            env.close()
    graph.parse(ROOT / "ontology" / "qudt-catalog-extras.ttl")
    modules = {
        "units.py": (
            "QUDT units",
            (f"{QUDT}Unit",),
            "http://qudt.org/vocab/unit/",
        ),
        "quantity_kinds.py": (
            "QUDT quantity kinds",
            (f"{QUDT}QuantityKind",),
            "http://qudt.org/vocab/quantitykind/",
        ),
    }
    for filename, (name, rdf_types, namespace) in modules.items():
        source = emit_vocabulary_module(
            graph,
            name=name,
            rdf_types=rdf_types,
            primary_namespace=namespace,
            ontology_iri=QUDT_ALL,
        )
        (OUT / filename).write_text(source)


if __name__ == "__main__":
    main()
