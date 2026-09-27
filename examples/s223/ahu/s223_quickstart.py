"""Quickstart: define reusable S223 equipment and connect it without RDF.

The coil recipe declares its two connection points once. Each model instance
gets its own points, and the solver chooses their directions and the Duct/Pipe
classes from the connected equipment.

Run with:  uv run python examples/s223/ahu/s223_quickstart.py
Produces:  ahu.ttl and ahu_schema.ttl next to this script.
"""

from pathlib import Path

from objectrdf import Model, choose, connect, fixed
from objectrdf.s223 import (
    AirHandlingUnit,
    Chiller,
    ConnectionPoint,
    CoolingCoil,
    Damper,
    Fan,
    enums,
)


class AHUCoolingCoil(CoolingCoil):
    class_iri = "urn:example:ahu-recipes#AHUCoolingCoil"
    ontology_iri = "urn:example:ahu-recipes"
    class_label = "AHU cooling coil"
    air = ConnectionPoint.declare(
        medium=fixed(enums.values.Fluid_Air),
        direction=choose("in", "out"),
        label=fixed("Air connection"),
    )
    water = ConnectionPoint.declare(
        medium=fixed(enums.values.Fluid_Water),
        direction=choose("in", "out"),
        label=fixed("Water connection"),
    )


with Model("urn:example/ahu#") as model:
    with AirHandlingUnit("ahu-1"):
        outdoor_air_damper = Damper("oa-damper")
        supply_fan = Fan("supply-fan")
        coil = AHUCoolingCoil("cooling-coil")
        chiller = Chiller("chiller")

        air_duct = connect(outdoor_air_damper, supply_fan)
        air_to_coil = connect(supply_fan, coil.air)
        water_to_coil = connect(chiller, coil.water)

resolved = model.resolve()
air_point = resolved.point(coil.air)
water_point = resolved.point(coil.water)
assert air_point.medium is enums.values.Fluid_Air
assert water_point.medium is enums.values.Fluid_Water
assert resolved.connection(air_duct).medium is enums.values.Fluid_Air

print(f"air point: {air_point.name} ({air_point.medium})")
print(f"water point: {water_point.name} ({water_point.medium})")
for name, handle in (("air", air_to_coil), ("water", water_to_coil)):
    explanation = resolved.explain(handle)
    print(
        f"{name} connection: {explanation.source_point} -> "
        f"{explanation.target_point} ({explanation.medium_reason})"
    )

out_dir = Path(__file__).parent
instance_path = out_dir / "ahu.ttl"
schema_path = out_dir / "ahu_schema.ttl"
model.save(instance_path)
model.export_ontology(schema_path)
print(f"wrote {instance_path} and {schema_path}: {len(resolved)} entities")
