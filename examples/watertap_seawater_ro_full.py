"""Author WaTr/S223 graphs inspired by a seawater-RO reference flowsheet.

This is a semantic topology and nominal-design description, not a WaterTAP
simulation model. A WaTr/S223-to-WaterTAP translator is future work.

Source:
https://watertap.readthedocs.io/en/latest/technical_reference/flowsheets/
seawater_RO_desalination.html#full-flowsheet
"""

from pathlib import Path

from objectrdf import (
    ConnectionHandle,
    Entity,
    Model,
    ResolvedModel,
    TermValue,
    connect,
)
from objectrdf.qudt import quantity, quantity_kinds, stream_state, units
from objectrdf.watr import (
    CartridgeFiltrationUnit,
    ChlorinationUnit,
    CoagulationBasin,
    Connection,
    Equipment,
    MediaFiltration,
    OutletConnectionPoint,
    PressureExchanger,
    Process,
    Process_AdvancedOxidation,
    Process_Backwashing,
    Process_ChemicalAddition,
    Process_Chlorination,
    Process_Coagulation,
    Process_Filtration,
    Process_MediaFiltration,
    Process_Mixing,
    Process_ReverseOsmosis,
    Process_Separation,
    Property,
    Pump,
    QuantifiableProperty,
    Reactor,
    ReverseOsmosisMembrane,
    StaticMixer,
    Tank,
    UVH2O2Reactor,
    UnitProcess,
    enums,
)


def nominal_quantity(
    name: str,
    label: str,
    value: float,
    unit: TermValue,
    quantity_kind: TermValue,
    *,
    of: Entity | ConnectionHandle,
) -> QuantifiableProperty:
    """Attach a fixed nominal design property to equipment or a flow."""
    return quantity(
        QuantifiableProperty,
        name,
        value,
        unit,
        quantity_kind,
        of=of,
        label=label,
        has_aspect=[enums.Aspect_Nominal],
    )


def process(
    cls: type[Process],
    name: str,
    definition: str,
) -> Process:
    """Create a WaTr process with the definition required by its shape."""
    return cls(name, definition=definition)


