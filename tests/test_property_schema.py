"""Generated schema values, explicit units, and exact RDF attachment."""

from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
import importlib.util
import sys

import pytest
from rdflib import Literal, RDF, URIRef, XSD
from typing import cast

from objectrdf import (
    Model,
    PropertySchema,
    QuantityDefinition,
    connect,
    quantity_field,
)
from objectrdf.core.errors import ModelingError
from objectrdf.qudt import QuantityAmount as Q, quantity_kinds, units
from objectrdf.watr import enums
from objectrdf.watr import Pump, QuantifiableProperty
from objectrdf.watr.asm2d import (
    AerobicDesign,
    AerobicStage,
    OverallFlowSplit,
    OxygenOutletState,
    PressureState,
    RecyclePump,
)


def test_schema_defaults_documentation_and_immutability():
    design = AerobicDesign(oxygen_transfer_coefficient=10.0)
    assert design.volume == 1333.0
    assert "PER-HR" in design.describe()
    assert "S_O2" in OxygenOutletState.describe()
    with pytest.raises(FrozenInstanceError):
        setattr(design, "volume", 1.0)
    with pytest.raises(TypeError):
        AerobicDesign()  # ty: ignore[missing-argument]
    with pytest.raises(TypeError):
        AerobicDesign(oxygen_transfer_coeficient=10.0)  # ty: ignore[unknown-argument, missing-argument]


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "10"])
def test_schema_rejects_invalid_numeric_values(value):
    with pytest.raises((TypeError, ValueError)):
        AerobicDesign(oxygen_transfer_coefficient=value)


def test_explicit_compatible_unit_is_preserved_and_incompatible_unit_rejected():
    with Model("urn:test:units#") as model:
        stage = AerobicStage("r5")
        properties = stage.outlet.apply_properties(
            OxygenOutletState(oxygen_concentration=Q(0.00191, units.KiloGM_PER_M3))
        )
    prop = cast(QuantifiableProperty, properties["oxygen_concentration"])
    assert prop.has_value == 0.00191
    assert prop.has_unit is units.KiloGM_PER_M3
    assert prop.of_substance is enums.values.Constituent_DissolvedOxygen
    assert prop.of_medium is enums.values.Fluid_Water
    assert prop.has_aspect == [enums.values.Aspect_Nominal]
    assert properties["oxygen_concentration"].name in {
        entity.name for entity in model.resolve()["r5"].outlet._port.has_property
    }
    with pytest.raises(ValueError, match="incompatible unit"):
        OxygenOutletState(oxygen_concentration=Q(1.0, units.SEC))


def test_applications_create_independent_entities_and_reject_name_collisions():
    with Model("urn:test:properties#") as model:
        left, right = AerobicStage("left"), AerobicStage("right")
        design = AerobicDesign(oxygen_transfer_coefficient=10.0)
        first = left.apply_properties(design)
        second = right.apply_properties(design)
        assert first["volume"] is not second["volume"]
        assert (
            cast(QuantifiableProperty, first["volume"]).has_value
            == cast(QuantifiableProperty, second["volume"]).has_value
        )
        count, revision = len(model), model._revision
        with pytest.raises(ValueError, match="duplicate"):
            left.apply_properties(design)
        assert (len(model), model._revision) == (count, revision)
        left.apply_properties(design, prefix="alternate")


@pytest.mark.parametrize("hydrate", [False, True])
def test_application_rolls_back_after_later_property_fails(hydrate):
    @dataclass(frozen=True, kw_only=True)
    class FaultySchema(PropertySchema):
        _definitions = (
            QuantityDefinition(
                "first", "urn:shape:first", quantity_kinds.Volume, units.M3
            ),
            QuantityDefinition(
                "second",
                "urn:shape:second",
                quantity_kinds.Volume,
                units.M3,
                properties=(("unknown_field", 1),),
            ),
        )
        first: float = 1.0
        second: float = 2.0

    with Model("urn:test:rollback#") as model:
        stage = AerobicStage("stage")
        if hydrate:
            model = Model.from_graph(
                model.graph(), registries=AerobicStage.meta.registry
            )
            stage = cast(AerobicStage, model["stage"])
        before_graph = set(model.graph())
        revision = model._revision
        names = set(model._by_name)
        reserved = set(model._reserved_names)
        with pytest.raises(TypeError):
            stage.outlet.apply_properties(FaultySchema())
        assert model._revision == revision
        assert set(model._by_name) == names
        assert model._reserved_names == reserved
        if hydrate:
            assert list(getattr(stage.outlet._port, "has_property")) == []
        else:
            assert stage.outlet._port._properties == []
        assert set(model.graph()) == before_graph


