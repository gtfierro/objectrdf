"""Finding objects, containment navigation, and topology walks."""

import gc
import re
import weakref
from importlib import import_module

import pytest
import toy
from rdflib import URIRef

from plumb import Model, ModelingError, connect, exact, s223
from plumb.core.traversal import OPTION_NAMES, matches, value_matches
from plumb.gen.naming import RESERVED
from plumb.s223 import enums

WATER = enums.values.Fluid_Water
HOT_WATER = WATER["HotWater"]
AIR = enums.values.Fluid_Air
S = "http://data.ashrae.org/standard223#"


# -- filters ---------------------------------------------------------------


@pytest.fixture
def site():
    with Model("urn:site#") as model:
        building = toy.Location("building")
        floor = toy.Location("floor")
        building.has_part.add(floor)
        ahu = toy.Equipment("ahu", label="AHU 1", has_location=floor)
        fan = toy.Fan("fan", label="Supply fan")
        ahu.has_part.add(fan)
        sensor = toy.Sensor("sensor")
        fan.has_point.add(sensor)
    return model


def test_class_filters_match_subclasses_unless_exact(site):
    ahu, fan = site["ahu"], site["fan"]

    assert site.find_all(toy.Equipment, has_part=toy.Fan) == [ahu]
    assert site.find_all(toy.Equipment, has_part=exact(toy.Equipment)) == []
    assert site.find_all(exact(toy.Equipment)) == [ahu]
    assert site.find_all((toy.Fan, toy.Sensor)) == [fan, site["sensor"]]
    assert site.find_all(type=toy.Equipment) == [ahu, fan]
    assert site.find_all(type=exact(toy.Fan)) == [fan]
    assert site.find_all(type="Fan") == [fan]
    assert site.find_all(type=["Fan", "Sensor"]) == [fan, site["sensor"]]
    assert site.find_all(type=re.compile("^Fa")) == [fan]
    assert site.find_all(type=lambda cls: cls is toy.Fan) == [fan]
    assert value_matches(toy.Fan, toy.Equipment)
    assert not value_matches(toy.Fan, exact(toy.Equipment))


def test_exact_class_filter_matches_related_entities_of_that_class(site):
    assert site.find_all(toy.Equipment, has_part=exact(toy.Fan)) == [site["ahu"]]
    assert site.find_all(has_point=exact(toy.Sensor)) == [site["fan"]]
    assert site.find_all(has_point=exact(toy.Point)) == []


def test_filter_vocabulary(site):
    ahu, fan = site["ahu"], site["fan"]

    assert site.find_all(toy.Equipment, label=re.compile("^Supply")) == [fan]
    assert site.find_all(toy.Equipment, label=["AHU 1", "Supply fan"]) == [ahu, fan]
    assert site.find_all(toy.Equipment, has_location=True) == [ahu]
    assert site.find_all(toy.Equipment, has_location=False) == [fan]
    assert site.find_all(toy.Equipment, has_part=False) == [fan]
    assert site.find_all(toy.Equipment, limit=1) == [ahu]
    assert site.find_all(attrs={"label": "AHU 1"}) == [ahu]
    assert site.find(toy.Sensor, attrs={"iri": "urn:site#sensor"}) is site["sensor"]
    with pytest.raises(TypeError, match="both"):
        site.find_all(label="AHU 1", attrs={"label": "AHU 1"})


def test_boolean_filters_compare_values_on_boolean_properties():
    assert value_matches(False, False, boolean=True)
    assert not value_matches(True, False, boolean=True)
    assert value_matches(False, True)  # presence: False is a value


def test_boolean_filters_compare_attributes_holding_bools(site, monkeypatch):
    # An attribute without an xsd:boolean spec still compares bools as values.
    monkeypatch.setattr(
        toy.Fan, "is_spare", property(lambda self: False), raising=False
    )
    fan = site["fan"]

    assert matches(fan, {"is_spare": False})
    assert not matches(fan, {"is_spare": True})


def test_enum_filters_match_narrower_values_unless_exact():
    with Model("urn:t#") as model:
        pump = s223.Pump("pump", medium=[HOT_WATER])
        fan = s223.Fan("fan", medium=[AIR])

    assert model.find_all(s223.Equipment, medium=WATER) == [pump]
    assert model.find_all(s223.Equipment, medium=exact(WATER)) == []
    assert model.find_all(s223.Equipment, medium=exact(HOT_WATER)) == [pump]
    assert model.find_all(s223.Equipment, medium=[exact(WATER), AIR]) == [fan]


