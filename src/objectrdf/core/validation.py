"""SHACL validation (via shifty), reported in Python terms.

The report translator does one job: turn a standard SHACL validation report
graph into :class:`Issue` objects that name *entities and attributes*, not
focus nodes and IRIs. Users should be able to read an issue and know which
line of their authoring script to fix.

shifty also exposes a structured result API (``validate_algebra``); we use
the W3C-report path for now because its vocabulary is stable, and revisit
once the structured API covers result paths end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import rdflib
from rdflib import RDF
from rdflib.namespace import SH

if TYPE_CHECKING:
    from .entity import Entity
    from .model import Model


@dataclass(frozen=True)
class Issue:
    """One validation result, mapped back to the authoring layer."""

    severity: str
    """``violation`` | ``warning`` | ``info``."""

    message: str
    """Human-readable description (SHACL ``resultMessage``)."""

    entity: Entity | None
    """The entity the result focuses on, when it maps to one."""

    focus: str | None
    """The raw focus node IRI (useful when ``entity`` is None)."""

    path: str | None
    """The offending property path (IRI), if reported."""

    def __str__(self) -> str:
        where = (
            f"{self.entity.name} ({type(self.entity).__name__})"
            if self.entity is not None
            else self.focus or "<model>"
        )
        prop = f" [{_local(self.path)}]" if self.path else ""
        return f"{self.severity}: {where}{prop}: {self.message}"


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of :meth:`Model.validate`.

    Truthy when there are no *violations*; warnings/infos (223 uses info
    severity for advisory notices like dangling boundary connection points)
    are listed in ``issues`` but don't fail the model.
    """

    ok: bool
    issues: tuple[Issue, ...]

    @property
    def violations(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == "violation")

    def __bool__(self) -> bool:
        return self.ok

    def __str__(self) -> str:
        if not self.issues:
            return "conforms"
        return "\n".join(str(issue) for issue in self.issues)


def validate_model(
    model: Model, shapes: object = None, *, infer: bool = True
) -> ValidationReport:
    """Run shifty over the model's graph and map results to entities.

    ``shapes`` may be an rdflib Graph, a Turtle file path/URL, or None; with
    None, the ontology sources of the generated packages present in the model
    are used (each package's Registry knows its ontology's source).
    """
    import shifty

    shapes_graph = _resolve_shapes(model, shapes)
    snapshot = model.resolve()
    conforms, report, _text = shifty.validate(snapshot.graph(), shapes_graph, infer=infer)
    issues = tuple(_issues_from_report(model, report, fallback=snapshot._model))
    ok = bool(conforms) or not any(i.severity == "violation" for i in issues)
    return ValidationReport(ok=ok, issues=issues)


def _resolve_shapes(model: Model, shapes: object) -> rdflib.Graph:
    """Normalize the ``shapes`` argument to an rdflib Graph."""
    if isinstance(shapes, rdflib.Graph):
        return shapes
    if isinstance(shapes, (str, Path)):
        g = rdflib.Graph()
        g.parse(str(shapes))
        return g
    if shapes is None:
        return _package_shapes(model)
    raise TypeError(
        f"shapes must be a Graph, path/URL, or None; got {type(shapes).__name__}"
    )


def _package_shapes(model: Model) -> rdflib.Graph:
    """Collect shapes from the ontology sources of the packages in use.

    Each generated package records where its ontology was loaded from
    (``OntologyInfo.source``); we parse the union of the distinct sources.
    """
    package_files: set[Path] = set()
    sources: set[str] = set()
    for entity in model.entities:
        module = sys.modules.get(type(entity).__module__)
        module_file = getattr(module, "__file__", None)
        bundled = Path(module_file).with_name("_shapes.ttl") if module_file else None
        if bundled is not None and bundled.exists():
            package_files.add(bundled)
            continue
        source = entity._classinfo_effective().ontology.source
        if source is not None:
            sources.add(source)
    if not package_files and not sources:
        raise ValueError(
            "no shapes given and no generated package in this model "
            "records an ontology source; pass shapes= explicitly"
        )
    g = rdflib.Graph()
    for package_file in package_files:
        g.parse(package_file)
    for source in sources:
        g.parse(source)
    return g


def _issues_from_report(
    model: Model, report: rdflib.Graph, *, fallback: Model | None = None
):
    """Yield an Issue per ``sh:ValidationResult`` in a report graph."""
    for result in report.subjects(RDF.type, SH.ValidationResult):
        focus = report.value(result, SH.focusNode)
        severity = report.value(result, SH.resultSeverity)
        path = report.value(result, SH.resultPath)
        messages = [str(m) for m in report.objects(result, SH.resultMessage)]
        focus_iri = str(focus) if focus is not None else None
        entity = model._by_iri.get(focus_iri) if focus_iri else None
        if entity is None and focus_iri and fallback is not None:
            entity = fallback._by_iri.get(focus_iri)
        yield Issue(
            severity=_local(str(severity)).lower() if severity else "violation",
            message="; ".join(messages) or "constraint violated",
            entity=entity,
            focus=focus_iri,
            path=str(path) if path is not None else None,
        )


def _local(iri: str | None) -> str:
    """Local name of an IRI, for compact display."""
    if iri is None:
        return ""
    for sep in ("#", "/"):
        if sep in iri:
            return iri.rsplit(sep, 1)[1]
    return iri
