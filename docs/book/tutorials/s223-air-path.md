---
file_format: mystnb
kernelspec:
  name: python3
---

# An S223 air path

The API is the same for 223P building systems. This tutorial builds an air
handling unit around a damper and a fan, inspects the chosen connection,
walks the air path, and validates the RDF.

## 1. Create and connect

The damper and fan are created inside the AHU, so the AHU contains them. A
zone damper outside the AHU takes its supply air:

```{code-cell} python3
from plumb import Model, connect
from plumb.s223 import AirHandlingUnit, Damper, Fan, enums

with Model("urn:example:air-path#") as model:
    with AirHandlingUnit("ahu") as ahu:
        damper = Damper("outside-air-damper")
        fan = Fan("supply-fan")
    zone_damper = Damper("zone-damper")

air_link = connect(damper, fan)
connect(ahu, zone_damper, name="supply-duct")
print(damper.name, fan.name, air_link.name)
```

`damper >> fan` also records the connection, but returns the fan for
chaining.

The AHU's own inlet and outlet stand for points inside it. `maps_to` says
which: air enters through the damper and leaves through the fan.

```{code-cell} python3
model["outside-air-damper-in"].maps_to = model["ahu-in"]
model["supply-fan-out"].maps_to = model["ahu-out"]
```

## 2. Resolve

`check()` reports whether one interpretation exists. `resolve()` returns a
frozen snapshot with the chosen points and connection:

```{code-cell} python3
print(model.check().status)

resolved = model.resolve()
connection = resolved.connection(air_link)
explanation = resolved.explain(air_link)
print(connection.type, connection.medium)
print(explanation.source_point, "->", explanation.target_point)
```

The connection is a `Duct` because the medium is air. The snapshot holds the
derived points; the authored model does not:

```{code-cell} python3
print("authored:", len(model))
print("resolved:", len(resolved))
```

```{code-cell} python3
resolved_fan = resolved["supply-fan"]
list(resolved_fan.ports)
```

## 3. Walk the air path

`find_all_previous()` walks upstream along ducts and points. By default
equipment is a single node, so the zone damper sees only the AHU:

```{code-cell} python3
zone = resolved["zone-damper"]
zone.find_all_previous()
```

`descend=True` also steps into containers through their `maps_to` points.
`walk()` shows how far away each object is:

```{code-cell} python3
for hop in zone.walk("upstream", descend=True):
    print(hop.depth, hop.entity.name)
```

The fan is one step in, behind the AHU's outlet. The damper is one step past
it, through the duct the solver chose. Containment answers the other
question, what holds the fan:

```{code-cell} python3
resolved["supply-fan"].find_parent(AirHandlingUnit)
```

A walk can also start inside a container. It leaves through `maps_to`
without needing `descend`:

```{code-cell} python3
resolved["supply-fan"].find_all_next()
```

## 4. Validate

```{code-cell} python3
validation = model.validate()
print("conforms:", validation.ok, "issues:", len(validation.issues))
print("triples:", len(model.graph()))
```

`examples/s223/ahu/s223_quickstart.py` is a larger air and water example.
