"""Integration tests against the committed generated 223P package."""

import pytest
from rdflib import RDF, URIRef

s223 = pytest.importorskip("objectrdf.s223")

from objectrdf import (  # noqa: E402
    AmbiguousModelError,
    Model,
    ModelingError,
    UnsatisfiableModelError,
    connect,
)
from objectrdf.core import RangeError  # noqa: E402
from objectrdf.s223 import enums  # noqa: E402

S = "http://data.ashrae.org/standard223#"


@pytest.fixture
def m():
    with Model("urn:test/s223#") as model:
        yield model


# -- enums -----------------------------------------------------------------


def test_enum_hierarchy():
    assert enums.values.Fluid_Air.is_a(enums.values.Substance_Medium)
    assert enums.values.Water_ChilledWater.is_a(enums.values.Fluid_Water)
    assert not enums.values.Fluid_Air.is_a(enums.values.Fluid_Water)
    assert enums.values.Fluid_Air.iri == f"{S}Fluid-Air"


def test_enum_hierarchical_access():
    # Flat constants are primary; hierarchy access works for exploration.
    assert enums.values.Substance_Medium.Mix.Fluid.Air is enums.values.Fluid_Air


def test_generated_package_exposes_canonical_point_properties():
    with Model("urn:test/s223-names#"):
        fan = s223.Fan("fan")
        point = next(
            cp
            for cp in fan.has_connection_point
            if isinstance(cp, s223.InletConnectionPoint)
        )

    assert point.medium is enums.values.Fluid_Air
    assert point.owner is fan
    point.medium = enums.values.Fluid_Water
    assert point.medium is enums.values.Fluid_Water


def test_enum_tree_prints_all_descendants(capsys):
    result = enums.values.Substance_Medium.tree()

    assert result is None
    tree = capsys.readouterr().out
    assert tree.startswith("Substance-Medium\n├── Medium-Constituent\n")
    assert "│   ├── Constituent-H2O\n" in tree
    assert "├── Medium-Mix\n" in tree
    assert "│   ├── Mix-Fluid\n" in tree
    assert "│   │   ├── Fluid-Air\n" in tree
    assert tree.endswith("└── Medium-ThermalContact\n")


def test_enum_tree_text_options():
    tree = enums.values.Substance_Medium.tree_text(max_depth=1)
    assert "├── Medium-Constituent\n│   └── …" in tree
    assert "Fluid-Air" not in tree

    iris = enums.values.Fluid_Water.tree_text(max_depth=0, show_iris=True)
    assert iris.startswith(f"{S}Fluid-Water")
    assert "\n└── …" in iris

    with pytest.raises(ValueError, match="non-negative"):
        enums.values.Fluid_Water.tree_text(max_depth=-1)


def test_enums_registered():
    reg = s223.Connectable.meta.registry
    assert reg.resolve_enum(f"{S}Fluid-Water") is enums.values.Fluid_Water


# -- structure -------------------------------------------------------------


def test_scale_and_abstractness(m):
    assert len(s223.__all__) > 150
    assert s223.Connectable.meta.abstract
    with pytest.raises(ModelingError, match="organizational class"):
        s223.Connectable("x")
    assert issubclass(s223.Fan, s223.Equipment)


def test_connection_point_requires_medium(m):
    with pytest.raises(TypeError, match="medium"):
        s223.InletConnectionPoint("cp")


def test_fan_cp_slots_extracted():
    slots = {(s.direction, s.medium) for s in s223.Fan._classinfo.cp_slots}
    assert ("out", f"{S}Fluid-Air") in slots
    assert ("in", f"{S}Fluid-Air") in slots


# -- connection negotiation ------------------------------------------------


def test_rshift_negotiates_air_connection(m):
    damper = s223.Damper("oad")
    fan = s223.Fan("sf")
    result = damper >> fan
    assert result is fan

    resolved = m.resolve()
    duct = resolved["oad--sf"]
    assert isinstance(duct, s223.Duct)
    assert duct.medium is enums.values.Fluid_Air
    out_cp = resolved["oad-out"]
    in_cp = resolved["sf-in"]
    assert isinstance(out_cp, s223.OutletConnectionPoint)
    assert out_cp.medium is enums.values.Fluid_Air
    # full 223 plumbing, both directions, from one statement:
    resolved_damper = resolved[damper.name]
    resolved_fan = resolved[fan.name]
    assert out_cp in resolved_damper.has_connection_point
    assert out_cp.owner is resolved_damper
    assert out_cp.connection is duct
    assert out_cp in duct.connects_at
    assert in_cp in duct.connects_at
    assert in_cp.owner is resolved_fan


