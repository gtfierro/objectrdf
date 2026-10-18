"""Constructive SHACL value constraints shared by generated configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from collections.abc import Iterable

from .errors import ModelingError

if TYPE_CHECKING:
    from .entity import Entity


@dataclass(frozen=True)
class ShapeValues:
    """Required members, defaults, choices, and cardinality for one predicate."""

    name: str
    source_shape: str
    required: tuple[Any, ...] = ()
    defaults: tuple[Any, ...] = ()
    choices: tuple[Any, ...] = ()
    minimum: int = 0
    maximum: int | None = None


def constraints(cls: type[Entity]) -> tuple[ShapeValues, ...]:
    return tuple(
        item
        for base in reversed(cls.__mro__)
        for item in base.__dict__.get("_shape_constraints", ())
    )


def initial_values(entity: Entity, supplied: dict[str, Any]) -> dict[str, Any]:
    values = dict(supplied)
    specs = entity._effective_specs()
    inherited = constraints(type(entity))
    for item in inherited:
        if supplied.get(item.name) is None and item.defaults:
            values[item.name] = item.defaults
    for item in inherited:
        spec = specs[item.name]
        many = spec.kind in {"object", "class", "enum"} and spec.max_count != 1
        current = values.get(item.name)
        if current is None:
            current = ()
        if many:
            current = list(current or ())
            for required in item.required:
                if required not in current:
                    current.append(required)
        else:
            if isinstance(current, tuple):
                current = current[0] if current else None
            if current is None and item.required:
                current = item.required[0]
        if current is not None:
            values[item.name] = current
    return values


def check_values(entity: Entity, name: str, value: object) -> None:
    specs = entity._effective_specs()
    spec = specs.get(name)
    if spec is None:
        return
    many = spec.kind in {"object", "class", "enum"} and spec.max_count != 1
    values = (
        list(cast(Iterable[object], value))
        if many
        else ([] if value is None else [value])
    )
    for item in constraints(type(entity)):
        if item.name != name:
            continue
        if any(required not in values for required in item.required):
            raise ModelingError(
                f"{entity.name}.{name}: missing sh:hasValue member ({item.source_shape})"
            )
        if item.choices and any(value not in item.choices for value in values):
            raise ModelingError(
                f"{entity.name}.{name}: value is outside sh:in ({item.source_shape})"
            )
        if len(values) < item.minimum or (
            item.maximum is not None and len(values) > item.maximum
        ):
            raise ModelingError(
                f"{entity.name}.{name}: violates shape cardinality ({item.source_shape})"
            )
