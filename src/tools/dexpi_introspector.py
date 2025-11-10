"""Dynamic introspection and schema generation for pyDEXPI classes."""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type, Union, get_origin, get_args
from datetime import datetime
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from pydexpi.toolkits import base_model_utils as bmt
import pydexpi.dexpi_classes.equipment as equipment_module
import pydexpi.dexpi_classes.piping as piping_module
import pydexpi.dexpi_classes.instrumentation as inst_module

logger = logging.getLogger(__name__)


class DexpiIntrospector:
    """Introspects pyDEXPI classes to dynamically generate tool schemas."""
    
    def __init__(self):
        """Initialize the introspector."""
        self._equipment_classes = {}
        self._piping_classes = {}
        self._instrumentation_classes = {}
        self._discover_all_classes()
    
    def _discover_all_classes(self):
        """Discover all available pyDEXPI classes."""
        # Discover equipment classes
        for name in dir(equipment_module):
            obj = getattr(equipment_module, name)
            if inspect.isclass(obj) and hasattr(obj, 'model_fields'):
                if not name.startswith('_'):
                    self._equipment_classes[name] = obj
        
        # Discover piping classes
        for name in dir(piping_module):
            obj = getattr(piping_module, name)
            if inspect.isclass(obj) and hasattr(obj, 'model_fields'):
                if not name.startswith('_'):
                    self._piping_classes[name] = obj
        
        # Discover instrumentation classes
        for name in dir(inst_module):
            obj = getattr(inst_module, name)
            if inspect.isclass(obj) and hasattr(obj, 'model_fields'):
                if not name.startswith('_'):
                    self._instrumentation_classes[name] = obj
        
        logger.info(f"Discovered {len(self._equipment_classes)} equipment types")
        logger.info(f"Discovered {len(self._piping_classes)} piping components")
        logger.info(f"Discovered {len(self._instrumentation_classes)} instrumentation types")
    
    def get_class_attributes(self, class_name: str, category: str = "equipment") -> Dict[str, Any]:
        """Get all attributes for a specific class."""
        # Get the class from the appropriate module
        if category == "equipment":
            cls = self._equipment_classes.get(class_name)
        elif category == "piping":
            cls = self._piping_classes.get(class_name)
        elif category == "instrumentation":
            cls = self._instrumentation_classes.get(class_name)
        else:
            return None
        
        if not cls:
            return None
        
        try:
            # Create an instance to introspect
            instance = cls()
            
            # Get attributes by category
            comp_attrs = bmt.get_composition_attributes(instance)
            ref_attrs = bmt.get_reference_attributes(instance)
            data_attrs = bmt.get_data_attributes(instance)
            
            return {
                "class_name": class_name,
                "category": category,
                "composition_attributes": list(comp_attrs.keys()),
                "reference_attributes": list(ref_attrs.keys()),
                "data_attributes": list(data_attrs.keys()),
                "all_attributes": {
                    **{k: "composition" for k in comp_attrs.keys()},
                    **{k: "reference" for k in ref_attrs.keys()},
                    **{k: "data" for k in data_attrs.keys()}
                }
            }
        except Exception as e:
            logger.error(f"Failed to introspect {class_name}: {e}")
            return None
    
    def generate_tool_schema(self, class_name: str, category: str = "equipment") -> Dict[str, Any]:
        """Generate a tool schema for a specific pyDEXPI class."""
        attrs = self.get_class_attributes(class_name, category)
        if not attrs:
            return None
        
        # Build the properties schema
        properties = {
            "model_id": {"type": "string", "description": "Model ID"},
            "tag_name": {"type": "string", "description": "Tag name for the element"}
        }
        
        # Add nozzle configuration for equipment
        if category == "equipment" and "nozzles" in attrs["composition_attributes"]:
            properties["nozzles"] = {
                "type": "array",
                "description": "Nozzle configurations",
                "items": {
                    "type": "object",
                    "properties": {
                        "subTagName": {"type": "string"},
                        "nominalPressure": {"type": "string"},
                        "nominalDiameter": {"type": "string"},
                        "connectionType": {"type": "string"}
                    }
                },
                "default": [
                    {"subTagName": "N1", "nominalPressure": "PN16", "nominalDiameter": "DN50"},
                    {"subTagName": "N2", "nominalPressure": "PN16", "nominalDiameter": "DN50"}
                ]
            }
        
        # Add data attributes as optional properties
        for attr in attrs["data_attributes"]:
            if attr not in ["tagName", "id", "uri"]:  # Skip built-in fields
                properties[attr] = {
                    "type": "object",
                    "description": f"Optional: {attr}",
                    "required": False
                }
        
        # Add custom attributes support
        properties["customAttributes"] = {
            "type": "array",
            "description": "Custom attributes for extensibility",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": "string"}
                }
            }
        }
        
        return {
            "type": "object",
            "properties": properties,
            "required": ["model_id", "tag_name"]
        }
    
    def get_available_types(self) -> Dict[str, List[str]]:
        """Get all available types organized by category."""
        return {
            "equipment": sorted(list(self._equipment_classes.keys())),
            "piping": sorted(list(self._piping_classes.keys())),
            "instrumentation": sorted(list(self._instrumentation_classes.keys()))
        }
    
    def get_equipment_with_nozzles(self) -> List[str]:
        """Get equipment types that support nozzles.

        Raises:
            RuntimeError: If any equipment class fails to instantiate or introspect
        """
        from pydantic import ValidationError

        nozzle_equipment = []

        for name, cls in self._equipment_classes.items():
            try:
                instance = cls()
            except ValidationError as e:
                raise RuntimeError(
                    f"Equipment class '{name}' requires constructor arguments and cannot be introspected for nozzle support. "
                    f"The introspector needs to be updated to inspect class schemas directly rather than requiring instantiation. "
                    f"Validation error: {e}"
                ) from e
            except (AttributeError, TypeError) as e:
                raise RuntimeError(
                    f"Failed to instantiate equipment class '{name}' for nozzle introspection. "
                    f"This indicates a problem with the class definition. "
                    f"Error: {e}"
                ) from e

            try:
                comp_attrs = bmt.get_composition_attributes(instance)
                if "nozzles" in comp_attrs:
                    nozzle_equipment.append(name)
            except (AttributeError, KeyError) as e:
                raise RuntimeError(
                    f"Failed to get composition attributes from equipment class '{name}'. "
                    f"This indicates a problem with base_model_utils or the class structure. "
                    f"Error: {e}"
                ) from e

        return sorted(nozzle_equipment)
    
    def get_valves(self) -> List[str]:
        """Get all valve types from piping components."""
        valves = []
        for name in self._piping_classes.keys():
            if "Valve" in name:
                valves.append(name)
        return sorted(valves)
    
    def _get_class(self, class_name: str, category: str) -> Optional[Type]:
        """Get a class by name and category."""
        if category == "equipment":
            return self._equipment_classes.get(class_name)
        elif category == "piping":
            return self._piping_classes.get(class_name)
        elif category == "instrumentation":
            return self._instrumentation_classes.get(class_name)
        return None
    
    def map_python_type_to_json(self, python_type: Any) -> str:
        """Convert Python type annotation to JSON schema type."""
        import types
        
        # Handle Union types (Optional fields) - both typing.Union and types.UnionType (Python 3.10+)
        origin = get_origin(python_type)
        if origin is Union or (hasattr(types, 'UnionType') and isinstance(python_type, types.UnionType)):
            args = get_args(python_type)
            # Filter out NoneType
            non_none_types = [arg for arg in args if arg is not type(None)]
            if non_none_types:
                return self.map_python_type_to_json(non_none_types[0])
        
        # Handle list types
        if origin is list:
            return "array"
        
        # Map basic Python types to JSON schema types
        if python_type is str:
            return "string"
        elif python_type is int:
            return "integer"
        elif python_type is float:
            return "number"
        elif python_type is bool:
            return "boolean"
        elif python_type is datetime:
            return "string"  # datetime as ISO string
        elif hasattr(python_type, '__bases__'):
            # Check if it's a Pydantic model
            if BaseModel in python_type.__bases__:
                return "object"
            # Try to check the type name for common types
            elif hasattr(python_type, '__name__'):
                type_name = python_type.__name__
                if 'String' in type_name or type_name == 'str':
                    return "string"
                elif 'Integer' in type_name or type_name == 'int':
                    return "integer"
                elif 'Float' in type_name or 'Quantity' in type_name or type_name == 'float':
                    return "number"
                elif 'Bool' in type_name or type_name == 'bool':
                    return "boolean"
        
        # Default to object for complex types
        return "object"
    
    def get_field_schema(self, field_info: FieldInfo, field_name: str) -> Dict[str, Any]:
        """Convert Pydantic FieldInfo to JSON schema for a field."""
        schema = {
            "type": self.map_python_type_to_json(field_info.annotation),
            "description": field_info.description or f"{field_name} attribute"
        }
        
        # Handle list types
        origin = get_origin(field_info.annotation)
        if origin is list:
            args = get_args(field_info.annotation)
            if args:
                item_type = self.map_python_type_to_json(args[0])
                schema["items"] = {"type": item_type}
        
        # Add default if present
        if field_info.default is not None and field_info.default != ... and field_info.default != PydanticUndefined:
            # Don't include callable defaults (like list factories)
            if not callable(field_info.default):
                schema["default"] = field_info.default
        
        # Add attribute category if present
        if field_info.json_schema_extra:
            category = field_info.json_schema_extra.get("attribute_category")
            if category:
                schema["x-attribute-category"] = category
        
        return schema
    
    def generate_class_schema(self, class_name: str, category: str = "equipment") -> Optional[Dict[str, Any]]:
        """Generate full JSON schema for a pyDEXPI class."""
        cls = self._get_class(class_name, category)
        if not cls:
            return None
        
        properties = {}
        required = []
        
        # Always include model_id and tag_name for MCP tools
        properties["model_id"] = {"type": "string", "description": "Model ID"}
        properties["tag_name"] = {"type": "string", "description": "Tag name for the element"}
        required.extend(["model_id", "tag_name"])
        
        # Process all fields from the class
        for field_name, field_info in cls.model_fields.items():
            # Skip internal fields and already added fields
            if field_name.startswith('_') or field_name in ['id', 'uri', 'tagName']:
                continue
            
            # Generate field schema
            field_schema = self.get_field_schema(field_info, field_name)
            properties[field_name] = field_schema
            
            # Check if required
            if field_info.is_required:
                required.append(field_name)
        
        # Special handling for equipment with nozzles
        if category == "equipment":
            from pydantic import ValidationError

            try:
                instance = cls()
            except ValidationError as e:
                raise RuntimeError(
                    f"Cannot generate schema for equipment class '{class_name}' - requires constructor arguments. "
                    f"Schema generation needs to be updated to inspect class fields directly. "
                    f"Validation error: {e}"
                ) from e
            except (AttributeError, TypeError) as e:
                raise RuntimeError(
                    f"Failed to instantiate equipment class '{class_name}' for schema generation. "
                    f"Error: {e}"
                ) from e

            try:
                comp_attrs = bmt.get_composition_attributes(instance)
            except (AttributeError, KeyError) as e:
                raise RuntimeError(
                    f"Failed to get composition attributes for '{class_name}'. "
                    f"Error: {e}"
                ) from e

            if "nozzles" in comp_attrs:
                properties["nozzles"] = {
                    "type": "array",
                    "description": "Nozzle configurations",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subTagName": {"type": "string"},
                            "nominalPressure": {"type": "string"},
                            "nominalDiameter": {"type": "string"}
                        }
                    },
                    "x-attribute-category": "composition"
                }
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "x-class-name": class_name,
            "x-category": category
        }
    
    def get_required_fields(self, class_name: str, category: str = "equipment") -> List[str]:
        """Get list of required fields for a class."""
        cls = self._get_class(class_name, category)
        if not cls:
            return []
        
        required = []
        for field_name, field_info in cls.model_fields.items():
            if field_info.is_required:
                required.append(field_name)
        
        return required
    
    def generate_dynamic_enum(self, category: str, filter_func: Optional[callable] = None) -> List[str]:
        """Generate dynamic enum of class names for a category."""
        if category == "equipment":
            classes = list(self._equipment_classes.keys())
        elif category == "piping":
            classes = list(self._piping_classes.keys())
        elif category == "instrumentation":
            classes = list(self._instrumentation_classes.keys())
        elif category == "valves":
            # Special case for valves
            classes = self.get_valves()
        else:
            classes = []
        
        # Apply filter if provided
        if filter_func:
            classes = [c for c in classes if filter_func(c)]
        
        return sorted(classes)
    
    def describe_class(self, class_name: str, category: str = None) -> Dict[str, Any]:
        """Get comprehensive description of a class including schema and attributes."""
        # Try to find the class in any category if not specified
        if not category:
            for cat in ["equipment", "piping", "instrumentation"]:
                if self._get_class(class_name, cat):
                    category = cat
                    break
        
        if not category:
            return {"error": f"Class {class_name} not found"}
        
        # Get basic attributes
        attrs = self.get_class_attributes(class_name, category)
        if not attrs:
            return {"error": f"Could not get attributes for {class_name}"}
        
        # Get schema
        schema = self.generate_class_schema(class_name, category)
        
        # Get required fields
        required = self.get_required_fields(class_name, category)
        
        return {
            "class_name": class_name,
            "category": category,
            "composition_attributes": attrs.get("composition_attributes", []),
            "reference_attributes": attrs.get("reference_attributes", []),
            "data_attributes": attrs.get("data_attributes", []),
            "required_fields": required,
            "schema": schema
        }
    
    def validate_equipment_completeness(self, equipment_type: str, provided_attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that provided attributes match the pyDEXPI class definition."""
        class_attrs = self.get_class_attributes(equipment_type, "equipment")
        if not class_attrs:
            return {"valid": False, "error": f"Unknown equipment type: {equipment_type}"}
        
        all_attrs = class_attrs["all_attributes"]
        provided_keys = set(provided_attrs.keys())
        class_keys = set(all_attrs.keys())
        
        # Check for missing important attributes
        missing = class_keys - provided_keys
        extra = provided_keys - class_keys
        
        # Nozzles are critical for equipment
        if "nozzles" in class_attrs["composition_attributes"] and "nozzles" not in provided_attrs:
            return {
                "valid": False,
                "error": "Equipment must have nozzles for proper connectivity",
                "missing_critical": ["nozzles"]
            }
        
        return {
            "valid": True,
            "coverage": len(provided_keys & class_keys) / len(class_keys) if class_keys else 1.0,
            "missing_attributes": list(missing),
            "extra_attributes": list(extra)
        }