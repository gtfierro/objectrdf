---
file_format: mystnb
kernelspec:
  name: python3
---

# Inspect port requirements while authoring

Start with `SomeClass.describe_ports()` to see its connection-point directions,
counts, medium roots, and any shape alternatives. When you need to work with
that information in code, use `SomeClass.meta.port_contract`. The class
contract tells you what kinds of points the solver may need; `instance.ports`
tells you which concrete points or deferred handles exist on one instance.

## Read the contract

WaTr's `Pump` inherits the S223 pump requirement for an inlet and an outlet:

```{code-cell} python3
from objectrdf import Model, connect
from objectrdf.watr import Chiller, Pump, Tank, enums

with Model("urn:example:port-contract#") as model:
    pump = Pump("transfer-pump")

print(Pump.describe_ports())
```

Each row maps the value you pass as `direction` to the ontology class of the
point that will exist after resolution: `"in"` selects an
`InletConnectionPoint`, `"out"` an `OutletConnectionPoint`, and `"bi"` a
`BidirectionalConnectionPoint`. The directions are relative to the pump:
flow arriving at it uses `"in"`; flow leaving it uses `"out"`. When you
connect whole entities, `connect(source, pump)` chooses a compatible inlet on
the pump, while `connect(pump, tank)` chooses a compatible outlet.

Named and unnamed connections use the same port matching. When a stream needs
additional points, request them explicitly:

```python
connect(source, pump, name="feed", medium=enums.values.Fluid_Water, ports="new")
```

For bare equipment endpoints this allocates a new directed point on each,
subject to their port constraints. Port names derive from the equipment,
independently of the connection name. An explicit port passed to `connect` is
used as given, so you can attach quantities or mark a system boundary on that
exact point. Without `ports="new"`, the resolver chooses compatible points.

RDF/SHACL-generated configurations can also expose named references such as
`stage.outlet`. Their `describe_ports()` summaries include these names. See
[domain API generation](generate-domain-api.md).

The count applies to points satisfying that row, not to the number of named
handles you must create. The summary labels unconditional slots separately
from `all of`, `any of`, and `exactly one of` shape constraints. Medium roots
include their descendants. The class summary does not list named ports on
`pump`.

## Access the structured contract

Each slot exposes its point class, direction, count, and allowed medium roots:

```{code-cell} python3
contract = pump.meta.port_contract
for slot in contract.slots:
    media = slot.medium_options or ((slot.medium,) if slot.medium else ())
    print(
        slot.direction,
        slot.point_class.__name__,
        f"count {slot.min_count}..{slot.max_count if slot.max_count is not None else 'any'}",
        [getattr(value, "label", value) for value in media],
    )
print("alternative constraints:", [item.operator for item in contract.constraints])
```

`min_count` and `max_count` describe a requirement, not named instance ports.
`max_count=None` means the ontology supplies no upper bound. A medium root
permits values beneath it in the enum hierarchy. Some shapes use `and`, `or`,
or `xone`; those remain as nested `contract.constraints`. Constraints marked
`opaque` are checked by validation but cannot be used by the constructive
solver. `contract.describe()` produces the same summary without the class name.

## Name and constrain a particular output

The ontology does not give individual outlets names before they exist. Create
a named deferred port when you want to target one specific outlet. The summary's
`direction="out" -> OutletConnectionPoint` row tells you which direction to
pass; `medium=enums.values.Fluid_Water` selects a value beneath the listed
`Fluid-Water` root. The returned handle lets you connect from that exact port:

```{code-cell} python3
with model:
    source = Chiller("source")
    tank = Tank("tank")
    product_out = pump.port(
        "product-out",
        direction="out",
        medium=enums.values.Fluid_Water,
    )
    connect(source, pump)
    outlet_link = connect(product_out, tank)

print([(port.name, port.medium) for port in pump.ports])
```

`pump.ports` includes concrete points already attached to the pump and any
authored deferred handles. A general pump may have no concrete points yet.
After resolution, use the corresponding instance in the snapshot to see every
chosen concrete point and its selected medium:

```{code-cell} python3
resolved = model.resolve()
resolved_pump = resolved[pump.name]
for point in resolved_pump.ports:
    print(point.name, point.type, point.medium)

from objectrdf.watr import OutletConnectionPoint

outlets = [
    point for point in resolved_pump.ports
    if isinstance(point, OutletConnectionPoint)
]
print("outlets:", [point.name for point in outlets])

assert resolved.connection(outlet_link).medium is enums.values.Fluid_Water
```

The solver may add unnamed-in-advance points to satisfy the contract. Naming
one outlet gives that outlet a stable authoring handle; it does not assume a
particular generated name for the others. Before resolution, `pump.ports`
contains authored handles such as `product_out`; after resolution,
`resolved_pump.ports` contains concrete connection-point instances. To query
all outlets, filter those concrete points by `OutletConnectionPoint`, as above.
For the reasoning behind a chosen medium or point, use
`resolved.explain(outlet_link)`.
