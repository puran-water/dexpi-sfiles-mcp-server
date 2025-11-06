"""
Parameter substitution engine for template system.

Handles ${variable} substitution in template strings with support for:
- Simple variables: ${param_name}
- Formatted output: ${sequence:03d}
- Expressions: ${param1 + param2}
- Conditionals: ${control_type} == "flow"
"""

import logging
import re
from typing import Any, Dict, Optional
from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.toolkits import model_toolkit as mt

logger = logging.getLogger(__name__)


class ParameterSubstitutionEngine:
    """Handles parameter substitution in templates."""

    def __init__(self):
        """Initialize substitution engine."""
        self.parameters: Dict[str, Any] = {}
        self._sequence_counters: Dict[str, int] = {}

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set parameter values for substitution.

        Args:
            params: Parameter dictionary
        """
        self.parameters = params.copy()
        self._sequence_counters = {}

    def substitute(self, template: str, context: Optional[Dict] = None) -> str:
        """
        Substitute parameters in template string.

        Supports:
        - Simple: ${param_name}
        - Formatted: ${param_name:format_spec}
        - Expressions: ${param1 + param2}
        - Conditionals: ${param1} == "value"

        Args:
            template: Template string with ${...} placeholders
            context: Additional context variables (ephemeral, not stored)

        Returns:
            Substituted string

        Raises:
            KeyError: If required variable not found
            ValueError: If expression evaluation fails
        """
        if not isinstance(template, str):
            return template

        # Merge parameters and context
        all_params = {**self.parameters, **(context or {})}

        # Find all ${...} patterns
        pattern = re.compile(r'\$\{([^}]+)\}')

        def replacer(match):
            expr = match.group(1)

            try:
                # Check for format spec (e.g., "sequence:03d")
                if ':' in expr and not any(op in expr for op in ['==', '!=', '>=', '<=']):
                    var_name, format_spec = expr.split(':', 1)
                    var_name = var_name.strip()
                    value = self._resolve_variable(var_name, all_params)
                    return format(value, format_spec)

                # Check for arithmetic/boolean expressions
                elif any(op in expr for op in ['+', '-', '*', '/', '==', '!=', '>=', '<=', '<', '>', 'and', 'or']):
                    result = self._evaluate_expression(expr, all_params)
                    return str(result)

                # Simple variable substitution
                else:
                    value = self._resolve_variable(expr.strip(), all_params)
                    return str(value)

            except Exception as e:
                logger.warning(f"Failed to substitute '{expr}': {e}")
                # Return original placeholder on error
                return match.group(0)

        return pattern.sub(replacer, template)

    def substitute_dict(self, template_dict: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Recursively substitute parameters in a dictionary.

        Args:
            template_dict: Dictionary with template values
            context: Additional context variables

        Returns:
            Dictionary with substituted values
        """
        result = {}

        for key, value in template_dict.items():
            if isinstance(value, str):
                result[key] = self.substitute(value, context)
            elif isinstance(value, dict):
                result[key] = self.substitute_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self.substitute(item, context) if isinstance(item, str)
                    else self.substitute_dict(item, context) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def substitute_model(self, model: DexpiModel, params: Dict[str, Any]) -> DexpiModel:
        """
        Apply parameter substitution to DexpiModel attributes.

        Walks the model tree and substitutes string attributes.

        Args:
            model: DexpiModel to modify
            params: Parameters for substitution

        Returns:
            Modified model (in-place)
        """
        self.set_parameters(params)

        # Walk all objects in model
        all_objects = mt.get_all_instances_in_model(model, None)

        for obj in all_objects:
            # Substitute string attributes
            for attr_name in dir(obj):
                # Skip private/protected attributes
                if attr_name.startswith('_'):
                    continue

                try:
                    attr_value = getattr(obj, attr_name, None)

                    # Only substitute string attributes
                    if isinstance(attr_value, str) and '${' in attr_value:
                        substituted_value = self.substitute(attr_value)
                        setattr(obj, attr_name, substituted_value)

                except (AttributeError, TypeError):
                    # Skip attributes that can't be set
                    continue

        return model

    def _resolve_variable(self, var_name: str, params: Dict) -> Any:
        """
        Resolve variable name to value.

        Supports:
        - Simple: param_name
        - Sequence: sequence (auto-increments)
        - Array index: pump[0] (not implemented yet)

        Args:
            var_name: Variable name
            params: Parameter dictionary

        Returns:
            Resolved value

        Raises:
            KeyError: If variable not found
        """
        # Handle sequence counters
        if var_name == 'sequence':
            # Default sequence counter
            counter_key = '__default__'
            if counter_key not in self._sequence_counters:
                self._sequence_counters[counter_key] = 0
            self._sequence_counters[counter_key] += 1
            return self._sequence_counters[counter_key]

        # Simple parameter lookup
        if var_name in params:
            return params[var_name]

        raise KeyError(f"Variable '{var_name}' not found in parameters")

    def _evaluate_expression(self, expr: str, params: Dict) -> Any:
        """
        Evaluate arithmetic or boolean expression.

        Uses safe evaluation with restricted namespace.

        Args:
            expr: Expression string
            params: Parameter dictionary

        Returns:
            Expression result

        Raises:
            ValueError: If expression invalid or unsafe
        """
        # Create safe evaluation namespace
        safe_dict = {
            '__builtins__': {},
            **params
        }

        # Replace ${var} with actual values in expression
        substituted_expr = self.substitute(expr, params) if '${' in expr else expr

        # Evaluate safely
        try:
            result = eval(substituted_expr, safe_dict)
            return result
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression '{expr}': {e}")

    def reset_sequence_counters(self) -> None:
        """Reset all sequence counters to zero."""
        self._sequence_counters = {}

    def get_sequence_counter(self, key: str = '__default__') -> int:
        """
        Get current value of sequence counter.

        Args:
            key: Counter key (default: '__default__')

        Returns:
            Current counter value
        """
        return self._sequence_counters.get(key, 0)
