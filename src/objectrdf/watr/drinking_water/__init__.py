"""DrinkingWater: generated from RDF/SHACL. DO NOT EDIT."""
# ruff: noqa
from __future__ import annotations
from dataclasses import dataclass as _dataclass
from typing import Iterable as _Iterable
import objectrdf.watr as _BASE
from objectrdf.core import (Entity as _Entity, ClassInfo as _ClassInfo, CPSlot as _CPSlot,
    Model as _Model, Registry as _Registry, OntologyInfo as _OntologyInfo,
    PropertySpec as _PropertySpec, TermOne as _TermOne, Lit as _Lit,
    PropertySchema as _PropertySchema, QuantityDefinition as _QuantityDefinition,
    QuantityAmount as _QuantityAmount, TermValue as _TermValue, EnumValue as _EnumValue)
from objectrdf.core.points import PointDeclaration as _PointDeclaration, PointRef as _PointRef, PointGroupRef as _PointGroupRef
from objectrdf.core.shape_constraints import ShapeValues as _ShapeValues
from objectrdf.qudt import units as _units, quantity_kinds as _kinds
ONTOLOGY = _OntologyInfo('DrinkingWater', 'https://w3id.org/objectrdf/drinking-water#', source='ontology/drinking-water.ttl')
_REGISTRY = _Registry(ONTOLOGY)
REGISTRY = _REGISTRY
_REGISTRY.by_name.update(_BASE._REGISTRY.by_name)
_REGISTRY.by_iri.update(_BASE._REGISTRY.by_iri)
_REGISTRY.enums_by_iri.update(_BASE._REGISTRY.enums_by_iri)
_REGISTRY.terms_by_iri.update(_BASE._REGISTRY.terms_by_iri)
_REGISTRY.containment.rules.extend(_BASE._REGISTRY.containment.rules)
from pathlib import Path as _Path
from rdflib import Graph as _Graph
if '__file__' in globals():
    _REGISTRY.schema_graph = _Graph().parse(_Path(__file__).with_name('_shapes.ttl'))
_REGISTRY.terms_by_iri.update({})

class ChlorinationStage(_BASE.ChlorinationUnit):
    'Chlorine dosing and a contact stage with the objective of disinfection.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/objectrdf/drinking-water#ChlorinationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Chlorination and contact stage',
        definition='Chlorine dosing and a contact stage with the objective of disinfection.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='outlet', label='outlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb1cc2ee3c9d0b3b0e7adf56e4a477130f51b4cfd8f3dbc2e8e98079efd72c550f1', required=(_BASE.Process_ChlorineDosing,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cbdfd50f578fe39a7140829518789903fa5d3f29e031e2bb9f33afc0c7f54ced22', required=(_BASE.TreatmentObjective_Disinfection,), defaults=(), choices=(), minimum=0, maximum=None),
    )
    _shape_max_ports = 2
    inlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='in', label='inlet')
    outlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='out', label='outlet')
    _point_declarations = {
        'inlet': inlet,
        'outlet': outlet,
    }
    def __init__(self, name: str | None = None, *,
        actuated_by_property: _Iterable[_BASE.ActuatableProperty] | None = None,
        cnx: _Iterable[_BASE.ConnectionPoint] | None = None,
        connected: _Iterable[_BASE.Connectable] | None = None,
        connected_from: _Iterable[_BASE.Connectable] | None = None,
        connected_through: _Iterable[_BASE.Connection] | None = None,
        connected_to: _Iterable[_BASE.Connectable] | None = None,
        contains_: _Iterable[_Entity] | None = None,
        executes: _Iterable[_BASE.Function] | None = None,
        has_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_optional_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_physical_location: _Iterable[_BASE.PhysicalSpace] | None = None,
        has_process: _Iterable[type[_BASE.Process]] | None = None,
        has_property: _Iterable[_BASE.Property] | None = None,
        has_role: _Iterable[_EnumValue] | None = None,
        has_treatment_objective: _Iterable[type[_BASE.TreatmentObjective]] | None = None,
        medium: _Iterable[_Entity] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'has_property': has_property,
            'medium': medium,
            'has_optional_connection_point': has_optional_connection_point,
            'connected_to': connected_to,
            'has_connection_point': has_connection_point,
            'cnx': cnx,
            'connected': connected,
            'connected_through': connected_through,
            'connected_from': connected_from,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'executes': executes,
            'contains_': contains_,
            'has_physical_location': has_physical_location,
            'has_role': has_role,
            'actuated_by_property': actuated_by_property,
        })

