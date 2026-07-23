"""The Model: the session object that collects entities and emits RDF.

A Model owns a namespace, mints IRIs for entities, and is the only place in
the runtime that touches rdflib. Users interact with it three ways:

- ``with Model("urn:ex/bldg#") as m:`` — ambient binding; entities created
  inside the block belong to ``m`` without passing it around;
- ``m.save("bldg.ttl")`` — serialize;
- ``m.validate()`` — SHACL validation (via shifty) with errors mapped back
  to Python objects.
"""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator
from urllib.parse import quote

import rdflib
from rdflib import OWL, RDF, RDFS, Literal, URIRef

from .errors import ModelingError

if TYPE_CHECKING:
    from .entity import Entity
    from .enums import EnumValue
    from .resolution import ConnectionHandle, PortHandle, ResolutionReport, ResolvedModel
    from .validation import ValidationReport

#: The ambient model set by ``with Model(...)`` blocks.
_current: ContextVar[Model | None] = ContextVar("objectrdf_model", default=None)


def current_model() -> Model | None:
    """The innermost active ``with Model(...)`` block, if any."""
    return _current.get()


class Model:
    """A model under construction: a namespace plus the entities in it."""

    def __init__(
        self,
        namespace: str,
        *,
        name: str | None = None,
        ontology_iri: str | None = None,
        imports: Iterable[str] = (),
    ) -> None:
        """Create a model.

        ``namespace`` is the IRI prefix instance IRIs are minted under; a
        trailing ``#`` is added if it doesn't already end in ``#`` or ``/``.
        """
        if not namespace.endswith(("#", "/")):
            namespace += "#"
        self.namespace = namespace
        self.name = name
        self.ontology_iri = ontology_iri or namespace.rstrip("#/")
        self.imports = set(imports)
        self.entities: list[Entity] = []
        self._by_name: dict[str, Entity] = {}
        self._by_iri: dict[str, Entity] = {}
        self._tokens: list[Token[Model | None]] = []
        self._auto_counters: dict[str, int] = {}
        self._connection_intents: list[ConnectionHandle] = []
        self._port_intents: list[PortHandle] = []
        self._system_intents: list[tuple[Entity, tuple[Entity, ...]]] = []
        self._reserved_names: set[str] = set()
        self._next_intent_id = 1
        self._revision = 0
        self._resolved_cache: ResolvedModel | None = None
        self._component_cache: dict[tuple[Any, ...], Any] = {}
        self._frozen = False
        self._resolving = False

    # -- ambient binding --------------------------------------------------

    def __enter__(self) -> Model:
        self._tokens.append(_current.set(self))
        return self

    def __exit__(self, *exc_info: object) -> None:
        _current.reset(self._tokens.pop())

    def _bind(self, entity: Entity) -> None:
        """Mint an IRI for a new entity and index it. Called by Entity."""
        self._assert_mutable()
        if entity.name in self._by_name or entity.name in self._reserved_names:
            raise ModelingError(
                f"an entity named {entity.name!r} already exists in this "
                f"model ({self._by_name[entity.name]!r}); names must be "
                f"unique within a model"
            )
        entity._iri = self.namespace + quote(entity.name, safe="")
        self.entities.append(entity)
        self._by_name[entity.name] = entity
        self._by_iri[entity._iri] = entity
        self._touch(entity)

    def _unbind(self, entity: Entity) -> None:
        """Remove a partially constructed entity (failed __init__)."""
        self.entities.remove(entity)
        del self._by_name[entity.name]
        del self._by_iri[entity._iri]
        self._touch(entity)

    def _assert_mutable(self) -> None:
        if self._frozen:
            raise ModelingError("resolved model snapshots are immutable")

    def _touch(self, *entities: object) -> None:
        """Invalidate cached resolution after an authored mutation."""
        self._assert_mutable()
        self._revision += 1
        self._resolved_cache = None

    def _defer_connection(
        self,
        source: Entity | PortHandle,
        target: Entity | PortHandle,
        *,
        medium: EnumValue | None,
        connection: type[Entity] | None,
        name: str | None,
    ) -> ConnectionHandle:
        """Record an S223 connection intention without materializing it."""
        from .resolution import ConnectionHandle, PortHandle

        self._assert_mutable()
        source_owner = source.owner if isinstance(source, PortHandle) else source
        target_owner = target.owner if isinstance(target, PortHandle) else target
        if source_owner.meta.model is not self or target_owner.meta.model is not self:
            raise ModelingError("connection endpoints must belong to the same Model")
        base = name or f"{source.name}--{target.name}"
        reserved = base
        suffix = 2
        while reserved in self._by_name or reserved in self._reserved_names:
            if name is not None:
                raise ModelingError(f"an entity or connection named {name!r} already exists")
            reserved = f"{base}_{suffix}"
            suffix += 1
        handle = ConnectionHandle(
            self,
            self._next_intent_id,
            source,
            target,
            medium=medium,
            connection=connection,
            name=reserved,
        )
        self._next_intent_id += 1
        self._connection_intents.append(handle)
        self._reserved_names.add(reserved)
        self._touch(source, target)
        return handle

    def _defer_port(
        self,
        owner: Entity,
        name: str,
        direction: str,
        *,
        medium: EnumValue | None,
    ) -> PortHandle:
        """Record a named connection point without choosing its medium."""
        from .resolution import PortHandle

        self._assert_mutable()
        if direction not in {"in", "out", "bi"}:
            raise ValueError("port direction must be 'in', 'out', or 'bi'")
        if owner.meta.model is not self:
            raise ModelingError("port owner must belong to this Model")
        if name in self._by_name or name in self._reserved_names:
            raise ModelingError(f"an entity, port, or connection named {name!r} exists")
        port = PortHandle(self, owner, name, direction, medium=medium)
        self._port_intents.append(port)
        self._reserved_names.add(name)
        self._touch(owner)
        return port

    def _auto_name(self, cls: type[Entity]) -> str:
        """Generate the next free ``<class>_<n>`` name for this model.

        The counter is per class-name prefix and only moves forward, but
        names a user minted manually (e.g. an explicit ``vav_2``) are
        skipped rather than collided with.
        """
        prefix = _snake(cls.__name__)
        counter = self._auto_counters.get(prefix, 0)
        while True:
            counter += 1
            candidate = f"{prefix}_{counter}"
            if candidate not in self._by_name and candidate not in self._reserved_names:
                break
        self._auto_counters[prefix] = counter
        return candidate

    def system(self, name: str, *, label: str | None = None) -> _SystemScope:
        """Collect equipment created in a scope into an S223 System."""
        return _SystemScope(self, name, label=label)

    # -- lookup -----------------------------------------------------------

    def __getitem__(self, name: str) -> Entity:
        """Look an entity up by its local name."""
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"no entity named {name!r} in this model") from None

    def __iter__(self) -> Iterator[Entity]:
        return iter(self.entities)

    def __len__(self) -> int:
        return len(self.entities)

    # -- RDF output -------------------------------------------------------

    def _graph_unresolved(self) -> rdflib.Graph:
        """Build the rdflib Graph for the current model state.

        Emits, per entity: the ``rdf:type`` triple, ``rdfs:label``/
        ``rdfs:comment``, and one triple per property value. Both directions
        of an inverse pair are emitted when both are populated (inverse
        maintenance keeps them in sync in memory); this is redundant but
        valid, and keeps the serializer trivial.
        """
        g = rdflib.Graph()
        namespaces: dict[str, str] = {"": self.namespace}
        imports = set(self.imports)
        for entity in self.entities:
            subject = URIRef(entity._iri)
            info = entity._classinfo_effective()
            ontology = info.ontology
            dependency = ontology.iri or ontology.source
            if dependency:
                imports.add(dependency)
            g.add((subject, RDF.type, URIRef(info.iri)))
            g.add((subject, RDFS.label, Literal(entity.label)))
            if entity.comment is not None:
                g.add((subject, RDFS.comment, Literal(entity.comment)))
            for spec, value in entity._property_values():
                dependency = getattr(value, "ontology_iri", None)
                if dependency:
                    imports.add(dependency)
                if spec.kind == "object":
                    obj = URIRef(
                        value.iri if hasattr(value, "iri") else value._iri
                    )
                elif spec.kind in {"enum", "term"}:
                    obj = URIRef(value.iri)
                elif spec.kind == "value":
                    if hasattr(value, "_iri"):
                        obj = URIRef(value._iri)
                    elif hasattr(value, "iri"):
                        obj = URIRef(value.iri)
                    else:
                        obj = Literal(value)
                else:
                    obj = Literal(value)
                g.add((subject, URIRef(spec.predicate), obj))
            # Bind a prefix for the ontology namespace for readable output.
            ns = _split_namespace(info.iri)
            if ns is not None:
                namespaces.setdefault(info.ontology.name.lower(), ns)
        ontology_subject = URIRef(self.ontology_iri)
        g.add((ontology_subject, RDF.type, OWL.Ontology))
        if self.name is not None:
            g.add((ontology_subject, RDFS.label, Literal(self.name)))
        for dependency in sorted(imports):
            if dependency != self.ontology_iri:
                g.add((ontology_subject, OWL.imports, URIRef(dependency)))
        for prefix, ns in namespaces.items():
            g.bind(prefix, ns)
        g.bind("owl", OWL)
        return g

    def check(self) -> ResolutionReport:
        """Check deferred S223 constraints without materializing a snapshot."""
        from objectrdf.solver223 import check_model

        return check_model(self)

    def resolve(self) -> ResolvedModel:
        """Resolve all deferred intentions into a cached frozen snapshot."""
        if (
            self._resolved_cache is not None
            and self._resolved_cache.source_revision == self._revision
        ):
            return self._resolved_cache
        from objectrdf.solver223 import resolve_model

        snapshot = resolve_model(self)
        self._resolved_cache = snapshot
        return snapshot

    def compile(
        self,
        *,
        validate: bool = True,
        shapes: object = None,
        infer: bool = True,
    ) -> ResolvedModel:
        """Resolve and, by default, validate one concrete immutable graph.

        Validation uses the exact SHACL graph bundled with each generated
        package when available. Pass ``validate=False`` only for deliberate
        diagnostic or partial-model workflows.
        """
        snapshot = self.resolve()
        if validate:
            report = self.validate(shapes, infer=infer)
            if not report:
                from .errors import ValidationError

                raise ValidationError(
                    f"compiled model does not conform:\n{report}",
                    report=report,
                )
        return snapshot

    def graph(self) -> rdflib.Graph:
        """Resolve the authored model and return its concrete RDF graph."""
        return self.resolve().graph()

    def save(self, path: str | Path, *, format: str | None = None) -> None:
        """Serialize to a file; format inferred from the extension
        (``.ttl``, ``.nt``, ``.xml``, ``.jsonld``) unless given."""
        path = Path(path)
        if format is None:
            format = {
                ".ttl": "turtle",
                ".nt": "nt",
                ".xml": "xml",
                ".rdf": "xml",
                ".jsonld": "json-ld",
            }.get(path.suffix, "turtle")
        self.graph().serialize(destination=str(path), format=format)

    # -- validation -------------------------------------------------------

    def validate(
        self, shapes: object = None, *, infer: bool = True
    ) -> ValidationReport:
        """Validate against SHACL shapes (via shifty).

        ``shapes`` may be an rdflib Graph, a path, or a URL; when omitted,
        the shapes graphs advertised by the generated packages used in this
        model are collected automatically (each package knows its ontology
        source). Violations are mapped back to entities where possible.
        """
        from .validation import validate_model

        return validate_model(self, shapes, infer=infer)

    def __repr__(self) -> str:
        return f"<Model {self.namespace} ({len(self.entities)} entities)>"