@pytest.mark.parametrize("datatype", [XSD.double, XSD.float, XSD.decimal])
def test_schema_numeric_datatype_survives_export_and_hydration(datatype):
    @dataclass(frozen=True, kw_only=True)
    class NumericSchema(PropertySchema):
        _definitions = (
            QuantityDefinition(
                "volume",
                "urn:shape:volume",
                quantity_kinds.Volume,
                units.M3,
                datatype=str(datatype),
            ),
        )
        volume: float = 1.5

    with Model("urn:test:datatypes#") as model:
        prop = RecyclePump("pump").apply_properties(NumericSchema())["volume"]
    graph = model.graph()
    value = graph.value(
        URIRef(prop.meta.instance_iri),
        URIRef("http://data.ashrae.org/standard223#hasValue"),
    )
    assert isinstance(value, Literal)
    assert value.datatype == datatype
    assert getattr(prop, "has_value") == 1.5
    loaded = Model.from_graph(graph, registries=RecyclePump.meta.registry)
    assert set(loaded.graph()) == set(graph)
    assert getattr(loaded[prop.name], "has_value") == 1.5


def test_schema_applies_to_connection_and_loaded_point_without_relocating():
    with Model("urn:test:subjects#") as model:
        pump, target = RecyclePump("pump"), RecyclePump("target")
        handle = connect(pump.outlet, target.inlet, name="stream")
        properties = handle.apply_properties(
            PressureState(pressure=Q(101325, units.PA))
        )
    resolved = model.resolve()
    assert properties["pressure"].name in {
        prop.name for prop in resolved.connection(handle).has_property
    }
    assert not list(resolved["pump"].outlet._port.has_property)
    loaded = Model.from_graph(resolved.graph(), registries=RecyclePump.meta.registry)
    loaded_pump = loaded["pump"]
    port = getattr(loaded_pump, "outlet")
    port.apply_properties(PressureState(pressure=101325.0))
    assert len(list(port._port.has_property)) == 1
    with pytest.raises(ModelingError, match="immutable"):
        resolved["pump"].apply_properties(PressureState(pressure=101325.0))


def test_fraction_bounds_and_machine_readable_basis():
    with pytest.raises(ValueError, match="<="):
        OverallFlowSplit(fraction=1.1)
    with Model("urn:test:split#") as model:
        pump = RecyclePump("pump")
        split = pump.outlet.apply_properties(OverallFlowSplit(fraction=0.6))["fraction"]
    graph = model.graph()
    subject = URIRef(split.meta.instance_iri)
    assert (
        subject,
        RDF.type,
        URIRef("https://w3id.org/objectrdf/asm2d#SplitFraction"),
    ) in graph
    assert (
        subject,
        URIRef("https://w3id.org/objectrdf/asm2d#hasSplitBasis"),
        URIRef("https://w3id.org/objectrdf/asm2d#OverallFlow"),
    ) in graph


def test_full_asm2d_semantics_validation_and_hydration():
    path = Path(__file__).parents[1] / "examples/watr/asm2d/watertap_asm2d.py"
    spec = importlib.util.spec_from_file_location("test_asm2d_example", path)
    assert spec and spec.loader
    example = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = example
    spec.loader.exec_module(example)
    model = example.build_model()
    resolved = model.resolve()
    from objectrdf.watr import Connection

    connections = [entity for entity in resolved if isinstance(entity, Connection)]
    assert len(connections) == 14
    system = resolved["ASM2d-system"]
    assert len(system.has_member) == 13
    assert len(system.has_boundary_connection_point) == 3
    assert len(resolved["MX1"].feed_water._port.has_property) == 22
    assert resolved["R5-outlet-oxygen-concentration"].has_value == 1.91
    assert model.validate().ok
    graph = resolved.graph()
    loaded = Model.from_graph(graph, registries=AerobicStage.meta.registry)
    assert getattr(loaded["R5"], "outlet")._port.name == "R5-outlet"
    assert set(loaded.graph()) == set(graph)


def test_system_scope_failure_restores_members_ports_and_boundaries():
    with Model("urn:test:system-rollback#") as model:
        original = RecyclePump("original")
        revision = model._revision
        ports = tuple(model._port_intents)
        with pytest.raises(RuntimeError):
            with model.system("system") as system:
                added = RecyclePump("added")
                system.boundary(original.inlet, added.outlet)
                raise RuntimeError("abort")
        assert model.entities == [original]
        assert model._revision == revision
        assert tuple(model._port_intents) == ports


