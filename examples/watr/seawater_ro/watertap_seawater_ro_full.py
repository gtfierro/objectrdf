"""Describe the seawater RO reference flowsheet with generated domain types.

Equipment configurations and quantity schemas come from ontology/seawater-ro.ttl.
This describes topology and nominal design values; it does not solve WaterTAP.

Source:
https://watertap.readthedocs.io/en/latest/technical_reference/flowsheets/
seawater_RO_desalination.html#full-flowsheet
"""

from pathlib import Path

from plumb import Model, ResolvedModel, connect
from plumb.qudt import QuantityAmount as Q, units
from plumb.watr import (
    Connection,
    Equipment,
    OutletConnectionPoint,
    Property,
    enums,
)
from plumb.watr.seawater_ro import (
    AdvancedOxidationStage,
    BackwashSeparator,
    BoosterPump,
    CartridgeFiltrationStage,
    ChlorinationStage,
    CoagulationStage,
    DosingStage,
    EnergyRecoveryExchanger,
    FeedSplitter,
    HighPressurePumpDesign,
    HighPressurePump,
    IntakePump,
    Landfill,
    MediaFilter,
    MembraneDesign,
    MixingStage,
    PermeateConnection,
    PermeateState,
    PressureExchangerDesign,
    PumpDesign,
    ResidenceTimeDesign,
    ROFeedMixer,
    ROStage,
    SeawaterFeed,
    SeawaterFeedState,
    StorageTank,
    UVDesign,
)


