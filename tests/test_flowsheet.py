"""Flow-sheet rendering of resolved S223/WaTr models."""

import re
import shutil

import pytest

from objectrdf import Flowsheet, Model, connect, flowsheet
from objectrdf.qudt import quantity_kinds, units
from objectrdf.watr import LevelSensor, Pump, Tank, enums
from objectrdf.watr.drinking_water import (
    ClarificationStage,
    RapidSandFiltrationStage,
)

values = enums.values


@pytest.fixture
def plant() -> Model:
    model = Model("urn:example:flowsheet#")
    with model, model.system("plant"):
        pump = Pump("intake")
        clarifier = ClarificationStage("clarifier")
        sand_filter = RapidSandFiltrationStage("filter")
        Tank("clearwell")
    raw = connect(pump, clarifier.inlet, name="raw-water")
    connect(clarifier.clarified_water, sand_filter.inlet, name="settled")
    connect(sand_filter.filtered_water, model["clearwell"], name="filtered")
    connect(
        clarifier.sludge,
        Tank("sludge-tank", model=model),
        name="sludge",
        medium=values.Fluid_Sludge,
    )
    raw.quantity(
        "raw-flow", 40_000, unit=units.M3_PER_DAY, kind=quantity_kinds.VolumeFlowRate
    )
    raw.sensor(
        "raw-water-flow", kind=quantity_kinds.VolumeFlowRate, unit=units.M3_PER_DAY
    )
    model["clearwell"].sensor(
        "clearwell-level",
        kind=quantity_kinds.Length,
        unit=units.M,
        sensor_class=LevelSensor,
    )
    pump.actuator("intake-speed", kind=quantity_kinds.Frequency, unit=units.HZ)
    model["plant"].boundary(pump.port("suction", direction="in"))
    return model


def test_streams_are_lines_between_equipment(plant):
    source = flowsheet(plant).source
    # Connections are edges, not nodes: no node carries a Pipe class label.
    assert "Pipe" not in source
    # Stream names are tooltips, not drawn labels.
    assert 'tooltip="settled (Water)"' in source
    assert "<B>settled</B>" not in source
    assert "#8c564b" in source  # sludge line colour
    assert "#1f77b4" in source  # water line colour


def test_unit_operations_list_processes_and_objectives(plant):
    source = flowsheet(plant).source
    assert "Processes" in source and "Objectives" in source
    assert "Rapid Sand Filtration" in source
    assert "Settling" in source


def test_instruments_sit_beside_what_they_observe(plant):
    source = flowsheet(plant).source
    assert "<B>FT</B>" in source and "raw-water-flow" in source
    assert "<B>LT</B>" in source and "clearwell-level" in source
    assert "<B>ZC</B>" in source and "intake-speed" in source
    assert source.count("{rank=same;") == 3
    # The observed flow is shown on its instrument, not as a stream property.
    assert "raw-water-flow-value" not in source
    assert "raw-flow = <B>40,000" in source


def test_systems_become_clusters_and_boundaries_terminals(plant):
    source = flowsheet(plant).source
    assert "subgraph cluster_" in source and "<B>plant</B>" in source
    assert 'shape="cds"' in source and "suction" in source


def test_options_hide_instruments_and_properties(plant):
    source = flowsheet(plant, instruments=False, properties=False).source
    assert "<B>FT</B>" not in source
    assert "raw-flow =" not in source
    assert "rank=same" not in source


def test_source_is_deterministic(plant):
    resolved = plant.resolve()
    assert flowsheet(resolved).source == flowsheet(resolved).source


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz not installed")
def test_renders_svg(plant, tmp_path):
    sheet = flowsheet(plant, title="Plant")
    assert isinstance(sheet, Flowsheet)
    svg = sheet._repr_svg_()
    assert svg is not None and "<svg" in svg
    assert sheet.save(tmp_path / "plant.png").read_bytes()[:4] == b"\x89PNG"
    assert sheet.save(tmp_path / "plant.dot").read_text() == sheet.source


def test_a_model_loaded_from_turtle_draws_the_same_sheet(plant, tmp_path):
    resolved = plant.resolve()
    path = tmp_path / "plant.ttl"
    resolved.graph().serialize(path, format="turtle")
    loaded = Model.from_graph(path)

    def shape(source: str) -> list[str]:
        # Node ids follow iteration order, which RDF does not preserve.
        return sorted(re.sub(r"\b[nj]\d+\b", "#", line) for line in source.splitlines())

    assert shape(flowsheet(loaded).source) == shape(flowsheet(resolved).source)