def test_scalar_quantity_capability_and_aspect_are_independent():
    with Model("urn:test:capabilities#") as model:
        pump = RecyclePump("pump")
        static = pump.quantity(
            "static-pressure",
            Q(100000.0, units.PA),
            kind=quantity_kinds.Pressure,
        )
        nominal = pump.outlet.quantity(
            "nominal-pressure",
            101325.0,
            unit=units.PA,
            kind=quantity_kinds.Pressure,
            has_aspect=[enums.values.Aspect_Nominal],
        )
        observable = pump.inlet.quantity(
            "reading",
            Q(100000.0, units.PA),
            kind=quantity_kinds.Pressure,
            capability="observable",
        )
    assert cast(QuantifiableProperty, static).has_aspect == []
    assert cast(QuantifiableProperty, nominal).has_aspect == [
        enums.values.Aspect_Nominal
    ]
    assert observable.meta.iri.endswith("QuantifiableObservableProperty")
    assert cast(QuantifiableProperty, observable).has_aspect == []
    assert model.resolve()["reading"].meta.iri.endswith(
        "QuantifiableObservableProperty"
    )


def test_scalar_quantity_rejects_conflicting_explicit_units_without_mutation():
    with Model("urn:test:scalar-unit#") as model:
        pump = RecyclePump("pump")
        revision = model._revision
        with pytest.raises(ValueError, match="disagree"):
            pump.outlet.quantity(
                "pressure",
                Q(101325.0, units.PA),
                unit=units.BAR,
                kind=quantity_kinds.Pressure,
            )
        assert model._revision == revision


@pytest.mark.parametrize("subject", ["entity", "port", "reference", "connection"])
@pytest.mark.parametrize("capability", ["static", "observable", "actuatable"])
def test_scalar_capabilities_and_aspects_are_consistent_on_all_subjects(
    subject, capability
):
    with Model("urn:test:shared-scalar-api#") as model:
        if subject == "reference":
            target = RecyclePump("pump").outlet
        else:
            pump = Pump("pump")
            if subject == "port":
                target = pump.port("custom-out", direction="out")
            elif subject == "connection":
                target = connect(pump, Pump("other"))
            else:
                target = pump
        prop = target.quantity(
            "pressure",
            Q(101325.0, units.PA),
            kind=quantity_kinds.Pressure,
            capability=capability,
            has_aspect=[enums.values.Aspect_Nominal],
        )
    expected = {
        "static": "QuantifiableProperty",
        "observable": "QuantifiableObservableProperty",
        "actuatable": "QuantifiableActuatableProperty",
    }[capability]
    assert prop.meta.iri.endswith("#" + expected)
    assert getattr(prop, "has_unit") is units.PA
    assert getattr(prop, "has_aspect") == [enums.values.Aspect_Nominal]
    assert model["pressure"] is prop


class RawWater(PropertySchema):
    """Raw-water quality entering a plant."""

    flow_rate: float | Q = quantity_field(
        kind=quantity_kinds.VolumeFlowRate,
        unit=units.M3_PER_DAY,
        label="Influent flow",
        of_medium=enums.values.Fluid_Water,
        aspects=(enums.values.Aspect_Nominal,),
        minimum=0.0,
    )
    turbidity: float | Q = quantity_field(
        kind=quantity_kinds.Turbidity,
        unit=units.NTU,
        of_medium=enums.values.Fluid_Water,
    )
    temperature: float | Q = quantity_field(
        kind=quantity_kinds.Temperature, unit=units.DEG_C, default=15.0
    )


def test_python_schema_is_a_frozen_validated_dataclass():
    raw = RawWater(flow_rate=40_000.0, turbidity=12.0)
    assert raw.temperature == 15.0
    with pytest.raises(FrozenInstanceError):
        setattr(raw, "turbidity", 1.0)
    with pytest.raises(ValueError, match=">= 0.0"):
        RawWater(flow_rate=-1.0, turbidity=12.0)
    with pytest.raises(TypeError):
        RawWater(flow_rate=1.0)  # ty: ignore[missing-argument]
    description = RawWater.describe()
    assert "Raw-water quality" in description
    assert "turbidity: Turbidity" in description
    assert "default=15.0" in description


def test_python_schema_applies_like_a_generated_one():
    with Model("urn:test:python-schema#") as model:
        pump = Pump("intake")
        properties = pump.apply_properties(
            RawWater(flow_rate=40_000.0, turbidity=Q(12.0, units.NTU)),
            prefix="raw",
        )
    assert list(properties) == ["flow_rate", "turbidity", "temperature"]
    flow = properties["flow_rate"]
    assert flow.name == "raw-flow-rate"
    assert isinstance(flow, QuantifiableProperty)
    assert flow.label == "Influent flow"
    assert flow.of_medium is enums.values.Fluid_Water
    assert list(flow.has_aspect) == [enums.values.Aspect_Nominal]
    graph = model.graph()
    turbidity = URIRef(model.namespace + "raw-turbidity")
    assert (URIRef(model.namespace + "intake"), None, turbidity) in graph
    assert any(str(unit).endswith("/NTU") for unit in graph.objects(turbidity, None))


def test_python_schema_fields_must_declare_quantities():
    with pytest.raises(TypeError, match="declare count with quantity_field"):

        class Counted(PropertySchema):
            count: float = 1.0
