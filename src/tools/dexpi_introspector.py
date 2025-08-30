"""Dynamic introspection and schema generation for pyDEXPI classes."""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

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
        """Get equipment types that support nozzles."""
        nozzle_equipment = []
        for name, cls in self._equipment_classes.items():
            try:
                instance = cls()
                comp_attrs = bmt.get_composition_attributes(instance)
                if "nozzles" in comp_attrs:
                    nozzle_equipment.append(name)
            except:
                pass
        return sorted(nozzle_equipment)
    
    def get_valves(self) -> List[str]:
        """Get all valve types from piping components."""
        valves = []
        for name in self._piping_classes.keys():
            if "Valve" in name:
                valves.append(name)
        return sorted(valves)
    
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