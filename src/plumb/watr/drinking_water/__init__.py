"""DrinkingWater: generated from RDF/SHACL. DO NOT EDIT."""
# ruff: noqa
from __future__ import annotations
from dataclasses import dataclass as _dataclass
from typing import Iterable as _Iterable
import plumb.watr as _BASE
from plumb.core import (Entity as _Entity, ClassInfo as _ClassInfo, CPSlot as _CPSlot,
    Model as _Model, Registry as _Registry, OntologyInfo as _OntologyInfo,
    PropertySpec as _PropertySpec, TermOne as _TermOne, Lit as _Lit,
    PropertySchema as _PropertySchema, QuantityDefinition as _QuantityDefinition,
    QuantityAmount as _QuantityAmount, TermValue as _TermValue, EnumValue as _EnumValue)
from plumb.core.points import PointDeclaration as _PointDeclaration, PointRef as _PointRef, PointGroupRef as _PointGroupRef
from plumb.core.shape_constraints import ShapeValues as _ShapeValues
from plumb.qudt import units as _units, quantity_kinds as _kinds
ONTOLOGY = _OntologyInfo('DrinkingWater', 'https://w3id.org/plumb/drinking-water#', source='ontology/drinking-water.ttl')
_REGISTRY = _Registry(ONTOLOGY)
REGISTRY = _REGISTRY
_REGISTRY.by_name.update(_BASE._REGISTRY.by_name)
_REGISTRY.by_iri.update(_BASE._REGISTRY.by_iri)
_REGISTRY.enums_by_iri.update(_BASE._REGISTRY.enums_by_iri)
_REGISTRY.terms_by_iri.update(_BASE._REGISTRY.terms_by_iri)
_REGISTRY.containment.rules.extend(_BASE._REGISTRY.containment.rules)
_REGISTRY.sensor_classes.update(_BASE._REGISTRY.sensor_classes)
from pathlib import Path as _Path
from rdflib import Graph as _Graph
if '__file__' in globals():
    _REGISTRY.schema_graph = _Graph().parse(_Path(__file__).with_name('_shapes.ttl'))
_REGISTRY.terms_by_iri.update({})

class ChlorinationStage(_BASE.ChlorinationUnit):
    'Chlorine dosing and a contact stage with the objective of disinfection.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/plumb/drinking-water#ChlorinationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Chlorination and contact stage',
        definition='Chlorine dosing and a contact stage with the objective of disinfection.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='outlet', label='outlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb1821d557d202af516a5e45ed030891a444ec946dd8b0c97ab9ce55507a9240f2b', required=(_BASE.Process_Chlorination,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cbd78b350f97cb1aaf88e57bcec3b96ba4b8ea8f095487f7dc8d140b6c0529aa97', required=(_BASE.TreatmentObjective_Disinfection,), defaults=(), choices=(), minimum=0, maximum=None),
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
        medium: _Iterable[_EnumValue] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'medium': medium,
            'has_property': has_property,
            'connected_through': connected_through,
            'connected': connected,
            'cnx': cnx,
            'connected_from': connected_from,
            'connected_to': connected_to,
            'has_optional_connection_point': has_optional_connection_point,
            'has_connection_point': has_connection_point,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'actuated_by_property': actuated_by_property,
            'has_physical_location': has_physical_location,
            'contains_': contains_,
            'executes': executes,
            'has_role': has_role,
        })

class ClarificationStage(_BASE.SedimentationTank):
    'Settles flocs and separates clarified water from a sludge withdrawal.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/plumb/drinking-water#ClarificationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Clarification stage',
        definition='Settles flocs and separates clarified water from a sludge withdrawal.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='clarified_water', label='clarified_water'), _CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='https://watermetadata.org/ontology/watr#Fluid-Sludge', min_count=1, max_count=1, name='sludge', label='sludge'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb732140c42afdc63278487f511a6dddb56cfd3545f49fcfcfd2ece73cf901d139', required=(_BASE.Process_Settling,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cb2fd2e9d081cb19bea52e4603593ca87ce9ee627a15eff8006d421e92e4b21b2', required=(_BASE.TreatmentObjective_Clarification,), defaults=(), choices=(), minimum=0, maximum=None),
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
        medium: _Iterable[_EnumValue] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'medium': medium,
            'has_property': has_property,
            'connected_through': connected_through,
            'connected': connected,
            'cnx': cnx,
            'connected_from': connected_from,
            'connected_to': connected_to,
            'has_optional_connection_point': has_optional_connection_point,
            'has_connection_point': has_connection_point,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'actuated_by_property': actuated_by_property,
            'has_physical_location': has_physical_location,
            'contains_': contains_,
            'executes': executes,
            'has_role': has_role,
        })