# -- containment -----------------------------------------------------------


def test_containment_navigation(site):
    building, floor, ahu = site["building"], site["floor"], site["ahu"]
    fan, sensor = site["fan"], site["sensor"]

    assert building.contents == (floor,)
    assert list(building.descendants) == [floor, ahu, fan, sensor]
    assert floor.contents == (ahu,)  # stored on the child as has_location
    assert ahu.container is floor
    assert building.container is None
    assert list(sensor.containers) == [fan, ahu, floor, building]


def test_scoped_find_and_upward_search(site):
    building, floor, ahu = site["building"], site["floor"], site["ahu"]
    fan, sensor = site["fan"], site["sensor"]

    assert building.find_all(toy.Equipment) == [ahu, fan]
    assert building.find_all(toy.Equipment, recursive=False) == []
    assert building.find(toy.Point) is sensor
    assert ahu.find(toy.Fan, label="Supply fan") is fan
    assert sensor.find_parent(toy.Location) is floor
    assert sensor.find_parents(toy.Location) == [floor, building]
    assert sensor.find_parent(toy.Equipment, label=re.compile("AHU")) is ahu


def test_indexes_do_not_keep_models_alive():
    with Model("urn:gc#") as model:
        floor = toy.Location("floor")
        toy.Equipment("ahu", has_location=floor)
    assert floor.contents
    reference = weakref.ref(model)
    del model, floor

    gc.collect()

    assert reference() is None


def test_rolled_back_edits_do_not_leave_stale_indexes(site):
    floor, ahu, sensor = site["floor"], site["ahu"], site["sensor"]
    assert floor.contents == (ahu,)

    with pytest.raises(RuntimeError):
        with site.system("scratch"):
            floor.has_point.add(sensor)
            assert floor.contents == (ahu, sensor)
            raise RuntimeError
    site["building"].label = "Building"  # the next edit after the rollback

    assert floor.contents == (ahu,)
    assert list(floor.has_point) == []


def test_containment_index_follows_edits(site):
    floor, sensor = site["floor"], site["sensor"]
    assert floor.contents == (site["ahu"],)

    floor.has_point.add(sensor)

    assert floor.contents == (site["ahu"], sensor)
    with pytest.raises(ModelingError, match="2 containers"):
        sensor.container


# -- topology --------------------------------------------------------------


def _point(kind, name, owner, medium=WATER):
    return getattr(s223, f"{kind}ConnectionPoint")(name, medium=medium, owner=owner)


def _pipe(name, a, b, medium=WATER, cls=s223.Pipe):
    return cls(name, connects_at=[a, b], medium=medium)


@pytest.fixture
def loop():
    """pump -> boiler -> valve -> chiller, the last leg carrying air."""
    with Model("urn:loop#") as model:
        pump, boiler = s223.Pump("pump"), s223.Boiler("boiler")
        valve, chiller = s223.Valve("valve"), s223.Chiller("chiller")
        _pipe(
            "supply",
            _point("Outlet", "pump-out", pump),
            _point("Inlet", "boiler-in", boiler),
        )
        _pipe(
            "hot",
            _point("Outlet", "boiler-out", boiler, HOT_WATER),
            _point("Inlet", "valve-in", valve, HOT_WATER),
            HOT_WATER,
        )
        _pipe(
            "air",
            _point("Outlet", "valve-out", valve, AIR),
            _point("Inlet", "chiller-in", chiller, AIR),
            AIR,
            s223.Duct,
        )
    return model


def test_walk_downstream_and_upstream(loop):
    pump, boiler = loop["pump"], loop["boiler"]
    valve, chiller = loop["valve"], loop["chiller"]

    assert pump.find_all_next() == [boiler, valve, chiller]
    assert chiller.find_all_previous() == [valve, boiler, pump]
    assert pump.find_next(s223.Valve) is valve
    assert boiler.find_previous() is pump
    assert chiller.find_all_next() == []
    assert pump.find_all_next(max_hops=1) == [boiler]
    assert pump.find_all_next(max_hops=0) == []
    assert pump.find_all_next(limit=2) == [boiler, valve]


