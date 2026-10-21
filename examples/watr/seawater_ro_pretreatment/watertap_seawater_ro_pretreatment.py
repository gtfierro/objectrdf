"""Describe seawater RO pretreatment using SHACL-defined process configurations.

Source:
https://watertap.readthedocs.io/en/latest/technical_reference/flowsheets/
seawater_RO_desalination.html#pre-treatment
"""

from pathlib import Path

from plumb import Model, connect
from plumb.qudt import QuantityAmount as Q, units
from plumb.watr import enums
from plumb.watr.seawater_ro import (
    BackwashStage,
    CartridgeFiltrationStage,
    ChlorinationStage,
    CoagulationStage,
    DosingStage,
    IntakePump,
    MediaFiltrationStage,
    MixingStage,
    ResidenceTimeDesign,
    StorageTank,
)


def build_model() -> Model:
    """Construct the pretreatment train with a seawater boundary medium."""
    with Model("urn:example/watertap/seawater-ro/pretreatment#") as model:
        with model.system("pretreatment-system") as system:
            # These general process configurations retain inferred port media.
            # The inlet supplies the seawater hint for the connected train.
            intake = IntakePump("intake", label="Seawater intake")
            feed = intake.port(
                "intake-seawater-in",
                direction="in",
                medium=enums.values.Water_Seawater,
            )
            ferric_chloride_addition = CoagulationStage(
                "ferric-chloride-addition", label="Ferric chloride addition"
            )
            chlorination = ChlorinationStage("chlorination")
            static_mixer = MixingStage("static-mixer", label="Static mixer")
            storage_tank = StorageTank(
                "storage-tank-1", label="Pretreatment storage tank"
            )
            storage_tank.apply_properties(
                ResidenceTimeDesign(residence_time=Q(2.0, units.HR))
            )
            media_filtration = MediaFiltrationStage(
                "media-filtration",
                label="Media filtration",
                comment="WaterTAP media filtration zero-order unit model.",
            )
            antiscalant_addition = DosingStage(
                "antiscalant-addition", label="Antiscalant addition"
            )
            cartridge_filtration = CartridgeFiltrationStage(
                "cartridge-filtration",
                label="Cartridge filtration",
                comment="WaterTAP cartridge filtration zero-order unit model.",
            )
            backwash_handling = BackwashStage(
                "backwash-handling", label="Media-filter backwash handling"
            )

            intake >> ferric_chloride_addition >> chlorination >> static_mixer
            static_mixer >> storage_tank >> media_filtration
            product = media_filtration.port("media-product-out", direction="out")
            backwash_out = media_filtration.port("media-backwash-out", direction="out")
            connect(product, antiscalant_addition)
            antiscalant_addition >> cartridge_filtration
            backwash = connect(backwash_out, backwash_handling, name="s06")
            backwash.has_role.add(enums.values.Role_Backwash)
            system.boundary(
                feed,
                cartridge_filtration.port("cartridge-product-out", direction="out"),
                backwash_handling.port("backwash-out", direction="out"),
            )
    return model


if __name__ == "__main__":
    model = build_model()
    resolved = model.resolve()
    out = Path(__file__).with_name("seawater_ro_pretreatment.ttl")
    model.save(out)
    print(f"wrote {out}: {len(resolved)} resolved entities")
    print(f"  treatment medium: {resolved['intake-seawater-in'].medium}")