class CoagulationStage(_BASE.CoagulationBasin):
    'Coagulant addition and particle destabilization ahead of flocculation.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/plumb/drinking-water#CoagulationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Coagulation stage',
        definition='Coagulant addition and particle destabilization ahead of flocculation.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='outlet', label='outlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb16ad896b8a10c7c751aaf34da3ecc2e2e0e9d5e5534a298def8815b2371b4e589', required=(_BASE.Process_Coagulation,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cb7016eac5307e8cb34c5efa607ddc78211f15a751c76ef7f9af99f74c046e939b', required=(_BASE.TreatmentObjective_TurbidityRemoval,), defaults=(), choices=(), minimum=0, maximum=None),
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
        medium: _Iterable[_EnumValue] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'medium': medium,
            'has_property': has_property,
            'connected_through': connected_through,
            'connected': connected,
            'cnx': cnx,
            'connected_from': connected_from,
            'connected_to': connected_to,
            'has_optional_connection_point': has_optional_connection_point,
            'has_connection_point': has_connection_point,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'actuated_by_property': actuated_by_property,
            'has_physical_location': has_physical_location,
            'contains_': contains_,
            'executes': executes,
            'has_role': has_role,
        })

class FlocculationStage(_BASE.FlocculationBasin):
    'Gentle mixing to form flocs that can settle in the clarifier.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/plumb/drinking-water#FlocculationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Flocculation stage',
        definition='Gentle mixing to form flocs that can settle in the clarifier.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='outlet', label='outlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cba5be655409a1546d89a59a06a02c145147bff9b0fd3660d59bb56904ef32da14', required=(_BASE.Process_Flocculation,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cb9d0dbf1e57e4f612212d20ba3b78ad263f9147b03e514f4d54d6beffb5c6020d', required=(_BASE.TreatmentObjective_TurbidityRemoval,), defaults=(), choices=(), minimum=0, maximum=None),
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
        medium: _Iterable[_EnumValue] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'medium': medium,
            'has_property': has_property,
            'connected_through': connected_through,
            'connected': connected,
            'cnx': cnx,
            'connected_from': connected_from,
            'connected_to': connected_to,
            'has_optional_connection_point': has_optional_connection_point,
            'has_connection_point': has_connection_point,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'actuated_by_property': actuated_by_property,
            'has_physical_location': has_physical_location,
            'contains_': contains_,
            'executes': executes,
            'has_role': has_role,
        })

class RapidSandFiltrationStage(_BASE.RapidSandFilter):
    'Filters clarified water through sand; spent backwash leaves separately during cleaning.'
    _classinfo = _ClassInfo(
        iri='https://w3id.org/plumb/drinking-water#RapidSandFiltrationStage',
        ontology=ONTOLOGY,
        registry=_REGISTRY,
        label='Rapid sand filtration stage',
        definition='Filters clarified water through sand; spent backwash leaves separately during cleaning.',
        properties=(),
        cp_slots=(_CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='backwash_supply', label='backwash_supply'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='backwash_waste', label='backwash_waste'), _CPSlot(cp_class='OutletConnectionPoint', direction='out', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='filtered_water', label='filtered_water'), _CPSlot(cp_class='InletConnectionPoint', direction='in', medium='http://data.ashrae.org/standard223#Fluid-Water', min_count=1, max_count=1, name='inlet', label='inlet'),),
    )
    _shape_constraints = (
        _ShapeValues('has_process', 'cb136173b156ca2050c2a6b64e1f0a37ea9bfdc3db95636c7c07535fe7c588fb803', required=(_BASE.Process_RapidSandFiltration,), defaults=(), choices=(), minimum=0, maximum=None),
        _ShapeValues('has_treatment_objective', 'cbb21c7fd37a6009a96d33589f769c7815502b23c4426048ccd0e0c6a8519acdf7', required=(_BASE.TreatmentObjective_TurbidityRemoval,), defaults=(), choices=(), minimum=0, maximum=None),
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
        medium: _Iterable[_EnumValue] | None = None,
        label: str | None = None, comment: str | None = None, model: _Model | None = None) -> None:
        _Entity.__init__(self, name, label=label, comment=comment, model=model, **{
            'medium': medium,
            'has_property': has_property,
            'connected_through': connected_through,
            'connected': connected,
            'cnx': cnx,
            'connected_from': connected_from,
            'connected_to': connected_to,
            'has_optional_connection_point': has_optional_connection_point,
            'has_connection_point': has_connection_point,
            'has_process': has_process,
            'has_treatment_objective': has_treatment_objective,
            'actuated_by_property': actuated_by_property,
            'has_physical_location': has_physical_location,
            'contains_': contains_,
            'executes': executes,
            'has_role': has_role,
        })

__all__ = ['ONTOLOGY', 'REGISTRY', 'ChlorinationStage', 'ClarificationStage', 'CoagulationStage', 'FlocculationStage', 'RapidSandFiltrationStage']
