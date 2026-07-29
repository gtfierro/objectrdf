"""Hydrate generated Python objects from RDF and select them."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote

import rdflib
from rdflib import RDF, RDFS, Literal, URIRef

from .entity import Entity
from .errors import ModelingError
from .meta import PropertySpec, Registry
from .relations import RelSet
from .terms import TermValue

if TYPE_CHECKING:
    from .model import Model


def load_graph(
    model_type: type[Model],
    source: rdflib.Graph | str | Path,
    *,
    registries: Registry | Iterable[Registry],
    namespace: str | None,
    infer: bool,
    shapes: rdflib.Graph | str | Path | None,
    strict: bool,
) -> Model:
    """Build a Model whose generated objects write through to ``source``."""
    graph = _read_graph(source)
    if infer:
        import shifty

        inferred = shifty.infer(graph, shapes).graph()
        if isinstance(source, rdflib.Graph):
            graph += inferred
        else:
            graph = inferred

    registry_list = (
        (registries,) if isinstance(registries, Registry) else tuple(registries)
    )
    if not registry_list:
        raise ValueError("at least one generated package registry is required")

    classes_by_iri: dict[str, list[type[Entity]]] = {}
    for registry in registry_list:
        for iri, entity_type in registry.by_iri.items():
            classes_by_iri.setdefault(iri, []).append(entity_type)

    model = model_type(namespace or _infer_namespace(graph, classes_by_iri))
    model._loaded_graph = graph
    by_node: dict[URIRef, Entity] = {}

    subjects = sorted(set(graph.subjects(RDF.type)), key=str)
    for subject in subjects:
        if not isinstance(subject, URIRef):
            continue
        candidates: list[type[Entity]] = []
        for rdf_type in graph.objects(subject, RDF.type):
            candidates.extend(classes_by_iri.get(str(rdf_type), ()))
        entity_type = _most_specific(subject, candidates, strict=strict)
        if entity_type is None:
            continue
        entity = entity_type.__new__(entity_type)
        label_node = next(iter(graph.objects(subject, RDFS.label)), None)
        comment_node = next(iter(graph.objects(subject, RDFS.comment)), None)
        entity._label = str(label_node) if label_node is not None else None
        entity._comment = str(comment_node) if comment_node is not None else None
        entity._data = {}
        entity._rels = {}
        name = _local_name(str(subject))
        if entity._label is None:
            entity._label = name
        model._bind_loaded(entity, str(subject), name)
        by_node[subject] = entity
        managed = model._managed_triples.setdefault(str(subject), set())
        managed.add(
            (subject, RDF.type, URIRef(entity_type.meta.iri))
        )
        if label_node is not None:
            managed.add((subject, RDFS.label, label_node))
        if comment_node is not None:
            managed.add((subject, RDFS.comment, comment_node))

    for subject, entity in by_node.items():
        specs = {
            spec.predicate: spec for spec in type(entity)._effective_specs().values()
        }
        for predicate, spec in specs.items():
            values = list(graph.objects(subject, URIRef(predicate)))
            if not values:
                continue
            converted: list[object] = []
            accepted_nodes: list[rdflib.term.Node] = []
            for value in values:
                item = _convert_value(
                    graph,
                    value,
                    spec,
                    entity.meta.registry,
                    by_node,
                    strict=strict,
                )
                if item is _SKIP:
                    continue
                converted.append(item)
                accepted_nodes.append(value)
            managed_count = _store_values(
                entity,
                spec,
                converted,
                strict=strict,
            )
            for value in accepted_nodes[:managed_count]:
                model._managed_triples[str(subject)].add(
                    (subject, URIRef(predicate), value)
                )

    return model


def matches(entity: Entity, attributes: Mapping[str, object]) -> bool:
    """Apply simple BeautifulSoup-style attribute filters to an entity."""
    for name, expected in attributes.items():
        if name == "iri":
            actual: Any = entity.meta.instance_iri
        else:
            try:
                actual = getattr(entity, name)
            except AttributeError:
                return False
        if callable(expected):
            predicate = cast(Callable[[Any], object], expected)
            if not predicate(actual):
                return False
        elif isinstance(actual, (RelSet, list, tuple, set, frozenset)):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


def _read_graph(source: rdflib.Graph | str | Path) -> rdflib.Graph:
    if isinstance(source, rdflib.Graph):
        return source
    graph = rdflib.Graph()
    graph.parse(str(source))
    return graph


def _most_specific(
    subject: URIRef,
    candidates: list[type[Entity]],
    *,
    strict: bool,
) -> type[Entity] | None:
    candidates = list(dict.fromkeys(candidates))
    if not candidates:
        return None
    most_specific = [
        candidate
        for candidate in candidates
        if all(issubclass(candidate, other) for other in candidates)
    ]
    if len(most_specific) == 1:
        return most_specific[0]
    if strict:
        names = ", ".join(sorted(candidate.__name__ for candidate in candidates))
        raise ModelingError(
            f"{subject} has incompatible generated Python types: {names}"
        )
    return max(candidates, key=lambda candidate: len(candidate.__mro__))


def _convert_value(
    graph: rdflib.Graph,
    value: rdflib.term.Node,
    spec: PropertySpec,
    registry: Registry,
    by_node: Mapping[URIRef, Entity],
    *,
    strict: bool,
) -> object:
    if spec.kind == "literal":
        if isinstance(value, Literal):
            return value.toPython()
        return _bad_value(value, spec, "an RDF literal", strict=strict)

    if spec.kind == "object":
        if isinstance(value, URIRef):
            if value in by_node:
                return by_node[value]
            return _bad_value(
                value,
                spec,
                "a resource with a generated Python type (include its registry)",
                strict=strict,
            )
        return _bad_value(
            value,
            spec,
            "a resource with a generated Python type",
            strict=strict,
        )

    if spec.kind == "enum":
        if isinstance(value, URIRef):
            try:
                return registry.resolve_enum(str(value))
            except KeyError:
                return _bad_value(
                    value, spec, "a registered enum value", strict=strict
                )
        return _bad_value(value, spec, "a registered enum value", strict=strict)

    if spec.kind == "term":
        if isinstance(value, URIRef):
            return _term(graph, value)
        return _bad_value(value, spec, "a named RDF resource", strict=strict)

    if isinstance(value, Literal):
        return value.toPython()
    if isinstance(value, URIRef):
        if value in by_node:
            return by_node[value]
        return _term(graph, value)
    return _bad_value(value, spec, "a literal or named RDF resource", strict=strict)


def _bad_value(
    value: rdflib.term.Node,
    spec: PropertySpec,
    expected: str,
    *,
    strict: bool,
) -> object:
    if strict:
        raise ModelingError(
            f"cannot load {value.n3()} as {spec.name}: expected {expected}"
        )
    return _SKIP


def _store_values(
    entity: Entity,
    spec: PropertySpec,
    values: list[object],
    *,
    strict: bool,
) -> int:
    if not values:
        return 0
    many = spec.max_count != 1 and spec.kind in {"object", "enum"}
    if many:
        if spec.kind == "object":
            entity._store_for(spec)._items.extend(values)
        else:
            entity._data[spec.name] = values
        return len(values)
    if len(values) > 1 and strict:
        raise ModelingError(
            f"{entity.meta.instance_iri} has {len(values)} values for scalar "
            f"property {spec.name}"
        )
    entity._data[spec.name] = values[0]
    return 1


def _term(graph: rdflib.Graph, value: URIRef) -> TermValue:
    return TermValue(
        str(value),
        label=_first_text(graph.objects(value, RDFS.label)),
        types=tuple(str(rdf_type) for rdf_type in graph.objects(value, RDF.type)),
    )


def _first_text(values: Iterable[rdflib.term.Node]) -> str | None:
    return next((str(value) for value in values), None)


def _local_name(iri: str) -> str:
    local = iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return unquote(local) or iri


def _infer_namespace(
    graph: rdflib.Graph,
    classes_by_iri: Mapping[str, list[type[Entity]]],
) -> str:
    namespaces: Counter[str] = Counter()
    for subject in set(graph.subjects(RDF.type)):
        if not isinstance(subject, URIRef):
            continue
        if not any(
            str(rdf_type) in classes_by_iri
            for rdf_type in graph.objects(subject, RDF.type)
        ):
            continue
        iri = str(subject)
        if "#" in iri:
            namespaces[iri.rsplit("#", 1)[0] + "#"] += 1
        elif "/" in iri:
            namespaces[iri.rsplit("/", 1)[0] + "/"] += 1
    if namespaces:
        return namespaces.most_common(1)[0][0]
    return "urn:objectrdf:loaded#"


_SKIP = object()