def test_hops_record_depth_and_path(loop):
    hops = list(loop["pump"].walk())

    assert [(hop.entity.name, hop.depth) for hop in hops] == [
        ("boiler", 1),
        ("valve", 2),
        ("chiller", 3),
    ]
    assert [crossing.connection.name for crossing in hops[-1].via] == [
        "supply",
        "hot",
        "air",
    ]
    assert hops[0].via[0].exit is loop["pump-out"]
    assert hops[0].via[0].entry is loop["boiler-in"]


def test_through_prunes_the_path_and_matches_narrower_media(loop):
    pump = loop["pump"]
    boiler, valve = loop["boiler"], loop["valve"]

    assert pump.find_all_next(through={"medium": WATER}) == [boiler, valve]
    assert pump.find_all_next(through={"medium": exact(WATER)}) == [boiler]
    assert pump.find_all_next(through={"type": s223.Pipe}) == [boiler, valve]
    assert pump.find_all_next(
        through=lambda crossing: crossing.connection.name != "hot"
    ) == [boiler]
    # Filters select results; through restricts the path.
    assert pump.find_all_next(s223.Chiller, through={"medium": WATER}) == []


def test_connections_are_results_only_on_request(loop):
    pump = loop["pump"]

    assert pump.find_next(s223.Pipe) is None
    assert pump.find_next(s223.Pipe, include_connections=True) is loop["supply"]
    assert pump.find_all_next(
        s223.Connection, include_connections=True, medium=AIR
    ) == [loop["air"]]


def test_walks_can_start_on_points_and_connections(loop):
    assert loop["boiler-out"].find_all_next() == [loop["valve"], loop["chiller"]]
    assert loop["hot"].find_all_next() == [loop["valve"], loop["chiller"]]
    assert loop["hot"].find_all_previous() == [loop["boiler"], loop["pump"]]
    assert loop["hot"].find_all_next(max_hops=0) == []
    assert loop["hot"].find_all_next(max_hops=1) == [loop["valve"]]


def test_bidirectional_points_cross_both_ways():
    with Model("urn:bi#") as model:
        pump = s223.Pump("pump")
        junction = s223.Equipment("junction")
        tank = s223.Equipment("tank")
        _pipe(
            "a",
            _point("Outlet", "pump-out", pump),
            _point("Bidirectional", "junction-1", junction),
        )
        _pipe(
            "b",
            _point("Bidirectional", "junction-2", junction),
            _point("Bidirectional", "tank-port", tank),
        )
    del model

    assert pump.find_all_next() == [junction, tank]
    assert tank.find_all_previous() == [junction, pump]
    # From the tank, "downstream" reaches the junction but not the pump's outlet.
    assert tank.find_all_next() == [junction]


@pytest.fixture
def air_path():
    """damper -> unit (containing a fan mapped to its ports) -> terminal."""
    with Model("urn:air#") as model:
        damper = s223.Equipment("damper")
        ahu = s223.Equipment("ahu")
        fan = s223.Equipment("fan")
        ahu.contains(fan)
        terminal = s223.Equipment("terminal")
        ahu_in = _point("Inlet", "ahu-in", ahu, AIR)
        ahu_out = _point("Outlet", "ahu-out", ahu, AIR)
        _point("Inlet", "fan-in", fan, AIR).maps_to = ahu_in
        _point("Outlet", "fan-out", fan, AIR).maps_to = ahu_out
        _pipe("d1", _point("Outlet", "damper-out", damper, AIR), ahu_in, AIR, s223.Duct)
        _pipe(
            "d2", ahu_out, _point("Inlet", "terminal-in", terminal, AIR), AIR, s223.Duct
        )
    return model


def test_containers_are_opaque_unless_descending(air_path):
    damper, ahu = air_path["damper"], air_path["ahu"]
    fan, terminal = air_path["fan"], air_path["terminal"]

    assert damper.find_all_next() == [ahu, terminal]
    assert [(hop.entity.name, hop.depth) for hop in damper.walk(descend=True)] == [
        ("ahu", 1),
        ("fan", 2),
        ("terminal", 2),
    ]
    assert terminal.find_all_previous(descend=True) == [ahu, damper, fan]
    assert damper.find_all_next(descend=True, max_hops=2) == [ahu, fan, terminal]
    assert ahu.contents == (fan,)
    assert fan.find_parent(s223.Equipment) is ahu


