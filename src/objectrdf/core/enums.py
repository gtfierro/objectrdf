"""Enumeration constants generated from punned ontology hierarchies.

223P models enumerations (media, roles, aspects, ...) as a class hierarchy
under ``s223:EnumerationKind`` where every member is simultaneously a class
and an individual. In Python they become :class:`EnumValue` constants — not
Entity subclasses — because users *reference* them, never instantiate them:

    from objectrdf.s223.enums import Fluid_Air, Water_ChilledWater
    Water_ChilledWater.is_a(Fluid_Water)   # hierarchy-aware -> True

The generated ``enums`` module holds one flat constant per member (named
after the ontology local name, ``Fluid-Air`` -> ``Fluid_Air``). Each value
also exposes its children as attributes (``EnumerationKind.Substance...``)
for exploratory use; the flat names are the primary, statically-typed API.
"""

from __future__ import annotations


class EnumValue:
    """One enumeration member (a punned class/individual in the ontology)."""

    __slots__ = ("iri", "label", "definition", "parent", "_children")

    def __init__(
        self,
        iri: str,
        *,
        label: str | None = None,
        definition: str | None = None,
        parent: EnumValue | None = None,
    ) -> None:
        self.iri = iri
        self.label = label
        self.definition = definition
        self.parent = parent
        self._children: dict[str, EnumValue] = {}
        if parent is not None:
            parent._children[_segment(iri)] = self

    def is_a(self, other: EnumValue) -> bool:
        """True if this value is ``other`` or a descendant of it."""
        node: EnumValue | None = self
        while node is not None:
            if node.iri == other.iri:
                return True
            node = node.parent
        return False

    def __getattr__(self, name: str) -> EnumValue:
        try:
            return self._children[name]
        except KeyError:
            raise AttributeError(
                f"{self!r} has no member {name!r} "
                f"(children: {sorted(self._children) or 'none'})"
            ) from None

    def __repr__(self) -> str:
        return f"<enum {_local(self.iri)}>"


def _local(iri: str) -> str:
    for sep in ("#", "/"):
        if sep in iri:
            return iri.rsplit(sep, 1)[1]
    return iri


def _segment(iri: str) -> str:
    """Attribute name for hierarchical child access.

    223 locals repeat the parent as a prefix (``Fluid-Air``); the child
    segment is what follows the dash, sanitized to an identifier.
    """
    local = _local(iri)
    segment = local.split("-", 1)[1] if "-" in local else local
    return "".join(c if c.isalnum() or c == "_" else "_" for c in segment)
