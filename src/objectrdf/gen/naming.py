"""Naming policy: ontology terms -> Python identifiers.

Deterministic and documented, because generated names are user-facing API:

- classes keep their IRI local name, sanitized to a valid identifier
  (Brick's ``Air_Handling_Unit`` style survives unchanged);
- properties are the local name converted camelCase -> snake_case
  (``hasPoint`` -> ``has_point``);
- names colliding with reserved Entity API (``name``, ``type``, ``label``,
  ``comment``, ``meta``, ``model``, ``contains``, ``ports``,
  ``describe_ports``) or Python keywords get a
  trailing ``_``;
- two terms mapping to the same Python name are disambiguated by suffixing
  ``_2``, ``_3``, ... in sorted-IRI order (stable across runs).
"""

from __future__ import annotations

import keyword
import re

#: Attribute/method names owned by the Entity base class.
RESERVED = frozenset(
    {
        "name", "type", "label", "comment", "meta", "model", "contains",
        "ports", "describe_ports",
        "apply_properties", "quantity", "apply_property_block", "boundary", "port",
    }
) | frozenset(keyword.kwlist)

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_INVALID = re.compile(r"[^0-9A-Za-z_]")

# Python-facing names for the S223 point properties most commonly used by
# equipment authors. Keep this mapping IRI-scoped so unrelated ontologies
# such as Brick retain their established property names.
_S223_POINT_NAMES = {
    "http://data.ashrae.org/standard223#hasMedium": "medium",
    "http://data.ashrae.org/standard223#isConnectionPointOf": "owner",
    "http://data.ashrae.org/standard223#connectsThrough": "connection",
    "http://data.ashrae.org/standard223#pairedConnectionPoint": "paired_with",
}
_LEGACY_S223_POINT_NAMES = {
    "medium": "has_medium",
    "owner": "is_connection_point_of",
    "connection": "connects_through",
    "paired_with": "paired_connection_point",
}


def local_name(iri: str) -> str:
    """The fragment/last path segment of an IRI."""
    for sep in ("#", "/"):
        if sep in iri:
            candidate = iri.rsplit(sep, 1)[1]
            if candidate:
                return candidate
    return iri


def class_name(iri: str) -> str:
    """Python class name for an ontology class IRI."""
    return _sanitize(local_name(iri))


def property_name(iri: str) -> str:
    """Python attribute name for an ontology property IRI."""
    if iri in _S223_POINT_NAMES:
        return _S223_POINT_NAMES[iri]
    snake = _CAMEL_BOUNDARY.sub("_", local_name(iri)).lower()
    return _sanitize(snake)


def legacy_property_name(iri: str) -> str | None:
    """Return a temporary compatibility name for a canonicalized predicate."""
    if iri not in _S223_POINT_NAMES:
        return None
    return _LEGACY_S223_POINT_NAMES[_S223_POINT_NAMES[iri]]


def _sanitize(name: str) -> str:
    """Make a valid, non-reserved Python identifier."""
    name = _INVALID.sub("_", name)
    if name[:1].isdigit():
        name = "_" + name
    if name in RESERVED:
        name += "_"
    return name


def disambiguate(
    assignments: dict[str, str], *, preferred_namespace: str | None = None
) -> dict[str, str]:
    """Resolve name collisions across a set of IRIs.

    ``assignments`` maps IRI -> desired Python name. Returns IRI -> final
    name, where every duplicate group keeps the name for its sorted-first
    IRI and suffixes ``_2``, ``_3``, ... onto the rest.
    """
    by_name: dict[str, list[str]] = {}
    for iri in sorted(assignments):
        by_name.setdefault(assignments[iri], []).append(iri)
    final: dict[str, str] = {}
    for name, iris in by_name.items():
        ordered = sorted(
            iris,
            key=lambda iri: (
                not (
                    preferred_namespace is not None
                    and iri.startswith(preferred_namespace)
                ),
                iri,
            ),
        )
        for index, iri in enumerate(ordered):
            final[iri] = name if index == 0 else f"{name}_{index + 1}"
    return final