def test_descending_into_a_partly_mapped_container_still_passes_through(air_path):
    # Only the inlet is mapped inside; the outlet has no internal counterpart.
    air_path["fan-out"].maps_to = None

    assert air_path["damper"].find_all_next(descend=True) == [
        air_path["ahu"],
        air_path["fan"],
        air_path["terminal"],
    ]


def test_walks_leave_containers_through_maps_to(air_path):
    assert air_path["fan"].find_all_next() == [air_path["terminal"]]
    assert air_path["fan"].find_all_previous() == [air_path["damper"]]


def test_systems_are_reached_through_their_boundary(loop):
    pump, boiler, valve = loop["pump"], loop["boiler"], loop["valve"]
    with loop:
        plant = s223.System(
            "plant",
            has_member=[boiler, valve],
            has_boundary_connection_point=[loop["boiler-in"], loop["valve-out"]],
        )

    assert pump.find_all_next(s223.System) == [plant]
    assert pump.find_all_next() == [boiler, plant, valve, loop["chiller"]]
    assert boiler.find_all_next(s223.System) == []
    assert loop["chiller"].find_all_previous(s223.System) == [plant]


def test_authored_connections_are_walked_on_the_resolved_snapshot():
    from plumb.watr import Pipe, Pump
    from plumb.watr.drinking_water import (
        ClarificationStage,
        CoagulationStage,
        RapidSandFiltrationStage,
    )

    with Model("urn:plant#") as model:
        intake = Pump("intake")
        coagulation = CoagulationStage("coagulation")
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("sand-filter")
    connect(intake, coagulation.inlet, name="raw")
    connect(coagulation.outlet, clarifier.inlet, name="coagulated")
    connect(clarifier.clarified_water, sand_filter.inlet, name="clarified")

    with pytest.raises(ModelingError, match="resolve"):
        intake.find_all_next()

    snapshot = model.resolve()
    names = [entity.name for entity in snapshot["intake"].find_all_next()]
    assert names == ["coagulation", "clarifier", "sand-filter"]
    assert snapshot["clarifier"].find_previous() is snapshot["coagulation"]
    assert snapshot.find(Pipe, iri="urn:plant#raw") is snapshot["raw"]
    assert [
        pipe.name
        for pipe in snapshot["intake"].find_all_next(Pipe, include_connections=True)
    ] == ["raw", "coagulated", "clarified"]


def test_loaded_graphs_walk_with_one_side_of_each_inverse(loop, tmp_path):
    graph = loop.graph()
    for predicate in ("isConnectionPointOf", "connectsThrough"):
        graph.remove((None, URIRef(S + predicate), None))
    path = tmp_path / "loop.ttl"
    graph.serialize(path)

    model = Model.from_graph(path)

    assert [entity.name for entity in model["pump"].find_all_next()] == [
        "boiler",
        "valve",
        "chiller",
    ]


def test_topology_index_follows_edits(loop):
    pump, boiler = loop["pump"], loop["boiler"]
    assert pump.find_all_next() == [boiler, loop["valve"], loop["chiller"]]

    loop["supply"].connects_at.remove(loop["boiler-in"])

    assert pump.find_all_next() == []


# -- reserved names --------------------------------------------------------

_PACKAGES = (
    "plumb.brick",
    "plumb.s223",
    "plumb.s223.hvac",
    "plumb.watr",
    "plumb.watr.asm2d",
    "plumb.watr.drinking_water",
    "plumb.watr.seawater_ro",
)
_METHODS = {
    "contents",
    "descendants",
    "container",
    "containers",
    "find",
    "find_all",
    "find_parent",
    "find_parents",
    "walk",
    "find_next",
    "find_all_next",
    "find_previous",
    "find_all_previous",
}


def test_generated_properties_do_not_shadow_find_options_or_methods():
    names: set[str] = set()
    for package in _PACKAGES:
        for cls in import_module(package).REGISTRY.classes:
            names.update(cls._effective_specs())

    assert names & OPTION_NAMES == set()
    assert names & _METHODS == set()
    assert _METHODS <= RESERVED
