"""Deferred connection intentions and immutable resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator, Literal

if TYPE_CHECKING:
    import rdflib

    from .entity import Entity
    from .enums import EnumValue
    from .model import Model


class PortHandle:
    """Stable authored name and constraints for a deferred connection point."""

    def __init__(
        self,
        model: Model,
        owner: Entity,
        name: str,
        direction: Literal["in", "out", "bi"],
        *,
        medium: EnumValue | None = None,
    ) -> None:
        self._model = model
        self.owner = owner
        self.name = name
        self.direction = direction
        self._medium = medium
        self._paired_with: PortHandle | None = None
        self.roles: list[EnumValue] = []

    @property
    def medium(self) -> EnumValue | None:
        return self._medium

    @medium.setter
    def medium(self, value: EnumValue | None) -> None:
        self._model._assert_mutable()
        self._medium = value
        self._model._touch(self.owner)

    @property
    def paired_with(self) -> PortHandle | None:
        return self._paired_with

    def pair(self, other: PortHandle) -> PortHandle:
        """Pair two internal ports and constrain them to one medium."""
        if other._model is not self._model:
            raise ValueError("paired ports must belong to the same Model")
        self._model._assert_mutable()
        self._paired_with = other
        other._paired_with = self
        self._model._touch(self.owner, other.owner)
        return self

    def __repr__(self) -> str:
        return f"<PortHandle {self.owner.name}.{self.name}>"


class ConnectionHandle:
    """Stable, editable reference to a deferred connection intention.

    Generated Connection properties are staged on the handle before
    resolution. Multi-valued properties expose a small set-like proxy, so
    ``handle.has_role.add(role)`` mirrors authored entity relationships.
    """

    _OWN_ATTRIBUTES = frozenset(
        {
            "identifier",
            "source",
            "target",
            "name",
            "medium",
            "connection_class",
            "label",
            "comment",
        }
    )

    def __init__(
        self,
        model: Model,
        identifier: int,
        source: Entity | PortHandle,
        target: Entity | PortHandle,
        *,
        medium: EnumValue | None,
        connection: type[Entity] | None,
        name: str,
    ) -> None:
        self._model = model
        self.identifier = identifier
        self.source = source
        self.target = target
        self._medium = medium
        self._connection_class = connection
        self.name = name
        self._label = name
        self._comment: str | None = None
        self._assignments: dict[str, Any] = {}

    @property
    def medium(self) -> EnumValue | None:
        """The authored medium constraint, or ``None`` if unconstrained.

        Assignment invalidates cached resolution so the next check or resolve
        uses the new hint.
        """
        return self._medium

    @medium.setter
    def medium(self, value: EnumValue | None) -> None:
        self._model._assert_mutable()
        self._medium = value
        self._model._touch(self.source, self.target)

    @property
    def connection_class(self) -> type[Entity] | None:
        return self._connection_class

    @connection_class.setter
    def connection_class(self, value: type[Entity] | None) -> None:
        self._model._assert_mutable()
        self._connection_class = value
        self._model._touch(self.source, self.target)

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._model._assert_mutable()
        self._label = value
        self._model._touch(self.source, self.target)

    @property
    def comment(self) -> str | None:
        return self._comment

    @comment.setter
    def comment(self, value: str | None) -> None:
        self._model._assert_mutable()
        self._comment = value
        self._model._touch(self.source, self.target)

    def __getattr__(self, name: str) -> Any:
        """Expose generated Connection properties as staged values."""
        descriptor = self._connection_descriptor(name)
        if descriptor is None:
            raise AttributeError(
                f"{type(self).__name__!s} has no attribute {name!r}"
            )
        if _is_many_descriptor(descriptor):
            return _StagedCollection(self, name)
        return self._assignments.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Stage assignment to a generated Connection property."""
        if (
            name.startswith("_")
            or name in self._OWN_ATTRIBUTES
            or "_model" not in self.__dict__
        ):
            object.__setattr__(self, name, value)
            return
        descriptor = self._connection_descriptor(name)
        if descriptor is None:
            object.__setattr__(self, name, value)
            return
        if _is_many_descriptor(descriptor):
            try:
                value = list(value)
            except TypeError:
                raise TypeError(
                    f"{name} is multi-valued; assign an iterable or use "
                    f"handle.{name}.add(value)"
                ) from None
        self._stage(name, value)

    def assign(self, **properties: Any) -> ConnectionHandle:
        """Stage properties, including custom-subclass escape-hatch values."""
        for name, value in properties.items():
            descriptor = self._connection_descriptor(name)
            if descriptor is None:
                self._stage(name, value)
            else:
                setattr(self, name, value)
        return self

    def _connection_descriptor(self, name: str) -> object | None:
        connection_cls = self._connection_class
        if connection_cls is None:
            source = (
                self.source.owner
                if isinstance(self.source, PortHandle)
                else self.source
            )
            connection_cls = source.meta.registry.resolve("Connection")
        for cls in connection_cls.__mro__:
            if name in cls.__dict__:
                return cls.__dict__[name]
        return None

    def _stage(self, name: str, value: Any) -> None:
        self._model._assert_mutable()
        self._assignments[name] = value
        self._model._touch(self.source, self.target)

    def __repr__(self) -> str:
        return f"<ConnectionHandle {self.source.name}--{self.target.name}>"


