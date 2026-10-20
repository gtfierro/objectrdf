"""objectrdf runtime core.

Everything generated packages and user code need from the runtime:
the Entity base, the Model session, the property descriptors, and the
metadata types the compiler instantiates.
"""

from .containment import ContainmentRule, ContainmentTable
from .entity import ClassMetaView, Entity, InstanceMetaView, provided
from .enums import EnumValue
from .errors import (
    AmbiguousModelError,
    ContainmentError,
    ModelingError,
    ObjectRDFError,
    RangeError,
    ResolutionError,
    UnsatisfiableModelError,
    ValidationError,
)
from .meta import (
    CPConstraint,
    ClassInfo,
    CPSlot,
    OntologyInfo,
    PortContract,
    PortSlot,
    PropertySpec,
    Registry,
)
from .model import Model, current_model
from .property_schema import (
    PropertySchema,
    PropertySet,
    QuantityAmount,
    QuantityDefinition,
    quantity_field,
)
from .relations import (
    EnumOne,
    EnumSet,
    EnumValues,
    Lit,
    Rel,
    RelOne,
    RelSet,
    TermOne,
    ValueOne,
)
from .resolution import (
    ConnectionHandle,
    DeferredEndpoint,
    PortHandle,
    ResolutionExplanation,
    ResolutionIssue,
    ResolutionReport,
    ResolvedModel,
)
from .validation import Issue, ValidationReport
from .terms import TermValue

__all__ = [
    "AmbiguousModelError",
    "CPSlot",
    "DeferredEndpoint",
    "ClassInfo",
    "CPConstraint",
    "ClassMetaView",
    "ConnectionHandle",
    "PortHandle",
    "ResolutionExplanation",
    "ContainmentError",
    "ContainmentRule",
    "ContainmentTable",
    "Entity",
    "EnumOne",
    "EnumSet",
    "EnumValues",
    "EnumValue",
    "InstanceMetaView",
    "Issue",
    "Lit",
    "Model",
    "ModelingError",
    "ObjectRDFError",
    "OntologyInfo",
    "PortContract",
    "PortSlot",
    "PropertySpec",
    "PropertySchema",
    "PropertySet",
    "QuantityAmount",
    "QuantityDefinition",
    "quantity_field",
    "RangeError",
    "ResolutionError",
    "ResolutionIssue",
    "ResolutionReport",
    "ResolvedModel",
    "Registry",
    "Rel",
    "RelOne",
    "RelSet",
    "TermOne",
    "TermValue",
    "ValidationReport",
    "ValidationError",
    "ValueOne",
    "UnsatisfiableModelError",
    "current_model",
    "provided",
]
