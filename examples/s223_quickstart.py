"""Quickstart: author a small ASHRAE 223P model with no RDF in sight.

The point of the 223 layer: one ``>>`` replaces the whole
Connectable/ConnectionPoint/Connection/medium ceremony — connection points
required by the shapes exist the moment equipment is created, and
connections negotiate media and pick Duct/Pipe automatically.

Run with:  uv run python examples/s223_quickstart.py
Produces:  ahu.ttl (Turtle) next to this script.
"""

from pathlib import Path

from objectrdf import Model, connect
from objectrdf.s223 import (
    Chiller,
    Damper,
    DomainSpace,
    ChilledWaterCoil,
    Fan,
    InletConnectionPoint,
    OutletConnectionPoint,
    PhysicalSpace,
    Pump,
    enums,
    Thermostat,
    AirHandlingUnit,
)

with Model("urn:example/ahu#") as model:
    # The AHU is a container for the equipment that lives inside it.
    with AirHandlingUnit("ahu-1"):
        # Equipment created in the AHU's scope gets hasPhysicalLocation.
        oad = Damper("oa-damper")
        sf = Fan("supply-fan")
        # Air path: shapes constrain both sides to Fluid-Air, so the medium,
        # the connection points, and the Duct are all worked out automatically.
        duct = connect(oad, sf)
        duct.label = "supply duct"

        chw_coil = ChilledWaterCoil()  # this will get a made-up name
    # A Coil has three valid xone layouts. Declare the intended two-fluid
    # layout; connections and media can still be authored in any order.
    for name, cls, medium in (
        ("coil-air-in", InletConnectionPoint, enums.Fluid_Air),
        ("coil-water-in", InletConnectionPoint, enums.Fluid_Water),
        ("coil-air-out", OutletConnectionPoint, enums.Fluid_Air),
        ("coil-water-out", OutletConnectionPoint, enums.Fluid_Water),
    ):
        cls(name, has_medium=medium, is_connection_point_of=chw_coil)

    # Spaces nest like the building does; the HVAC zone lives in the room.
    with PhysicalSpace("mech-room"):
        zone = DomainSpace("zone-1", has_domain=enums.Domain_HVAC)

        # Equipment created in the room's scope gets hasPhysicalLocation.
        tsta = Thermostat("tsta-1")

    # Water side: the chiller's shape says Fluid-Water. Water is permitted at
    # both pump ports, so the optimizer prefers that coherent assignment while
    # satisfying the coil layout selected from its SHACL xone alternatives.
    pump = Pump("chw-pump2")
    chiller = Chiller("chiller1")
    chw2 = connect(chiller, pump)
    pump_to_coil = connect(pump, chw_coil)
    chw_coil >> chiller

    # When neither side constrains the medium (pump to pump), say it:
    connect(
        Pump("primary-pump"),
        Pump("standby-pump"),
        medium=enums.Water_ChilledWater,
    )

out = Path(__file__).parent / "ahu.ttl"
resolved = model.resolve()
model.save(out)
print(f"wrote {out}: {len(resolved)} resolved entities")

# The full 223 plumbing came from two statements:
resolved_sf = resolved[sf.name]
for cp in resolved_sf.has_connection_point:
    print(f"  {sf.name} has {type(cp).__name__} {cp.name} ({cp.has_medium})")
print(f"  water medium: {resolved.connection(chw2).has_medium}")
print(f"  preferred medium: {resolved.connection(pump_to_coil).has_medium}")
resolved_duct = resolved.connection(duct)
print(f"  duct medium: {resolved_duct.has_medium} / {resolved_duct.label}")