def test_connect_handle_resolves_connection_and_medium(m):
    handle = connect(s223.Chiller("ch"), s223.Pump("p"))
    conn = m.resolve().connection(handle)
    assert isinstance(conn, s223.Pipe)  # inferred from Fluid-Water
    assert conn.medium is enums.values.Fluid_Water  # chiller side constrains it


def test_boolean_layout_supplies_coil_connection_candidates(m):
    coil = s223.ChilledWaterCoil("coil")
    for name, cls, medium in (
        ("coil-air-in", s223.InletConnectionPoint, enums.values.Fluid_Air),
        ("coil-water-in", s223.InletConnectionPoint, enums.values.Fluid_Water),
        ("coil-air-out", s223.OutletConnectionPoint, enums.values.Fluid_Air),
        ("coil-water-out", s223.OutletConnectionPoint, enums.values.Fluid_Water),
    ):
        cls(name, medium=medium, owner=coil)
    handle = connect(s223.Chiller("ch"), coil)
    conn = m.resolve().connection(handle)

    assert isinstance(conn, s223.Pipe)
    assert conn.medium is enums.values.Fluid_Water
    inlet = m.resolve()["coil-water-in"]
    assert isinstance(inlet, s223.InletConnectionPoint)
    assert inlet.medium is enums.values.Fluid_Water


def test_incomplete_coil_layout_is_deferred_as_ambiguous(m):
    pump = s223.Pump("pump")
    connect(s223.Chiller("ch"), pump)
    connect(pump, s223.ChilledWaterCoil("coil"))

    assert m.check().status == "underconstrained"
    with pytest.raises(AmbiguousModelError):
        m.resolve()


def test_chaining_reads_along_the_flow(m):
    s223.Damper("oad") >> s223.Fan("sf") >> s223.Damper("ret")
    resolved = m.resolve()
    assert isinstance(resolved["oad--sf"], s223.Duct)
    assert isinstance(resolved["sf--ret"], s223.Duct)


def test_explicit_medium_and_connection_class(m):
    a, b = s223.Pump("a"), s223.Pump("b")
    handle = connect(a, b, medium=enums.values.Water_ChilledWater)
    conn = m.resolve().connection(handle)
    assert conn.medium is enums.values.Water_ChilledWater
    assert isinstance(conn, s223.Pipe)  # ChilledWater is_a Fluid-Water


def test_medium_affinity_is_a_preference_not_hard_preservation(m):
    source = s223.Chiller("water-source")
    pump = s223.Pump("pump")
    oil_side = s223.Pump("oil-side")
    s223.InletConnectionPoint(
        "oil-in",
        medium=enums.values.Fluid_Oil,
        owner=oil_side,
    )
    water = connect(source, pump)
    oil = connect(pump, oil_side)

    assert m.check().complete
    resolved = m.resolve()
    assert resolved.connection(water).medium is enums.values.Fluid_Water
    assert resolved.connection(oil).medium is enums.values.Fluid_Oil
    assert {cp.medium for cp in resolved[pump.name].has_connection_point} == {
        enums.values.Fluid_Water,
        enums.values.Fluid_Oil,
    }


def test_unconstrained_sides_remain_deferred(m):
    connect(s223.Pump("p1"), s223.Pump("p2"))
    assert m.check().status == "underconstrained"
    with pytest.raises(AmbiguousModelError):
        m.resolve()


def test_mutually_required_cycle_is_constructible(m):
    # 223 deadlock case: Junction requires a ConnectionPoint, which requires
    # its Connectable. The compiler demotes the container side to
    # validate-time, so a Junction is constructible and connectable.
    j = s223.Junction("j1", medium=enums.values.Fluid_Water)
    handle = connect(s223.Chiller("ch"), j)
    conn = m.resolve().connection(handle)
    assert conn.medium is enums.values.Fluid_Water


def test_incompatible_media_rejected(m):
    boiler = s223.Boiler("b")  # water outlet
    fan = s223.Fan("f")  # air inlet
    boiler >> fan
    assert m.check().status == "unsatisfiable"
    with pytest.raises(UnsatisfiableModelError):
        m.resolve()


def test_unbounded_slot_supports_multiple_connections(m):
    ch = s223.Chiller("ch")
    first = connect(ch, s223.Pump("p1"))
    second = connect(ch, s223.Pump("p2"))
    resolved = m.resolve()
    assert isinstance(resolved.connection(first), s223.Pipe)
    assert isinstance(resolved.connection(second), s223.Pipe)


