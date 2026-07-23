"""Immutable references to named individuals in external RDF vocabularies."""

from __future__ import annotations


class TermValue:
    """A compiled vocabulary individual, referenced by IRI rather than minted."""

    __slots__ = ("iri", "label", "definition", "types", "ontology_iri")

    def __init__(
        self,
        iri: str,
        *,
        label: str | None = None,
        definition: str | None = None,
        types: tuple[str, ...] = (),
        ontology_iri: str | None = None,
    ) -> None:
        self.iri = iri
        self.label = label
        self.definition = definition
        self.types = types
        self.ontology_iri = ontology_iri

    def is_instance_of(self, class_iri: str) -> bool:
        """Return whether the vocabulary declares this term with ``class_iri``."""
        return class_iri in self.types

    def __repr__(self) -> str:
        local = self.iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        return f"<term {local}>"
