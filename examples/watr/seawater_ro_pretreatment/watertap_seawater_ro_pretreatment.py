"""Author a WaTr/S223 graph inspired by a seawater-RO pretreatment diagram.

This describes semantic topology, not a WaterTAP simulation model.

Source:
https://watertap.readthedocs.io/en/latest/technical_reference/flowsheets/
seawater_RO_desalination.html#pre-treatment
"""

from pathlib import Path

from objectrdf import Model, connect
from objectrdf.watr import (
    ChlorinationUnit,
    InletConnectionPoint,
    Process_Backwashing,
    Process_ChemicalAddition,
    Process_Chlorination,
    Process_Coagulation,
    Process_Filtration,
    Process_MediaFiltration,
    Process_Mixing,
    Pump,
    Reactor,
    StaticMixer,
    Tank,
    UnitProcess,
    enums,
)


with Model("urn:example/watertap/seawater-ro/pretreatment#") as model:
    # The WaterTAP intake is represented as the pump bringing raw seawater
    # into the pretreatment train. This known boundary port is the only
    # medium hint the affinity solver needs for the connected process train.
    intake = Pump("intake", label="Seawater intake")
    InletConnectionPoint(
        "intake-seawater-in",
        has_medium=enums.Water_Seawater,
        is_connection_point_of=intake,
    )

    ferric_chloride_process = Process_Coagulation(
        "ferric-chloride-addition-process",
        definition="Add 20 mg/L ferric chloride to promote coagulation.",
    )
    ferric_chloride_addition = Reactor(
        "ferric-chloride-addition",
        label="Ferric chloride addition",
        has_process=[ferric_chloride_process],
    )

    chlorination_process = Process_Chlorination(
        "chlorination-process",
        definition="Disinfect the seawater by chlorination.",
    )
    chlorination = ChlorinationUnit(
        "chlorination",
        has_process=[chlorination_process],
    )

    static_mixing_process = Process_Mixing(
        "static-mixing-process",
        definition="Mix added treatment chemicals into the seawater.",
    )
    static_mixer = StaticMixer(
        "static-mixer",
        label="Static mixer",
        has_process=[static_mixing_process],
    )

    storage_tank = Tank(
        "storage-tank-1",
        label="Pretreatment storage tank",
        comment="WaterTAP storage time: 2 hr.",
    )

    media_filtration_process = Process_MediaFiltration(
        "media-filtration-process",
        definition="Remove suspended matter by filtration through media.",
    )
    media_filtration = UnitProcess(
        "media-filtration",
        label="Media filtration",
        has_process=[media_filtration_process],
        comment="WaterTAP media filtration zero-order unit model.",
    )

    antiscalant_process = Process_ChemicalAddition(
        "antiscalant-addition-process",
        definition="Add antiscalant before cartridge filtration.",
    )
    antiscalant_addition = Reactor(
        "antiscalant-addition",
        label="Antiscalant addition",
        has_process=[antiscalant_process],
    )

    cartridge_filtration_process = Process_Filtration(
        "cartridge-filtration-process",
        definition="Polish the pretreated seawater by cartridge filtration.",
    )
    cartridge_filtration = UnitProcess(
        "cartridge-filtration",
        label="Cartridge filtration",
        has_process=[cartridge_filtration_process],
        comment="WaterTAP cartridge filtration zero-order unit model.",
    )
    backwash_handling_process = Process_Backwashing(
        "backwash-handling-process",
        definition="Collect and handle backwash from media filtration.",
    )
    backwash_handling = UnitProcess(
        "backwash-handling",
        label="Media-filter backwash handling",
        has_process=[backwash_handling_process],
    )

    # Use the flow operator for the unannotated treatment path. The solver
    # selects Water-Seawater for these connections from the boundary hint and
    # the overlapping permitted-media domains of adjacent process equipment.
    (
        intake
        >> ferric_chloride_addition
        >> chlorination
        >> static_mixer
        >> storage_tank
        >> media_filtration
        >> antiscalant_addition
        >> cartridge_filtration
    )

    # Keep a handle only for the connection that needs a role annotation.
    backwash = connect(
        media_filtration,
        backwash_handling,
        name="s06",
    )
    backwash.has_role.add(enums.Role_Backwash)

resolved = model.resolve()
out = Path(__file__).with_name("seawater_ro_pretreatment.ttl")
model.save(out)

print(f"wrote {out}: {len(resolved)} resolved entities")
print(f"  treatment medium: {resolved.connection(backwash).has_medium}")
