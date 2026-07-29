"""Build a small WaTr treatment path and compile its S223 topology."""

from pathlib import Path

from objectrdf import Model, connect
from objectrdf.watr import Chiller, Pump, Tank


with Model("urn:example/treatment#") as model:
    # WaTr extends S223, so imported S223 equipment and WaTr-specific classes
    # participate in one connection component. The source establishes water;
    # water is permitted across the WaTr pump and the tank's Mix-Fluid domain,
    # so the optimizer prefers one coherent water assignment.
    source = Chiller("water-source")
    pump = Pump("transfer-pump")
    product = Tank("product-tank")

    source_to_pump = connect(source, pump)
    pump_to_product = connect(pump, product)

resolved = model.resolve()
out = Path(__file__).with_name("treatment.ttl")
model.save(out)

print(f"wrote {out}: {len(resolved)} resolved entities")
print(f"  inlet: {resolved.connection(source_to_pump).has_medium}")
print(f"  outlet: {resolved.connection(pump_to_product).has_medium}")