_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _snake(class_name: str) -> str:
    """Class name -> auto-name prefix (``AHU`` -> ``ahu``,
    ``Air_Handling_Unit`` -> ``air_handling_unit``)."""
    return _CAMEL_BOUNDARY.sub("_", class_name).lower()


class _SystemScope:
    """Deferred ``with model.system(...)`` member collector."""

    def __init__(self, model: Model, name: str, *, label: str | None) -> None:
        self.model = model
        self.name = name
        self.label = label
        self._start = 0
        self.entity: Entity | None = None

    def __enter__(self) -> _SystemScope:
        self._start = len(self.model.entities)
        return self

    def __exit__(self, *exc_info: object) -> None:
        if exc_info[0] is not None:
            return
        candidates = self.model.entities[self._start :]
        if not candidates:
            raise ModelingError(f"system {self.name!r} has no members")
        registry = candidates[0].meta.registry
        equipment_cls = registry.resolve("Equipment")
        system_cls = registry.resolve("System")
        members = tuple(
            entity
            for entity in candidates
            if isinstance(entity, (equipment_cls, system_cls))
        )
        if not members:
            raise ModelingError(f"system {self.name!r} has no equipment members")
        self.entity = system_cls(
            self.name,
            label=self.label,
            has_member=members,
            model=self.model,
        )
        self.model._system_intents.append((self.entity, members))


def _split_namespace(class_iri: str) -> str | None:
    """Namespace part of a class IRI (up to and including '#' or last '/')."""
    for sep in ("#", "/"):
        if sep in class_iri:
            return class_iri.rsplit(sep, 1)[0] + sep
    return None
