"""Quickstart: import an RDF/SHACL-defined coil and connect its named ports.

The generated configuration supplies separate air and water inlets/outlets.
Model authors supply equipment identities and topology; the reusable definition
lives in ontology/hvac.ttl.

Run with:  uv run python examples/s223/ahu/s223_quickstart.py
Produces: ahu.ttl and ahu_schema.ttl next to this script.
"""

from pathlib import Path

from plumb import Model, connect
from plumb.s223 import (
    AirHandlingUnit,
    Chiller,
    Damper,
    Fan,
    enums,
)
from plumb.s223.hvac import AirWaterCoolingCoil

with Model("urn:example/ahu#") as model:
    with AirHandlingUnit("ahu-1"):
        outdoor_air_damper = Damper("oa-damper")
        supply_fan = Fan("supply-fan")
        coil = AirWaterCoolingCoil("cooling-coil")
        chiller = Chiller("chiller")

        air_duct = connect(outdoor_air_damper, supply_fan)
        air_to_coil = connect(supply_fan, coil.air_inlet)
        water_to_coil = connect(chiller, coil.water_inlet)

resolved = model.resolve()
air_point = resolved.point(coil.air_inlet)
water_point = resolved.point(coil.water_inlet)
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
