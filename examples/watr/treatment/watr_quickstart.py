"""Model a conventional surface-water treatment train with WaTr equipment.

The generated configurations select WaTr processes, treatment objectives, and
named water/sludge ports from ontology/drinking-water.ttl.

Source: https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html
Run: uv run python examples/watr/treatment/watr_quickstart.py
"""

from pathlib import Path

from plumb import Model, connect
from plumb.watr import Pipe, System
from plumb.watr.drinking_water import (
    ChlorinationStage,
    ClarificationStage,
    CoagulationStage,
    FlocculationStage,
    RapidSandFiltrationStage,
)


def build_model() -> Model:
    """Describe the main treatment path and its external water/residual ports."""
    with Model(
        "urn:example/treatment#",
        name="Conventional surface-water treatment train",
        prefixes={
            "s223": "http://data.ashrae.org/standard223#",
            "watr": "https://watermetadata.org/ontology/watr#",
        },
    ) as model:
        with model.system("treatment-system") as system:
            coagulation = CoagulationStage("coagulation")
            flocculation = FlocculationStage("flocculation")
            clarifier = ClarificationStage("clarifier")
            sand_filter = RapidSandFiltrationStage("sand-filter")
            disinfection = ChlorinationStage("chlorination-contact")

            connect(coagulation.outlet, flocculation.inlet, name="coagulated-water")
            connect(flocculation.outlet, clarifier.inlet, name="flocculated-water")
            connect(
                clarifier.clarified_water, sand_filter.inlet, name="clarified-water"
            )
            connect(
                sand_filter.filtered_water, disinfection.inlet, name="filtered-water"
            )

            # Source water and finished water cross the plant boundary. Sludge
            # leaves for residuals handling; filter cleaning has its own supply
            # and waste points, rather than sharing the production outlets.
            system.boundary(
                coagulation.inlet,
                disinfection.outlet,
                clarifier.sludge,
                sand_filter.backwash_supply,
                sand_filter.backwash_waste,
            )
    return model


def main() -> None:
    model = build_model()
    resolved = model.compile()
    out = Path(__file__).with_name("treatment.ttl")
    model.save(out)
    plant = resolved["treatment-system"]
    assert isinstance(plant, System)
    print(f"wrote {out}: {len(plant.has_member)} treatment stages")
    for pipe in resolved:
        if isinstance(pipe, Pipe):
            print(f"  {pipe.name}: {pipe.medium}")
    print(f"  boundary points: {len(plant.has_boundary_connection_point)}")


if __name__ == "__main__":
    main()
