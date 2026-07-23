"""Deferred, finite-domain Z3 planner for S223 connection intentions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

import z3

from .core import (
    AmbiguousModelError,
    CPConstraint,
    CPSlot,
    PortHandle,
    ResolutionIssue,
    ResolutionExplanation,
    ResolutionReport,
    ResolvedModel,
    UnsatisfiableModelError,
)
from .core.relations import RelSet

if TYPE_CHECKING:
    from .connect223 import S223Connector
    from .core import ConnectionHandle, Entity, EnumValue, Model


@dataclass
class _Point:
    owner: Entity
    cls: type[Entity]
    name: str
    active: z3.BoolRef
    medium: z3.IntNumRef | z3.ArithRef
    existing: Entity | None = None
    authored: PortHandle | None = None


@dataclass(frozen=True)
class _PointResult:
    owner: Entity
    cls: type[Entity]
    name: str
    medium: EnumValue
    existing: Entity | None
    authored: PortHandle | None = None


@dataclass(frozen=True)
class _IntentResult:
    handle: ConnectionHandle
    source: _PointResult
    target: _PointResult
    medium: EnumValue
    connection_class: type[Entity]


@dataclass(frozen=True)
class _Plan:
    points: tuple[_PointResult, ...]
    intents: tuple[_IntentResult, ...]


@dataclass
class _ComponentResult:
    report: ResolutionReport
    plan: _Plan | None


def check_model(model: Model) -> ResolutionReport:
    """Check all deferred components without constructing a snapshot."""
    reports = [_solve_cached(model, handles).report for handles in _components(model)]
    if any(report.status == "unsatisfiable" for report in reports):
        issues = tuple(issue for report in reports for issue in report.issues)
        return ResolutionReport("unsatisfiable", issues)
    if any(report.status == "underconstrained" for report in reports):
        issues = tuple(issue for report in reports for issue in report.issues)
        return ResolutionReport("underconstrained", issues)
    return ResolutionReport("complete")


def resolve_model(model: Model) -> ResolvedModel:
    """Solve all components and build a frozen concrete snapshot."""
    plans: list[_Plan] = []
    for handles in _components(model):
        result = _solve_cached(model, handles)
        if result.report.status == "unsatisfiable":
            labels = tuple(
                label for issue in result.report.issues for label in issue.labels
            )
            raise UnsatisfiableModelError(
                "; ".join(issue.message for issue in result.report.issues),
                core=labels,
            )
        if result.report.status == "underconstrained":
            raise AmbiguousModelError(
                "; ".join(issue.message for issue in result.report.issues),
                alternatives=tuple(
                    issue.message for issue in result.report.issues
                ),
            )
        assert result.plan is not None
        plans.append(result.plan)
    return _materialize(model, plans)


def _solve_cached(model: Model, handles: list[ConnectionHandle]) -> _ComponentResult:
    """Reuse plans for unchanged sparse components across authored edits."""
    key = _component_key(handles)
    cached = model._component_cache.get(key)
    if cached is not None:
        return cached
    result = _solve_component(handles, materialize=True)
    # Bound stale plans retained during long interactive authoring sessions.
    if len(model._component_cache) >= 256:
        model._component_cache.pop(next(iter(model._component_cache)))
    model._component_cache[key] = result
    return result


def _component_key(handles: list[ConnectionHandle]) -> tuple[Any, ...]:
    """Fingerprint the authored facts that affect one solver component."""
    endpoints = {
        endpoint
        for handle in handles
        for endpoint in (_owner(handle.source), _owner(handle.target))
    }
    endpoint_facts: list[tuple[Any, ...]] = []
    for endpoint in sorted(endpoints, key=lambda entity: entity.name):
        points = []
        for point in getattr(endpoint, "has_connection_point"):
            medium = getattr(point, "has_medium")
            bound = getattr(point, "connects_through")
            points.append(
                (
                    point.name,
                    type(point).__name__,
                    medium.iri if medium is not None else None,
                    bound.name if bound is not None else None,
                )
            )
        for port in endpoint.meta.model._port_intents:
            if port.owner is endpoint:
                points.append(
                    (
                        port.name,
                        f"deferred-{port.direction}",
                        port.medium.iri if port.medium is not None else None,
                        port.paired_with.name if port.paired_with is not None else None,
                    )
                )
        endpoint_facts.append(
            (endpoint.name, type(endpoint).__name__, tuple(sorted(points)))
        )
    intent_facts = tuple(
        (
            handle.identifier,
            handle.source.name,
            handle.target.name,
            handle.medium.iri if handle.medium is not None else None,
            handle.connection_class.__name__
            if handle.connection_class is not None
            else None,
        )
        for handle in sorted(handles, key=lambda item: item.identifier)
    )
    return (intent_facts, tuple(endpoint_facts))


def _components(model: Model) -> list[list[ConnectionHandle]]:
    """Partition intentions by shared endpoint for sparse-model scaling."""
    handles = list(model._connection_intents)
    if not handles:
        return []
    parent: dict[Entity, Entity] = {}

    def find(entity: Entity) -> Entity:
        parent.setdefault(entity, entity)
        while parent[entity] is not entity:
            parent[entity] = parent[parent[entity]]
            entity = parent[entity]
        return entity

    def union(left: Entity, right: Entity) -> None:
        a, b = find(left), find(right)
        if a is not b:
            parent[b] = a

    for handle in handles:
        union(_owner(handle.source), _owner(handle.target))
    groups: dict[Entity, list[ConnectionHandle]] = {}
    for handle in handles:
        groups.setdefault(find(_owner(handle.source)), []).append(handle)
    return list(groups.values())


def _solve_component(
    handles: list[ConnectionHandle], *, materialize: bool
) -> _ComponentResult:
    entities = {
        _owner(endpoint)
        for h in handles
        for endpoint in (h.source, h.target)
    }
    connector = _owner(handles[0].source)._CONNECTOR
    assert connector is not None
    enum_values = _relevant_media(entities, handles)
    enum_ids = {value.iri: index for index, value in enumerate(enum_values)}
    by_id = {index: value for index, value in enumerate(enum_values)}
    solver = z3.Solver()
    points: list[_Point] = []
    labels: dict[str, str] = {}

    def tracked(expr: z3.BoolRef, label: str, message: str) -> None:
        token = z3.Bool(f"track_{len(labels)}")
        labels[token.decl().name()] = f"{label}: {message}"
        solver.assert_and_track(expr, token)

    incident: dict[Entity, dict[str, int]] = {
        entity: {
            "in": sum(_owner(h.target) is entity for h in handles),
            "out": sum(_owner(h.source) is entity for h in handles),
        }
        for entity in entities
    }
    for entity in sorted(entities, key=lambda item: item.name):
        entity_points = _make_points(entity, incident[entity], enum_values)
        points.extend(entity_points)
        for point in entity_points:
            solver.add(point.medium >= 0, point.medium < len(enum_values))
            roots = _point_roots(point)
            if roots:
                solver.add(
                    z3.Implies(
                        point.active,
                        _medium_in_roots(
                            point.medium, roots, enum_values, enum_ids
                        ),
                    )
                )
            if point.existing is not None:
                solver.add(point.active)
                existing_medium = getattr(point.existing, "has_medium")
                if existing_medium is not None and existing_medium.iri in enum_ids:
                    solver.add(point.medium == enum_ids[existing_medium.iri])
            if point.authored is not None and point.authored.medium is not None:
                solver.add(point.medium == enum_ids[point.authored.medium.iri])
        for slot_index, slot in enumerate(_all_slots(type(entity))):
            tracked(
                _slot_expr(entity_points, slot, enum_values, enum_ids),
                entity.name,
                f"required connection-point slot {slot_index}",
            )
        for constraint_index, constraint in enumerate(
            _all_constraints(type(entity))
        ):
            if _contains_opaque(constraint):
                continue
            tracked(
                _constraint_expr(
                    entity_points, constraint, enum_values, enum_ids
                ),
                entity.name,
                f"boolean connection layout {constraint_index}",
            )

    by_authored = {
        point.authored: point for point in points if point.authored is not None
    }
    by_existing = {
        point.existing: point for point in points if point.existing is not None
    }
    for point in points:
        paired = None
        if point.authored is not None:
            paired = point.authored.paired_with
            other = by_authored.get(paired)
        elif point.existing is not None:
            paired = getattr(point.existing, "paired_connection_point", None)
            other = by_existing.get(paired)
        else:
            other = None
        if paired is not None and other is not None:
            solver.add(point.medium == other.medium)

    point_selections: dict[tuple[int, int], z3.BoolRef] = {}
    intent_mediums: dict[int, z3.ArithRef] = {}
    for handle in handles:
        intent_medium = z3.Int(f"intent_{handle.identifier}_medium")
        intent_mediums[handle.identifier] = intent_medium
        solver.add(intent_medium >= 0, intent_medium < len(enum_values))
        if handle.medium is not None:
            tracked(
                intent_medium == enum_ids[handle.medium.iri],
                handle.name,
                f"explicit medium {handle.medium.iri.rsplit('#', 1)[-1]}",
            )
        source_candidates = _eligible(points, handle.source, "out")
        target_candidates = _eligible(points, handle.target, "in")
        for side, candidates in (("source", source_candidates), ("target", target_candidates)):
            choices: list[z3.BoolRef] = []
            for point in candidates:
                key = (handle.identifier, points.index(point))
                selected = z3.Bool(f"intent_{handle.identifier}_{side}_{len(choices)}")
                point_selections[key] = selected
                choices.append(selected)
                solver.add(z3.Implies(selected, point.active))
                solver.add(z3.Implies(selected, point.medium == intent_medium))
            tracked(
                z3.PbEq([(choice, 1) for choice in choices], 1)
                if choices
                else z3.BoolVal(False),
                handle.name,
                f"exactly one {side} connection point",
            )

    for index, point in enumerate(points):
        uses = [
            selected
            for (handle_id, point_index), selected in point_selections.items()
            if point_index == index
        ]
        bound = (
            point.existing is not None
            and getattr(point.existing, "connects_through") is not None
        )
        if uses:
            solver.add(z3.PbLe([(use, 1) for use in uses], 0 if bound else 1))

    if solver.check() == z3.unsat:
        core = tuple(str(item) for item in solver.unsat_core())
        messages = tuple(labels.get(item, item) for item in core)
        return _ComponentResult(
            ResolutionReport(
                "unsatisfiable",
                (ResolutionIssue("connection constraints are inconsistent", messages),),
            ),
            None,
        )

    _minimize_active(solver, points)
    _minimize_expression(
        solver,
        _medium_affinity_penalty(entities, points, enum_values, enum_ids),
    )
    assert solver.check() == z3.sat
    assignment = solver.model()
    observables = _observable_expressions(
        entities, points, handles, point_selections, intent_mediums
    )
    values = [assignment.eval(expr, model_completion=True) for expr in observables]
    solver.push()
    solver.add(z3.Or([expr != value for expr, value in zip(observables, values)]))
    ambiguous = solver.check() == z3.sat
    differences: tuple[str, ...] = ()
    if ambiguous:
        alternate = solver.model()
        differences = tuple(
            f"{expr}={value}/{alternate.eval(expr, model_completion=True)}"
            for expr, value in zip(observables, values)
            if not z3.is_true(
                z3.simplify(value == alternate.eval(expr, model_completion=True))
            )
        )
    solver.pop()
    if ambiguous:
        names = ", ".join(handle.name for handle in handles)
        return _ComponentResult(
            ResolutionReport(
                "underconstrained",
                (
                    ResolutionIssue(
                        f"connection component is ambiguous: {names}",
                        differences,
                    ),
                ),
            ),
            None,
        )
    if not materialize:
        return _ComponentResult(ResolutionReport("complete"), None)
    return _ComponentResult(
        ResolutionReport("complete"),
        _extract_plan(
            handles,
            points,
            point_selections,
            intent_mediums,
            assignment,
            by_id,
            connector,
        ),
    )


def _relevant_media(
    entities: Iterable[Entity], handles: Iterable[ConnectionHandle]
) -> list[EnumValue]:
    values: dict[str, EnumValue] = {}
    registry = next(iter(entities)).meta.registry
    roots: set[str] = set()
    for entity in entities:
        for slot in _all_slots(type(entity)) + _constraint_slots(type(entity)):
            roots.update(_slot_roots(slot))
        for cp in getattr(entity, "has_connection_point"):
            medium = getattr(cp, "has_medium")
            if medium is not None:
                values[medium.iri] = medium
        for port in entity.meta.model._port_intents:
            if port.owner is entity and port.medium is not None:
                values[port.medium.iri] = port.medium
    for handle in handles:
        if handle.medium is not None:
            values[handle.medium.iri] = handle.medium
    for iri in roots:
        if iri in registry.enums_by_iri:
            values[iri] = registry.enums_by_iri[iri]
    if not values:
        root = registry.enums_by_iri.get(
            "http://data.ashrae.org/standard223#Substance-Medium"
        )
        if root is not None:
            values[root.iri] = root
    return sorted(values.values(), key=lambda value: value.iri)


def _make_points(
    entity: Entity, incident: dict[str, int], media: list[EnumValue]
) -> list[_Point]:
    registry = entity.meta.registry
    points: list[_Point] = []
    for cp in getattr(entity, "has_connection_point"):
        points.append(
            _Point(
                entity,
                type(cp),
                cp.name,
                z3.BoolVal(True),
                z3.Int(f"existing_{_safe(cp.name)}_medium"),
                cp,
            )
        )
    for port in entity.meta.model._port_intents:
        if port.owner is not entity:
            continue
        cls_name = {
            "in": "InletConnectionPoint",
            "out": "OutletConnectionPoint",
            "bi": "BidirectionalConnectionPoint",
        }[port.direction]
        points.append(
            _Point(
                entity,
                registry.resolve(cls_name),
                port.name,
                z3.BoolVal(True),
                z3.Int(f"authored_{_safe(port.name)}_medium"),
                authored=port,
            )
        )
    slots = _all_slots(type(entity)) + _constraint_slots(type(entity))
    classes: dict[type[Entity], int] = {}
    for slot in slots:
        cls = registry.resolve(slot.cp_class)
        needed = max(slot.min_count, slot.max_count or 0)
        needed = max(needed, incident["in"] if slot.direction in {"in", "bi"} else 0)
        needed = max(needed, incident["out"] if slot.direction in {"out", "bi"} else 0)
        classes[cls] = max(classes.get(cls, 0), needed)
    if not classes:
        for direction in ("in", "out"):
            if incident[direction]:
                name = "InletConnectionPoint" if direction == "in" else "OutletConnectionPoint"
                classes[registry.resolve(name)] = incident[direction]
    existing_names = {point.name for point in points}
    for cls, count in sorted(classes.items(), key=lambda item: item[0].__name__):
        existing_count = sum(
            point.existing is not None and isinstance(point.existing, cls)
            for point in points
        )
        count = max(count - existing_count, 0)
        direction = _direction_of(cls)
        for offset in range(count):
            base = f"{entity.name}-{direction}"
            name = base if offset == 0 else f"{base}_{offset + 1}"
            while name in existing_names:
                offset += 1
                name = f"{base}_{offset + 1}"
            existing_names.add(name)
            points.append(
                _Point(
                    entity,
                    cls,
                    name,
                    z3.Bool(f"point_{_safe(entity.name)}_{_safe(cls.__name__)}_{offset}"),
                    z3.Int(f"point_{_safe(entity.name)}_{_safe(cls.__name__)}_{offset}_medium"),
                )
            )
    return points


def _slot_expr(
    points: list[_Point],
    slot: CPSlot,
    media: list[EnumValue],
    enum_ids: dict[str, int],
) -> z3.BoolRef:
    slot_cls = points[0].owner.meta.registry.resolve(slot.cp_class)
    matching = [
        z3.And(point.active, _medium_allowed(point.medium, slot, media, enum_ids))
        for point in points
        if issubclass(point.cls, slot_cls)
    ]
    count = z3.Sum([z3.If(item, 1, 0) for item in matching]) if matching else z3.IntVal(0)
    terms = [count >= slot.min_count]
    if slot.max_count is not None:
        terms.append(count <= slot.max_count)
    return z3.And(terms)


def _constraint_expr(
    points: list[_Point],
    constraint: CPConstraint,
    media: list[EnumValue],
    enum_ids: dict[str, int],
) -> z3.BoolRef:
    if constraint.operator == "slot":
        assert constraint.slot is not None
        return _slot_expr(points, constraint.slot, media, enum_ids)
    children = [
        _constraint_expr(points, child, media, enum_ids)
        for child in constraint.children
    ]
    if constraint.operator == "and":
        return z3.And(children)
    if constraint.operator == "or":
        return z3.Or(children)
    if constraint.operator == "xone":
        return z3.PbEq([(child, 1) for child in children], 1)
    return z3.BoolVal(True)


def _medium_allowed(
    variable: z3.ArithRef,
    slot: CPSlot,
    media: list[EnumValue],
    enum_ids: dict[str, int],
) -> z3.BoolRef:
    roots = _slot_roots(slot)
    if not roots:
        return z3.BoolVal(True)
    allowed = [
        enum_ids[value.iri]
        for value in media
        if any(_is_descendant_iri(value, root) for root in roots)
    ]
    return z3.Or([variable == value for value in allowed])


def _eligible(
    points: list[_Point], endpoint: Entity | PortHandle, direction: str
) -> list[_Point]:
    names = {
        "out": {"OutletConnectionPoint", "BidirectionalConnectionPoint"},
        "in": {"InletConnectionPoint", "BidirectionalConnectionPoint"},
    }[direction]
    return [
        point
        for point in points
        if point.owner is _owner(endpoint)
        and (
            not hasattr(endpoint, "owner")
            or point.authored is endpoint
        )
        and any(base.__name__ in names for base in point.cls.__mro__)
    ]


def _medium_affinity_penalty(
    entities: set[Entity],
    points: list[_Point],
    media: list[EnumValue],
    enum_ids: dict[str, int],
) -> z3.ArithRef:
    """Penalty for differing media on ports with overlapping permissions.

    This is a preference, not a physical preservation rule. Hard constraints
    come from SHACL domains and connection endpoints; the objective ranks
    otherwise-valid assignments by how coherently they use the media that an
    equipment/entity kind permits.
    """
    penalties: list[z3.ArithRef] = []
    for entity in entities:
        owned = [point for point in points if point.owner is entity]
        for index, left in enumerate(owned):
            for right in owned[index + 1 :]:
                if not (
                    _possible_medium_ids(left, media, enum_ids)
                    & _possible_medium_ids(right, media, enum_ids)
                ):
                    continue
                penalties.append(
                    z3.If(
                        z3.And(
                            left.active,
                            right.active,
                            left.medium != right.medium,
                        ),
                        1,
                        0,
                    )
                )
    return z3.Sum(penalties) if penalties else z3.IntVal(0)


def _point_roots(point: _Point) -> set[str]:
    registry = point.owner.meta.registry
    return {
        root
        for slot in _all_slots(type(point.owner))
        + _constraint_slots(type(point.owner))
        if issubclass(point.cls, registry.resolve(slot.cp_class))
        for root in _slot_roots(slot)
    }


def _possible_medium_ids(
    point: _Point,
    media: list[EnumValue],
    enum_ids: dict[str, int],
) -> set[int]:
    roots = _point_roots(point)
    if not roots:
        return set(enum_ids.values())
    return {
        enum_ids[value.iri]
        for value in media
        if any(_is_descendant_iri(value, root) for root in roots)
    }


def _medium_in_roots(
    variable: z3.ArithRef,
    roots: Iterable[str],
    media: list[EnumValue],
    enum_ids: dict[str, int],
) -> z3.BoolRef:
    allowed = [
        enum_ids[value.iri]
        for value in media
        if any(_is_descendant_iri(value, root) for root in roots)
    ]
    return z3.Or([variable == value for value in allowed])


def _minimize_active(solver: z3.Solver, points: list[_Point]) -> None:
    candidates = [point.active for point in points if point.existing is None]
    if not candidates:
        return
    total = z3.Sum([z3.If(active, 1, 0) for active in candidates])
    _minimize_expression(solver, total)


def _minimize_expression(solver: z3.Solver, expression: z3.ArithRef) -> None:
    """Constrain an integer objective to its minimum using the core solver."""
    while solver.check() == z3.sat:
        evaluated = z3.simplify(
            solver.model().eval(expression, model_completion=True)
        )
        value = evaluated.as_long()
        solver.push()
        solver.add(expression < value)
        if solver.check() == z3.unsat:
            solver.pop()
            solver.add(expression == value)
            return
        solver.pop()
        solver.add(expression < value)


def _observable_expressions(
    entities: set[Entity],
    points: list[_Point],
    handles: list[ConnectionHandle],
    selections: dict[tuple[int, int], z3.BoolRef],
    intent_mediums: dict[int, z3.ArithRef],
) -> list[z3.ArithRef]:
    expressions: list[z3.ArithRef] = list(intent_mediums.values())
    for entity in sorted(entities, key=lambda item: item.name):
        classes = sorted(
            {point.cls for point in points if point.owner is entity},
            key=lambda cls: cls.__name__,
        )
        for cls in classes:
            expressions.append(
                z3.Sum(
                    [
                        z3.If(point.active, 1, 0)
                        for point in points
                        if point.owner is entity and point.cls is cls
                    ]
                )
            )
    for handle in handles:
        for side_endpoint in (handle.source, handle.target):
            side_owner = _owner(side_endpoint)
            classes = sorted(
                {point.cls for point in points if point.owner is side_owner},
                key=lambda cls: cls.__name__,
            )
            for cls in classes:
                expressions.append(
                    z3.Sum(
                        [
                            z3.If(selections.get((handle.identifier, index), z3.BoolVal(False)), 1, 0)
                            for index, point in enumerate(points)
                            if point.owner is side_owner and point.cls is cls
                        ]
                    )
                )
    return expressions


def _extract_plan(
    handles: list[ConnectionHandle],
    points: list[_Point],
    selections: dict[tuple[int, int], z3.BoolRef],
    intent_mediums: dict[int, z3.ArithRef],
    model: z3.ModelRef,
    by_id: dict[int, EnumValue],
    connector: S223Connector,
) -> _Plan:
    results: dict[int, _PointResult] = {}
    materialized: list[_PointResult] = []
    for index, point in enumerate(points):
        if z3.is_true(model.eval(point.active, model_completion=True)):
            result = _PointResult(
                point.owner,
                point.cls,
                point.name,
                by_id[model.eval(point.medium, model_completion=True).as_long()],
                point.existing,
                point.authored,
            )
            results[index] = result
            materialized.append(result)
    intent_results: list[_IntentResult] = []
    for handle in handles:
        selected = [
            index
            for index in results
            if z3.is_true(
                model.eval(
                    selections.get((handle.identifier, index), z3.BoolVal(False)),
                    model_completion=True,
                )
            )
        ]
        source_owner = _owner(handle.source)
        target_owner = _owner(handle.target)
        source_index = next(
            index for index in selected if points[index].owner is source_owner
        )
        target_index = next(
            index for index in selected if points[index].owner is target_owner
        )
        medium = by_id[
            model.eval(intent_mediums[handle.identifier], model_completion=True).as_long()
        ]
        connection_class = handle.connection_class or _connection_class(connector, medium)
        intent_results.append(
            _IntentResult(
                handle,
                results[source_index],
                results[target_index],
                medium,
                connection_class,
            )
        )
    return _Plan(tuple(materialized), tuple(intent_results))


def _connection_class(connector: S223Connector, medium: EnumValue) -> type[Entity]:
    node: EnumValue | None = medium
    while node is not None:
        name = connector.connection_classes.get(node.iri)
        if name is not None:
            return connector.registry.resolve(name)
        node = node.parent
    return connector.registry.resolve("Connection")


def _materialize(model: Model, plans: list[_Plan]) -> ResolvedModel:
    snapshot, mapping = _clone_model(model)
    snapshot._resolving = True
    point_entities: dict[tuple[int, str], Entity] = {}
    connection_entities: dict[int, Entity] = {}
    explanations: dict[int, ResolutionExplanation] = {}
    authored_points: dict[PortHandle, Entity] = {}
    for plan in plans:
        for point in plan.points:
            key = (id(point.owner), point.name)
            if point.existing is not None:
                point_entities[key] = mapping[point.existing]
                continue
            owner = mapping[point.owner]
            point_entities[key] = point.cls(
                point.name,
                has_medium=point.medium,
                is_connection_point_of=owner,
                model=snapshot,
            )
            if point.authored is not None:
                authored_points[point.authored] = point_entities[key]
        for intent in plan.intents:
            source = point_entities[(id(intent.source.owner), intent.source.name)]
            target = point_entities[(id(intent.target.owner), intent.target.name)]
            connection = intent.connection_class(
                intent.handle.name,
                connects_at=[source, target],
                has_medium=intent.medium,
                label=intent.handle.label,
                comment=intent.handle.comment,
                model=snapshot,
            )
            for name, value in intent.handle._assignments.items():
                setattr(connection, name, _map_value(value, mapping))
            connection_entities[intent.handle.identifier] = connection
            explanations[intent.handle.identifier] = _explain_intent(intent)
    for handle, point in authored_points.items():
        if handle.roles:
            setattr(point, "has_role", handle.roles)
        if handle.paired_with is not None and handle.paired_with in authored_points:
            setattr(
                point,
                "paired_connection_point",
                authored_points[handle.paired_with],
            )
    for authored_system, authored_members in model._system_intents:
        system = mapping[authored_system]
        members = set(authored_members)
        for plan in plans:
            for intent in plan.intents:
                source_inside = intent.source.owner in members
                target_inside = intent.target.owner in members
                if source_inside == target_inside:
                    continue
                boundary = intent.source if source_inside else intent.target
                point = point_entities[(id(boundary.owner), boundary.name)]
                getattr(system, "has_boundary_connection_point").add(point)
    snapshot._resolving = False
    return ResolvedModel(
        snapshot,
        connection_entities,
        explanations,
        model._revision,
    )


def _explain_intent(intent: _IntentResult) -> ResolutionExplanation:
    """Classify the strongest authored or inferred source of a medium."""
    handle = intent.handle
    evidence = [
        f"selected {intent.source.cls.__name__} {intent.source.name}",
        f"selected {intent.target.cls.__name__} {intent.target.name}",
    ]
    if handle.medium is not None:
        reason = "explicit connection"
        evidence.append(f"{handle.name}.medium = {handle.medium.iri}")
    else:
        explicit = _point_medium_evidence(intent.source) or _point_medium_evidence(
            intent.target
        )
        paired = _paired_medium_evidence(intent.source) or _paired_medium_evidence(
            intent.target
        )
        if explicit is not None:
            reason = "explicit port"
            evidence.append(explicit)
        elif paired is not None:
            reason = "paired port"
            evidence.append(paired)
        elif _ontology_determines_medium(intent):
            reason = "ontology constraint"
            evidence.append("connection-point SHACL domains admit one medium")
        else:
            reason = "affinity preference"
            evidence.append(
                "the solver minimized medium changes among otherwise valid choices"
            )
    return ResolutionExplanation(
        connection=handle.name,
        medium=intent.medium,
        source_point=intent.source.name,
        target_point=intent.target.name,
        medium_reason=reason,
        evidence=tuple(evidence),
    )


def _point_medium_evidence(point: _PointResult) -> str | None:
    if point.authored is not None and point.authored.medium is not None:
        return f"{point.authored.name}.medium = {point.authored.medium.iri}"
    if point.existing is not None:
        medium = getattr(point.existing, "has_medium", None)
        if medium is not None:
            return f"{point.existing.name}.has_medium = {medium.iri}"
    return None


def _paired_medium_evidence(point: _PointResult) -> str | None:
    if point.authored is not None and point.authored.paired_with is not None:
        paired = point.authored.paired_with
        if paired.medium is not None:
            return (
                f"{point.authored.name} is paired with {paired.name}, "
                f"whose medium is {paired.medium.iri}"
            )
    if point.existing is not None:
        paired = getattr(point.existing, "paired_connection_point", None)
        medium = getattr(paired, "has_medium", None) if paired is not None else None
        if medium is not None:
            assert paired is not None
            return (
                f"{point.existing.name} is paired with {paired.name}, "
                f"whose medium is {medium.iri}"
            )
    return None


def _ontology_determines_medium(intent: _IntentResult) -> bool:
    source_roots = _result_roots(intent.source)
    target_roots = _result_roots(intent.target)
    roots = source_roots | target_roots
    if not roots:
        return False
    registry = intent.source.owner.meta.registry
    allowed = {
        value.iri
        for value in registry.enums_by_iri.values()
        if any(_is_descendant_iri(value, root) for root in roots)
    }
    return allowed == {intent.medium.iri}


def _result_roots(point: _PointResult) -> set[str]:
    registry = point.owner.meta.registry
    return {
        root
        for slot in _all_slots(type(point.owner))
        + _constraint_slots(type(point.owner))
        if issubclass(point.cls, registry.resolve(slot.cp_class))
        for root in _slot_roots(slot)
    }


def _owner(endpoint: Entity | PortHandle) -> Entity:
    return endpoint.owner if isinstance(endpoint, PortHandle) else endpoint


def _clone_model(model: Model) -> tuple[Model, dict[Entity, Entity]]:
    from .core.model import Model

    clone = Model(
        model.namespace,
        name=model.name,
        ontology_iri=model.ontology_iri,
        imports=model.imports,
        prefixes=model.prefixes,
    )
    clone._resolving = True
    mapping: dict[Entity, Entity] = {}
    for entity in model.entities:
        copied = object.__new__(type(entity))
        copied._name = entity.name
        copied._label = entity.label
        copied._comment = entity.comment
        copied._data = {}
        copied._rels = {}
        copied._iri = ""
        copied._model = clone
        clone._bind(copied)
        mapping[entity] = copied
    for entity, copied in mapping.items():
        copied._data = {
            name: _map_value(value, mapping) for name, value in entity._data.items()
        }
        for name, store in entity._rels.items():
            new_store = RelSet(copied, store._spec)
            new_store._items = [mapping[item] for item in store._items]
            copied._rels[name] = new_store
    clone._resolving = False
    return clone, mapping


def _map_value(value: Any, mapping: dict[Entity, Entity]) -> Any:
    if value in mapping if _hashable(value) else False:
        return mapping[value]
    if isinstance(value, list):
        return [_map_value(item, mapping) for item in value]
    if isinstance(value, tuple):
        return tuple(_map_value(item, mapping) for item in value)
    return value


def _hashable(value: Any) -> bool:
    try:
        hash(value)
    except TypeError:
        return False
    return True


def _all_slots(cls: type[Entity]) -> list[CPSlot]:
    return [
        slot
        for base in cls.__mro__
        if (info := base.__dict__.get("_classinfo")) is not None
        for slot in info.cp_slots
    ]


def _all_constraints(cls: type[Entity]) -> list[CPConstraint]:
    return [
        constraint
        for base in cls.__mro__
        if (info := base.__dict__.get("_classinfo")) is not None
        for constraint in info.cp_constraints
    ]


def _constraint_slots(cls: type[Entity]) -> list[CPSlot]:
    slots: list[CPSlot] = []

    def visit(constraint: CPConstraint) -> None:
        if constraint.slot is not None:
            slots.append(constraint.slot)
        for child in constraint.children:
            visit(child)

    for constraint in _all_constraints(cls):
        visit(constraint)
    return slots


def _contains_opaque(constraint: CPConstraint) -> bool:
    return constraint.operator == "opaque" or any(
        _contains_opaque(child) for child in constraint.children
    )


def _slot_roots(slot: CPSlot) -> tuple[str, ...]:
    if slot.medium_options:
        return slot.medium_options
    return (slot.medium,) if slot.medium is not None else ()


def _is_descendant_iri(value: EnumValue, root_iri: str) -> bool:
    node: EnumValue | None = value
    while node is not None:
        if node.iri == root_iri:
            return True
        node = node.parent
    return False


def _direction_of(cls: type[Entity]) -> str:
    names = {base.__name__ for base in cls.__mro__}
    if "BidirectionalConnectionPoint" in names:
        return "bi"
    if "InletConnectionPoint" in names:
        return "in"
    return "out"


def _safe(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)