def build_model() -> Model:
    """Build the pressure-exchanger WaTr/S223 reference configuration."""
    model = Model(
        "urn:example/watertap/seawater-ro/full#",
        name="WaTr seawater RO reference",
    )

    with model:
        # Flowsheet feed. The known outlet is the sole seawater boundary hint
        # needed by the affinity solver for pretreatment and the RO feed path.
        feed = Equipment("feed", label="Seawater feed")
        feed_out = OutletConnectionPoint(
            "feed-seawater-out",
            has_medium=enums.Water_Seawater,
            is_connection_point_of=feed,
        )
        influent = stream_state(feed_out, medium=enums.Water_Seawater)
        influent.quantity(
            QuantifiableProperty,
            "influent-flow-rate",
            7.05e6,
            units.GAL_US_PER_DAY,
            quantity_kinds.VolumeFlowRate,
            label="Influent flow rate",
            has_aspect=[enums.Aspect_Nominal],
        )
        influent.quantity(
            QuantifiableProperty,
            "influent-tds-concentration",
            35.0,
            units.GM_PER_L,
            quantity_kinds.MassConcentration,
            substance=enums.Constituent_Salt,
            label="Influent total dissolved solids concentration",
            has_aspect=[enums.Aspect_Nominal],
        )
        influent.quantity(
            QuantifiableProperty,
            "influent-tss-concentration",
            0.03,
            units.GM_PER_L,
            quantity_kinds.MassConcentration,
            substance=enums.Constituent_SuspendedSolids,
            label="Influent total suspended solids concentration",
            has_aspect=[enums.Aspect_Nominal],
        )
        influent.quantity(
            QuantifiableProperty,
            "influent-temperature",
            298.0,
            units.K,
            quantity_kinds.Temperature,
            label="Influent temperature",
            has_aspect=[enums.Aspect_Nominal],
        )
        influent.quantity(
            QuantifiableProperty,
            "influent-pressure",
            100000.0,
            units.PA,
            quantity_kinds.Pressure,
            label="Influent pressure",
            has_aspect=[enums.Aspect_Nominal],
        )

        # Pretreatment.
        intake = Pump("intake", label="Seawater intake")
        ferric_chloride_addition = CoagulationBasin(
            "ferric-chloride-addition",
            label="Ferric chloride addition",
            has_process=[
                process(
                    Process_Coagulation,
                    "ferric-chloride-addition-process",
                    "Add 20 mg/L ferric chloride to promote coagulation.",
                )
            ],
        )
        chlorination = ChlorinationUnit(
            "chlorination",
            has_process=[
                process(
                    Process_Chlorination,
                    "chlorination-process",
                    "Disinfect the seawater by chlorination.",
                )
            ],
        )
        static_mixer = StaticMixer(
            "static-mixer",
            label="Static mixer",
            has_process=[
                process(
                    Process_Mixing,
                    "static-mixing-process",
                    "Mix added treatment chemicals into the seawater.",
                )
            ],
        )
        storage_tank_1 = Tank(
            "storage-tank-1",
            label="Pretreatment storage tank",
        )
        nominal_quantity(
            "storage-tank-1-residence-time",
            "Nominal residence time",
            2.0,
            units.HR,
            quantity_kinds.Time,
            of=storage_tank_1,
        )
        media_filtration = MediaFiltration(
            "media-filtration",
            label="Media filtration",
            has_process=[
                process(
                    Process_MediaFiltration,
                    "media-filtration-process",
                    "Remove suspended matter by filtration through media.",
                )
            ],
        )
        media_product_out = media_filtration.port(
            "media-filtration-product-out",
            direction="out",
        )
        media_backwash_out = media_filtration.port(
            "media-filtration-backwash-out",
            direction="out",
        )
        antiscalant_addition = Reactor(
            "antiscalant-addition",
            label="Antiscalant addition",
            has_process=[
                process(
                    Process_ChemicalAddition,
                    "antiscalant-addition-process",
                    "Add antiscalant before cartridge filtration.",
                )
            ],
        )
        cartridge_filtration = CartridgeFiltrationUnit(
            "cartridge-filtration",
            label="Cartridge filtration",
            has_process=[
                process(
                    Process_Filtration,
                    "cartridge-filtration-process",
                    "Polish the pretreated seawater by cartridge filtration.",
                )
            ],
        )
        backwash_handling = UnitProcess(
            "backwash-handling",
            label="Media-filter backwash handling",
            has_process=[
                process(
                    Process_Backwashing,
                    "backwash-handling-process",
                    "Collect and handle backwash from media filtration.",
                )
            ],
        )
        landfill = Equipment("landfill", label="Landfill")

        (
            feed
            >> intake
            >> ferric_chloride_addition
            >> chlorination
            >> static_mixer
            >> storage_tank_1
            >> media_filtration
        )
        connect(
            media_product_out,
            antiscalant_addition,
            name="media-filtration--antiscalant-addition",
        )
        antiscalant_addition >> cartridge_filtration

        backwash = connect(
            media_backwash_out,
            backwash_handling,
            name="pretreatment-backwash",
        )
        backwash.has_role.add(enums.Role_Backwash)

        landfill_waste = connect(
            backwash_handling,
            landfill,
            medium=enums.Fluid_Sludge,
            name="landfill-waste",
        )
        landfill_waste.has_role.add(enums.Role_SolidsHandling)

        # This records a change in reference property-package assumptions.
        # It does not perform or claim a WaterTAP translation.
        pretreatment_to_desalination = Equipment(
            "pretreatment-to-desalination-boundary",
            label="Pretreatment-to-desalination semantic boundary",
        )
        cartridge_filtration >> pretreatment_to_desalination

        # Desalination.
        reverse_osmosis = ReverseOsmosisMembrane(
            "reverse-osmosis",
            label="Reverse osmosis",
            has_process=[
                process(
                    Process_ReverseOsmosis,
                    "reverse-osmosis-process",
                    "Separate pressurized seawater into freshwater permeate and brine.",
                )
            ],
        )
        nominal_quantity(
            "reverse-osmosis-membrane-area",
            "Membrane area",
            13914.0,
            units.M2,
            quantity_kinds.Area,
            of=reverse_osmosis,
        )
        water_permeability = Property(
            "reverse-osmosis-water-permeability",
            label="Water permeability coefficient [m/(Pa·s)]",
            has_value=4.2e-12,
            has_aspect=[enums.Aspect_Nominal],
        )
        # QUDT has the exact unit, but no dimensionally compatible quantity
        # kind. Use a scalar Property until WaTr defines that missing kind.
        reverse_osmosis.has_property.add(water_permeability)
        nominal_quantity(
            "reverse-osmosis-salt-permeability",
            "Salt permeability coefficient",
            3.5e-8,
            units.M_PER_SEC,
            quantity_kinds.Velocity,
            of=reverse_osmosis,
        )
        pump_1 = Pump(
            "pump-1",
            label="High-pressure pump P1",
        )
        nominal_quantity(
            "pump-1-efficiency",
            "Pump efficiency",
            0.8,
            units.UNITLESS,
            quantity_kinds.Efficiency,
            of=pump_1,
        )
        nominal_quantity(
            "pump-1-operating-pressure",
            "Operating pressure",
            70e5,
            units.PA,
            quantity_kinds.Pressure,
            of=pump_1,
        )
        disposal = Equipment("disposal", label="Brine disposal")

        separator = UnitProcess(
            "separator-1",
            label="Feed separator S1",
            has_process=[
                process(
                    Process_Separation,
                    "separator-1-process",
                    "Split pretreated seawater between P1 and the pressure exchanger.",
                )
            ],
        )
        separator_pump_out = separator.port(
            "separator-1-pump-out",
            direction="out",
        )
        separator_pxr_out = separator.port(
            "separator-1-pxr-out",
            direction="out",
        )
        pressure_exchanger = PressureExchanger(
            "pressure-exchanger",
            label="Pressure exchanger PXR",
        )
        nominal_quantity(
            "pressure-exchanger-efficiency",
            "Pressure-exchanger efficiency",
            0.95,
            units.UNITLESS,
            quantity_kinds.Efficiency,
            of=pressure_exchanger,
        )
        pxr_feed_in = pressure_exchanger.port("pxr-feed-in", direction="in")
        pxr_feed_out = pressure_exchanger.port("pxr-feed-out", direction="out")
        pxr_feed_in.pair(pxr_feed_out)
        pxr_brine_in = pressure_exchanger.port("pxr-brine-in", direction="in")
        pxr_brine_out = pressure_exchanger.port("pxr-brine-out", direction="out")
        pxr_brine_in.pair(pxr_brine_out)
        pump_2 = Pump(
            "pump-2",
            label="Booster pump P2",
        )
        nominal_quantity(
            "pump-2-efficiency",
            "Pump efficiency",
            0.8,
            units.UNITLESS,
            quantity_kinds.Efficiency,
            of=pump_2,
        )
        mixer_1 = StaticMixer(
            "mixer-1",
            label="RO feed mixer M1",
            has_process=[
                process(
                    Process_Mixing,
                    "ro-feed-mixing-process",
                    "Combine the P1 and pressure-exchanger feed streams.",
                )
            ],
        )
        mixer_pump_1_in = mixer_1.port("mixer-1-pump-1-in", direction="in")
        mixer_pump_2_in = mixer_1.port("mixer-1-pump-2-in", direction="in")
        mixer_out = mixer_1.port("mixer-1-out", direction="out")
        reverse_osmosis_concentrate_out = reverse_osmosis.port(
            "reverse-osmosis-concentrate-out",
            direction="out",
        )
        reverse_osmosis_permeate_out = reverse_osmosis.port(
            "reverse-osmosis-permeate-out",
            direction="out",
        )
        ro_feed_boundary = Equipment(
            "ro-feed-boundary",
            label="Seawater-to-RO-carrier semantic boundary",
        )
        ro_concentrate_boundary = Equipment(
            "ro-concentrate-boundary",
            label="RO-carrier-to-brine semantic boundary",
        )

        pretreatment_to_desalination >> separator
        connect(
            separator_pump_out,
            pump_1,
            name="separator-1--pump-1",
        )
        connect(
            pump_1,
            mixer_pump_1_in,
            name="pump-1--mixer-1",
        )
        connect(
            mixer_out,
            ro_feed_boundary,
            medium=enums.Water_Seawater,
            name="ro-feed",
        )
        connect(
            ro_feed_boundary,
            reverse_osmosis,
            medium=enums.Fluid_Water,
            name="ro-membrane-feed",
        )
        connect(
            separator_pxr_out,
            pxr_feed_in,
            medium=enums.Water_Seawater,
            name="pxr-feed-connection-in",
        )
        connect(
            pxr_feed_out,
            pump_2,
            name="pxr-feed-connection-out",
        )
        connect(
            pump_2,
            mixer_pump_2_in,
            name="pump-2--mixer-1",
        )
        connect(
            reverse_osmosis_concentrate_out,
            ro_concentrate_boundary,
            medium=enums.Fluid_Water,
            name="ro-concentrate",
        )
        connect(
            ro_concentrate_boundary,
            pxr_brine_in,
            medium=enums.Water_Brine,
            name="pxr-brine-connection-in",
        )
        connect(
            pxr_brine_out,
            disposal,
            name="pxr-brine-connection-out",
        )

        # S223 Filter ports use the common water carrier. These boundaries
        # record the process-specific feed and product classifications without
        # claiming that seawater, freshwater, and brine flow through unchanged.
        desalination_to_posttreatment = Equipment(
            "desalination-to-posttreatment-boundary",
            label="Desalination-to-posttreatment semantic boundary",
        )
        permeate = connect(
            reverse_osmosis_permeate_out,
            desalination_to_posttreatment,
            medium=enums.Fluid_Water,
            name="ro-permeate",
        )
        permeate.has_role.add(enums.Role_Supply)

        # Post-treatment.
        storage_tank_2 = Tank(
            "storage-tank-2",
            label="Post-treatment storage tank 2",
        )
        nominal_quantity(
            "storage-tank-2-residence-time",
            "Nominal residence time",
            1.0,
            units.HR,
            quantity_kinds.Time,
            of=storage_tank_2,
        )
        uv_aop = UVH2O2Reactor(
            "uv-aop",
            label="UV advanced oxidation process",
            has_process=[
                process(
                    Process_AdvancedOxidation,
                    "uv-aop-process",
                    "Disinfect freshwater by UV advanced oxidation.",
                )
            ],
        )
        nominal_quantity(
            "uv-aop-reduction-equivalent-dose",
            "Reduction-equivalent UV dose",
            0.35,
            units.J_PER_CentiM2,
            quantity_kinds.EnergyPerArea,
            of=uv_aop,
        )
        nominal_quantity(
            "uv-aop-transmittance",
            "UV transmittance",
            0.95,
            units.UNITLESS,
            quantity_kinds.Transmittance,
            of=uv_aop,
        )
        co2_addition = Reactor(
            "co2-addition",
            label="Carbon dioxide addition",
            has_process=[
                process(
                    Process_ChemicalAddition,
                    "co2-addition-process",
                    "Add carbon dioxide during remineralization.",
                )
            ],
        )
        lime_addition = Reactor(
            "lime-addition",
            label="Lime addition",
            has_process=[
                process(
                    Process_ChemicalAddition,
                    "lime-addition-process",
                    "Add 2.3 mg/L lime during remineralization.",
                )
            ],
        )
        storage_tank_3 = Tank(
            "storage-tank-3",
            label="Municipal-water storage tank 3",
        )
        nominal_quantity(
            "storage-tank-3-residence-time",
            "Nominal residence time",
            1.0,
            units.HR,
            quantity_kinds.Time,
            of=storage_tank_3,
        )
        municipal = Equipment("municipal", label="Municipal distribution")

        connect(
            desalination_to_posttreatment,
            storage_tank_2,
            medium=enums.Water_Freshwater,
            name="desalination-to-posttreatment-boundary--storage-tank-2",
        )
        storage_tank_2 >> uv_aop >> co2_addition >> lime_addition >> storage_tank_3
        municipal_supply = connect(
            storage_tank_3,
            municipal,
            medium=enums.Water_Freshwater,
            name="municipal-supply",
        )
        municipal_supply.has_role.add(enums.Role_Supply)

    return model


