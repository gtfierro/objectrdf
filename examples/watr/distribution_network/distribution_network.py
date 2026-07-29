"""Build a small water-distribution network directly in objectrdf.

Unlike the EPANET example, this script has no input file.  The nodes, pipes,
and instruments below are the source of truth, so the model can also serve as
a compact topology authoring example.

Topology:

                          elevated tank
                               |
    reservoir -> pump -> header -> north
                            \\        \\
                             south -> east -> delivery
"""

from objectrdf import Model
from objectrdf.qudt import quantity_kinds, units
from objectrdf.watr import (
    FlowSensor,
    Junction,
    LevelSensor,
    PressureSensor,
    Pump,
    QuantifiableObservableProperty,
    Reservoir,
    Tank,
    TemperatureSensor,
    TurbidityMeter,
    WaterOutlet,
    enums,
)

NAMESPACE = "urn:example/distribution-network#"
WATER = enums.Fluid_Water


def build_model() -> Model:
    """Create the distribution topology and its monitoring points."""
    model = Model(
        NAMESPACE,
        name="Example municipal water distribution network",
        prefixes={
            "s223": "http://data.ashrae.org/standard223#",
            "watr": "urn:nawi-water-ontology#",
        },
    )

    with model:
        # ------------------------------------------------------------------
        # 1. Network assets
        # ------------------------------------------------------------------
        reservoir = Reservoir("reservoir", label="Clearwell reservoir")
        pump = Pump("high-service-pump", label="High-service pump")
        tank = Tank("elevated-tank", label="North elevated tank")
        delivery = WaterOutlet(
            "neighborhood-delivery",
            label="Neighborhood delivery point",
        )

        header = Junction("header", label="Pump station header", has_medium=WATER)
        north = Junction("north", label="North branch junction", has_medium=WATER)
        south = Junction("south", label="South branch junction", has_medium=WATER)
        east = Junction("east", label="East merge junction", has_medium=WATER)

        # ------------------------------------------------------------------
        # 2. Topology
        # ------------------------------------------------------------------
        # The >> operator reads in the direction of nominal water flow.
        # objectrdf retains these as connection intentions and infers the
        # concrete connection-point annotations when the model is resolved.
        reservoir >> pump >> header

        # Two paths leave the header...
        header >> north
        header >> south

        # ...and rejoin at the east junction before delivery.
        north >> east
        south >> east
        east >> delivery

        # Storage branches from the north side of the network.
        north >> tank

        # ------------------------------------------------------------------
        # 3. Hydraulic monitoring
        # ------------------------------------------------------------------
        discharge_flow = QuantifiableObservableProperty(
            "pump-discharge-flow-value",
            label="Pump discharge flow",
            has_quantity_kind=quantity_kinds.VolumeFlowRate,
            has_unit=units.GAL_US_PER_MIN,
            of_medium=WATER,
        )
        header.has_property.add(discharge_flow)
        FlowSensor(
            "pump-discharge-flow-sensor",
            label="Pump discharge flow sensor",
            has_observation_location=header,
            observes=discharge_flow,
        )

        station_pressure = QuantifiableObservableProperty(
            "station-pressure-value",
            label="Pump station pressure",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        header.has_property.add(station_pressure)
        PressureSensor(
            "station-pressure-sensor",
            label="Pump station pressure sensor",
            has_observation_location=header,
            observes=station_pressure,
        )

        east_pressure = QuantifiableObservableProperty(
            "east-pressure-value",
            label="East merge pressure",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        east.has_property.add(east_pressure)
        PressureSensor(
            "east-pressure-sensor",
            label="East merge pressure sensor",
            has_observation_location=east,
            observes=east_pressure,
        )

        delivery_pressure = QuantifiableObservableProperty(
            "delivery-pressure-value",
            label="Delivery pressure",
            has_quantity_kind=quantity_kinds.Pressure,
            has_unit=units.PSI,
            of_medium=WATER,
        )
        delivery.has_property.add(delivery_pressure)
        PressureSensor(
            "delivery-pressure-sensor",
            label="Delivery pressure sensor",
            has_observation_location=delivery,
            observes=delivery_pressure,
        )

        tank_level = QuantifiableObservableProperty(
            "tank-level-value",
            label="Elevated tank level",
            has_quantity_kind=quantity_kinds.Length,
            has_unit=units.FT,
            of_medium=WATER,
        )
        tank.has_property.add(tank_level)
        LevelSensor(
            "tank-level-sensor",
            label="Elevated tank level sensor",
            has_observation_location=tank,
            observes=tank_level,
        )

        # ------------------------------------------------------------------
        # 4. Water-quality monitoring
        # ------------------------------------------------------------------
        source_turbidity = QuantifiableObservableProperty(
            "source-turbidity-value",
            label="Source turbidity",
            has_quantity_kind=quantity_kinds.Turbidity,
            has_unit=units.NTU,
            of_medium=WATER,
        )
        reservoir.has_property.add(source_turbidity)
        TurbidityMeter(
            "source-turbidity-meter",
            label="Source turbidity meter",
            has_observation_location=reservoir,
            observes=source_turbidity,
        )

        tank_temperature = QuantifiableObservableProperty(
            "tank-temperature-value",
            label="Tank water temperature",
            has_quantity_kind=quantity_kinds.Temperature,
            has_unit=units.DEG_C,
            of_medium=WATER,
        )
        tank.has_property.add(tank_temperature)
        TemperatureSensor(
            "tank-temperature-sensor",
            label="Tank water temperature sensor",
            has_observation_location=tank,
            observes=tank_temperature,
        )

    return model


def main() -> None:
    model = build_model()
    print(f"authored distribution network with {len(model)} named entities")


if __name__ == "__main__":
    main()
