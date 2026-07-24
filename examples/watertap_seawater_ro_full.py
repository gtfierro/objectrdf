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
    Junction,
    MediaFiltration,
    OutletConnectionPoint,
    PressureExchanger,
    Process_AdvancedOxidation,
    Process_ChemicalAddition,
    Process_Chlorination,
    Process_Coagulation,
    Process_Filtration,
    Process_Landfill,
    Process_MediaFiltration,
    Process_Mixing,
    Process_Separation,
    Process_ReverseOsmosis,
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


def build_model() -> Model:
    """Build the pressure-exchanger WaTr/S223 reference configuration."""
    model = Model(
        "urn:example/watertap/seawater-ro/full#",
        name="WaTr seawater RO reference",
        prefixes={
            "qudt": "http://qudt.org/schema/qudt/",
            "s223": "http://data.ashrae.org/standard223#",
            "watr": "urn:nawi-water-ontology#",
        },
    )

    with model:
        # Flowsheet feed. The known outlet is the sole seawater boundary hint
        # needed by the affinity solver for pretreatment and the RO feed path.
        feed = Equipment(
            "feed",
            label="Seawater feed",
            has_role=[enums.Role_Feed],
        )
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
        intake = Pump(
            "intake",
            label="Seawater intake",
            has_role=[enums.Role_Feed],
        )
        feed_connection = connect(
            feed,
            intake,
            medium=enums.Water_Seawater,
            name="feed--intake",
        )
        feed_connection.has_role.add(enums.Role_Feed)
        ferric_chloride_addition = CoagulationBasin(
            "ferric-chloride-addition",
            label="Ferric chloride addition",
            has_process=[
                Process_Coagulation(
                    "ferric-chloride-addition-process",
                    definition="Add 20 mg/L ferric chloride to promote coagulation.",
                )
            ],
        )
        chlorination = ChlorinationUnit(
            "chlorination",
            has_process=[
                Process_Chlorination(
                    "chlorination-process",
                    definition="Disinfect the seawater by chlorination.",
                )
            ],
        )
        static_mixer = StaticMixer(
            "static-mixer",
            label="Static mixer",
            has_process=[
                Process_Mixing(
                    "static-mixing-process",
                    definition="Mix added treatment chemicals into the seawater.",
                )
            ],
        )
        storage_tank_1 = Tank(
            "storage-tank-1",
            label="Pretreatment storage tank",
            has_role=[enums.Role_Storage],
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
                Process_MediaFiltration(
                    "media-filtration-process",
                    definition="Remove suspended matter by filtration through media.",
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
                Process_ChemicalAddition(
                    "antiscalant-addition-process",
                    definition="Add antiscalant before cartridge filtration.",
                )
            ],
        )
        cartridge_filtration = CartridgeFiltrationUnit(
            "cartridge-filtration",
            label="Cartridge filtration",
            has_process=[
                Process_Filtration(
                    "cartridge-filtration-process",
                    definition=(
                        "Polish the pretreated seawater by cartridge filtration."
                    ),
                )
            ],
        )
        backwash_handling = UnitProcess(
            "backwash-handling",
            label="Media-filter backwash handling",
            has_process=[
                Process_Separation(
                    "backwash-handling-process",
                    definition=(
                        "Separate media-filter backwash into treated water and a "
                        "solids-rich byproduct."
                    ),
                )
            ],
            has_role=[enums.Role_SolidsHandling],
        )
        backwash_treated_out = OutletConnectionPoint(
            "backwash-handling-treated-out",
            has_medium=enums.Water_Seawater,
            is_connection_point_of=backwash_handling,
        )
        backwash_handling.has_optional_connection_point.add(backwash_treated_out)
        backwash_byproduct_out = backwash_handling.port(
            "backwash-handling-byproduct-out",
            direction="out",
            medium=enums.Fluid_Sludge,
        )
        landfill = UnitProcess(
            "landfill",
            label="Landfill",
            has_process=[
                Process_Landfill(
                    "landfill-process",
                    definition="Dispose of the backwash solids by landfilling.",
                )
            ],
            has_role=[enums.Role_SolidsHandling],
        )
        # WaterTAP models landfill as pass-through; its outlet is an external
        # boundary of this reference flowsheet.
        landfill_out = OutletConnectionPoint(
            "landfill-out",
            has_medium=enums.Fluid_Sludge,
            is_connection_point_of=landfill,
        )
        landfill.has_optional_connection_point.add(landfill_out)

        (
            intake
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
            medium=enums.Water_Seawater,
            name="pretreatment-backwash",
        )
        backwash.has_role.add(enums.Role_Backwash)

        landfill_waste = connect(
            backwash_byproduct_out,
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
            has_role=[enums.Role_Pretreatment],
        )
        cartridge_filtration >> pretreatment_to_desalination

        # Desalination.
        reverse_osmosis = ReverseOsmosisMembrane(
            "reverse-osmosis",
            label="Reverse osmosis",
            has_process=[
                Process_ReverseOsmosis(
                    "reverse-osmosis-process",
                    definition=(
                        "Separate pressurized seawater into freshwater permeate "
                        "and brine."
                    ),
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
        nominal_quantity(
            "reverse-osmosis-spacer-porosity",
            "Feed spacer porosity",
            0.97,
            units.UNITLESS,
            quantity_kinds.DimensionlessRatio,
            of=reverse_osmosis,
        )
        nominal_quantity(
            "reverse-osmosis-channel-height",
            "Membrane channel height",
            1e-3,
            units.M,
            quantity_kinds.Length,
            of=reverse_osmosis,
        )
        nominal_quantity(
            "reverse-osmosis-stage-width",
            "Membrane width per stage",
            1000.0,
            units.M,
            quantity_kinds.Length,
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
        disposal = Equipment(
            "disposal",
            label="Brine disposal",
            has_role=[enums.Role_Discharge],
        )

        separator = Junction(
            "separator-1",
            label="Feed separator S1",
            has_medium=enums.Water_Seawater,
            comment=(
                "IDAES stream splitter; this junction does not perform a "
                "water-treatment process."
            ),
        )
        separator_in = separator.port(
            "separator-1-in",
            direction="in",
            medium=enums.Water_Seawater,
        )
        separator_pump_out = separator.port(
            "separator-1-pump-out",
            direction="out",
            medium=enums.Water_Seawater,
        )
        separator_pxr_out = separator.port(
            "separator-1-pxr-out",
            direction="out",
            medium=enums.Water_Seawater,
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
                Process_Mixing(
                    "ro-feed-mixing-process",
                    definition=(
                        "Combine the P1 and pressure-exchanger feed streams."
                    ),
                )
            ],
        )
        mixer_pump_1_in = mixer_1.port("mixer-1-pump-1-in", direction="in")
        mixer_pump_2_in = mixer_1.port("mixer-1-pump-2-in", direction="in")
        mixer_out = mixer_1.port("mixer-1-out", direction="out")
        reverse_osmosis_concentrate_out = reverse_osmosis.port(
            "reverse-osmosis-concentrate-out",
            direction="out",
            medium=enums.Water_Brine,
        )
        reverse_osmosis_permeate_out = reverse_osmosis.port(
            "reverse-osmosis-permeate-out",
            direction="out",
            medium=enums.Water_Freshwater,
        )
        # WaTr models seawater, freshwater, and brine as constituent-bearing
        # mixtures. Their shared H2O constituent makes the specific stream
        # media compatible with the S223 Filter constraint on the membrane.

        connect(
            pretreatment_to_desalination,
            separator_in,
            medium=enums.Water_Seawater,
            name="pretreatment-to-desalination-boundary--separator-1",
        )
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
        ro_feed = connect(
            mixer_out,
            reverse_osmosis,
            medium=enums.Water_Seawater,
            name="ro-feed",
        )
        ro_feed.has_role.add(enums.Role_Feed)
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
            pxr_brine_in,
            medium=enums.Water_Brine,
            name="ro-concentrate--pxr-brine-connection-in",
        )
        brine_disposal = connect(
            pxr_brine_out,
            disposal,
            name="pxr-brine-connection-out",
        )
        brine_disposal.has_role.add(enums.Role_Discharge)

        desalination_to_posttreatment = Equipment(
            "desalination-to-posttreatment-boundary",
            label="Desalination-to-posttreatment semantic boundary",
            has_role=[enums.Role_Posttreatment],
        )
        permeate = connect(
            reverse_osmosis_permeate_out,
            desalination_to_posttreatment,
            medium=enums.Water_Freshwater,
            name="ro-permeate",
        )
        permeate.has_role.add(enums.Role_Permeate)
        permeate.has_role.add(enums.Role_Supply)
        nominal_quantity(
            "reverse-osmosis-permeate-side-pressure",
            "Nominal permeate-side pressure",
            101325.0,
            units.PA,
            quantity_kinds.Pressure,
            of=permeate,
        )

        # Post-treatment.
        storage_tank_2 = Tank(
            "storage-tank-2",
            label="Post-treatment storage tank 2",
            has_role=[enums.Role_Storage],
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
                Process_AdvancedOxidation(
                    "uv-aop-process",
                    definition="Disinfect freshwater by UV advanced oxidation.",
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
                Process_ChemicalAddition(
                    "co2-addition-process",
                    definition="Add carbon dioxide during remineralization.",
                )
            ],
        )
        lime_addition = Reactor(
            "lime-addition",
            label="Lime addition",
            has_process=[
                Process_ChemicalAddition(
                    "lime-addition-process",
                    definition="Add 2.3 mg/L lime during remineralization.",
                )
            ],
        )
        storage_tank_3 = Tank(
            "storage-tank-3",
            label="Municipal-water storage tank 3",
            has_role=[enums.Role_Storage],
        )
        nominal_quantity(
            "storage-tank-3-residence-time",
            "Nominal residence time",
            1.0,
            units.HR,
            quantity_kinds.Time,
            of=storage_tank_3,
        )
        municipal = Equipment(
            "municipal",
            label="Municipal distribution",
            has_role=[enums.Role_Supply],
        )

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