class ClarificationStage(_BASE.SedimentationTank):
    'Settles flocs and separates clarified water from a sludge withdrawal.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/objectrdf/drinking-water#ClarificationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Clarification stage',
        definition='Settles flocs and separates clarified water from a sludge withdrawal.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='clarified_water', label='clarified_water'), _CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='https://watermetadata.org/ontology/watr#Fluid-Sludge', min_count=1, max_count=1, name='sludge', label='sludge'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb111a38824b54f10c16954eca2c5203ae8efdc58af8e58ace26d4eb61fb8f16774', required=(_BASE.Process_Sedimentation,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cba2396c842b6af7786b903c2ca288cd5fe341bdb6e39004f274590db65c8324a5', required=(_BASE.TreatmentObjective_Clarification,), defaults=(), choices=(), minimum=0, maximum=None),
    )
    _shape_max_ports = 3
    clarified_water = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='out', label='clarified_water')
    inlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='in', label='inlet')
    sludge = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['https://watermetadata.org/ontology/watr#Fluid-Sludge'], direction='out', label='sludge')
    _point_declarations = {
        'clarified_water': clarified_water,
        'inlet': inlet,
        'sludge': sludge,
    }
    def __init__(self, name: str | None = None, *,
        actuated_by_property: _Iterable[_BASE.ActuatableProperty] | None = None,
        cnx: _Iterable[_BASE.ConnectionPoint] | None = None,
        connected: _Iterable[_BASE.Connectable] | None = None,
        connected_from: _Iterable[_BASE.Connectable] | None = None,
        connected_through: _Iterable[_BASE.Connection] | None = None,
        connected_to: _Iterable[_BASE.Connectable] | None = None,
        contains_: _Iterable[_Entity] | None = None,
        executes: _Iterable[_BASE.Function] | None = None,
        has_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_optional_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_physical_location: _Iterable[_BASE.PhysicalSpace] | None = None,
        has_process: _Iterable[type[_BASE.Process]] | None = None,
        has_property: _Iterable[_BASE.Property] | None = None,
        has_role: _Iterable[_EnumValue] | None = None,
        has_treatment_objective: _Iterable[type[_BASE.TreatmentObjective]] | None = None,
        medium: _Iterable[_Entity] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'has_property': has_property,
            'medium': medium,
            'has_optional_connection_point': has_optional_connection_point,
            'connected_to': connected_to,
            'has_connection_point': has_connection_point,
            'cnx': cnx,
            'connected': connected,
            'connected_through': connected_through,
            'connected_from': connected_from,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'executes': executes,
            'contains_': contains_,
            'has_physical_location': has_physical_location,
            'has_role': has_role,
            'actuated_by_property': actuated_by_property,
        })

class CoagulationStage(_BASE.CoagulationBasin):
    'Coagulant addition and particle destabilization ahead of flocculation.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/objectrdf/drinking-water#CoagulationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Coagulation stage',
        definition='Coagulant addition and particle destabilization ahead of flocculation.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='outlet', label='outlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb15035466b04bb04744f7c9c66763bb433dec8738b0a9619d047794fb530551fb7', required=(_BASE.Process_Coagulation,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cb55739a77942d14b2812c61ecb54bfe26ef40bc879d6278eafe91ebddc30ecdc9', required=(_BASE.TreatmentObjective_TurbidityRemoval,), defaults=(), choices=(), minimum=0, maximum=None),
    )
    _shape_max_ports = 2
    inlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='in', label='inlet')
    outlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='out', label='outlet')
    _point_declarations = {
        'inlet': inlet,
        'outlet': outlet,
    }
    def __init__(self, name: str | None = None, *,
        actuated_by_property: _Iterable[_BASE.ActuatableProperty] | None = None,
        cnx: _Iterable[_BASE.ConnectionPoint] | None = None,
        connected: _Iterable[_BASE.Connectable] | None = None,
        connected_from: _Iterable[_BASE.Connectable] | None = None,
        connected_through: _Iterable[_BASE.Connection] | None = None,
        connected_to: _Iterable[_BASE.Connectable] | None = None,
        contains_: _Iterable[_Entity] | None = None,
        executes: _Iterable[_BASE.Function] | None = None,
        has_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_optional_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_physical_location: _Iterable[_BASE.PhysicalSpace] | None = None,
        has_process: _Iterable[type[_BASE.Process]] | None = None,
        has_property: _Iterable[_BASE.Property] | None = None,
        has_role: _Iterable[_EnumValue] | None = None,
        has_treatment_objective: _Iterable[type[_BASE.TreatmentObjective]] | None = None,
        medium: _Iterable[_Entity] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'has_property': has_property,
            'medium': medium,
            'has_optional_connection_point': has_optional_connection_point,
            'connected_to': connected_to,
            'has_connection_point': has_connection_point,
            'cnx': cnx,
            'connected': connected,
            'connected_through': connected_through,
            'connected_from': connected_from,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'executes': executes,
            'contains_': contains_,
            'has_physical_location': has_physical_location,
            'has_role': has_role,
            'actuated_by_property': actuated_by_property,
        })

