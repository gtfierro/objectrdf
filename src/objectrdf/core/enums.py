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

from typing import TextIO


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

    def tree_text(
        self,
        *,
        max_depth: int | None = None,
        show_iris: bool = False,
    ) -> str:
        """Return a deterministic text tree rooted at this value.

        ``max_depth=0`` shows only this value (and an ellipsis when it has
        children); the default walks every descendant. Set ``show_iris`` to
        display full RDF identifiers instead of ontology-local names.
        """
        if max_depth is not None and (
            isinstance(max_depth, bool) or max_depth < 0
        ):
            raise ValueError("max_depth must be a non-negative integer or None")

        def display(node: EnumValue) -> str:
            return node.iri if show_iris else _local(node.iri)

        lines = [display(self)]

        def walk(node: EnumValue, prefix: str, depth: int) -> None:
            children = sorted(
                node._children.values(),
                key=lambda item: (_local(item.iri), item.iri),
            )
            if max_depth is not None and depth >= max_depth:
                if children:
                    lines.append(f"{prefix}└── …")
                return
            for index, child in enumerate(children):
                last = index == len(children) - 1
                branch = "└── " if last else "├── "
                lines.append(f"{prefix}{branch}{display(child)}")
                walk(child, prefix + ("    " if last else "│   "), depth + 1)

        walk(self, "", 0)
        return "\n".join(lines)

    def tree(
        self,
        *,
        max_depth: int | None = None,
        show_iris: bool = False,
        file: TextIO | None = None,
    ) -> None:
        """Print the hierarchy rooted at this value."""
        print(
            self.tree_text(max_depth=max_depth, show_iris=show_iris),
            file=file,
        )

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