def resolved_topology(resolved: ResolvedModel) -> str:
    """Render the concrete connections selected by the S223 solver."""
    lines = [
        f"resolved {len(resolved)} entities",
        "connections:",
    ]
    connections = sorted(
        (entity for entity in resolved if isinstance(entity, Connection)),
        key=lambda entity: entity.name,
    )
    for connection in connections:
        points = sorted(
            connection.connects_at,
            key=lambda point: (
                not isinstance(point, OutletConnectionPoint),
                point.name,
            ),
        )
        path = " -> ".join(point.name for point in points)
        medium = connection.has_medium
        medium_name = medium.iri.rsplit("#", 1)[-1] if medium else "unresolved"
        lines.append(
            f"  {connection.name}: {type(connection).__name__}"
            f" [{medium_name}] {path}"
        )

    paired = sorted(
        (
            entity
            for entity in resolved
            if isinstance(entity, OutletConnectionPoint)
            and entity.paired_connection_point is not None
        ),
        key=lambda entity: entity.name,
    )
    if paired:
        lines.append("paired connection points:")
        for point in paired:
            mate = point.paired_connection_point
            medium = point.has_medium
            medium_name = medium.iri.rsplit("#", 1)[-1] if medium else "unresolved"
            lines.append(f"  {mate.name} <-> {point.name} [{medium_name}]")
    return "\n".join(lines)


if __name__ == "__main__":
    model = build_model()
    resolved = model.compile()
    out = Path(__file__).with_name("seawater_ro_full.ttl")
    model.save(out)
    print(f"wrote {out}")
    print(resolved_topology(resolved))