def test_new_ports_are_allocated_on_bare_equipment(m):
    ch, pump = s223.Chiller("ch"), s223.Pump("p")
    first = connect(ch, pump, ports="new", medium=enums.values.Fluid_Water)
    second = connect(ch, s223.Pump("q"), ports="new")
    assert first.source.name == "ch-out"
    assert first.target.name == "p-in"
    assert second.source.name == "ch-out-2"
    assert {port.name for port in ch.ports} >= {"ch-out", "ch-out-2"}
    assert first.source.medium is enums.values.Fluid_Water
    resolved = m.resolve()
    assert isinstance(resolved.connection(first), s223.Pipe)


def test_new_ports_require_one_model(m):
    with Model("urn:test/other#"):
        other = s223.Pump("p")
    with pytest.raises(ModelingError, match="same Model"):
        connect(s223.Chiller("ch"), other, ports="new")
    assert not m._port_intents


def test_new_ports_are_refused_on_graph_backed_model(m):
    connect(s223.Chiller("ch"), s223.Pump("p"))
    loaded = Model.from_graph(m.resolve().graph(), registries=s223.REGISTRY)
    with pytest.raises(ModelingError, match="deferred S223/WaTr connections"):
        connect(loaded["ch"], loaded["p"], ports="new")
    assert not loaded._port_intents


def test_equipment_medium_accepts_enum_values(m):
    pump = s223.Pump("p", medium=[enums.values.Fluid_Water])
    assert pump.medium == [enums.values.Fluid_Water]
    assert (
        URIRef(m.namespace + "p"),
        URIRef(f"{S}hasMedium"),
        URIRef(f"{S}Fluid-Water"),
    ) in m.graph()


def test_single_value_for_collection_names_the_fix(m):
    with pytest.raises(RangeError, match=r"takes a collection.*pass \["):
        s223.Pump("p", medium=enums.values.Fluid_Water)
    assert "p" not in {entity.name for entity in m.entities}


def test_explain_by_equipment_finds_connection_through_concrete_point(m):
    pump, chiller = s223.Pump("p"), s223.Chiller("ch")
    inlet = s223.InletConnectionPoint(
        "ch-in", medium=enums.values.Fluid_Water, owner=chiller
    )
    connect(pump, inlet)
    resolved = m.resolve()
    # The solver treats the point's owner as the endpoint; so does explain().
    assert resolved.explain(pump, chiller).connection == "p--ch-in"
    assert resolved.explain(pump, inlet).connection == "p--ch-in"


def test_construction_materializes_required_cps(m):
    # The Fan shape requires an air inlet and outlet: they exist immediately.
    fan = s223.Fan("f")
    cps = list(fan.has_connection_point)
    assert len(cps) == 2
    assert {type(cp).__name__ for cp in cps} == {
        "InletConnectionPoint",
        "OutletConnectionPoint",
    }
    assert all(cp.medium is enums.values.Fluid_Air for cp in cps)


def test_existing_cps_reused_not_duplicated(m):
    fan = s223.Fan("f")
    handle = connect(fan, s223.Damper("d"))
    # negotiation binds the construction-time CPs; nothing extra appears
    assert len(list(fan.has_connection_point)) == 2
    resolved = m.resolve()
    assert resolved["f-out"].connection is resolved.connection(handle)
    assert m["f-out"].connection is None


def test_handle_assignments_transfer_to_frozen_snapshot(m):
    handle = connect(s223.Damper("d"), s223.Fan("f"))
    handle.label = "Supply duct"
    handle.comment = "authored before resolution"
    handle.has_role.add(enums.values.Role_Supply, enums.values.Role_Return)
    handle.has_role.remove(enums.values.Role_Return)

    resolved = m.resolve()
    duct = resolved.connection(handle)
    assert duct.label == "Supply duct"
    assert duct.comment == "authored before resolution"
    assert duct.has_role == [enums.values.Role_Supply]
    with pytest.raises(ModelingError, match="immutable"):
        duct.label = "changed"


def test_handle_collection_assignment_invalidates_resolution(m):
    handle = connect(s223.Damper("d"), s223.Fan("f"))
    handle.has_role.add(enums.values.Role_Supply)
    first = m.resolve()

    handle.has_role = [enums.values.Role_Return]
    second = m.resolve()
    assert second is not first
    assert list(handle.has_role) == [enums.values.Role_Return]
    assert second.connection(handle).has_role == [enums.values.Role_Return]

    with pytest.raises(TypeError, match="multi-valued"):
        handle.has_role = enums.values.Role_Supply