class _StagedCollection:
    """Live collection view over one multi-valued handle assignment."""

    def __init__(self, handle: ConnectionHandle, name: str) -> None:
        self._handle = handle
        self._name = name

    def add(self, *values: Any) -> None:
        """Append values, ignoring duplicates."""
        current = list(self._handle._assignments.get(self._name, ()))
        changed = False
        for value in values:
            if value not in current:
                current.append(value)
                changed = True
        if changed:
            self._handle._stage(self._name, current)

    def remove(self, value: Any) -> None:
        """Remove a staged value."""
        current = list(self._handle._assignments.get(self._name, ()))
        current.remove(value)
        self._handle._stage(self._name, current)

    def clear(self) -> None:
        """Remove all staged values."""
        if self._handle._assignments.get(self._name):
            self._handle._stage(self._name, [])

    def __iter__(self) -> Iterator[Any]:
        return iter(self._handle._assignments.get(self._name, ()))

    def __len__(self) -> int:
        return len(self._handle._assignments.get(self._name, ()))

    def __contains__(self, value: object) -> bool:
        return value in self._handle._assignments.get(self._name, ())

    def __repr__(self) -> str:
        values = list(self)
        return f"StagedCollection({self._name}={values!r})"


def _is_many_descriptor(descriptor: object) -> bool:
    from .relations import EnumSet, Rel

    return isinstance(descriptor, (EnumSet, Rel))


@dataclass(frozen=True)
class ResolutionIssue:
    """A solver diagnostic tied to authored object names when possible."""

    message: str
    labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolutionReport:
    """Non-materializing result returned by :meth:`Model.check`."""

    status: Literal["complete", "underconstrained", "unsatisfiable"]
    issues: tuple[ResolutionIssue, ...] = ()

    @property
    def satisfiable(self) -> bool:
        return self.status != "unsatisfiable"

    @property
    def complete(self) -> bool:
        return self.status == "complete"

    def __bool__(self) -> bool:
        return self.satisfiable


@dataclass(frozen=True)
class ResolutionExplanation:
    """Human-readable provenance for one materialized connection decision."""

    connection: str
    medium: EnumValue
    source_point: str
    target_point: str
    medium_reason: Literal[
        "explicit connection",
        "explicit port",
        "paired port",
        "ontology constraint",
        "affinity preference",
    ]
    evidence: tuple[str, ...] = ()


class ResolvedModel:
    """Frozen concrete model produced from authored entities and intentions."""

    def __init__(
        self,
        model: Model,
        connections: dict[int, Entity],
        explanations: dict[int, ResolutionExplanation],
        source_revision: int,
    ) -> None:
        self._model = model
        self._connections = connections
        self._explanations = explanations
        self.source_revision = source_revision
        self._model._frozen = True

    @property
    def entities(self) -> tuple[Entity, ...]:
        return tuple(self._model.entities)

    def __getitem__(self, name: str) -> Any:
        return self._model[name]

    def __iter__(self):
        return iter(self._model)

    def __len__(self) -> int:
        return len(self._model)

    def connection(self, handle: ConnectionHandle) -> Any:
        """Return the concrete connection corresponding to ``handle``."""
        try:
            return self._connections[handle.identifier]
        except KeyError:
            raise KeyError("connection handle does not belong to this snapshot") from None

    def explain(self, handle: ConnectionHandle) -> ResolutionExplanation:
        """Explain the solver choices made for one authored connection."""
        try:
            return self._explanations[handle.identifier]
        except KeyError:
            raise KeyError("connection handle does not belong to this snapshot") from None

    def graph(self) -> rdflib.Graph:
        return self._model._graph_unresolved()
