"""Define a portable air/water coil recipe and author one instance.

Run with:  uv run python examples/s223/recipe_coil/recipe_coil.py
Produces: recipe_coil.ttl and recipe_coil_schema.ttl next to this script.
"""

from pathlib import Path

from objectrdf import Model, choose, connect, fixed
from objectrdf.s223 import Chiller, ConnectionPoint, CoolingCoil, Fan, enums


class AirWaterCoolingCoil(CoolingCoil):
    class_iri = "urn:example:hvac-recipes#AirWaterCoolingCoil"
    ontology_iri = "urn:example:hvac-recipes"
    class_label = "Air and water cooling coil"
    air = ConnectionPoint.declare(
        medium=fixed(enums.Fluid_Air),
        direction=choose("in", "out"),
        label=fixed("Air connection"),
    )
    water = ConnectionPoint.declare(
        medium=fixed(enums.Fluid_Water),
        direction=choose("in", "out"),
        label=fixed("Water connection"),
    )


with Model("urn:example:hvac#") as model:
    supply_fan = Fan("supply-fan")
    coil = AirWaterCoolingCoil("cooling-coil")
    chiller = Chiller("chiller")

    air_connection = connect(supply_fan, coil.air)
    water_connection = connect(chiller, coil.water)

resolved = model.resolve()
air_point = resolved.point(coil.air)
water_point = resolved.point(coil.water)

print(f"air: {air_point.name} ({air_point.medium})")
print(f"water: {water_point.name} ({water_point.medium})")
for name, handle in (
    ("air", air_connection),
    ("water", water_connection),
):
    explanation = resolved.explain(handle)
    print(
        f"{name} routing: {explanation.source_point} -> "
        f"{explanation.target_point} ({explanation.medium_reason})"
    )

out_dir = Path(__file__).parent
instance_path = out_dir / "recipe_coil.ttl"
schema_path = out_dir / "recipe_coil_schema.ttl"
model.save(instance_path)
model.export_ontology(schema_path)
print(f"wrote {instance_path} and {schema_path}")