def test_resolution_cache_invalidates_on_handle_edit(m):
    handle = connect(s223.Damper("d"), s223.Fan("f"))
    first = m.resolve()
    assert m.resolve() is first

    handle.label = "Changed before recompilation"
    second = m.resolve()
    assert second is not first
    assert second.connection(handle).label == "Changed before recompilation"


def test_unsat_core_uses_authored_connection_name(m):
    connect(s223.Boiler("boiler"), s223.Fan("fan"))
    with pytest.raises(UnsatisfiableModelError) as caught:
        m.resolve()
    assert any("boiler--fan" in label for label in caught.value.core)


def test_sparse_components_resolve_independently():
    with Model("urn:test/sparse#") as model:
        handles = [connect(s223.Damper(f"d{i}"), s223.Fan(f"f{i}")) for i in range(30)]
    assert model.check().status == "complete"
    resolved = model.resolve()
    assert all(isinstance(resolved.connection(h), s223.Duct) for h in handles)


# -- containment -----------------------------------------------------------


def test_containment_negotiation(m):
    with s223.PhysicalSpace("building") as b:
        with s223.PhysicalSpace("room") as r:
            zone = s223.DomainSpace("zone", has_domain=enums.values.Domain_HVAC)
            ahu = s223.Fan("fan")
    # s223:contains is exposed as `contains_` (contains() is the method)
    assert r in b.contains_
    assert zone in r.encloses
    assert r in ahu.has_physical_location


# -- serialization ---------------------------------------------------------


def test_serialization_produces_223_triples(m):
    s223.Damper("oad") >> s223.Fan("sf")
    g = m.graph()
    ns = "urn:test/s223#"

    def u(x):
        return URIRef(ns + x)

    assert (u("oad--sf"), RDF.type, URIRef(f"{S}Duct")) in g
    assert (u("oad--sf"), URIRef(f"{S}hasMedium"), URIRef(f"{S}Fluid-Air")) in g
    assert (u("oad"), URIRef(f"{S}hasConnectionPoint"), u("oad-out")) in g
    assert (u("oad-out"), URIRef(f"{S}connectsThrough"), u("oad--sf")) in g
    assert (u("oad--sf"), URIRef(f"{S}connectsAt"), u("sf-in")) in g
    assert (u("sf-in"), URIRef(f"{S}hasMedium"), URIRef(f"{S}Fluid-Air")) in g


def test_cp_cannot_belong_to_two_connectables(m):
    f1, f2 = s223.Fan("f1"), s223.Fan("f2")
    cp = s223.OutletConnectionPoint("cp", medium=enums.values.Fluid_Air, owner=f1)
    with pytest.raises(ModelingError, match="already"):
        f2.has_connection_point.add(cp)


# -- validation & example --------------------------------------------------


def test_negotiated_model_conforms_to_223(m):
    """The whole point: what the negotiator emits passes 223's own shapes.

    Uses the package's recorded ontology source (a URL), so this needs the
    network; skipped when offline.
    """
    s223.Damper("oad") >> s223.Fan("sf")
    try:
        report = m.validate()  # shapes fetched from ONTOLOGY.source
    except Exception as exc:  # pragma: no cover - offline environments
        pytest.skip(f"could not fetch 223 shapes: {exc}")
    assert report.ok, str(report)
    assert report.violations == ()
    # dangling boundary CPs are advisory only (info severity)
    assert all(i.severity == "info" for i in report.issues)


def test_quickstart_example_runs(tmp_path):
    import runpy
    import shutil
    from pathlib import Path

    example = (
        Path(__file__).parent.parent
        / "examples"
        / "s223"
        / "ahu"
        / "s223_quickstart.py"
    )
    target = tmp_path / "s223_quickstart.py"
    shutil.copy(example, target)
    runpy.run_path(str(target))
    assert (tmp_path / "ahu.ttl").exists()


def test_system_scope_collects_members_and_resolved_boundaries(m):
    source = s223.Chiller("source")
    with m.system("transfer-system", label="Transfer system") as scope:
        pump_1 = s223.Pump("pump-1")
        pump_2 = s223.Pump("pump-2")
        pump_1 >> pump_2
    target = s223.Chiller("target")
    source >> pump_1
    pump_2 >> target

    resolved = m.resolve()
    system = resolved["transfer-system"]
    assert scope.entity is not None
    assert {member.name for member in system.has_member} == {"pump-1", "pump-2"}
    assert {point.owner.name for point in system.has_boundary_connection_point} == {
        "pump-1",
        "pump-2",
    }
