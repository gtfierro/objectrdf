"""Source SHACL determines generated signatures, defaults, and constraints."""

from importlib.util import module_from_spec, spec_from_file_location
import inspect
from pathlib import Path
import sys

import pytest
from rdflib import Graph, Literal, Namespace, URIRef, OWL, RDF, RDFS
from rdflib.compare import isomorphic
from rdflib.namespace import SH

from plumb import Model, connect
from plumb.core.errors import ModelingError
from plumb.gen import compile_modules, generate
from plumb.qudt import QuantityAmount as Q, units
from plumb.watr import Process_Aeration, Process_Denitrification, enums
from plumb.watr.asm2d import AerobicStage, RecyclePump

EX = Namespace("https://w3id.org/plumb/asm2d#")
S223 = Namespace("http://data.ashrae.org/standard223#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
SOURCE = Path(__file__).parents[1] / "ontology/asm2d.ttl"


def generated(graph, tmp_path):
    path = generate(graph, tmp_path / "generated", name="TestConfigurations")
    spec = spec_from_file_location("test_generated_configurations", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_regeneration_is_byte_identical_across_fresh_parses():
    first = compile_modules(
        Graph().parse(SOURCE), name="ASM2d", source="ontology/asm2d.ttl"
    )
    second = compile_modules(
        Graph().parse(SOURCE), name="ASM2d", source="ontology/asm2d.ttl"
    )
    assert first == second
    output = Path(__file__).parents[1] / "src/plumb/watr/asm2d"
    for filename, text in first.items():
        assert (output / filename).read_text() == text


@pytest.mark.parametrize("node", [EX.AerobicStage, EX.AerobicDesignShape])
def test_explicit_names_cannot_shadow_the_package_registry(node):
    graph = Graph().parse(SOURCE)
    graph.set(
        (
            node,
            URIRef("https://w3id.org/plumb/codegen#pythonName"),
            Literal("REGISTRY"),
        )
    )
    with pytest.raises(ValueError, match="generated name collision REGISTRY"):
        compile_modules(graph, name="Invalid")


def test_shape_default_edit_changes_generated_constructor(tmp_path):
    graph = Graph().parse(SOURCE)
    prop = next(
        prop
        for prop in graph.objects(EX.AerobicVolumeShape, SH.property)
        if graph.value(prop, SH.path) == S223.hasValue
    )
    graph.set((prop, SH.defaultValue, Literal(1400.0)))
    module = generated(graph, tmp_path)
    schema = module.AerobicDesign(oxygen_transfer_coefficient=10.0)
    assert schema.volume == 1400.0
    signature = inspect.signature(module.AerobicDesign)
    assert signature.parameters["volume"].default == 1400.0
    assert (
        signature.parameters["oxygen_transfer_coefficient"].default
        is inspect.Parameter.empty
    )
    with Model("urn:test:source#") as model:
        stage = module.AerobicStage("stage")
        stage.apply_properties(schema)
    assert isomorphic(model.export_ontology(), graph)


def test_required_collection_members_allow_additional_members():
    with Model("urn:test:members#"):
        stage = AerobicStage("stage", has_process=[Process_Denitrification])
        assert Process_Denitrification in stage.has_process
        assert Process_Aeration in stage.has_process
        before = list(stage.has_process)
        with pytest.raises(ModelingError, match="sh:hasValue"):
            stage.has_process.remove(Process_Aeration)
        assert list(stage.has_process) == before


def test_shape_defaults_are_replaceable_and_not_applied_on_hydration(tmp_path):
    graph = Graph().parse(SOURCE)
    prop = next(
        prop
        for prop in graph.objects(EX.AerobicStageShape, SH.property)
        if graph.value(prop, SH.hasValue) == URIRef(enums.values.Role_Aerobic.iri)
    )
    value = graph.value(prop, SH.hasValue)
    assert value is not None
    graph.remove((prop, SH.hasValue, value))
    graph.add((prop, SH.defaultValue, value))
    module = generated(graph, tmp_path)
    with Model("urn:test:defaults#") as model:
        stage = module.AerobicStage("stage")
        overridden = module.AerobicStage(
            "overridden", has_role=[enums.values.Role_Anoxic]
        )
        assert enums.values.Role_Aerobic in stage.has_role
        assert enums.values.Role_Aerobic not in overridden.has_role
        assert enums.values.Role_Anoxic in overridden.has_role
    data = model.graph()
    data.remove((URIRef(stage.meta.instance_iri), S223.hasRole, value))
    loaded = Model.from_graph(data, registries=module.AerobicStage.meta.registry)
    assert enums.values.Role_Aerobic not in getattr(loaded["stage"], "has_role")


def test_fixed_unit_rejects_otherwise_compatible_explicit_unit(tmp_path):
    graph = Graph().parse(SOURCE)
    prop = next(
        prop
        for prop in graph.objects(EX.DissolvedOxygenShape, SH.property)
        if graph.value(prop, SH.path) == QUDT.hasUnit
    )
    unit = graph.value(prop, SH.defaultValue)
    assert unit is not None
    graph.remove((prop, SH.defaultValue, unit))
    graph.add((prop, SH.hasValue, unit))
    module = generated(graph, tmp_path)
    with pytest.raises(ValueError, match="fixes unit"):
        module.OxygenOutletState(oxygen_concentration=Q(0.00191, units.KiloGM_PER_M3))


def test_source_shapes_reject_tampered_unit():
    import importlib.util

    path = SOURCE.parents[0].parent / "examples/watr/asm2d/watertap_asm2d.py"
    spec = importlib.util.spec_from_file_location("asm2d_unit_validation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.build_model()
    loaded = Model.from_graph(model.graph(), registries=AerobicStage.meta.registry)
    oxygen = loaded["R5-outlet-oxygen-concentration"]
    setattr(oxygen, "has_unit", units.SEC)
    assert not loaded.validate().ok


def test_named_and_unnamed_matching_select_identical_ports():
    selected = []
    for name in (None, "named"):
        with Model("urn:test:matching#") as model:
            left, right = RecyclePump("left"), RecyclePump("right")
            handle = connect(left, right, name=name)
        explanation = model.resolve().explain(handle)
        selected.append((explanation.source_point, explanation.target_point))
    assert selected[0] == selected[1] == ("left-outlet", "right-inlet")


def test_fresh_allocation_cannot_bypass_shape_counts():
    with Model("urn:test:ports#") as model:
        left, right = RecyclePump("left"), RecyclePump("right")
        before = model._revision
        with pytest.raises(ModelingError, match="additional ports"):
            connect(left, right, name="new", ports="new")
        assert model._revision == before
        assert not model._connection_intents


def test_compiler_diagnoses_default_outside_allowed_unit_set():
    graph = Graph().parse(SOURCE)
    prop = next(
        prop
        for prop in graph.objects(EX.DissolvedOxygenShape, SH.property)
        if graph.value(prop, SH.path) == QUDT.hasUnit
    )
    graph.set((prop, SH.defaultValue, URIRef(units.SEC.iri)))
    with pytest.raises(ValueError, match="outside sh:in"):
        compile_modules(graph, name="Invalid")


def test_local_class_inherits_generated_signature_and_named_ports(tmp_path):
    graph = Graph().parse(SOURCE)
    graph.add((EX.CustomAerobicStage, RDF.type, OWL.Class))
    graph.add((EX.CustomAerobicStage, RDFS.subClassOf, EX.AerobicStage))
    module = generated(graph, tmp_path)
    assert issubclass(module.CustomAerobicStage, module.AerobicStage)
    with Model("urn:test:inheritance#"):
        stage = module.CustomAerobicStage("custom")
        assert Process_Aeration in stage.has_process
        assert stage.outlet.name == "outlet"
    assert (
        inspect.signature(module.CustomAerobicStage).parameters["has_process"].default
        is None
    )


def test_generated_typing_checks_required_fields_and_value_types(tmp_path):
    import subprocess

    executable = Path(sys.executable).with_name("ty")
    if not executable.exists():
        pytest.skip("ty is not installed")
    fixture = tmp_path / "bad_schema_calls.py"
    fixture.write_text(
        "from plumb.watr.asm2d import AerobicDesign\n"
        "AerobicDesign(oxygen_transfer_coeficient=10.0)\n"
        "AerobicDesign(oxygen_transfer_coefficient='ten')\n"
    )
    result = subprocess.run(
        [str(executable), "check", str(fixture), "--output-format", "concise"],
        capture_output=True,
        text=True,
        check=False,
        cwd=SOURCE.parents[1],
    )
    assert result.returncode != 0
    assert "unknown-argument" in result.stdout
    assert "missing-argument" in result.stdout
    assert "invalid-argument-type" in result.stdout
