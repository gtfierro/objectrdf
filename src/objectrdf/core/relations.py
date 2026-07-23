"""Typed descriptors that back generated attributes.

Three descriptor flavors cover the SHACL cardinality/kind matrix:

- :class:`Rel` — object property, unbounded: ``ahu.feeds`` is a
  :class:`RelSet` you ``.add()`` to.
- :class:`RelOne` — object property with ``maxCount 1``: plain attribute
  holding an entity or ``None``.
- :class:`Lit` — datatype property with ``maxCount 1``: plain attribute
  holding a Python literal or ``None``.

The descriptors carry a :class:`~objectrdf.core.meta.PropertySpec` and perform
runtime range checks that mirror what a static type checker enforces from the
generated annotations — so users who don't run a checker still get immediate,
readable errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Iterable, Iterator, TypeVar, overload

from .errors import RangeError
from .meta import PropertySpec

if TYPE_CHECKING:
    from .entity import Entity

T = TypeVar("T", bound="Entity")
#: Literal values are plain Python objects, not entities.
V = TypeVar("V")


class RelSet(Generic[T]):
    """Live, ordered, duplicate-free set of links from one entity.

    Obtained by accessing a :class:`Rel` attribute on an instance
    (``ahu.feeds``). Mutations write through to the model immediately and
    keep the inverse property (if one exists) in sync.
    """

    __slots__ = ("_owner", "_spec", "_items")

    def __init__(self, owner: Entity, spec: PropertySpec) -> None:
        self._owner = owner
        self._spec = spec
        self._items: list[T] = []

    def add(self, *items: T) -> None:
        """Link one or more target entities. Duplicates are ignored."""
        self._owner._model._assert_mutable()
        changed = False
        for item in items:
            self._owner._check_range(self._spec, item)
            if item in self._items:
                continue
            self._items.append(item)
            _link_inverse(self._owner, self._spec, item)
            changed = True
        if changed:
            self._owner._model._touch(self._owner)

    def remove(self, item: T) -> None:
        """Unlink a target entity (and the mirrored inverse edge)."""
        self._owner._model._assert_mutable()
        self._items.remove(item)
        _unlink_inverse(self._owner, self._spec, item)
        self._owner._model._touch(self._owner)

    def clear(self) -> None:
        """Unlink everything."""
        for item in list(self._items):
            self.remove(item)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def __repr__(self) -> str:
        return f"RelSet({self._spec.name}={list(self._items)!r})"


class Rel(Generic[T]):
    """Descriptor for an unbounded object property.

    Generated code declares ``feeds: Rel[Equipment] = Rel(_P_feeds)``; the
    annotation gives type checkers ``RelSet[Equipment]`` on read and
    ``Iterable[Equipment]`` on assignment.
    """

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:  # pragma: no cover - generator invariant
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> Rel[T]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> RelSet[T]: ...

    def __get__(self, obj: Entity | None, owner: type) -> Rel[T] | RelSet[T]:
        if obj is None:
            return self
        return obj._store_for(self.spec)

    def __set__(self, obj: Entity, value: Iterable[T]) -> None:
        """Replace the full contents (used by constructor kwargs)."""
        store: RelSet[T] = obj._store_for(self.spec)
        store.clear()
        store.add(*value)


class RelOne(Generic[T]):
    """Descriptor for an object property with ``maxCount 1``."""

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:  # pragma: no cover - generator invariant
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> RelOne[T]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> T | None: ...

    def __get__(self, obj: Entity | None, owner: type) -> RelOne[T] | T | None:
        if obj is None:
            return self
        return obj._data.get(self.spec.name)

    def __set__(self, obj: Entity, value: T | None) -> None:
        obj._model._assert_mutable()
        if value is not None:
            obj._check_range(self.spec, value)
        previous = obj._data.get(self.spec.name)
        if previous is not None:
            _unlink_inverse(obj, self.spec, previous)
        obj._data[self.spec.name] = value
        if value is not None:
            _link_inverse(obj, self.spec, value)
        obj._model._touch(obj)


class TermOne(Generic[V]):
    """Descriptor for a scalar link to a compiled vocabulary individual."""

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> TermOne[V]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> V | None: ...

    def __get__(self, obj: Entity | None, owner: type) -> TermOne[V] | V | None:
        if obj is None:
            return self
        return obj._data.get(self.spec.name)

    def __set__(self, obj: Entity, value: V | None) -> None:
        from .terms import TermValue

        obj._model._assert_mutable()
        if value is not None and not isinstance(value, TermValue):
            raise RangeError(
                f"{type(obj).__name__}.{self.spec.name} expects a compiled "
                f"vocabulary term, got {type(value).__name__} ({value!r})"
            )
        if value is not None and self.spec.term_ranges and not any(
            value.is_instance_of(class_iri)
            for class_iri in self.spec.term_ranges
        ):
            allowed = " | ".join(self.spec.term_ranges)
            raise RangeError(
                f"{type(obj).__name__}.{self.spec.name} expects an instance "
                f"of {allowed}, got {value!r}"
            )
        obj._data[self.spec.name] = value
        obj._model._touch(obj)


class ValueOne(Generic[V]):
    """Descriptor for one unconstrained RDF value.

    S223 ``hasValue`` deliberately permits a simple literal as well as a
    named RDF resource.
    """

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> ValueOne[V]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> V | None: ...

    def __get__(self, obj: Entity | None, owner: type) -> ValueOne[V] | V | None:
        if obj is None:
            return self
        return obj._data.get(self.spec.name)

    def __set__(self, obj: Entity, value: V | None) -> None:
        obj._model._assert_mutable()
        obj._data[self.spec.name] = value
        obj._model._touch(obj)


class EnumOne(Generic[V]):
    """Descriptor for a scalar enum property (``maxCount 1``).

    Values are :class:`~objectrdf.core.enums.EnumValue` constants; the range
    check walks the enumeration hierarchy (a ``Water_ChilledWater`` is
    accepted wherever a ``Substance_Medium`` is required).
    """

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:  # pragma: no cover - generator invariant
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> EnumOne[V]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> V | None: ...

    def __get__(self, obj: Entity | None, owner: type) -> EnumOne[V] | V | None:
        if obj is None:
            return self
        return obj._data.get(self.spec.name)

    def __set__(self, obj: Entity, value: V | None) -> None:
        obj._model._assert_mutable()
        if value is not None:
            _check_enum(obj, self.spec, value)
        obj._data[self.spec.name] = value
        obj._model._touch(obj)


class EnumSet(Generic[V]):
    """Descriptor for a multi-valued enum property (e.g. 223 ``hasRole``).

    Reads as a plain list-valued attribute; assignment replaces contents.
    """

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:  # pragma: no cover - generator invariant
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> EnumSet[V]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> list[V]: ...

    def __get__(self, obj: Entity | None, owner: type) -> EnumSet[V] | list[V]:
        if obj is None:
            return self
        return obj._data.setdefault(self.spec.name, [])

    def __set__(self, obj: Entity, value: Iterable[V]) -> None:
        obj._model._assert_mutable()
        values = list(value)
        for item in values:
            _check_enum(obj, self.spec, item)
        obj._data[self.spec.name] = values
        obj._model._touch(obj)


def _check_enum(obj: Entity, spec: PropertySpec, value: object) -> None:
    """Runtime enum-range check: value must live under an allowed root."""
    from .enums import EnumValue, _local

    if not isinstance(value, EnumValue):
        raise RangeError(
            f"{type(obj).__name__}.{spec.name} expects an enum constant "
            f"(from the generated enums module), got {type(value).__name__} "
            f"({value!r})"
        )
    if not spec.enum_ranges:
        return
    registry = obj.meta.registry
    for root_iri in spec.enum_ranges:
        root = registry.enums_by_iri.get(root_iri)
        if root is not None and value.is_a(root):
            return
    allowed = " | ".join(_local(iri) for iri in spec.enum_ranges)
    raise RangeError(
        f"{type(obj).__name__}.{spec.name} expects {allowed} (or a "
        f"descendant), got {_local(value.iri)}"
    )


class Lit(Generic[V]):
    """Descriptor for a scalar datatype property (a Python literal)."""

    def __init__(self, spec: PropertySpec) -> None:
        self.spec = spec

    def __set_name__(self, owner: type, name: str) -> None:
        if name != self.spec.name:  # pragma: no cover - generator invariant
            raise TypeError(
                f"attribute {name!r} does not match spec name {self.spec.name!r}"
            )

    @overload
    def __get__(self, obj: None, owner: type) -> Lit[V]: ...
    @overload
    def __get__(self, obj: Entity, owner: type) -> V | None: ...

    def __get__(self, obj: Entity | None, owner: type) -> Lit[V] | V | None:
        if obj is None:
            return self
        return obj._data.get(self.spec.name)

    def __set__(self, obj: Entity, value: V | None) -> None:
        obj._model._assert_mutable()
        if value is not None and not _literal_ok(self.spec.datatype, value):
            raise RangeError(
                f"{type(obj).__name__}.{self.spec.name} expects "
                f"{self.spec.datatype.__name__ if self.spec.datatype else 'a literal'}, "
                f"got {type(value).__name__} ({value!r})"
            )
        obj._data[self.spec.name] = value
        obj._model._touch(obj)


def _literal_ok(datatype: type | None, value: object) -> bool:
    """Check a literal value against the spec's Python datatype.

    ``int`` is accepted where ``float`` is expected (but ``bool`` is not a
    number here, despite being an ``int`` subclass in Python).
    """
    if datatype is None:
        return True
    if datatype is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if datatype is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, datatype)


def _link_inverse(owner: Entity, spec: PropertySpec, target: Entity) -> None:
    """Mirror ``owner --spec--> target`` onto the target's inverse property.

    Writes into the target's store directly (not via ``add``/``__set__``) to
    avoid recursing back here. A scalar (RelOne) inverse is filled when
    empty; a conflicting existing value is an error rather than a silent
    overwrite (e.g. a ConnectionPoint can only belong to one Connectable).
    """
    if spec.inverse is None:
        return
    desc = getattr(type(target), spec.inverse, None)
    if isinstance(desc, Rel):
        store = target._store_for(desc.spec)
        if owner not in store._items:
            store._items.append(owner)
    elif isinstance(desc, RelOne):
        current = target._data.get(desc.spec.name)
        if current is None:
            target._data[desc.spec.name] = owner
        elif current is not owner:
            from .errors import ModelingError

            raise ModelingError(
                f"{target!r}.{desc.spec.name} is already {current!r}; "
                f"linking {owner!r}.{spec.name} would conflict "
                f"(remove the existing link first)"
            )


def _unlink_inverse(owner: Entity, spec: PropertySpec, target: Entity) -> None:
    """Remove the mirrored inverse edge, if present."""
    if spec.inverse is None:
        return
    desc = getattr(type(target), spec.inverse, None)
    if isinstance(desc, Rel):
        store = target._store_for(desc.spec)
        if owner in store._items:
            store._items.remove(owner)
    elif isinstance(desc, RelOne):
        if target._data.get(desc.spec.name) is owner:
            target._data[desc.spec.name] = None
