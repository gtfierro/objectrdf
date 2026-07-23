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
from objectrdf.s223 import enums  # noqa: E402

S = "http://data.ashrae.org/standard223#"


@pytest.fixture
def m():
    with Model("urn:test/s223#") as model:
        yield model


# -- enums -----------------------------------------------------------------


def test_enum_hierarchy():
    assert enums.Fluid_Air.is_a(enums.Substance_Medium)
    assert enums.Water_ChilledWater.is_a(enums.Fluid_Water)
    assert not enums.Fluid_Air.is_a(enums.Fluid_Water)
    assert enums.Fluid_Air.iri == f"{S}Fluid-Air"


def test_enum_hierarchical_access():
    # Flat constants are primary; hierarchy access works for exploration.
    assert enums.Substance_Medium.Mix.Fluid.Air is enums.Fluid_Air


def test_enums_registered():
    reg = s223.Connectable.meta.registry
    assert reg.resolve_enum(f"{S}Fluid-Water") is enums.Fluid_Water


# -- structure -------------------------------------------------------------


def test_scale_and_abstractness(m):
    assert len(s223.__all__) > 150
    assert s223.Connectable.meta.abstract
    with pytest.raises(ModelingError, match="organizational class"):
        s223.Connectable("x")
    assert issubclass(s223.Fan, s223.Equipment)


def test_connection_point_requires_medium(m):
    with pytest.raises(TypeError, match="has_medium"):
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
    assert duct.has_medium is enums.Fluid_Air
    out_cp = resolved["oad-out"]
    in_cp = resolved["sf-in"]
    assert isinstance(out_cp, s223.OutletConnectionPoint)
    assert out_cp.has_medium is enums.Fluid_Air
    # full 223 plumbing, both directions, from one statement:
    resolved_damper = resolved[damper.name]
    resolved_fan = resolved[fan.name]
    assert out_cp in resolved_damper.has_connection_point
    assert out_cp.is_connection_point_of is resolved_damper
    assert out_cp.connects_through is duct
    assert out_cp in duct.connects_at
    assert in_cp in duct.connects_at
    assert in_cp.is_connection_point_of is resolved_fan


def test_connect_handle_resolves_connection_and_medium(m):
    handle = connect(s223.Chiller("ch"), s223.Pump("p"))
    conn = m.resolve().connection(handle)
    assert isinstance(conn, s223.Pipe)  # inferred from Fluid-Water
    assert conn.has_medium is enums.Fluid_Water  # chiller side constrains it


def test_boolean_layout_supplies_coil_connection_candidates(m):
    coil = s223.ChilledWaterCoil("coil")
    for name, cls, medium in (
        ("coil-air-in", s223.InletConnectionPoint, enums.Fluid_Air),
        ("coil-water-in", s223.InletConnectionPoint, enums.Fluid_Water),
        ("coil-air-out", s223.OutletConnectionPoint, enums.Fluid_Air),
        ("coil-water-out", s223.OutletConnectionPoint, enums.Fluid_Water),
    ):
        cls(name, has_medium=medium, is_connection_point_of=coil)
    handle = connect(s223.Chiller("ch"), coil)
    conn = m.resolve().connection(handle)

    assert isinstance(conn, s223.Pipe)
    assert conn.has_medium is enums.Fluid_Water
    inlet = m.resolve()["coil-water-in"]
    assert isinstance(inlet, s223.InletConnectionPoint)
    assert inlet.has_medium is enums.Fluid_Water


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
    handle = connect(a, b, medium=enums.Water_ChilledWater)
    conn = m.resolve().connection(handle)
    assert conn.has_medium is enums.Water_ChilledWater
    assert isinstance(conn, s223.Pipe)  # ChilledWater is_a Fluid-Water


def test_medium_affinity_is_a_preference_not_hard_preservation(m):
    source = s223.Chiller("water-source")
    pump = s223.Pump("pump")
    oil_side = s223.Pump("oil-side")
    s223.InletConnectionPoint(
        "oil-in",
        has_medium=enums.Fluid_Oil,
        is_connection_point_of=oil_side,
    )
    water = connect(source, pump)
    oil = connect(pump, oil_side)

    assert m.check().complete
    resolved = m.resolve()
    assert resolved.connection(water).has_medium is enums.Fluid_Water
    assert resolved.connection(oil).has_medium is enums.Fluid_Oil
    assert {cp.has_medium for cp in resolved[pump.name].has_connection_point} == {
        enums.Fluid_Water,
        enums.Fluid_Oil,
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
    j = s223.Junction("j1", has_medium=enums.Fluid_Water)
    handle = connect(s223.Chiller("ch"), j)
    conn = m.resolve().connection(handle)
    assert conn.has_medium is enums.Fluid_Water


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


def test_construction_materializes_required_cps(m):
    # The Fan shape requires an air inlet and outlet: they exist immediately.
    fan = s223.Fan("f")
    cps = list(fan.has_connection_point)
    assert len(cps) == 2
    assert {type(cp).__name__ for cp in cps} == {
        "InletConnectionPoint",
        "OutletConnectionPoint",
    }
    assert all(cp.has_medium is enums.Fluid_Air for cp in cps)


def test_existing_cps_reused_not_duplicated(m):
    fan = s223.Fan("f")
    handle = connect(fan, s223.Damper("d"))
    # negotiation binds the construction-time CPs; nothing extra appears
    assert len(list(fan.has_connection_point)) == 2
    resolved = m.resolve()
    assert resolved["f-out"].connects_through is resolved.connection(handle)
    assert m["f-out"].connects_through is None


def test_handle_assignments_transfer_to_frozen_snapshot(m):
    handle = connect(s223.Damper("d"), s223.Fan("f"))
    handle.label = "Supply duct"
    handle.comment = "authored before resolution"
    handle.has_role.add(enums.Role_Supply, enums.Role_Return)
    handle.has_role.remove(enums.Role_Return)

    resolved = m.resolve()
    duct = resolved.connection(handle)
    assert duct.label == "Supply duct"
    assert duct.comment == "authored before resolution"
    assert duct.has_role == [enums.Role_Supply]
    with pytest.raises(ModelingError, match="immutable"):
        duct.label = "changed"


def test_handle_collection_assignment_invalidates_resolution(m):
    handle = connect(s223.Damper("d"), s223.Fan("f"))
    handle.has_role.add(enums.Role_Supply)
    first = m.resolve()

    handle.has_role = [enums.Role_Return]
    second = m.resolve()
    assert second is not first
    assert list(handle.has_role) == [enums.Role_Return]
    assert second.connection(handle).has_role == [enums.Role_Return]

    with pytest.raises(TypeError, match="multi-valued"):
        handle.has_role = enums.Role_Supply


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
        handles = [
            connect(s223.Damper(f"d{i}"), s223.Fan(f"f{i}"))
            for i in range(30)
        ]
    assert model.check().status == "complete"
    resolved = model.resolve()
    assert all(isinstance(resolved.connection(h), s223.Duct) for h in handles)


# -- containment -----------------------------------------------------------


def test_containment_negotiation(m):
    with s223.PhysicalSpace("building") as b:
        with s223.PhysicalSpace("room") as r:
            zone = s223.DomainSpace("zone", has_domain=enums.Domain_HVAC)
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
    cp = s223.OutletConnectionPoint(
        "cp", has_medium=enums.Fluid_Air, is_connection_point_of=f1
    )
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

    example = Path(__file__).parent.parent / "examples" / "s223_quickstart.py"
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
    assert {
        point.is_connection_point_of.name
        for point in system.has_boundary_connection_point
    } == {"pump-1", "pump-2"}
