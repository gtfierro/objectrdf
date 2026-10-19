# ASM2d example

This is the implemented [RDF/SHACL-driven interface](shacl-configurations.md).
The runnable source is [watertap_asm2d.py](../examples/watr/asm2d/watertap_asm2d.py).

The ontology and shapes define equipment configurations, processes, roles,
objectives, named ports, property fields, and default units. Model authors import
the generated classes and supply values and connections.

```python
"""Describe the ASM2d treatment train and reference conditions as RDF."""

from pathlib import Path

from objectrdf import Model, connect
from objectrdf.qudt import QuantityAmount as Q, units
from objectrdf.watr.asm2d import (
    ASM2dState,
    AerobicDesign,
    AerobicStage,
    AnaerobicStage,
    AnoxicStage,
    ClarifierEffluentSplit,
    InfluentMixer,
    InternalRecycleSplitter,
    OverallFlowSplit,
    OxygenOutletState,
    PressureState,
    ReactorDesign,
    RecycleMixer,
    RecyclePump,
    SecondaryClarifier,
    SludgeSplitter,
)


def build_model() -> Model:
    with Model(
        "urn:example/watertap/asm2d#",
        name="WaterTAP ASM2d flowsheet",
    ) as model:
        with model.system(
            "ASM2d-system", label="WaterTAP ASM2d treatment train"
        ) as system:
            # These generated configurations include their processes and ports.
            mx1 = InfluentMixer("MX1")
            r1 = AnaerobicStage("R1")
            r2 = AnaerobicStage("R2")
            mx2 = RecycleMixer("MX2")
            r3 = AnoxicStage("R3")
            r4 = AnoxicStage("R4")
            r5 = AerobicStage("R5")
            r6 = AerobicStage("R6")
            r7 = AerobicStage("R7")
            sp1 = InternalRecycleSplitter("SP1")
            cl1 = SecondaryClarifier("CL1")
            sp2 = SludgeSplitter("SP2")
            p1 = RecyclePump("P1")

            # Bare component values use the shape's default of g/m³.
            # Each field identifies its exact ASM2d pool in the source RDF.
            mx1.feed_water.apply_properties(
                ASM2dState(
                    flow_rate=Q(18446.0, units.M3_PER_DAY),
                    temperature=Q(298.15, units.K),
                    pressure=Q(101325.0, units.PA),
                    dissolved_oxygen=1e-6,
                    fermentable_substrate=30.0,
                    fermentation_products=20.0,
                    ammonia_ammonium_nitrogen=16.0,
                    nitrate_nitrite_nitrogen=1e-6,
                    soluble_inorganic_phosphorus=3.6,
                    inert_soluble_organics=30.0,
                    dissolved_nitrogen=1e-6,
                    inert_particulate_organics=25.0,
                    slowly_biodegradable_substrate=125.0,
                    heterotrophic_biomass=30.0,
                    phosphate_accumulating_biomass=1e-6,
                    stored_polyphosphate=1e-6,
                    stored_pha=1e-6,
                    autotrophic_biomass=1e-6,
                    metal_hydroxides=1e-6,
                    metal_phosphates=1e-6,
                    total_suspended_solids=180.0,
                    alkalinity=Q(7.0, units.MOL_PER_M3),
                ),
                prefix="feed",
            )

            # Applying an immutable value schema creates separate RDF properties.
            reactor_design = ReactorDesign(volume=Q(1000.0, units.M3))
            for reactor in (r1, r2, r3, r4):
                reactor.apply_properties(reactor_design)

            # AerobicDesign's shape supplies the default volume of 1333 m³.
            aerobic_design = AerobicDesign(
                oxygen_transfer_coefficient=Q(10.0, units.PER_HR),
            )
            r5.apply_properties(aerobic_design)
            r6.apply_properties(aerobic_design)
            r7.apply_properties(
                AerobicDesign(
                    oxygen_transfer_coefficient=Q(3.5, units.PER_HR),
                )
            )

            # Reference outlet conditions belong to the outlets, not the basins.
            r5.outlet.apply_properties(
                OxygenOutletState(oxygen_concentration=Q(1.91, units.GM_PER_M3))
            )
            r6.outlet.apply_properties(
                OxygenOutletState(oxygen_concentration=Q(2.60, units.GM_PER_M3))
            )
            r7.outlet.apply_properties(
                OxygenOutletState(oxygen_concentration=Q(3.20, units.GM_PER_M3))
            )

            # The schemas carry the split basis and component qualifications.
            sp1.underflow.apply_properties(OverallFlowSplit(fraction=0.60))
            cl1.effluent.apply_properties(
                ClarifierEffluentSplit(
                    h2o_fraction=0.48956,
                    tss_fraction=0.02194,
                )
            )
            sp2.recycle.apply_properties(OverallFlowSplit(fraction=0.97955))
            p1.outlet.apply_properties(PressureState(pressure=Q(101325.0, units.PA)))

            # All port directions and media come from the generated shapes.
            connect(mx1.outlet, r1.inlet, name="stream2")
            connect(r1.outlet, r2.inlet, name="stream3")
            connect(r2.outlet, mx2.reactor, name="stream4")
            connect(mx2.outlet, r3.inlet, name="stream5")
            connect(r3.outlet, r4.inlet, name="stream6")
            connect(r4.outlet, r5.inlet, name="stream7")
            connect(r5.outlet, r6.inlet, name="stream8")
            connect(r6.outlet, r7.inlet, name="stream9")
            connect(r7.outlet, sp1.inlet, name="stream10")
            connect(sp1.overflow, cl1.inlet, name="stream11")
            connect(sp1.underflow, mx2.internal_recycle, name="stream12")
            connect(cl1.underflow, sp2.inlet, name="stream14")
            connect(sp2.recycle, p1.inlet, name="stream16")
            connect(p1.outlet, mx1.recycle, name="stream17")

            system.boundary(mx1.feed_water, cl1.effluent, sp2.waste)

    return model


if __name__ == "__main__":
    output = Path(__file__).with_name("asm2d.ttl")
    build_model().save(output)
    print(f"Wrote {output}")
```

`Q` is an import alias for `QuantityAmount`. Bare numbers use the units declared
by their source shapes; explicit quantities preserve their supplied value and
compatible permitted unit. `AerobicDesign.describe()` lists units and defaults.
The volume default of 1333 m³ comes from SHACL.

Readable component keywords retain the original ASM2d symbols as `skos:notation`.
In that notation, S denotes soluble components and X denotes particulate
components. The ontology defines each component pool and its measurement basis.

Outlet oxygen values are 1.91, 2.60, and 3.20 g/m³, corresponding to the source's
0.00191, 0.00260, and 0.00320 kg/m³. These are reference initialization values;
this example describes a flowsheet and does not solve its process equations.

Regenerate the package with `uv run python scripts/generate_asm2d.py` after editing
[ontology/asm2d.ttl](../ontology/asm2d.ttl). Model authors import the generated
classes and write no supporting Python.
