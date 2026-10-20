"""QUDT-backed quantities and compiled unit/quantity-kind vocabularies."""

from __future__ import annotations

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
REGISTRY = _REGISTRY
PropertyT = TypeVar("PropertyT", bound=Entity)
PropertyCapability = Literal["static", "observable", "actuatable"]


def _quantity_class(registry: Registry, capability: PropertyCapability) -> type[Entity]:
    class_names = {
        "static": "QuantifiableProperty",
        "observable": "QuantifiableObservableProperty",
        "actuatable": "QuantifiableActuatableProperty",
    }
    try:
        class_name = class_names[capability]
    except KeyError:
        raise ValueError(f"unknown property capability {capability!r}") from None
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


def _create_quantity(
    property_class: type[PropertyT],
    name: str,
    value: float | None,
    unit: TermValue,
    quantity_kind: TermValue,
    *,
    of: Entity | ConnectionHandle | PortHandle | None = None,
    datatype: str | None = None,
    **properties: Any,
) -> PropertyT:
    """Instantiate an S223 property with a scalar value and QUDT context.

    ``value`` may be None for an observed or actuated property whose value
    lives outside the model.

    ``property_class`` remains explicit because the ontology, not this helper,
    determines whether the property is observable, actuatable, or static.
    """
    if not unit.is_instance_of(f"{QUDT}Unit"):
        raise TypeError(f"unit must be a QUDT Unit term, got {unit!r}")
    if not quantity_kind.is_instance_of(f"{QUDT}QuantityKind"):
        raise TypeError(
            f"quantity_kind must be a QUDT QuantityKind term, got {quantity_kind!r}"
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
    if datatype is not None and value is not None:
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
    label: str | None = None,
    **properties: Any,
) -> Entity:
    """Shared scalar construction for concrete and deferred subjects."""
    from objectrdf.core.property_schema import QuantityDefinition

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
    with model._atomic():
        return _create_quantity(
            _quantity_class(registry, capability),
            name,
            number,
            selected_unit,
            kind,
            of=target,
            label=label,
            **properties,
        )


_SENSOR = "http://data.ashrae.org/standard223#Sensor"
_LOCATIONS = tuple(
    f"http://data.ashrae.org/standard223#{name}"
    for name in ("Connectable", "Connection", "ConnectionPoint")
)


def _attached_sensor(
    target: Entity | PortHandle | ConnectionHandle,
    name: str,
    *,
    kind: TermValue,
    unit: TermValue | None = None,
    sensor_class: type[Entity] | None = None,
    value: float | QuantityAmount | None = None,
    label: str | None = None,
    **properties: Any,
) -> Entity:
    """Create an observed quantity on ``target`` and a sensor observing it.

    The sensor is named ``name`` and observes ``<name>-value``. Without
    ``sensor_class``, the package's quantity-kind table picks the most
    specific sensor class, falling back to ``Sensor``.
    """
    from objectrdf.core.property_schema import QuantityDefinition

    if isinstance(target, Entity):
        registry, model = target.meta.registry, target.meta.model
        if not any(
            (cls := registry.by_iri.get(iri)) is not None and isinstance(target, cls)
            for iri in _LOCATIONS
        ):
            raise TypeError(
                f"{target.type} cannot be a sensor's observation location; use "
                "equipment, a connection, or a connection point"
            )
    elif isinstance(target, PortHandle):
        registry, model = target.owner.meta.registry, target._model
    else:
        registry, model = target._connection_type().meta.registry, target._model
    base = registry.by_iri.get(_SENSOR)
    if base is None:
        raise TypeError(f"{registry.ontology.name} has no Sensor class")
    if sensor_class is None:
        chosen = registry.sensor_classes.get(kind.iri)
        sensor_class = registry.resolve(chosen) if chosen is not None else base
    elif not (isinstance(sensor_class, type) and issubclass(sensor_class, base)):
        raise TypeError(f"sensor_class must be a Sensor subclass, got {sensor_class!r}")
    if isinstance(value, QuantityAmount):
        if unit is not None and unit.iri != value.unit.iri:
            raise ValueError("explicit amount and unit argument disagree")
        unit = value.unit
    if unit is None:
        raise TypeError("supply unit= or a QuantityAmount value")
    # Constructing the definition checks that the unit fits the kind.
    definition = QuantityDefinition(f"{name}-value", "sensor reading", kind, unit)
    number: float | None = None
    if value is not None:
        number, unit = definition.unpack(value)
    constructor: Any = sensor_class
    with model._atomic():
        observed = _create_quantity(
            _quantity_class(registry, "observable"),
            f"{name}-value",
            number,
            unit,
            kind,
            of=target,
            **properties,
        )
        return constructor(
            name,
            has_observation_location=target,
            observes=observed,
            label=label,
            model=model,
        )


__all__ = [
    "ONTOLOGY",
    "REGISTRY",
    "QuantityValue",
    "QuantityAmount",
    "quantity_kinds",
    "units",
]
