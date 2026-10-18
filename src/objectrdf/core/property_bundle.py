"""Reusable templates for properties attached to equipment or ports."""

from __future__ import annotations

from builtins import property as builtin_property
from dataclasses import dataclass, field, replace
from inspect import cleandoc
from typing import Any, Literal, Mapping, Self

from .entity import Entity
from .resolution import PortHandle
from .terms import TermValue

QuantityMode = Literal["nominal", "observable", "actuatable"]


@dataclass(frozen=True)
class _QuantityEntry:
    name: str
    value: float | None
    unit: TermValue
    kind: TermValue
    mode: QuantityMode
    label: str | None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _PropertyEntry:
    name: str
    property_class: type[Entity]
    label: str | None
    properties: dict[str, Any] = field(default_factory=dict)


class PropertyBundle:
    """Reusable property definitions; each application creates new entities.

    Bundle entries are Python authoring templates, not RDF resources. Entry
    names are local to the bundle. Applying a bundle prefixes them with the
    target name by default, so the same bundle can be used on many targets.
    ``name`` and ``doc`` describe the template in Python; ``describe()`` also
    lists its entries. This documentation is not serialized into the model.
    """

    def __init__(self, name: str | None = None, *, doc: str | None = None) -> None:
        self.name = name
        self.documentation = cleandoc(doc) if doc else None
        if self.documentation is not None:
            self.__doc__ = self.documentation
        self._entries: list[_QuantityEntry | _PropertyEntry] = []
        self._bound = False

    def quantity(
        self,
        name: str,
        value: float | None = None,
        *,
        unit: TermValue,
        kind: TermValue,
        mode: QuantityMode = "nominal",
        label: str | None = None,
        **properties: Any,
    ) -> Self:
        """Add a quantity using the target's S223 property class.

        Omit ``value`` to supply it when calling the bundle later.
        """
        self._assert_editable()
        self._check_name(name)
        self._entries.append(
            _QuantityEntry(name, value, unit, kind, mode, label, dict(properties))
        )
        return self

    def property(
        self,
        name: str,
        property_class: type[Entity],
        *,
        label: str | None = None,
        **properties: Any,
    ) -> Self:
        """Add a generated ontology property class with constructor fields."""
        self._assert_editable()
        self._check_name(name)
        if not issubclass(property_class, Entity):
            raise TypeError("property_class must be an Entity subclass")
        self._entries.append(
            _PropertyEntry(name, property_class, label, dict(properties))
        )
        return self

    @builtin_property
    def parameters(self) -> tuple[str, ...]:
        """Names of quantities whose values must be supplied before application."""
        return tuple(
            entry.name.replace("-", "_")
            for entry in self._entries
            if isinstance(entry, _QuantityEntry) and entry.value is None
        )

    def __call__(self, *args: float, **values: float) -> PropertyBundle:
        """Bind quantity values and return an application-ready bundle.

        One unset quantity may be supplied positionally. For several values,
        use each entry name with hyphens changed to underscores as a keyword.
        Fixed quantity values may also be overridden by keyword.
        """
        self._assert_editable()
        quantities = [
            entry for entry in self._entries if isinstance(entry, _QuantityEntry)
        ]
        aliases = {entry.name.replace("-", "_"): entry.name for entry in quantities}
        if len(aliases) != len(quantities):
            raise ValueError("bundle quantity names have ambiguous Python aliases")
        unknown = values.keys() - aliases.keys()
        if unknown:
            raise TypeError(f"unknown bundle parameters: {sorted(unknown)}")
        bound = {aliases[key]: value for key, value in values.items()}

        if args:
            unset = [entry for entry in quantities if entry.value is None]
            positional = (
                unset if len(unset) == 1 else quantities if len(quantities) == 1 else []
            )
            if len(args) != 1 or len(positional) != 1:
                raise TypeError(
                    "a positional value requires exactly one unset quantity "
                    "or a bundle with just one quantity"
                )
            name = positional[0].name
            if name in bound:
                raise TypeError(f"multiple values for {name!r}")
            bound[name] = args[0]

        missing = [
            entry.name.replace("-", "_")
            for entry in quantities
            if entry.value is None and entry.name not in bound
        ]
        if missing:
            raise TypeError(f"missing bundle parameters: {missing}")

        application = PropertyBundle(self.name, doc=self.documentation)
        application._entries = [
            replace(
                entry,
                value=bound.get(entry.name, entry.value),
                properties=dict(entry.properties),
            )
            if isinstance(entry, _QuantityEntry)
            else replace(entry, properties=dict(entry.properties))
            for entry in self._entries
        ]
        application._bound = True
        return application

    def describe(self) -> str:
        """Summarize the bundle's documentation, quantities, and property types."""
        lines = [self.name or "Property bundle"]
        if self.documentation:
            lines.append(self.documentation)
        for entry in self._entries:
            if isinstance(entry, _QuantityEntry):
                value = (
                    f"required: {entry.name.replace('-', '_')}"
                    if entry.value is None
                    else str(entry.value)
                )
                kind = entry.kind.label or entry.kind.iri
                unit = entry.unit.label or entry.unit.iri
                details = [value, f"{kind} [{unit}]"]
                for key in ("of_substance", "of_medium"):
                    term = entry.properties.get(key)
                    if term is not None:
                        details.append(f"{key}={getattr(term, 'label', None) or term}")
                if entry.label:
                    details.append(entry.label)
                lines.append(f"- {entry.name}: {'; '.join(details)}")
            else:
                fields = ", ".join(
                    f"{name}={value!r}" for name, value in entry.properties.items()
                )
                summary = entry.property_class.__name__
                if fields:
                    summary += f" ({fields})"
                if entry.label:
                    summary += f"; {entry.label}"
                lines.append(f"- {entry.name}: {summary}")
        return "\n".join(lines)

    def apply(
        self,
        target: Entity | PortHandle,
        *,
        prefix: str | None = None,
        values: Mapping[str, float] | None = None,
    ) -> dict[str, Entity]:
        """Create and attach fresh properties; return them by bundle name.

        A deferred port stages the properties on its eventual concrete point.
        Use a different ``prefix`` when applying a bundle twice to one target.
        ``values`` can fill or override quantity values by local bundle name.
        """
        if isinstance(target, Entity):
            if not hasattr(target, "has_property"):
                raise TypeError(f"{type(target).__name__} has no has_property relation")
            model = target.meta.model
        elif isinstance(target, PortHandle):
            model = target._model
        else:
            raise TypeError("target must be an Entity or PortHandle")

        model._assert_mutable()
        overrides = dict(values or {})
        quantity_names = {
            entry.name for entry in self._entries if isinstance(entry, _QuantityEntry)
        }
        unknown = overrides.keys() - quantity_names
        if unknown:
            raise ValueError(f"unknown bundle quantities: {sorted(unknown)}")
        missing = {
            entry.name
            for entry in self._entries
            if isinstance(entry, _QuantityEntry)
            and entry.value is None
            and overrides.get(entry.name) is None
        }
        if missing:
            raise ValueError(f"missing bundle quantity values: {sorted(missing)}")
        stem = target.name if prefix is None else prefix
        names = [f"{stem}-{entry.name}" for entry in self._entries]
        if len(names) != len(set(names)) or any(
            name in model._by_name or name in model._reserved_names for name in names
        ):
            raise ValueError("property bundle would create duplicate model names")

        created: dict[str, Entity] = {}
        for entry, name in zip(self._entries, names, strict=True):
            if isinstance(entry, _QuantityEntry):
                value = overrides.get(entry.name, entry.value)
                if value is None:
                    raise ValueError(f"missing value for {entry.name!r}")
                prop = target.quantity(
                    name,
                    value,
                    unit=entry.unit,
                    kind=entry.kind,
                    mode=entry.mode,
                    label=entry.label,
                    **entry.properties,
                )
            else:
                prop = entry.property_class(
                    name,
                    model=model,
                    label=entry.label,
                    **entry.properties,
                )
                if isinstance(target, PortHandle):
                    target._properties.append(prop)
                    model._touch(target.owner)
                else:
                    getattr(target, "has_property").add(prop)
            created[entry.name] = prop
        return created

    def _check_name(self, name: str) -> None:
        if not name:
            raise ValueError("bundle property name must not be empty")
        if any(entry.name == name for entry in self._entries):
            raise ValueError(f"bundle already contains {name!r}")

    def _assert_editable(self) -> None:
        if self._bound:
            raise TypeError("a bound property bundle cannot be edited")
