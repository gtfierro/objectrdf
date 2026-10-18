"""Named points and interchangeable groups compiled from portable SHACL."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest
from rdflib import Graph, URIRef

from objectrdf import AmbiguousModelError, Model, connect
from objectrdf.core.errors import ModelingError
from objectrdf.gen import generate
from objectrdf.s223 import Chiller, Damper, Fan, OutletConnectionPoint, Pump, enums


@pytest.fixture
def domain(tmp_path):
    source = Path(__file__).with_name("fixtures") / "named_points.ttl"
    path = generate(Graph().parse(source), tmp_path / "domain", name="NamedPoints")
    spec = spec_from_file_location("test_named_points_domain", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_group_connection_ignores_interchangeable_point_permutations(domain):
    with Model("urn:test:groups#") as model:
        pump = domain.GroupedPump("pump")
        handle = connect(Chiller("chiller"), pump.inlets)
    assert model.check().complete
    resolved = model.resolve()
    assert len(resolved.point(pump.inlets)) == 2
    assert resolved.explain(handle).target_point in {
        point.name for point in resolved.point(pump.inlets)
    }
    loaded = Model.from_graph(resolved.graph(), registries=pump.meta.registry)
    restored = getattr(loaded["pump"], "inlets")
    assert {ref.name for ref in restored} == {"inlets-1", "inlets-2"}
    assert set(loaded.graph()) == set(resolved.graph())


def test_distinct_same_medium_inlets_require_explicit_selection(domain):
    with Model("urn:test:branches#") as model:
        pump = domain.BranchedPump("pump")
        connect(Chiller("chiller"), pump)
    assert model.check().status == "underconstrained"
    with pytest.raises(AmbiguousModelError, match="ambiguous"):
        model.resolve()
    with Model("urn:test:selected#") as selected:
        pump = domain.BranchedPump("pump")
        handle = connect(Chiller("chiller"), pump.secondary)
    assert selected.resolve().explain(handle).target_point == "pump-secondary"


def test_unconnected_named_points_materialize_and_enforce_medium(domain):
    with Model("urn:test:orphan#") as model:
        pump = domain.GroupedPump("pump")
        with pytest.raises(ModelingError, match="medium is fixed"):
            pump.outlet.medium = enums.values.Fluid_Air
    resolved = model.resolve()
    assert isinstance(resolved.point(pump.outlet), OutletConnectionPoint)
    assert len(resolved["pump"].ports) == 3


def test_group_connection_rejects_incompatible_medium(domain):
    with Model("urn:test:incompatible#") as model:
        pump = domain.GroupedPump("pump")
        connect(Fan("fan"), pump.inlets)
    assert model.check().status == "unsatisfiable"


def test_failed_configuration_construction_restores_reserved_names(domain):
    with Model("urn:test:rollback-points#") as model:
        original = Pump("pump-inlets-1")
        with pytest.raises(ModelingError, match="pump-inlets-1"):
            domain.GroupedPump("pump")
    assert model.entities == [original]
    assert model._port_intents == []
    assert model._reserved_names == set()


def test_hydration_rejects_missing_discriminating_point_facts(domain):
    with Model("urn:test:point-facts#") as model:
        pump = domain.BranchedPump("pump")
    graph = model.graph()
    primary = URIRef(model.namespace + "pump-primary")
    graph.remove((primary, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None))
    with pytest.raises(ModelingError, match="cannot identify named point"):
        Model.from_graph(graph, registries=pump.meta.registry)


def test_operator_connection_explanation_uses_authored_endpoints():
    with Model("urn:test:explanation#") as model:
        damper, fan = Damper("damper"), Fan("fan")
        damper >> fan
    explanation = model.resolve().explain(damper, fan)
    assert explanation.source_point == "damper-out"
    assert explanation.target_point == "fan-in"
