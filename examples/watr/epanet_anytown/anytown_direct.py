"""Author the Anytown distribution network directly in objectrdf.

This version intentionally does not read ``Anytown.inp``.  It keeps the
network assets, topology, and monitoring plan together as ordinary Python.
The topology is Thomas M. Walski's "01 Anytown" network (2016), available
under CC BY-NC 4.0 from https://uknowledge.uky.edu/wdst_models/1/.
"""

from objectrdf import Model
from objectrdf.qudt import quantity_kinds, units
from objectrdf.watr import (
    FlowSensor,
    Junction,
    PressureSensor,
    Pump,
    QuantifiableObservableProperty,
    Reservoir,
    TemperatureSensor,
    TurbidityMeter,
    enums,
)

NAMESPACE = "urn:example/epanet/anytown-direct#"
WATER = enums.Fluid_Water


def build_model() -> Model:
    """Create Anytown's distribution topology and monitoring points."""
    model = Model(
        NAMESPACE,
        name="Directly authored Anytown distribution network",
        prefixes={
            "s223": "http://data.ashrae.org/standard223#",
            "watr": "urn:nawi-water-ontology#",
        },
    )

    with model:
        # ------------------------------------------------------------------
        # 1. Sources and pumping
        # ------------------------------------------------------------------
        reservoir_10 = Reservoir("reservoir-10", label="Low reservoir 10")
        reservoir_65 = Reservoir("reservoir-65", label="North reservoir 65")
        reservoir_165 = Reservoir("reservoir-165", label="West reservoir 165")
        pump_82 = Pump("pump-82", label="High-service pump 82")

        # ------------------------------------------------------------------
        # 2. Distribution junctions
        # ------------------------------------------------------------------
        j20 = Junction("junction-20", label="Junction 20", has_medium=WATER)
        j30 = Junction("junction-30", label="Junction 30", has_medium=WATER)
        j40 = Junction("junction-40", label="Junction 40", has_medium=WATER)
        j50 = Junction("junction-50", label="Junction 50", has_medium=WATER)
        j55 = Junction("junction-55", label="Junction 55", has_medium=WATER)
        j60 = Junction("junction-60", label="Junction 60", has_medium=WATER)
        j70 = Junction("junction-70", label="Junction 70", has_medium=WATER)
        j75 = Junction("junction-75", label="Junction 75", has_medium=WATER)
        j80 = Junction("junction-80", label="Junction 80", has_medium=WATER)
        j90 = Junction("junction-90", label="Junction 90", has_medium=WATER)
        j100 = Junction("junction-100", label="Junction 100", has_medium=WATER)
        j110 = Junction("junction-110", label="Junction 110", has_medium=WATER)
        j115 = Junction("junction-115", label="Junction 115", has_medium=WATER)
        j120 = Junction("junction-120", label="Junction 120", has_medium=WATER)
        j130 = Junction("junction-130", label="Junction 130", has_medium=WATER)
        j140 = Junction("junction-140", label="Junction 140", has_medium=WATER)
        j150 = Junction("junction-150", label="Junction 150", has_medium=WATER)
        j160 = Junction("junction-160", label="Junction 160", has_medium=WATER)
        j170 = Junction("junction-170", label="Junction 170", has_medium=WATER)

        # ------------------------------------------------------------------
        # 3. Topology
        # ------------------------------------------------------------------
        # Main supplies. Reservoir 10 supplies the network through pump 82;
        # the two high-head reservoirs connect at junctions 60 and 160.
        reservoir_10 >> pump_82 >> j20
        reservoir_65 >> j60
        reservoir_165 >> j160

        # Long mains leaving the pump station.
        j20 >> j70
        j20 >> j30
        j20 >> j110

        # Central grid.
        j70 >> j30
        j70 >> j100
        j70 >> j90
        j70 >> j60
        j90 >> j60
        j60 >> j80
        j90 >> j80
        j90 >> j150
        j90 >> j100
        j100 >> j150
        j150 >> j80

        # North and northwest grid.
        j60 >> j30
        j30 >> j40
        j30 >> j50
        j40 >> j50
        j50 >> j80
        j50 >> j55
        j55 >> j75

        # Southern and eastern grid.
        j80 >> j140
        j150 >> j140
        j150 >> j160
        j100 >> j160
        j100 >> j110
        j110 >> j160
        j110 >> j120
        j120 >> j160
        j120 >> j130
        j130 >> j160
        j130 >> j170
        j160 >> j140
        j170 >> j140
        j50 >> j140

        # Western loop.
        j140 >> j115
        j140 >> j75
        j115 >> j75

        # ------------------------------------------------------------------
        # 4. Hydraulic monitoring
        # ------------------------------------------------------------------
        pump_flow = QuantifiableObservableProperty(
            "pump-82-flow-value",
            label="Pump 82 discharge flow",
            has_quantity_kind=quantity_kinds.VolumeFlowRate,
            has_unit=units.GAL_US_PER_MIN,
            of_medium=WATER,
        )
        j20.has_property.add(pump_flow)
        FlowSensor(
            "pump-82-flow-sensor",
            label="Pump 82 discharge flow sensor",
            has_observation_location=j20,
            observes=pump_flow,
        )

        north_supply_flow = QuantifiableObservableProperty(
            "reservoir-65-flow-value",
            label="Reservoir 65 supply flow",
            has_quantity_kind=quantity_kinds.VolumeFlowRate,
            has_unit=units.GAL_US_PER_MIN,
            of_medium=WATER,
        )
        j60.has_property.add(north_supply_flow)
        FlowSensor(
            "reservoir-65-flow-sensor",
            label="Reservoir 65 supply flow sensor",
            has_observation_location=j60,
            observes=north_supply_flow,
        )

        west_supply_flow = QuantifiableObservableProperty(
            "reservoir-165-flow-value",
            label="Reservoir 165 supply flow",
            has_quantity_kind=quantity_kinds.VolumeFlowRate,
            has_unit=units.GAL_US_PER_MIN,
            of_medium=WATER,
        )
        j160.has_property.add(west_supply_flow)
        FlowSensor(
            "reservoir-165-flow-sensor",
            label="Reservoir 165 supply flow sensor",
            has_observation_location=j160,
            observes=west_supply_flow,
        )

        pressure_20 = QuantifiableObservableProperty(
            "junction-20-pressure-value",
            label="Pressure at junction 20",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        j20.has_property.add(pressure_20)
        PressureSensor(
            "junction-20-pressure-sensor",
            label="Junction 20 pressure sensor",
            has_observation_location=j20,
            observes=pressure_20,
        )

        pressure_70 = QuantifiableObservableProperty(
            "junction-70-pressure-value",
            label="Pressure at junction 70",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        j70.has_property.add(pressure_70)
        PressureSensor(
            "junction-70-pressure-sensor",
            label="Junction 70 pressure sensor",
            has_observation_location=j70,
            observes=pressure_70,
        )

        pressure_100 = QuantifiableObservableProperty(
            "junction-100-pressure-value",
            label="Pressure at junction 100",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        j100.has_property.add(pressure_100)
        PressureSensor(
            "junction-100-pressure-sensor",
            label="Junction 100 pressure sensor",
            has_observation_location=j100,
            observes=pressure_100,
        )

        pressure_140 = QuantifiableObservableProperty(
            "junction-140-pressure-value",
            label="Pressure at junction 140",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        j140.has_property.add(pressure_140)
        PressureSensor(
            "junction-140-pressure-sensor",
            label="Junction 140 pressure sensor",
            has_observation_location=j140,
            observes=pressure_140,
        )

        pressure_160 = QuantifiableObservableProperty(
            "junction-160-pressure-value",
            label="Pressure at junction 160",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        j160.has_property.add(pressure_160)
        PressureSensor(
            "junction-160-pressure-sensor",
            label="Junction 160 pressure sensor",
            has_observation_location=j160,
            observes=pressure_160,
        )

        # ------------------------------------------------------------------
        # 5. Water-quality monitoring
        # ------------------------------------------------------------------
        source_turbidity = QuantifiableObservableProperty(
            "reservoir-10-turbidity-value",
            label="Reservoir 10 turbidity",
            has_quantity_kind=quantity_kinds.Turbidity,
            has_unit=units.NTU,
            of_medium=WATER,
        )
        reservoir_10.has_property.add(source_turbidity)
        TurbidityMeter(
            "reservoir-10-turbidity-meter",
            label="Reservoir 10 turbidity meter",
            has_observation_location=reservoir_10,
            observes=source_turbidity,
        )

        north_turbidity = QuantifiableObservableProperty(
            "reservoir-65-turbidity-value",
            label="Reservoir 65 turbidity",
            has_quantity_kind=quantity_kinds.Turbidity,
            has_unit=units.NTU,
            of_medium=WATER,
        )
        reservoir_65.has_property.add(north_turbidity)
        TurbidityMeter(
            "reservoir-65-turbidity-meter",
            label="Reservoir 65 turbidity meter",
            has_observation_location=reservoir_65,
            observes=north_turbidity,
        )

        west_turbidity = QuantifiableObservableProperty(
            "reservoir-165-turbidity-value",
            label="Reservoir 165 turbidity",
            has_quantity_kind=quantity_kinds.Turbidity,
            has_unit=units.NTU,
            of_medium=WATER,
        )
        reservoir_165.has_property.add(west_turbidity)
        TurbidityMeter(
            "reservoir-165-turbidity-meter",
            label="Reservoir 165 turbidity meter",
            has_observation_location=reservoir_165,
            observes=west_turbidity,
        )

        network_temperature = QuantifiableObservableProperty(
            "junction-100-temperature-value",
            label="Water temperature at junction 100",
            has_quantity_kind=quantity_kinds.Temperature,
            has_unit=units.DEG_C,
            of_medium=WATER,
        )
        j100.has_property.add(network_temperature)
        TemperatureSensor(
            "junction-100-temperature-sensor",
            label="Junction 100 water temperature sensor",
            has_observation_location=j100,
            observes=network_temperature,
        )

    return model


def main() -> None:
    model = build_model()
    print(f"authored Anytown with {len(model)} named entities")


if __name__ == "__main__":
    main()
