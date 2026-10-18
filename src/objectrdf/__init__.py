"""objectrdf: author RDF building models as plain typed Python.

Generated ontology packages (``objectrdf.brick``, ...) provide the classes;
this top-level module re-exports the runtime pieces users touch directly.

    from objectrdf import Model
    from objectrdf.brick import AHU, VAV

    with Model("urn:ex/bldg1#") as m:
        ahu = AHU("ahu1")
        vav = VAV("vav1")
        ahu >> vav

    m.save("bldg1.ttl")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

if TYPE_CHECKING:
    from .s223 import Connectable as S223Connectable
    from .watr import Connectable as WaTrConnectable

from .core import (
    AmbiguousModelError,
    ConnectionHandle,
    PortHandle,
    PortContract,
    PortSlot,
    PropertyBundle,
    PropertySchema,
    PropertySet,
    QuantityDefinition,
    ResolutionExplanation,
    Entity,
    EnumValue,
    Model,
    ModelingError,
    ObjectRDFError,
    ResolutionError,
    ResolutionReport,
    ResolvedModel,
    TermValue,
    UnsatisfiableModelError,
    ValidationError,
    ValidationReport,
    current_model,
)
from .core.recipes import PointGroupRef, PointRef, Policy, choose, default, fixed

__version__ = "0.1.0"


@overload
def connect(
    a: S223Connectable | WaTrConnectable | PortHandle | PointRef | PointGroupRef,
    b: Entity | PortHandle | PointRef | PointGroupRef,
    *, medium: EnumValue | None = None, connection: type[Entity] | None = None,
    name: str | None = None, ports: Literal["match", "new"] = "match",
) -> ConnectionHandle: ...


@overload
def connect(
    a: Entity, b: Entity | PortHandle | PointRef | PointGroupRef,
    *, medium: EnumValue | None = None, connection: type[Entity] | None = None,
    name: str | None = None, ports: Literal["match", "new"] = "match",
) -> ConnectionHandle | None: ...


def connect(
    a: Entity | PortHandle | PointRef | PointGroupRef,
    b: Entity | PortHandle | PointRef | PointGroupRef,
    *,
    medium: EnumValue | None = None,
    connection: type[Entity] | None = None,
    name: str | None = None,
    ports: Literal["match", "new"] = "match",
) -> ConnectionHandle | None:
    """Connect ``a`` to ``b`` along the flow direction; the functional form
    of ``a >> b`` for when you need to retain the connection intention.

    For S223/WaTr packages this returns a stable ``ConnectionHandle``.
    Named and unnamed connections select ports by the same rules. Use
    ``ports="new"`` to allocate fresh directed ports on bare equipment, or
    pass explicit point references. Port identity is independent of the name.
    ``medium=`` gives the Z3 resolver a flow-media hint, and the handle's
    ``medium`` property may be refined later. ``connection=`` constrains the
    materialized Connection subclass. Retrieve the concrete entity with
    ``resolved.connection(handle)`` after ``Model.resolve()``. Generated
    multi-valued properties can be staged with collection syntax, for example
    ``handle.has_role.add(role)``.
    For Brick-style packages it adds the flow property edge (``feeds``) and
    returns None (there is no intermediate resource to return).
    """
    if name == "":
        raise ValueError("connection name must not be empty")
    if ports not in {"match", "new"}:
        raise ValueError("ports must be 'match' or 'new'")
    if isinstance(a, PointRef):
        a = a._port
    if isinstance(b, PointRef):
        b = b._port
    a_owner = a.owner if isinstance(a, (PortHandle, PointGroupRef)) else a
    if isinstance(a_owner, Entity):
        point_owner = getattr(a_owner, "owner", None)
        if isinstance(point_owner, Entity):
            a_owner = point_owner
    if a_owner._CONNECTOR is not None:
        source_equipment = isinstance(a, Entity) and hasattr(a, "has_connection_point")
        target_equipment = isinstance(b, Entity) and hasattr(b, "has_connection_point")
        if ports == "new" and (source_equipment or target_equipment):
            a_model = a_owner.meta.model
            b_owner = b.owner if isinstance(b, (PortHandle, PointGroupRef)) else b
            if isinstance(b_owner, Entity):
                point_owner = getattr(b_owner, "owner", None)
                if isinstance(point_owner, Entity):
                    b_owner = point_owner
            if b_owner.meta.model is not a_model:
                raise ModelingError("connection endpoints must belong to the same Model")
            a_model._assert_mutable()
            if a_model._loaded_graph is not None:
                raise ModelingError(
                    "deferred connections cannot be added to a graph-backed model"
                )
            with a_model._atomic():
                for endpoint, direction in ((a, "out"), (b, "in")):
                    if not isinstance(endpoint, Entity) or not hasattr(endpoint, "has_connection_point"):
                        continue
                    maximum = type(endpoint)._shape_max_ports
                    count = len(endpoint.ports)
                    if maximum is not None and count >= maximum:
                        raise ModelingError(f"{endpoint.name}: shape prohibits additional ports")
                    stem = f"{endpoint.name}-{direction}"
                    candidate = stem
                    index = 2
                    while candidate in a_model._by_name or candidate in a_model._reserved_names:
                        candidate = f"{stem}-{index}"
                        index += 1
                    port = endpoint.port(candidate, direction=direction, medium=medium)
                    if direction == "out":
                        a = port
                    else:
                        b = port
                return a_owner._CONNECTOR.connect(
                    a, b, medium=medium, connection=connection, name=name,
                )
        return a_owner._CONNECTOR.connect(
            a, b, medium=medium, connection=connection, name=name
        )
    if isinstance(a, Entity) and a._RSHIFT is not None:
        getattr(a, a._RSHIFT).add(b)
        return None
    raise TypeError(f"{type(a).__name__} does not participate in flow connections")


__all__ = [
    "AmbiguousModelError",
    "ConnectionHandle",
    "PortHandle",
    "PortContract",
    "PortSlot",
    "PropertyBundle",
    "PropertySchema",
    "PropertySet",
    "QuantityDefinition",
    "PointGroupRef",
    "PointRef",
    "Policy",
    "ResolutionExplanation",
    "Entity",
    "EnumValue",
    "Model",
    "ModelingError",
    "ObjectRDFError",
    "ResolutionError",
    "ResolutionReport",
    "ResolvedModel",
    "TermValue",
    "UnsatisfiableModelError",
    "ValidationReport",
    "ValidationError",
    "connect",
    "choose",
    "current_model",
    "default",
    "fixed",
    "__version__",
]
