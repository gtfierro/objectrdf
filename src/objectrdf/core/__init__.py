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
from .meta import CPConstraint, ClassInfo, CPSlot, OntologyInfo, PropertySpec, Registry
from .model import Model, current_model
from .relations import (
    EnumOne,
    EnumSet,
    Lit,
    Rel,
    RelOne,
    RelSet,
    TermOne,
    ValueOne,
)
from .resolution import (
    ConnectionHandle,
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
    "EnumValue",
    "InstanceMetaView",
    "Issue",
    "Lit",
    "Model",
    "ModelingError",
    "ObjectRDFError",
    "OntologyInfo",
    "PropertySpec",
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
