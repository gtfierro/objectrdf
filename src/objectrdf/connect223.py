"""Deferred 223-style connection intentions.

Generated classes eagerly create only connection points whose shape fixes a
single medium. ``connect(a, b)`` records an intention; ``Model.resolve()`` (or
``graph()``, ``save()``, and ``validate()``) delegates layout, medium, point,
and Connection-subclass selection to the Z3 planner. Derived objects live in
an immutable resolved snapshot, leaving the authored model unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .core import CPSlot, ConnectionHandle, EnumValue, PortHandle
from .core import containment as _containment

if TYPE_CHECKING:
    from .core import Entity, Registry

S223 = "http://data.ashrae.org/standard223#"

class S223Connector:
    """Negotiates ``a >> b`` for a generated 223-style package.

    One instance per generated package, installed on the ``Connectable``
    root as ``_CONNECTOR`` by overlay code the emitter writes.
    """

    def __init__(
        self,
        registry: Registry,
        connection_classes: dict[str, str] | None = None,
    ) -> None:
        self.registry = registry
        #: medium IRI (or ancestor) -> Connection subclass python name
        self.connection_classes = connection_classes or {}

    # -- public entry points ---------------------------------------------

    def on_create(self, entity: Entity) -> None:
        """Materialize shape-required connection points on a new entity.

        A fresh ``Fan()`` immediately owns its air inlet and outlet — the
        shapes say they must exist whether or not anything is connected yet.
        Slots without a medium (e.g. Pump) stay lazy: a ConnectionPoint
        needs a medium, which only negotiation or the user can supply.
        """
        with _containment.suppressed():
            existing = list(getattr(entity, "has_connection_point"))
            for slot in self._all_slots(type(entity)):
                if slot.medium is None:
                    continue
                slot_cls = self.registry.resolve(slot.cp_class)
                medium = self.registry.resolve_enum(slot.medium)
                # A shape class with enum descendants is a domain, not one
                # exact value. Leave those points for the solver so adjacent
                # intentions can select Water, Sludge, etc. WaTr commonly
                # constrains equipment to the broad Mix-Fluid domain.
                if any(
                    value.parent is medium
                    for value in self.registry.enums_by_iri.values()
                ):
                    continue
                already = sum(
                    1
                    for cp in existing
                    if isinstance(cp, slot_cls)
                    and getattr(cp, "has_medium") is not None
                    and getattr(cp, "has_medium").is_a(medium)
                )
                for _ in range(max(slot.min_count - already, 0)):
                    cp = slot_cls(
                        self._free_name(entity, f"{entity.name}-{slot.direction}"),
                        has_medium=medium,
                        is_connection_point_of=entity,
                        model=entity.meta.model,
                    )
                    existing.append(cp)

    def connect(
        self,
        a: Entity | PortHandle,
        b: Entity | PortHandle,
        *,
        medium: EnumValue | None = None,
        connection: type[Entity] | None = None,
        name: str | None = None,
    ) -> ConnectionHandle:
        """Record a deferred connection intention and return its handle."""
        a_owner = a.owner if isinstance(a, PortHandle) else a
        return a_owner.meta.model._defer_connection(
            a,
            b,
            medium=medium,
            connection=connection,
            name=name,
        )

    def _all_slots(self, cls: type[Entity]) -> list[CPSlot]:
        """CPSlots declared anywhere along the MRO."""
        out: list[CPSlot] = []
        for klass in cls.__mro__:
            info = klass.__dict__.get("_classinfo")
            if info is not None:
                out.extend(info.cp_slots)
        return out

    def _free_name(self, entity: Entity, base: str) -> str | None:
        """Use a readable name when free; fall back to auto-naming."""
        model = entity.meta.model
        return base if base not in model._by_name else None
