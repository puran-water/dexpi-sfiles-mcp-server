"""
Template system for parametric model construction.

Provides thin wrapper over pyDEXPI's DexpiPattern with parameter substitution.
"""

from .substitution_engine import ParameterSubstitutionEngine
from .parametric_template import (
    ParametricTemplate,
    ValidationResult,
    TemplateInstantiationResult,
    TemplateError,
    ParameterValidationError,
    TemplateInstantiationError,
    TemplateLoadError,
)

__all__ = [
    'ParameterSubstitutionEngine',
    'ParametricTemplate',
    'ValidationResult',
    'TemplateInstantiationResult',
    'TemplateError',
    'ParameterValidationError',
    'TemplateInstantiationError',
    'TemplateLoadError',
]
