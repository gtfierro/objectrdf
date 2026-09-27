"""Portable class and point declaration tests."""

import pytest
from typing import cast

from objectrdf import AmbiguousModelError, Model, choose, connect, default, fixed
from objectrdf.core.errors import ModelingError
from objectrdf.s223 import (
    Chiller,
    ConnectionPoint,
    CoolingCoil,
    Damper,
    Fan,
    OutletConnectionPoint,
    Pump,
    enums,
)


class RecipePump(Pump):
    class_iri = "urn:test:recipes#RecipePump"
    ontology_iri = "urn:test:recipes"
    property_policies = {"label": default("Recipe pump")}
    water = ConnectionPoint.declare(
        count=2,
        medium=fixed(enums.values.Fluid_Water),
        direction=choose("in", "out"),
        label=default("Water port"),
    )


def test_recipe_registers_portable_class_and_point_references():
    with Model("urn:test:model#") as model:
        pump = RecipePump("pump")

    assert pump.label == "Recipe pump"
    assert len(pump.water) == 2
    assert model["pump"].meta.iri == "urn:test:recipes#RecipePump"
    schema = model.export_ontology()
    from rdflib import RDF, URIRef
    from rdflib.namespace import OWL, RDFS

    recipe = URIRef("urn:test:recipes#RecipePump")
    assert (recipe, RDF.type, OWL.Class) in schema
    assert (recipe, RDFS.subClassOf, URIRef(Pump.meta.iri)) in schema


def test_recipe_point_reference_can_be_connected_explicitly():
    with Model("urn:test:model#") as model:
        fan = Fan("fan")
        pump = RecipePump("pump")
        handle = connect(fan, pump.water)

    assert handle.target is pump.water
    # Fan air cannot connect to the recipe's fixed water point.
    assert model.check().status == "unsatisfiable"


def test_operator_authored_connection_can_be_explained_by_endpoints():
    with Model("urn:test:model#") as model:
        damper = Damper("damper")
        fan = Fan("fan")
        damper >> fan

    explanation = model.resolve().explain(damper, fan)
    assert explanation.source_point == "damper-out"
    assert explanation.target_point == "fan-in"


def test_recipe_connects_by_declared_media_and_round_trips():
    class AirWaterCoolingCoil(CoolingCoil):
        class_iri = "urn:test:recipes#AirWaterCoolingCoil"
        ontology_iri = "urn:test:recipes"
        air = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Air),
            direction=choose("in", "out"),
            label=fixed("recipe air"),
        )
        water = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Water),
            direction=choose("in", "out"),
            label=fixed("recipe water"),
        )

    with Model("urn:test:model#") as model:
        fan = Fan("fan")
        coil = AirWaterCoolingCoil("coil")
        chiller = Chiller("chiller")
        air_link = connect(fan, coil.air)
        water_link = connect(chiller, coil.water)

    assert model.check().status == "complete"
    resolved = model.resolve()
    air_point = resolved.point(coil.air)
    water_point = resolved.point(coil.water)
    assert air_point.medium is enums.values.Fluid_Air
    assert water_point.medium is enums.values.Fluid_Water
    assert resolved.explain(air_link).target_point == air_point.name
    assert resolved.explain(water_link).target_point == water_point.name
    from rdflib import Literal, URIRef
    from rdflib.namespace import SH

    schema = model.export_ontology()
    air_label = URIRef(
        "urn:test:recipes#AirWaterCoolingCoilShape/air/label"
    )
    assert (air_label, SH.hasValue, Literal("recipe air")) in schema
    assert model.validate(schema).ok

    loaded = Model.from_graph(
        resolved.graph(), registries=Pump.meta.registry, strict=True
    )
    loaded_coil = cast(AirWaterCoolingCoil, loaded["coil"])
    assert loaded_coil.meta.cls is AirWaterCoolingCoil
    assert loaded_coil.air.name == "air"
    assert loaded_coil.water.name == "water"
    loaded_resolved = loaded.resolve()
    assert loaded_resolved.point(loaded_coil.air).label == "recipe air"
    assert loaded_resolved.point(loaded_coil.water).label == "recipe water"


def test_unconnected_fixed_recipe_point_is_materialized():
    class FixedPointPump(Pump):
        class_iri = "urn:test:recipes#FixedPointPump"
        ontology_iri = "urn:test:recipes"
        outlet = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Water), direction=fixed("out")
        )

    with Model("urn:test:model#") as model:
        pump = FixedPointPump("pump")
        with pytest.raises(ModelingError, match="medium is fixed"):
            pump.outlet.medium = enums.values.Fluid_Air

    resolved = model.resolve()
    point = resolved.point(pump.outlet)
    assert isinstance(point, OutletConnectionPoint)
    assert point.medium is enums.values.Fluid_Water

    loaded = Model.from_graph(
        resolved.graph(), registries=Pump.meta.registry, strict=True
    )
    loaded_pump = cast(FixedPointPump, loaded["pump"])
    assert loaded_pump.meta.cls is FixedPointPump
    assert loaded_pump.outlet.name == "outlet"


