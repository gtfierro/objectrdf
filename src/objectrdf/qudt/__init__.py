"""QUDT-backed quantities and compiled unit/quantity-kind vocabularies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeVar, cast

from objectrdf.core import (
    ClassInfo,
    ConnectionHandle,
    Entity,
    Lit,
    Model,
    PortHandle,
    OntologyInfo,
    PropertySpec,
    Registry,
    TermOne,
    TermValue,
)

from . import quantity_kinds, units
from objectrdf.core.property_schema import QuantityAmount

QUDT = "http://qudt.org/schema/qudt/"
ONTOLOGY = OntologyInfo(
    name="QUDT",
    iri="http://qudt.org/3.4.0/qudt-all",
    version="3.4.0",
    source="http://qudt.org/3.4.0/qudt-all",
)
_REGISTRY = Registry(ONTOLOGY)
PropertyT = TypeVar("PropertyT", bound=Entity)
QuantityMode = Literal["static", "nominal", "observable", "actuatable"]


def _quantity_class(registry: Registry, mode: QuantityMode) -> type[Entity]:
    class_names = {
        "nominal": "QuantifiableProperty",
        "static": "QuantifiableProperty",
        "observable": "QuantifiableObservableProperty",
        "actuatable": "QuantifiableActuatableProperty",
    }
    try:
        class_name = class_names[mode]
    except KeyError:
        raise ValueError(f"unknown quantity mode {mode!r}") from None
    property_class = registry.by_iri.get(
        f"http://data.ashrae.org/standard223#{class_name}"
    )
    if property_class is None:
        raise TypeError(f"{registry.ontology.name} has no {class_name} class")
    return property_class

_NUMERIC_VALUE = PropertySpec(
    name="numeric_value",
    predicate=f"{QUDT}numericValue",
    kind="literal",
    datatype=float,
    required=True,
    max_count=1,
)
_HAS_UNIT = PropertySpec(
    name="has_unit",
    predicate=f"{QUDT}hasUnit",
    kind="term",
    required=True,
    max_count=1,
    term_ranges=(f"{QUDT}Unit",),
)


class QuantityValue(Entity):
    """A QUDT numeric value paired with its unit."""

    _classinfo = ClassInfo(
        iri=f"{QUDT}QuantityValue",
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        properties=(_NUMERIC_VALUE, _HAS_UNIT),
    )

    numeric_value: Lit[float] = Lit(_NUMERIC_VALUE)
    has_unit: TermOne[TermValue] = TermOne(_HAS_UNIT)

    def __init__(
        self,
        name: str | None = None,
        *,
        numeric_value: float,
        has_unit: TermValue,
        label: str | None = None,
        comment: str | None = None,
        model: Model | None = None,
    ) -> None:
        super().__init__(
            name,
            label=label,
            comment=comment,
            model=model,
            numeric_value=numeric_value,
            has_unit=has_unit,
        )


def quantity(
    property_class: type[PropertyT],
    name: str,
    value: float,
    unit: TermValue,
    quantity_kind: TermValue,
    *,
    of: Entity | ConnectionHandle | PortHandle | None = None,
    datatype: str | None = None,
    **properties: Any,
) -> PropertyT:
    """Instantiate an S223 property with a fixed scalar value and QUDT context.

    ``property_class`` remains explicit because the ontology, not this helper,
    determines whether the property is observable, actuatable, or static.
    """
    if not unit.is_instance_of(f"{QUDT}Unit"):
        raise TypeError(f"unit must be a QUDT Unit term, got {unit!r}")
    if not quantity_kind.is_instance_of(f"{QUDT}QuantityKind"):
        raise TypeError(
            "quantity_kind must be a QUDT QuantityKind term, "
            f"got {quantity_kind!r}"
        )
    model = (
        (of.meta.model if isinstance(of, Entity) else of._model)
        if of is not None
        else properties.get("model")
    )
    properties.setdefault("model", model)
    constructor: Any = property_class
    prop = constructor(
        name,
        has_quantity_kind=quantity_kind,
        has_unit=unit,
        has_value=value,
        **properties,
    )
    if datatype is not None:
        from rdflib import Literal, URIRef

        prop._data["has_value"] = Literal(value, datatype=URIRef(datatype))
        prop.meta.model._touch(prop)
    if of is not None:
        if isinstance(of, PortHandle):
            of._properties.append(prop)
            of._model._touch(of.owner)
        else:
            getattr(of, "has_property").add(prop)
    return cast(PropertyT, prop)


def _attached_quantity(
    target: Entity | PortHandle | ConnectionHandle,
    name: str,
    value: float | QuantityAmount,
    *,
    unit: TermValue | None,
    kind: TermValue,
    capability: Literal["static", "observable", "actuatable"] = "static",
    mode: Literal["nominal", "observable", "actuatable"] | None = None,
    label: str | None = None,
    **properties: Any,
) -> Entity:
    """Shared scalar construction for concrete and deferred subjects."""
    from objectrdf.core.property_schema import QuantityDefinition

    if mode is not None and capability != "static":
        raise ValueError("use capability or legacy mode, not both")
    if isinstance(value, QuantityAmount):
        if unit is not None and unit.iri != value.unit.iri:
            raise ValueError("explicit amount and unit argument disagree")
        unit = value.unit
    if unit is None:
        raise TypeError("supply unit= or a QuantityAmount")
    definition = QuantityDefinition(name, "scalar quantity", kind, unit)
    number, selected_unit = definition.unpack(value)
    if isinstance(target, Entity):
        registry = target.meta.registry
        model = target.meta.model
    elif isinstance(target, PortHandle):
        registry = target.owner.meta.registry
        model = target._model
    else:
        registry = target._connection_type().meta.registry
        model = target._model
    if mode == "nominal" and "has_aspect" not in properties:
        properties["has_aspect"] = [registry.resolve_enum(
            "http://data.ashrae.org/standard223#Aspect-Nominal"
        )]
    with model._atomic():
        return quantity(
            _quantity_class(registry, mode or capability), name, number,
            selected_unit, kind, of=target, label=label, **properties,
        )


@dataclass(frozen=True)
class StreamState:
    """Ergonomic view that attaches nominal properties to a flow entity.

    This is deliberately not an RDF class: S223/WaTr currently provide the
    property/medium pattern, but no standard stream-state or operating-point
    class with time/scenario identity.
    """

    subject: Entity | ConnectionHandle
    medium: Any

    def quantity(
        self,
        property_class: type[PropertyT],
        name: str,
        value: float,
        unit: TermValue,
        quantity_kind: TermValue,
        *,
        substance: Any = None,
        **properties: Any,
    ) -> PropertyT:
        """Attach one medium- or substance-qualified quantity to the flow."""
        properties.setdefault("of_medium", self.medium)
        if substance is not None:
            properties.setdefault("of_substance", substance)
        return quantity(
            property_class,
            name,
            value,
            unit,
            quantity_kind,
            of=self.subject,
            **properties,
        )


def stream_state(
    subject: Entity | ConnectionHandle,
    *,
    medium: Any,
) -> StreamState:
    """Create a non-RDF authoring view for nominal properties of ``subject``."""
    return StreamState(subject, medium)


__all__ = [
    "ONTOLOGY",
    "QuantityValue",
    "QuantityAmount",
    "StreamState",
    "quantity",
    "quantity_kinds",
    "stream_state",
    "units",
]
