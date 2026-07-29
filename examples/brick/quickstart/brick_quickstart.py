"""Quickstart: author a small Brick model with no RDF in sight.

Run with:  uv run python examples/brick/quickstart/brick_quickstart.py
Produces:  bldg1.ttl (Turtle) next to this script.
"""

from pathlib import Path

from objectrdf import Model
from objectrdf.brick import (
    AHU,
    VAV,
    Building,
    Floor,
    HVAC_Zone,
    Room,
    Supply_Air_Temperature_Sensor,
    Supply_Fan,
    Zone_Air_Temperature_Sensor,
)

with Model("urn:example/bldg1#") as model:
    # Spatial hierarchy: `with` blocks nest the way the building does.
    with Building("bldg1", label="Building 1"):
        with Floor("floor1"):
            room101 = Room("room101")
            room102 = Room("room102")

    # Equipment: an AHU with a supply fan inside it (Equipment/Equipment
    # containment negotiates brick hasPart).
    ahu = AHU("ahu1", label="Main AHU")
    with ahu:
        fan = Supply_Fan("sf1")
        sat = Supply_Air_Temperature_Sensor("sat1")  # -> ahu hasPoint

    # Flow: >> is Brick feeds, and returns its right operand so chains
    # read along the air path.
    vav1 = VAV("vav-101")
    vav2 = VAV("vav-102")
    ahu >> vav1
    ahu >> vav2

    # Zones and their sensors.
    zone1 = HVAC_Zone("zone1")
    zone1.contains(room101)  # Location/Location -> hasPart
    vav1 >> zone1
    zone1.contains(Zone_Air_Temperature_Sensor("zat1"))  # -> hasPoint

    # Plain attribute access reads back exactly what you authored.
    assert vav1 in ahu.feeds
    assert ahu in vav1.is_fed_by  # inverse maintained automatically
    assert fan in ahu.has_part
    assert sat in ahu.has_point

out = Path(__file__).parent / "bldg1.ttl"
model.save(out)
print(f"wrote {out}: {len(model)} entities")

# Class metadata comes straight from the ontology:
print(f"AHU is {AHU.meta.iri}")
print(f"   {(AHU.meta.definition or '')[:80]}...")
