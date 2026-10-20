# Changelog

All notable changes to objectrdf are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html). While
the version is below 1.0, minor releases may change the public API.

## [Unreleased]

## [0.1.0] - Unreleased

First public release.

### Added

- Typed Python packages generated from ontologies and their SHACL shapes:
  Brick 1.4.2, ASHRAE 223P (v1.0.0-2026), WATR v0.3.0.rc1, and QUDT units and
  quantity kinds. Generated classes carry ontology definitions and typed
  constructors, so editors and type checkers see the whole vocabulary.
- `Model` sessions that serialize authored objects to Turtle, with containment
  through `with` blocks, flow connections through `>>` and `connect()`, and
  SHACL validation through shifty whose reports name the authored objects.
- Deferred 223P and WATR connections: the Z3 resolver chooses connection
  points, media, and Connection classes, and `explain()` reports why.
- `Model.from_graph()` to load existing RDF as typed, editable objects, with
  optional SHACL-AF inference, plus querying helpers.
- Domain configurations and immutable property schemas compiled from SHACL,
  with QUDT-aware quantities (`apply_properties()`, `quantity()`).
- `.sensor()` on equipment, points, ports, and connections creates an observed
  quantity and the most specific sensor class for its quantity kind.
- A sensor's observation or reference location may be a deferred connection,
  port, or declared point; resolution places it on the concrete entity.
- Property schemas written in Python: subclass `PropertySchema` and declare
  fields with `quantity_field()`.
- WATR process and treatment-objective defaults implied by an equipment
  class's shapes are filled in at construction.
- The `objectrdf gen` command for compiling other ontologies, with
  deterministic output for an unchanged imports closure.

### Changed

- Compared with pre-release builds, multi-valued enum properties such as
  `has_role` and equipment `medium` return a live collection with `add()`,
  `remove()`, and `clear()` instead of a plain `list`. Each change is
  range-checked and shape-checked. Code that called `.append()` on the old list must use
  `.add()`; comparisons with lists, such as `duct.has_role == [...]`, still
  work.
- Equipment whose shapes require connection points in only one direction,
  such as WaTr's separation tanks and 223P's electrical appliances, now
  accepts deferred connections in the other direction instead of reporting
  them as unsatisfiable. `UnsatisfiableModelError` messages name the
  conflicting constraints.
- Deferred connections resolve for equipment whose shapes need several points
  of one class (an `IceMaker`'s electricity and water inlets), forbid a class
  outright (`AirHeatExchanger`), or require identical points
  (`DualDuctTerminal`'s two air inlets). Points created from shapes are named
  after their owner, such as `hx-in-2`, rather than `inlet_connection_point_1`.
- A port or connection point with an explicit medium is no longer held to the
  media its class's shapes mention, so a `Fan` can have a declared
  electricity inlet. Medium-domain conflicts now appear in unsatisfiable cores.

[Unreleased]: https://github.com/gtfierro/objectrdf/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gtfierro/objectrdf/releases/tag/v0.1.0
