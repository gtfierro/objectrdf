"""Exception types raised by the objectrdf runtime.

All errors aim to speak in Python terms (class names, attribute names) and,
where the fix is mechanical, include the exact code the user should write.
"""

from __future__ import annotations


class ObjectRDFError(Exception):
    """Base class for all objectrdf errors."""


class ModelingError(ObjectRDFError):
    """A model-construction mistake: no active model, duplicate names,
    missing required attributes, and similar."""


class RangeError(ModelingError, TypeError):
    """A value was linked through a property whose range does not allow it.

    Subclasses ``TypeError`` because this is morally a type error the static
    checker would also have caught.
    """


class ContainmentError(ModelingError):
    """No (or no unambiguous) containment rule relates a container/child
    class pair. The message lists what was tried and how to disambiguate."""


class ResolutionError(ModelingError):
    """A deferred model could not be resolved into one concrete graph."""


class UnsatisfiableModelError(ResolutionError):
    """The authored constraints have no solution."""

    def __init__(self, message: str, *, core: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.core = core


class AmbiguousModelError(ResolutionError):
    """Several semantically distinct concrete graphs remain possible."""

    def __init__(self, message: str, *, alternatives: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.alternatives = alternatives


class ValidationError(ModelingError):
    """A resolved graph does not conform to its compiled SHACL shapes."""

    def __init__(self, message: str, *, report: object | None = None) -> None:
        super().__init__(message)
        self.report = report
