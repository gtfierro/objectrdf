"""Generated example domains preserve topology, quantities, and base behavior."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import cast

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import SH

from objectrdf import Model
from objectrdf.gen import compile_modules
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.s223 import AirHandlingUnit, enums as s223_enums
from objectrdf.s223.hvac import AirWaterCoolingCoil
from objectrdf.watr import (
    ChlorinationUnit,
    CoagulationBasin,
    Connection,
    FlocculationBasin,
    OutletConnectionPoint,
    Pipe,
    RapidSandFilter,
    SedimentationTank,
    Sensor,
    System,
    drinking_water,
    enums,
)
from objectrdf.watr.drinking_water import ClarificationStage, CoagulationStage
from objectrdf.watr.seawater_ro import MembraneDesign, ROStage

ROOT = Path(__file__).parents[1]
S223 = Namespace("http://data.ashrae.org/standard223#")
RO = Namespace("https://w3id.org/objectrdf/seawater-ro#")


def example(relative: str):
    path = ROOT / "examples" / relative
    name = "example_" + path.stem
    spec = spec_from_file_location(name, path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "source,name,package",
    [
        ("hvac.ttl", "HVAC", "s223/hvac"),
        ("seawater-ro.ttl", "SeawaterRO", "watr/seawater_ro"),
        ("drinking-water.ttl", "DrinkingWater", "watr/drinking_water"),
    ],
)
def test_example_domain_regeneration_is_deterministic(source, name, package):
    path = ROOT / "ontology" / source
    first = compile_modules(Graph().parse(path), name=name, source=f"ontology/{source}")
    second = compile_modules(
        Graph().parse(path), name=name, source=f"ontology/{source}"
    )
    assert first == second
    for filename, text in first.items():
        assert (ROOT / "src/objectrdf" / package / filename).read_text() == text


def test_generated_coil_inherits_containment_and_restores_all_four_ports():
    with Model("urn:test:generated-coil#") as model:
        with AirHandlingUnit("ahu") as ahu:
            coil = AirWaterCoolingCoil("coil")
    assert coil in ahu.contains_
    resolved = model.resolve()
    assert len(resolved["coil"].ports) == 4
    loaded = Model.from_graph(resolved.graph(), registries=coil.meta.registry)
    restored = cast(AirWaterCoolingCoil, loaded["coil"])
    assert restored.air_inlet.medium is s223_enums.values.Fluid_Air
    assert restored.water_outlet.medium is s223_enums.values.Fluid_Water
    assert set(loaded.graph()) == set(resolved.graph())


def test_conventional_treatment_train_uses_watr_equipment_and_separates_residuals():
    model = example("watr/treatment/watr_quickstart.py").build_model()
    resolved = model.compile()
    plant = resolved["treatment-system"]
    assert isinstance(plant, System)
    expected = {
        "coagulation": (CoagulationBasin, "Process_Coagulation"),
        "flocculation": (FlocculationBasin, "Process_Flocculation"),
        "clarifier": (SedimentationTank, "Process_Settling"),
        "sand-filter": (RapidSandFilter, "Process_RapidSandFiltration"),
        "chlorination-contact": (ChlorinationUnit, "Process_Chlorination"),
    }
    assert {member.name for member in plant.has_member} == set(expected)
    for name, (equipment, process) in expected.items():
        stage = resolved[name]
        assert isinstance(stage, equipment)
        assert {term.__name__ for term in stage.has_process} == {process}
        assert stage.has_treatment_objective

    expected_links = {
        "coagulated-water": ("coagulation-outlet", "flocculation-inlet"),
        "flocculated-water": ("flocculation-outlet", "clarifier-inlet"),
        "clarified-water": ("clarifier-clarified_water", "sand-filter-inlet"),
        "filtered-water": (
            "sand-filter-filtered_water",
            "chlorination-contact-inlet",
        ),
    }
    pipes = [item for item in resolved if isinstance(item, Pipe)]
    assert {pipe.name for pipe in pipes} == set(expected_links)
    for pipe in pipes:
        assert {point.name for point in pipe.connects_at} == set(
            expected_links[pipe.name]
        )
        assert pipe.medium is enums.values.Fluid_Water
    assert {point.name for point in plant.has_boundary_connection_point} == {
        "coagulation-inlet",
        "chlorination-contact-outlet",
        "clarifier-sludge",
        "sand-filter-backwash_supply",
        "sand-filter-backwash_waste",
    }
    assert resolved["clarifier"].sludge.medium is enums.values.Fluid_Sludge
    assert resolved["sand-filter"].backwash_supply.medium is enums.values.Fluid_Water
    assert resolved["sand-filter"].backwash_waste.medium is enums.values.Fluid_Water

    graph = resolved.graph()
    assert "REGISTRY" in drinking_water.__all__
    loaded = Model.from_graph(graph, registries=drinking_water.REGISTRY)
    clarifier = loaded["clarifier"]
    assert isinstance(clarifier, ClarificationStage)
    assert clarifier.sludge.medium is enums.values.Fluid_Sludge
    assert set(loaded.graph()) == set(graph)


def test_treatment_stage_source_constraints_are_enforced_after_loading():
    model = example("watr/treatment/watr_quickstart.py").build_model()
    assert model.validate(infer=False).ok
    graph = model.graph()
    graph.remove(
        (
            URIRef("urn:example/treatment#clarifier"),
            URIRef("https://watermetadata.org/ontology/watr#hasProcess"),
            None,
        )
    )
    loaded = Model.from_graph(graph, registries=CoagulationStage.meta.registry)
    # Hydration must preserve authored facts, not silently restore required
    # process terms from the configuration's constructive defaults.
    clarifier = loaded["clarifier"]
    assert isinstance(clarifier, ClarificationStage)
    assert not clarifier.has_process
    # WaTr's own SHACL-AF rules can infer class-required processes. Disable
    # those rules here to validate only the facts supplied in the graph.
    assert not loaded.validate(infer=False).ok


def test_quantity_shape_fixed_labels_distinguish_same_kind_fields():
    with Model("urn:test:membrane-labels#") as model:
        stage = ROStage("ro")
        properties = stage.apply_properties(
            MembraneDesign(
                membrane_area=13914.0,
                spacer_porosity=0.97,
                channel_height=Q(1e-3, units.M),
                stage_width=Q(1000.0, units.M),
                salt_permeability=3.5e-8,
            )
        )
    assert properties["channel_height"].label == "Membrane channel height"
    assert properties["stage_width"].label == "Membrane width per stage"
    assert model.validate().ok
    loaded = Model.from_graph(model.graph(), registries=stage.meta.registry)
    loaded[properties["channel_height"].name].label = "Incorrect channel label"
    assert not loaded.validate().ok


def test_compiler_rejects_unlinked_quantity_property_class():
    graph = Graph().parse(ROOT / "ontology/seawater-ro.ttl")
    graph.set((RO.MembraneDesign_channel_heightShape, SH["class"], RO.UnknownProperty))
    with pytest.raises(ValueError, match="unlinked quantity property class"):
        compile_modules(graph, name="Invalid")


def test_full_ro_preserves_connections_design_values_and_paired_circuits():
    module = example("watr/seawater_ro/watertap_seawater_ro_full.py")
    model = module.build_model()
    resolved = model.resolve()
    connections = [item for item in resolved if isinstance(item, Connection)]
    assert len(connections) == 27
    assert len(resolved["seawater-ro-system"].has_member) == 26
    assert len(resolved["seawater-ro-system"].has_boundary_connection_point) == 2
    expected = {
        "influent-flow-rate": (7.05e6, units.GAL_US_PER_DAY),
        "influent-tds-concentration": (35.0, units.GM_PER_L),
        "influent-tss-concentration": (0.03, units.GM_PER_L),
        "reverse-osmosis-membrane-area": (13914.0, units.M2),
        "reverse-osmosis-channel-height": (1e-3, units.M),
        "reverse-osmosis-stage-width": (1000.0, units.M),
        "pump-1-operating-pressure": (70e5, units.PA),
        "pump-2-efficiency": (0.8, units.UNITLESS),
        "pressure-exchanger-efficiency": (0.95, units.UNITLESS),
        "uv-aop-reduction-equivalent-dose": (0.35, units.J_PER_CentiM2),
        "reverse-osmosis-permeate-side-pressure": (101325.0, units.PA),
    }
    for name, (value, unit) in expected.items():
        assert getattr(resolved[name], "has_value") == value
        assert getattr(resolved[name], "has_unit") is unit
        assert enums.values.Aspect_Nominal in getattr(resolved[name], "has_aspect")
    for circuit in ("feed", "brine"):
        inlet = resolved[f"pxr-{circuit}-in"]
        outlet = resolved[f"pxr-{circuit}-out"]
        assert getattr(inlet, "paired_with") is outlet
        assert getattr(outlet, "paired_with") is inlet
    assert resolved["reverse-osmosis-permeate-side-pressure"] in (
        resolved["ro-permeate"].has_property
    )
    assert model.validate().ok
    graph = resolved.graph()
    loaded = Model.from_graph(graph, registries=ROStage.meta.registry)
    assert set(loaded.graph()) == set(graph)
    assert (
        getattr(loaded["media-filtration"], "backwash").medium
        is enums.values.Fluid_Water
    )


def test_pretreatment_retains_seawater_and_separates_product_from_backwash():
    module = example(
        "watr/seawater_ro_pretreatment/watertap_seawater_ro_pretreatment.py"
    )
    model = module.build_model()
    resolved = model.resolve()
    outputs = [
        port
        for port in resolved["media-filtration"].ports
        if isinstance(port, OutletConnectionPoint)
    ]
    assert len(outputs) == 2
    assert {port.medium for port in outputs} == {enums.values.Water_Seawater}
    assert len(resolved["pretreatment-system"].has_member) == 9
    assert len(resolved["pretreatment-system"].has_boundary_connection_point) == 3
    assert getattr(resolved["storage-tank-1-residence-time"], "has_value") == 2.0
    assert model.validate().ok


@pytest.mark.parametrize(
    "flow_units,flow_unit,length_unit",
    [
        ("GPM", units.GAL_US_PER_MIN, units.FT),
        ("LPS", units.L_PER_SEC, units.M),
    ],
)
def test_epanet_converter_preserves_source_units_and_valueless_observables(
    tmp_path, flow_units, flow_unit, length_unit
):
    module = example("watr/epanet_anytown/epanet_anytown_to_watr.py")
    source = tmp_path / "mini.inp"
    source.write_text(f"""[OPTIONS]