class FlocculationStage(_BASE.FlocculationBasin):
    'Gentle mixing to form flocs that can settle in the clarifier.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/objectrdf/drinking-water#FlocculationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Flocculation stage',
        definition='Gentle mixing to form flocs that can settle in the clarifier.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='outlet', label='outlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cbebaeafbc6e7c1c092143f892a9503a6f19156da39a82ae623725beeb37ee842', required=(_BASE.Process_Flocculation,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cb60a44c6152b6365299bc63cc5e19c7be962a4d97ac3195ddc93b1e97a12103b', required=(_BASE.TreatmentObjective_TurbidityRemoval,), defaults=(), choices=(), minimum=0, maximum=None),
    )
    _shape_max_ports = 2
    inlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='in', label='inlet')
    outlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='out', label='outlet')
    _point_declarations = {
        'inlet': inlet,
        'outlet': outlet,
    }
    def __init__(self, name: str | None = None, *,
        actuated_by_property: _Iterable[_BASE.ActuatableProperty] | None = None,
        cnx: _Iterable[_BASE.ConnectionPoint] | None = None,
        connected: _Iterable[_BASE.Connectable] | None = None,
        connected_from: _Iterable[_BASE.Connectable] | None = None,
        connected_through: _Iterable[_BASE.Connection] | None = None,
        connected_to: _Iterable[_BASE.Connectable] | None = None,
        contains_: _Iterable[_Entity] | None = None,
        executes: _Iterable[_BASE.Function] | None = None,
        has_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_optional_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_physical_location: _Iterable[_BASE.PhysicalSpace] | None = None,
        has_process: _Iterable[type[_BASE.Process]] | None = None,
        has_property: _Iterable[_BASE.Property] | None = None,
        has_role: _Iterable[_EnumValue] | None = None,
        has_treatment_objective: _Iterable[type[_BASE.TreatmentObjective]] | None = None,
        medium: _Iterable[_Entity] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'has_property': has_property,
            'medium': medium,
            'has_optional_connection_point': has_optional_connection_point,
            'connected_to': connected_to,
            'has_connection_point': has_connection_point,
            'cnx': cnx,
            'connected': connected,
            'connected_through': connected_through,
            'connected_from': connected_from,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'executes': executes,
            'contains_': contains_,
            'has_physical_location': has_physical_location,
            'has_role': has_role,
            'actuated_by_property': actuated_by_property,
        })

class RapidSandFiltrationStage(_BASE.RapidSandFilter):
    'Filters clarified water through sand; spent backwash leaves separately during cleaning.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/objectrdf/drinking-water#RapidSandFiltrationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Rapid sand filtration stage',
        definition='Filters clarified water through sand; spent backwash leaves separately during cleaning.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='backwash_supply', label='backwash_supply'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='backwash_waste', label='backwash_waste'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='filtered_water', label='filtered_water'), _CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cbeab3a02735a3eedc5263877ff7407cf8ffd41281182f0e49935bfd8ee322fc4a', required=(_BASE.Process_RapidSandFiltration,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cb66b8e4e54361f379952b7b3d7d3976649022f88c04588f55ef06c5badc2e123e', required=(_BASE.TreatmentObjective_TurbidityRemoval,), defaults=(), choices=(), minimum=0, maximum=None),
    )
    _shape_max_ports = 4
    backwash_supply = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='in', label='backwash_supply')
    backwash_waste = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='out', label='backwash_waste')
    filtered_water = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='out', label='filtered_water')
    inlet = _PointDeclaration[_PointRef](count=1, medium=_BASE._REGISTRY.enums_by_iri['http://data.ashrae.org/standard223#Fluid-Water'], direction='in', label='inlet')
    _point_declarations = {
        'backwash_supply': backwash_supply,
        'backwash_waste': backwash_waste,
        'filtered_water': filtered_water,
        'inlet': inlet,
    }
    def __init__(self, name: str | None = None, *,
        actuated_by_property: _Iterable[_BASE.ActuatableProperty] | None = None,
        cnx: _Iterable[_BASE.ConnectionPoint] | None = None,
        connected: _Iterable[_BASE.Connectable] | None = None,
        connected_from: _Iterable[_BASE.Connectable] | None = None,
        connected_through: _Iterable[_BASE.Connection] | None = None,
        connected_to: _Iterable[_BASE.Connectable] | None = None,
        contains_: _Iterable[_Entity] | None = None,
        executes: _Iterable[_BASE.Function] | None = None,
        has_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_optional_connection_point: _Iterable[_BASE.ConnectionPoint] | None = None,
        has_physical_location: _Iterable[_BASE.PhysicalSpace] | None = None,
        has_process: _Iterable[type[_BASE.Process]] | None = None,
        has_property: _Iterable[_BASE.Property] | None = None,
        has_role: _Iterable[_EnumValue] | None = None,
        has_treatment_objective: _Iterable[type[_BASE.TreatmentObjective]] | None = None,
        medium: _Iterable[_Entity] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'has_property': has_property,
            'medium': medium,
            'has_optional_connection_point': has_optional_connection_point,
            'connected_to': connected_to,
            'has_connection_point': has_connection_point,
            'cnx': cnx,
            'connected': connected,
            'connected_through': connected_through,
            'connected_from': connected_from,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'executes': executes,
            'contains_': contains_,
            'has_physical_location': has_physical_location,
            'has_role': has_role,
            'actuated_by_property': actuated_by_property,
        })

__all__ = ['ONTOLOGY', 'REGISTRY', 'ChlorinationStage', 'ClarificationStage', 'CoagulationStage', 'FlocculationStage', 'RapidSandFiltrationStage']