def test_unconnected_direction_choice_blocks_strict_resolution():
    class ChoicePointPump(Pump):
        class_iri = "urn:test:recipes#ChoicePointPump"
        ontology_iri = "urn:test:recipes"
        port = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Water), direction=choose("in", "out")
        )

    with Model("urn:test:model#") as model:
        ChoicePointPump("pump")

    assert model.check().status == "underconstrained"
    with pytest.raises(AmbiguousModelError, match="fix a point direction"):
        model.resolve()


def test_interchangeable_group_points_resolve_as_one_choice():
    class GroupedInletPump(Pump):
        class_iri = "urn:test:recipes#GroupedInletPump"
        ontology_iri = "urn:test:recipes"
        inlets = ConnectionPoint.declare(
            count=2,
            medium=fixed(enums.values.Fluid_Water),
            direction=fixed("in"),
        )

    with Model("urn:test:model#") as model:
        pump = GroupedInletPump("pump")
        connect(Chiller("chiller"), pump.inlets)

    assert model.check().status == "complete"
    assert len(model.resolve().point(pump.inlets)) == 2


def test_distinct_same_class_recipe_points_are_ambiguous():
    class TwoInletPump(Pump):
        class_iri = "urn:test:recipes#TwoInletPump"
        ontology_iri = "urn:test:recipes"
        primary = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Water), direction=fixed("in")
        )
        secondary = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Water), direction=fixed("in")
        )

    with Model("urn:test:model#") as model:
        pump = TwoInletPump("pump")
        connect(Chiller("chiller"), pump)

    assert model.check().status == "underconstrained"
    with pytest.raises(AmbiguousModelError, match="ambiguous"):
        model.resolve()


def test_failed_recipe_construction_rolls_back_reserved_names_and_points():
    class RollbackPump(Pump):
        class_iri = "urn:test:recipes#RollbackPump"
        ontology_iri = "urn:test:recipes"
        outlet = ConnectionPoint.declare(
            medium=fixed(enums.values.Fluid_Water), direction=fixed("out")
        )

    with Model("urn:test:model#") as model:
        Pump("pump-outlet")
        with pytest.raises(ModelingError, match="named 'pump-outlet'"):
            RollbackPump("pump")

    assert len(model.entities) == 1
    assert model._port_intents == []
    assert model._reserved_names == set()


def test_policies_preserve_falsey_fixed_values_and_reject_changes():
    class FixedLabelPump(Pump):
        class_iri = "urn:test:recipes#FixedLabelPump"
        ontology_iri = "urn:test:recipes"
        property_policies = {"label": fixed("")}

    with Model("urn:test:model#"):
        pump = FixedLabelPump("pump")
        assert pump.label == ""
        with pytest.raises(ModelingError, match="fixed"):
            pump.label = "changed"
        schema = pump.meta.model.export_ontology()

    from rdflib import Literal, URIRef
    from rdflib.namespace import SH

    shape_property = URIRef(
        "urn:test:recipes#FixedLabelPumpShape/property/label"
    )
    assert (shape_property, SH.hasValue, Literal("")) in schema


def test_inherited_choose_can_be_narrowed_to_fixed():
    class ChoicePump(Pump):
        class_iri = "urn:test:recipes#ChoicePump"
        ontology_iri = "urn:test:recipes"
        property_policies = {"label": choose("A", "B")}

    class NarrowPump(ChoicePump):
        class_iri = "urn:test:recipes#NarrowPump"
        ontology_iri = "urn:test:recipes"
        property_policies = {"label": fixed("A")}

    assert NarrowPump._property_policies["label"] == fixed("A")


def test_mutable_defaults_are_copied_per_instance():
    class DefaultRolePump(Pump):
        class_iri = "urn:test:recipes#DefaultRolePump"
        ontology_iri = "urn:test:recipes"
        property_policies = {"has_role": default([enums.values.Role_Cooling])}

    with Model("urn:test:model#"):
        first = DefaultRolePump("first")
        second = DefaultRolePump("second")
        first.has_role.append(enums.values.Role_Heating)

    assert first.has_role == [enums.values.Role_Cooling, enums.values.Role_Heating]
    assert second.has_role == [enums.values.Role_Cooling]


def test_fixed_inherited_value_cannot_be_overridden():
    class ImmutablePump(Pump):
        class_iri = "urn:test:recipes#ImmutablePump"
        ontology_iri = "urn:test:recipes"
        property_policies = {"label": fixed("A")}

    with pytest.raises(TypeError, match="fixed value"):

        class ConflictPump(ImmutablePump):
            class_iri = "urn:test:recipes#ConflictPump"
            ontology_iri = "urn:test:recipes"
            property_policies = {"label": fixed("B")}