UNITS {flow_units}
[JUNCTIONS]
j1 100 20
j2 110 10
[RESERVOIRS]
r1 150
[TANKS]
t1 120 10 0 20 30 0
[PIPES]
p1 j1 j2 100 12 100
p2 j2 t1 200 12 100
[PUMPS]
pump1 r1 j1 HEAD curve1
[END]
""")
    model, counts = module.build_watr_model(module.parse_epanet(source))
    resolved = model.resolve()
    assert counts["nodes"] == 4
    assert getattr(resolved["base-demand-j1"], "has_value") == 20.0
    assert getattr(resolved["base-demand-j1"], "has_unit") is flow_unit
    assert getattr(resolved["length-p1"], "has_unit") is length_unit
    graph = resolved.graph()
    observed = list(graph.subjects(S223.hasValue, Literal(20.0)))
    assert observed
    sensors = [item for item in model if isinstance(item, Sensor)]
    assert sensors
    for sensor in sensors:
        prop = getattr(sensor, "observes")
        assert (URIRef(prop.meta.instance_iri), S223.hasValue, None) not in graph


@pytest.mark.parametrize(
    "path,system",
    [
        ("watr/distribution_network/distribution_network.py", "distribution-system"),
        ("watr/epanet_anytown/anytown_direct.py", "anytown-system"),
    ],
)
def test_monitoring_examples_collect_system_members_without_fabricating_readings(
    path, system
):
    model = example(path).build_model()
    assert list(getattr(model[system], "has_member"))
    sensors = [item for item in model if isinstance(item, Sensor)]
    assert sensors
    for sensor in sensors:
        prop = getattr(sensor, "observes")
        assert getattr(prop, "has_value") is None
