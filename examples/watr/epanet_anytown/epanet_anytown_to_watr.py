"""Convert an EPANET network, such as Anytown, into a sensor-rich WaTr model.

Download the Anytown "EPANET file" from:
https://uknowledge.uky.edu/wdst_models/1/

The source dataset is Thomas M. Walski's "01 Anytown" (2016), distributed
under CC BY-NC 4.0. Preserve that attribution when sharing generated models.

Then run:

    uv run python examples/watr/epanet_anytown/epanet_anytown_to_watr.py \
        examples/watr/epanet_anytown/Anytown.inp

The converter uses only the standard library and objectrdf. EPANET pipes are
modeled as bidirectional S223 Pipe connections because their simulated flow can
reverse. Pumps and valves retain the nominal Node1-to-Node2 direction from the
input file.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from objectrdf import Model, connect
from objectrdf.qudt import quantity, quantity_kinds, units
from objectrdf.watr import (
    FlowSensor,
    Junction,
    LevelSensor,
    Pipe,
    PressureSensor,
    Pump,
    QuantifiableObservableProperty,
    QuantifiableProperty,
    Reservoir,
    Tank,
    TemperatureSensor,
    TurbidityMeter,
    Valve,
    enums,
)

SOURCE = "https://uknowledge.uky.edu/wdst_models/1/"
DEFAULT_NAMESPACE = "urn:example/epanet/anytown#"


@dataclass(frozen=True)
class EpanetRow:
    """One tokenized row from an EPANET section."""

    values: tuple[str, ...]
    comment: str | None = None


@dataclass
class EpanetNetwork:
    """The EPANET sections used by this converter."""

    sections: dict[str, list[EpanetRow]] = field(
        default_factory=lambda: defaultdict(list)
    )
    options: dict[str, str] = field(default_factory=dict)
    coordinates: dict[str, tuple[float, float]] = field(default_factory=dict)


def parse_epanet(path: Path) -> EpanetNetwork:
    """Parse the whitespace-delimited portions of an EPANET INP file."""
    network = EpanetNetwork()
    section = ""

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        content, separator, comment = raw_line.partition(";")
        content = content.strip()
        if not content:
            continue
        if content.startswith("[") and content.endswith("]"):
            section = content[1:-1].strip().upper()
            continue
        if not section:
            raise ValueError(f"{path}:{line_number}: content before a section")

        values = tuple(content.split())
        row = EpanetRow(values, comment.strip() if separator and comment else None)
        network.sections[section].append(row)

    for row in network.sections.get("OPTIONS", []):
        if len(row.values) >= 2:
            network.options[row.values[0].upper()] = row.values[1]
    for row in network.sections.get("COORDINATES", []):
        if len(row.values) >= 3:
            network.coordinates[row.values[0]] = (
                _number(row.values[1], "coordinate"),
                _number(row.values[2], "coordinate"),
            )
    if not any(
        network.sections.get(section)
        for section in ("JUNCTIONS", "RESERVOIRS", "TANKS")
    ):
        raise ValueError(f"{path} does not contain any EPANET network nodes")
    return network


def _number(value: str, field_name: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"invalid {field_name} value {value!r}") from error


def _name(kind: str, epanet_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9._~-]+", "-", epanet_id).strip("-")
    return f"{kind}-{safe_id or 'unnamed'}"


def _location_comment(
    epanet_id: str,
    network: EpanetNetwork,
    row: EpanetRow,
) -> str:
    details = [f"EPANET ID: {epanet_id}."]
    if epanet_id in network.coordinates:
        x, y = network.coordinates[epanet_id]
        details.append(f"EPANET coordinates: ({x:g}, {y:g}).")
    if row.comment:
        details.append(row.comment)
    details.append(f"Source: Walski (2016), {SOURCE} (CC BY-NC 4.0).")
    return " ".join(details)


def _is_us_customary(flow_units: str) -> bool:
    return flow_units in {"CFS", "GPM", "MGD", "IMGD", "AFD"}


def _flow_unit(flow_units: str) -> tuple[Any, float]:
    mappings = {
        "CFS": (units.FT3_PER_SEC, 1.0),
        "GPM": (units.GAL_US_PER_MIN, 1.0),
        "MGD": (units.GAL_US_PER_DAY, 1_000_000.0),
        "IMGD": (units.GAL_UK_PER_DAY, 1_000_000.0),
        "LPS": (units.L_PER_SEC, 1.0),
        "LPM": (units.L_PER_MIN, 1.0),
        "MLD": (units.M3_PER_DAY, 1_000.0),
        "CMH": (units.M3_PER_HR, 1.0),
        "CMD": (units.M3_PER_DAY, 1.0),
    }
    if flow_units not in mappings:
        raise ValueError(
            f"unsupported EPANET flow units {flow_units!r}; "
            f"supported values: {', '.join(sorted(mappings))}"
        )
    return mappings[flow_units]


def _static_quantity(
    owner: Any,
    name: str,
    value: float,
    unit: Any,
    quantity_kind: Any,
    label: str,
) -> QuantifiableProperty:
    return quantity(
        QuantifiableProperty,
        name,
        value,
        unit,
        quantity_kind,
        of=owner,
        label=label,
        has_aspect=[enums.Aspect_Nominal],
    )


def _observable(
    location: Any,
    *,
    name: str,
    label: str,
    quantity_kind: Any,
    unit: Any,
) -> QuantifiableObservableProperty:
    observed = QuantifiableObservableProperty(
        name,
        label=label,
        has_quantity_kind=quantity_kind,
        has_unit=unit,
        of_medium=enums.Fluid_Water,
    )
    location.has_property.add(observed)
    return observed


def _add_sensor(
    sensor_class: type[Any],
    location: Any,
    *,
    sensor_name: str,
    property_name: str,
    label: str,
    quantity_kind: Any,
    unit: Any,
    comment: str,
) -> Any:
    observed = _observable(
        location,
        name=property_name,
        label=label,
        quantity_kind=quantity_kind,
        unit=unit,
    )
    return sensor_class(
        sensor_name,
        label=f"{label} sensor",
        comment=comment,
        has_observation_location=location,
        observes=observed,
    )


def build_watr_model(
    network: EpanetNetwork,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    sensor_density: float = 0.25,
    quality_sensors: bool = True,
) -> tuple[Model, dict[str, int]]:
    """Create a WaTr model and deterministic sensor plan from EPANET data."""
    if not 0.0 <= sensor_density <= 1.0:
        raise ValueError("sensor_density must be between 0 and 1")

    flow_units = network.options.get("UNITS", "GPM").upper()
    flow_unit, flow_scale = _flow_unit(flow_units)
    us_customary = _is_us_customary(flow_units)
    length_unit = units.FT if us_customary else units.M
    diameter_unit = units.IN if us_customary else units.MilliM
    pressure_unit = units.PSI if us_customary else units.KiloPA

    model = Model(
        namespace,
        name="EPANET Anytown WaTr network",
        prefixes={
            "s223": "http://data.ashrae.org/standard223#",
            "watr": "urn:nawi-water-ontology#",
        },
    )
    nodes: dict[str, Any] = {}
    row_by_node: dict[str, EpanetRow] = {}
    degree: dict[str, int] = defaultdict(int)
    downstream_by_pump: list[tuple[str, str]] = []
    pipe_candidates: list[tuple[float, str, str]] = []
    sensor_count: dict[str, int] = defaultdict(int)

    with model:
        for row in network.sections.get("JUNCTIONS", []):
            if len(row.values) < 2:
                continue
            epanet_id = row.values[0]
            node = Junction(
                _name("junction", epanet_id),
                label=f"EPANET junction {epanet_id}",
                comment=_location_comment(epanet_id, network, row),
                has_medium=enums.Fluid_Water,
            )
            nodes[epanet_id] = node
            row_by_node[epanet_id] = row
            _static_quantity(
                node,
                _name("elevation", epanet_id),
                _number(row.values[1], "junction elevation"),
                length_unit,
                quantity_kinds.Length,
                "Junction elevation",
            )
            if len(row.values) >= 3:
                demand = _number(row.values[2], "junction demand")
                if demand:
                    _static_quantity(
                        node,
                        _name("base-demand", epanet_id),
                        demand * flow_scale,
                        flow_unit,
                        quantity_kinds.VolumeFlowRate,
                        "Base demand",
                    )

        for row in network.sections.get("RESERVOIRS", []):
            if len(row.values) < 2:
                continue
            epanet_id = row.values[0]
            node = Reservoir(
                _name("reservoir", epanet_id),
                label=f"EPANET reservoir {epanet_id}",
                comment=_location_comment(epanet_id, network, row),
            )
            nodes[epanet_id] = node
            row_by_node[epanet_id] = row
            _static_quantity(
                node,
                _name("hydraulic-head", epanet_id),
                _number(row.values[1], "reservoir head"),
                length_unit,
                quantity_kinds.Length,
                "Hydraulic head",
            )

        for row in network.sections.get("TANKS", []):
            if len(row.values) < 7:
                continue
            epanet_id = row.values[0]
            node = Tank(
                _name("tank", epanet_id),
                label=f"EPANET tank {epanet_id}",
                comment=_location_comment(epanet_id, network, row),
            )
            nodes[epanet_id] = node
            row_by_node[epanet_id] = row
            tank_fields = (
                ("elevation", 1, "Tank elevation"),
                ("initial-level", 2, "Initial water level"),
                ("minimum-level", 3, "Minimum water level"),
                ("maximum-level", 4, "Maximum water level"),
            )
            for field_name, index, label in tank_fields:
                _static_quantity(
                    node,
                    _name(field_name, epanet_id),
                    _number(row.values[index], label.lower()),
                    length_unit,
                    quantity_kinds.Length,
                    label,
                )
            _static_quantity(
                node,
                _name("diameter", epanet_id),
                _number(row.values[5], "tank diameter"),
                length_unit,
                quantity_kinds.Length,
                "Tank diameter",
            )

        def require_node(epanet_id: str, link_id: str) -> Any:
            if epanet_id not in nodes:
                raise ValueError(
                    f"EPANET link {link_id!r} references unknown node {epanet_id!r}"
                )
            return nodes[epanet_id]

        for row in network.sections.get("PIPES", []):
            if len(row.values) < 6:
                continue
            link_id, node_1, node_2 = row.values[:3]
            first = require_node(node_1, link_id)
            second = require_node(node_2, link_id)
            degree[node_1] += 1
            degree[node_2] += 1
            first_port = first.port(
                _name(f"pipe-{link_id}", f"{node_1}-end"),
                direction="bi",
                medium=enums.Fluid_Water,
            )
            second_port = second.port(
                _name(f"pipe-{link_id}", f"{node_2}-end"),
                direction="bi",
                medium=enums.Fluid_Water,
            )
            pipe = connect(
                first_port,
                second_port,
                medium=enums.Fluid_Water,
                connection=Pipe,
                name=_name("pipe", link_id),
            )
            pipe.label = f"EPANET pipe {link_id}"
            pipe.comment = row.comment or f"EPANET link {node_1} — {node_2}."
            length = _number(row.values[3], "pipe length")
            diameter = _number(row.values[4], "pipe diameter")
            pipe_candidates.append((diameter, link_id, node_2))
            _static_quantity(
                pipe,
                _name("length", link_id),
                length,
                length_unit,
                quantity_kinds.Length,
                "Pipe length",
            )
            _static_quantity(
                pipe,
                _name("diameter", link_id),
                diameter,
                diameter_unit,
                quantity_kinds.Length,
                "Pipe diameter",
            )
            _static_quantity(
                pipe,
                _name("roughness", link_id),
                _number(row.values[5], "pipe roughness"),
                units.UNITLESS,
                quantity_kinds.Dimensionless,
                "EPANET roughness coefficient",
            )

        for row in network.sections.get("PUMPS", []):
            if len(row.values) < 3:
                continue
            link_id, node_1, node_2 = row.values[:3]
            first = require_node(node_1, link_id)
            second = require_node(node_2, link_id)
            degree[node_1] += 1
            degree[node_2] += 1
            pump = Pump(
                _name("pump", link_id),
                label=f"EPANET pump {link_id}",
                comment=" ".join(row.values[3:]) or "EPANET pump.",
            )
            upstream_port = first.port(
                _name("pump-suction", f"{link_id}-{node_1}-end"),
                direction="out",
                medium=enums.Fluid_Water,
            )
            pump_in = pump.port(
                _name("pump-suction", f"{link_id}-pump-end"),
                direction="in",
                medium=enums.Fluid_Water,
            )
            pump_out = pump.port(
                _name("pump-discharge", f"{link_id}-pump-end"),
                direction="out",
                medium=enums.Fluid_Water,
            )
            downstream_port = second.port(
                _name("pump-discharge", f"{link_id}-{node_2}-end"),
                direction="in",
                medium=enums.Fluid_Water,
            )
            connect(
                upstream_port,
                pump_in,
                medium=enums.Fluid_Water,
                connection=Pipe,
                name=_name("pump-suction", link_id),
            )
            connect(
                pump_out,
                downstream_port,
                medium=enums.Fluid_Water,
                connection=Pipe,
                name=_name("pump-discharge", link_id),
            )
            downstream_by_pump.append((link_id, node_2))

        for row in network.sections.get("VALVES", []):
            if len(row.values) < 3:
                continue
            link_id, node_1, node_2 = row.values[:3]
            first = require_node(node_1, link_id)
            second = require_node(node_2, link_id)
            degree[node_1] += 1
            degree[node_2] += 1
            valve = Valve(
                _name("valve", link_id),
                label=f"EPANET {row.values[4] if len(row.values) > 4 else ''} "
                f"valve {link_id}".strip(),
                comment=" ".join(row.values[3:]),
            )
            upstream_port = first.port(
                _name("valve-upstream", f"{link_id}-{node_1}-end"),
                direction="out",
                medium=enums.Fluid_Water,
            )
            valve_in = valve.port(
                _name("valve-upstream", f"{link_id}-valve-end"),
                direction="in",
                medium=enums.Fluid_Water,
            )
            valve_out = valve.port(
                _name("valve-downstream", f"{link_id}-valve-end"),
                direction="out",
                medium=enums.Fluid_Water,
            )
            downstream_port = second.port(
                _name("valve-downstream", f"{link_id}-{node_2}-end"),
                direction="in",
                medium=enums.Fluid_Water,
            )
            connect(
                upstream_port,
                valve_in,
                medium=enums.Fluid_Water,
                connection=Pipe,
                name=_name("valve-upstream", link_id),
            )
            connect(
                valve_out,
                downstream_port,
                medium=enums.Fluid_Water,
                connection=Pipe,
                name=_name("valve-downstream", link_id),
            )

        junction_ids = sorted(
            row.values[0] for row in network.sections.get("JUNCTIONS", [])
        )
        selected_junctions = {
            epanet_id for epanet_id in junction_ids if degree[epanet_id] >= 3
        }
        target_count = round(len(junction_ids) * sensor_density)
        if target_count and junction_ids:
            step = max(1, len(junction_ids) // target_count)
            selected_junctions.update(junction_ids[::step][:target_count])

        pressure_locations = (
            set(selected_junctions)
            | {row.values[0] for row in network.sections.get("RESERVOIRS", [])}
            | {row.values[0] for row in network.sections.get("TANKS", [])}
            | {node_id for _, node_id in downstream_by_pump}
        )
        for epanet_id in sorted(pressure_locations):
            location = nodes[epanet_id]
            _add_sensor(
                PressureSensor,
                location,
                sensor_name=_name("pressure-sensor", epanet_id),
                property_name=_name("observed-pressure", epanet_id),
                label=f"Pressure at {epanet_id}",
                quantity_kind=quantity_kinds.Pressure,
                unit=pressure_unit,
                comment="Pressure monitoring point selected from network topology.",
            )
            sensor_count["pressure"] += 1

        for row in network.sections.get("TANKS", []):
            epanet_id = row.values[0]
            _add_sensor(
                LevelSensor,
                nodes[epanet_id],
                sensor_name=_name("level-sensor", epanet_id),
                property_name=_name("observed-level", epanet_id),
                label=f"Water level at {epanet_id}",
                quantity_kind=quantity_kinds.Length,
                unit=length_unit,
                comment="Tank level instrumentation.",
            )
            sensor_count["level"] += 1

        flow_locations = {
            (f"pump-{link_id}", node_id)
            for link_id, node_id in downstream_by_pump
        }
        trunk_count = max(1, round(len(pipe_candidates) * sensor_density / 2))
        for _, link_id, node_id in sorted(pipe_candidates, reverse=True)[
            :trunk_count
        ]:
            flow_locations.add((f"pipe-{link_id}", node_id))
        for link_name, node_id in sorted(flow_locations):
            _add_sensor(
                FlowSensor,
                nodes[node_id],
                sensor_name=_name("flow-sensor", link_name),
                property_name=_name("observed-flow", link_name),
                label=f"Flow at {link_name}",
                quantity_kind=quantity_kinds.VolumeFlowRate,
                unit=flow_unit,
                comment=f"Flow meter assigned to EPANET link {link_name}.",
            )
            sensor_count["flow"] += 1

        if quality_sensors:
            quality_locations = {
                row.values[0]
                for section in ("RESERVOIRS", "TANKS")
                for row in network.sections.get(section, [])
            }
            quality_locations.update(
                sorted(junction_ids, key=lambda item: (-degree[item], item))[:3]
            )
            for epanet_id in sorted(quality_locations):
                location = nodes[epanet_id]
                _add_sensor(
                    TurbidityMeter,
                    location,
                    sensor_name=_name("turbidity-meter", epanet_id),
                    property_name=_name("observed-turbidity", epanet_id),
                    label=f"Turbidity at {epanet_id}",
                    quantity_kind=quantity_kinds.Turbidity,
                    unit=units.NTU,
                    comment="Water-quality monitoring suite.",
                )
                _add_sensor(
                    TemperatureSensor,
                    location,
                    sensor_name=_name("temperature-sensor", epanet_id),
                    property_name=_name("observed-temperature", epanet_id),
                    label=f"Water temperature at {epanet_id}",
                    quantity_kind=quantity_kinds.Temperature,
                    unit=units.DEG_C,
                    comment="Water-quality monitoring suite.",
                )
                sensor_count["quality"] += 2

    counts = {
        "nodes": len(nodes),
        "pipes": len(network.sections.get("PIPES", [])),
        "pumps": len(network.sections.get("PUMPS", [])),
        "valves": len(network.sections.get("VALVES", [])),
        "sensors": sum(sensor_count.values()),
        **{f"{kind}_sensors": count for kind, count in sensor_count.items()},
    }
    return model, counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an EPANET INP network into a WaTr/S223 RDF model.",
        epilog=f"Anytown source: {SOURCE}",
    )
    parser.add_argument("inp", type=Path, help="EPANET .inp file")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).with_name("anytown_watr.ttl"),
        help="output RDF file (default: beside this script)",
    )
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument(
        "--sensor-density",
        type=float,
        default=0.25,
        help="fraction of junctions sampled in addition to critical nodes",
    )
    parser.add_argument(
        "--no-quality-sensors",
        action="store_true",
        help="omit turbidity and water-temperature sensor suites",
    )
    args = parser.parse_args()

    network = parse_epanet(args.inp)
    model, counts = build_watr_model(
        network,
        namespace=args.namespace,
        sensor_density=args.sensor_density,
        quality_sensors=not args.no_quality_sensors,
    )
    model.save(args.out)
    summary = ", ".join(f"{name}={value}" for name, value in counts.items())
    print(f"wrote {args.out}: {summary}")


if __name__ == "__main__":
    main()