def build_model() -> Model:
    """Build the pressure-exchanger configuration using source-defined metadata."""
    with Model(
        "urn:example/watertap/seawater-ro/full#",
        name="WaTr seawater RO reference",
        prefixes={
            "qudt": "http://qudt.org/schema/qudt/",
            "s223": "http://data.ashrae.org/standard223#",
            "watr": "https://watermetadata.org/ontology/watr#",
        },
    ) as model:
        with model.system(
            "seawater-ro-system", label="Seawater RO treatment train"
        ) as system:
            # Broad water media permit composition changes across the train.
            # The feed schema identifies salt and suspended solids explicitly.
            feed = SeawaterFeed("feed", label="Seawater feed")
            feed.outlet.apply_properties(
                SeawaterFeedState(
                    flow_rate=Q(7.05e6, units.GAL_US_PER_DAY),
                    total_dissolved_solids=Q(35.0, units.GM_PER_L),
                    total_suspended_solids=Q(0.03, units.GM_PER_L),
                    temperature=Q(298.0, units.K),
                    pressure=Q(100000.0, units.PA),
                ),
                prefix="influent",
            )

            # Pretreatment processes and storage roles come from SHACL.
            intake = IntakePump("intake", label="Seawater intake")
            ferric_chloride_addition = CoagulationStage(
                "ferric-chloride-addition", label="Ferric chloride addition"
            )
            chlorination = ChlorinationStage("chlorination")
            static_mixer = MixingStage("static-mixer", label="Static mixer")
            storage_tank_1 = StorageTank(
                "storage-tank-1", label="Pretreatment storage tank"
            )
            storage_tank_1.apply_properties(ResidenceTimeDesign(residence_time=2.0))
            media_filtration = MediaFilter("media-filtration", label="Media filtration")
            antiscalant_addition = DosingStage(
                "antiscalant-addition", label="Antiscalant addition"
            )
            cartridge_filtration = CartridgeFiltrationStage(
                "cartridge-filtration", label="Cartridge filtration"
            )
            backwash_handling = BackwashSeparator(
                "backwash-handling", label="Media-filter backwash handling"
            )
            landfill = Landfill("landfill", label="Landfill")

            feed_connection = connect(feed.outlet, intake, name="feed--intake")
            feed_connection.has_role.add(enums.values.Role_Feed)
            intake >> ferric_chloride_addition >> chlorination >> static_mixer
            static_mixer >> storage_tank_1
            connect(
                storage_tank_1,
                media_filtration.inlet,
                name="storage-tank-1--media-filtration",
            )
            connect(
                media_filtration.product,
                antiscalant_addition,
                name="media-filtration--antiscalant-addition",
            )
            antiscalant_addition >> cartridge_filtration
            backwash = connect(
                media_filtration.backwash,
                backwash_handling.inlet,
                name="pretreatment-backwash",
            )
            backwash.has_role.add(enums.values.Role_Backwash)
            connect(backwash_handling.byproduct, landfill.inlet, name="landfill-waste")

            # These equipment nodes record changes in reference property-package
            # assumptions, rather than implementing a WaterTAP translation.
            pretreatment_to_desalination = Equipment(
                "pretreatment-to-desalination-boundary",
                label="Pretreatment-to-desalination semantic boundary",
                has_role=[enums.values.Role_Pretreatment],
            )
            cartridge_filtration >> pretreatment_to_desalination

            reverse_osmosis = ROStage("reverse-osmosis", label="Reverse osmosis")
            reverse_osmosis.apply_properties(
                MembraneDesign(
                    membrane_area=Q(13914.0, units.M2),
                    spacer_porosity=0.97,
                    channel_height=Q(1e-3, units.M),
                    stage_width=Q(1000.0, units.M),
                    salt_permeability=Q(3.5e-8, units.M_PER_SEC),
                )
            )
            # QUDT has the exact unit but no compatible quantity kind for this
            # coefficient. Preserve it as a scalar Property with a unit label.
            reverse_osmosis.has_property.add(
                Property(
                    "reverse-osmosis-water-permeability",
                    label="Water permeability coefficient [m/(Pa·s)]",
                    has_value=4.2e-12,
                    has_aspect=[enums.values.Aspect_Nominal],
                )
            )
            pump_1 = HighPressurePump("pump-1", label="High-pressure pump P1")
            pump_1.apply_properties(
                HighPressurePumpDesign(
                    efficiency=0.8, operating_pressure=Q(70e5, units.PA)
                )
            )
            pump_2 = BoosterPump("pump-2", label="Booster pump P2")
            pump_2.apply_properties(PumpDesign(efficiency=0.8))
            disposal = Equipment(
                "disposal",
                label="Brine disposal",
                has_role=[enums.values.Role_Discharge],
            )
            separator = FeedSplitter(
                "separator-1",
                label="Feed separator S1",
                comment="IDAES stream splitter; this junction performs no treatment process.",
            )
            mixer = ROFeedMixer("mixer-1", label="RO feed mixer M1")
            pressure_exchanger = EnergyRecoveryExchanger(
                "pressure-exchanger", label="Pressure exchanger PXR"
            )
            pressure_exchanger.apply_properties(
                PressureExchangerDesign(efficiency=0.95)
            )
            # Each exchanger circuit retains its own paired points.
            pxr_feed_in = pressure_exchanger.port("pxr-feed-in", direction="in")
            pxr_feed_out = pressure_exchanger.port("pxr-feed-out", direction="out")
            pxr_feed_in.pair(pxr_feed_out)
            pxr_brine_in = pressure_exchanger.port("pxr-brine-in", direction="in")
            pxr_brine_out = pressure_exchanger.port("pxr-brine-out", direction="out")
            pxr_brine_in.pair(pxr_brine_out)

            connect(
                pretreatment_to_desalination,
                separator.inlet,
                name="pretreatment-to-desalination-boundary--separator-1",
            )
            connect(separator.pump, pump_1, name="separator-1--pump-1")
            connect(pump_1, mixer.high_pressure, name="pump-1--mixer-1")
            ro_feed = connect(mixer.outlet, reverse_osmosis.inlet, name="ro-feed")
            ro_feed.has_role.add(enums.values.Role_Feed)
            connect(
                separator.pressure_exchanger, pxr_feed_in, name="pxr-feed-connection-in"
            )
            connect(pxr_feed_out, pump_2, name="pxr-feed-connection-out")
            connect(pump_2, mixer.booster, name="pump-2--mixer-1")
            connect(
                reverse_osmosis.concentrate,
                pxr_brine_in,
                name="ro-concentrate--pxr-brine-connection-in",
            )
            brine_disposal = connect(
                pxr_brine_out, disposal, name="pxr-brine-connection-out"
            )
            brine_disposal.has_role.add(enums.values.Role_Discharge)

            desalination_to_posttreatment = Equipment(
                "desalination-to-posttreatment-boundary",
                label="Desalination-to-posttreatment semantic boundary",
                has_role=[enums.values.Role_Posttreatment],
            )
            permeate = connect(
                reverse_osmosis.permeate,
                desalination_to_posttreatment,
                name="ro-permeate",
                connection=PermeateConnection,
            )
            permeate.has_role.add(enums.values.Role_Permeate)
            permeate.has_role.add(enums.values.Role_Supply)
            permeate.apply_properties(
                PermeateState(pressure=Q(101325.0, units.PA)),
                prefix="reverse-osmosis-permeate",
            )

            storage_tank_2 = StorageTank(
                "storage-tank-2", label="Post-treatment storage tank 2"
            )
            storage_tank_3 = StorageTank(
                "storage-tank-3", label="Municipal-water storage tank 3"
            )
            storage_design = ResidenceTimeDesign(residence_time=1.0)
            storage_tank_2.apply_properties(storage_design)
            storage_tank_3.apply_properties(storage_design)
            uv_aop = AdvancedOxidationStage(
                "uv-aop", label="UV advanced oxidation process"
            )
            uv_aop.apply_properties(
                UVDesign(
                    reduction_equivalent_dose=Q(0.35, units.J_PER_CentiM2),
                    transmittance=0.95,
                )
            )
            co2_addition = DosingStage("co2-addition", label="Carbon dioxide addition")
            lime_addition = DosingStage("lime-addition", label="Lime addition")
            municipal = Equipment(
                "municipal",
                label="Municipal distribution",
                has_role=[enums.values.Role_Supply],
            )
            connect(
                desalination_to_posttreatment,
                storage_tank_2,
                name="desalination-to-posttreatment-boundary--storage-tank-2",
            )
            storage_tank_2 >> uv_aop >> co2_addition >> lime_addition >> storage_tank_3
            municipal_supply = connect(
                storage_tank_3, municipal, name="municipal-supply"
            )
            municipal_supply.has_role.add(enums.values.Role_Supply)
            system.boundary(backwash_handling.treated, landfill.outlet)

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
        medium = connection.medium
        medium_name = medium.iri.rsplit("#", 1)[-1] if medium else "unresolved"
        lines.append(
            f"  {connection.name}: {type(connection).__name__} [{medium_name}] {path}"
        )

    paired = sorted(
        (
            entity
            for entity in resolved
            if isinstance(entity, OutletConnectionPoint)
            and entity.paired_with is not None
        ),
        key=lambda entity: entity.name,
    )
    if paired:
        lines.append("paired connection points:")
        for point in paired:
            mate = point.paired_with
            medium = point.medium
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
