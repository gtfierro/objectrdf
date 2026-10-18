"""Import a portable air/water coil generated from ontology/hvac.ttl.

Run with:  uv run python examples/s223/cooling_coil/cooling_coil.py
Produces: cooling_coil.ttl and cooling_coil_schema.ttl next to this script.
"""

from pathlib import Path

from objectrdf import Model, connect
from objectrdf.s223 import Chiller, Fan
from objectrdf.s223.hvac import AirWaterCoolingCoil

with Model("urn:example:hvac#") as model:
    supply_fan = Fan("supply-fan")
    coil = AirWaterCoolingCoil("cooling-coil")
    chiller = Chiller("chiller")

    air_connection = connect(supply_fan, coil.air_inlet)
    water_connection = connect(chiller, coil.water_inlet)

resolved = model.resolve()
air_point = resolved.point(coil.air_inlet)
water_point = resolved.point(coil.water_inlet)

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
instance_path = out_dir / "cooling_coil.ttl"
schema_path = out_dir / "cooling_coil_schema.ttl"
model.save(instance_path)
model.export_ontology(schema_path)
print(f"wrote {instance_path} and {schema_path}")
