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

from typing import Any

from .core import (
    AmbiguousModelError,
    ConnectionHandle,
    PortHandle,
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

__version__ = "0.1.0"


def connect(
    a: Entity | PortHandle,
    b: Entity | PortHandle,
    *,
    medium: EnumValue | None = None,
    connection: type[Entity] | None = None,
    name: str | None = None,
) -> Any:
    """Connect ``a`` to ``b`` along the flow direction; the functional form
    of ``a >> b`` for when you need to retain the connection intention.

    For S223/WaTr packages this returns a stable ``ConnectionHandle``.
    ``medium=`` gives the Z3 resolver a flow-media hint, and the handle's
    ``medium`` property may be refined later. ``connection=`` constrains the
    materialized Connection subclass. Retrieve the concrete entity with
    ``resolved.connection(handle)`` after ``Model.resolve()``. Generated
    multi-valued properties can be staged with collection syntax, for example
    ``handle.has_role.add(role)``.
    For Brick-style packages it adds the flow property edge (``feeds``) and
    returns None (there is no intermediate resource to return).
    """
    a_owner = a.owner if isinstance(a, PortHandle) else a
    if a_owner._CONNECTOR is not None:
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
    "current_model",
    "__version__",
]
