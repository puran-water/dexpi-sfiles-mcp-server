"""Schema introspection tools for DEXPI and SFILES models."""

import logging
from typing import Any, Dict, List, Optional
import inspect

from mcp import Tool
from ..utils.response import success_response, error_response
from .dexpi_introspector import DexpiIntrospector
from ..core.components import get_registry, ComponentType

# Import SFILES2 module for schema introspection - REQUIRED
try:
    from ..adapters.sfiles_adapter import get_flowsheet_class_cached
    import sys
    # Get the module for introspection
    Flowsheet = get_flowsheet_class_cached()
    # Get module from sys.modules since it's already loaded via adapter
    # This is safe because get_flowsheet_class_cached() validated the import
    sfiles_module = sys.modules.get(Flowsheet.__module__)
    if sfiles_module is None:
        raise ImportError("SFILES2 module not properly loaded in sys.modules")
except ImportError as e:
    raise ImportError(
        "Failed to import SFILES2 module for schema introspection. "
        "SFILES2 is required for schema_tools to function. "
        "Ensure sfiles2 is installed with: pip install sfiles2 "
        f"Original error: {e}"
    ) from e

logger = logging.getLogger(__name__)


class SchemaTools:
    """Provides schema introspection for engineering models."""
    
    def __init__(self):
        """Initialize schema introspection tools."""
        # Use existing DexpiIntrospector instead of duplicating
        self.dexpi_introspector = DexpiIntrospector()
        self._sfiles_cache = {}
    
    def get_tools(self) -> List[Tool]:
        """Return schema introspection tools."""
        return [
            Tool(
                name="schema_list_classes",
                description="[DEPRECATED] List all available classes in DEXPI or SFILES schemas. Use schema_query(operation='list_classes') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schema_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "all"],
                            "description": "Which schema to introspect"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["equipment", "piping", "instrumentation", "all"],
                            "description": "Filter by category (DEXPI only)",
                            "default": "all"
                        }
                    },
                    "required": ["schema_type"]
                }
            ),
            Tool(
                name="schema_describe_class",
                description="[DEPRECATED] Get detailed information about a specific class including attributes, methods, and inheritance. Use schema_query(operation='describe_class') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "class_name": {
                            "type": "string",
                            "description": "Name of the class to describe"
                        },
                        "schema_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Which schema the class belongs to"
                        },
                        "include_inherited": {
                            "type": "boolean",
                            "description": "Include inherited attributes and methods",
                            "default": False
                        }
                    },
                    "required": ["class_name", "schema_type"]
                }
            ),
            Tool(
                name="schema_find_class",
                description="[DEPRECATED] Search for classes by partial name or pattern. Use schema_query(operation='find_class') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "Term to search for in class names"
                        },
                        "schema_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "all"],
                            "description": "Which schema to search",
                            "default": "all"
                        }
                    },
                    "required": ["search_term"]
                }
            ),
            Tool(
                name="schema_get_hierarchy",
                description="[DEPRECATED] Get the inheritance hierarchy for a class or category. Use schema_query(operation='get_hierarchy') instead.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "root_class": {
                            "type": "string",
                            "description": "Root class to start from (optional)"
                        },
                        "schema_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Which schema to analyze"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth to traverse",
                            "default": 5
                        }
                    },
                    "required": ["schema_type"]
                }
            ),
            Tool(
                name="schema_query",
                description="Unified schema introspection tool - consolidates all schema_* operations",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["list_classes", "describe_class", "find_class", "get_hierarchy"],
                            "description": "Operation to perform"
                        },
                        "schema_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "all"],
                            "description": "Which schema to query"
                        },
                        "class_name": {
                            "type": "string",
                            "description": "Class name (for describe_class operation)"
                        },
                        "search_term": {
                            "type": "string",
                            "description": "Search term (for find_class operation)"
                        },
                        "root_class": {
                            "type": "string",
                            "description": "Root class (for get_hierarchy operation)"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["equipment", "piping", "instrumentation", "all"],
                            "description": "Filter category (for list_classes with DEXPI)",
                            "default": "all"
                        },
                        "include_inherited": {
                            "type": "boolean",
                            "description": "Include inherited members (for describe_class)",
                            "default": False
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum hierarchy depth (for get_hierarchy)",
                            "default": 5
                        }
                    },
                    "required": ["operation"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        handlers = {
            "schema_list_classes": self._list_classes,
            "schema_describe_class": self._describe_class,
            "schema_find_class": self._find_class,
            "schema_get_hierarchy": self._get_hierarchy,
            "schema_query": self._unified_query
        }
        
        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown schema tool: {name}", code="UNKNOWN_TOOL")
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return error_response(str(e), code="TOOL_ERROR")
    
    async def _list_classes(self, args: dict) -> dict:
        """List available classes in schemas."""
        schema_type = args["schema_type"]
        category = args.get("category", "all")
        
        result = {}
        
        if schema_type in ["dexpi", "all"]:
            dexpi_classes_list = self._get_dexpi_classes(category)
            result["dexpi"] = {
                "count": len(dexpi_classes_list),
                "classes": dexpi_classes_list
            }
        
        if schema_type in ["sfiles", "all"]:
            sfiles_classes_list = self._get_sfiles_classes()
            result["sfiles"] = {
                "count": len(sfiles_classes_list),
                "classes": sfiles_classes_list
            }
        
        return success_response(result)
    
    async def _describe_class(self, args: dict) -> dict:
        """Describe a specific class in detail."""
        class_name = args["class_name"]
        schema_type = args["schema_type"]
        include_inherited = args.get("include_inherited", False)
        
        if schema_type == "dexpi":
            class_info = self._describe_dexpi_class(class_name, include_inherited)
        else:  # sfiles
            class_info = self._describe_sfiles_class(class_name, include_inherited)
        
        if not class_info:
            return error_response(f"Class {class_name} not found in {schema_type}", code="CLASS_NOT_FOUND")
        
        return success_response(class_info)
    
    async def _find_class(self, args: dict) -> dict:
        """Search for classes by pattern."""
        search_term = args["search_term"].lower()
        schema_type = args.get("schema_type", "all")
        
        matches = {}
        
        if schema_type in ["dexpi", "all"]:
            dexpi_matches = []
            for category in ["equipment", "piping", "instrumentation"]:
                classes = self._get_dexpi_classes(category)
                dexpi_matches.extend([c for c in classes if search_term in c.lower()])
            matches["dexpi"] = list(set(dexpi_matches))
        
        if schema_type in ["sfiles", "all"]:
            sfiles_classes = self._get_sfiles_classes()
            matches["sfiles"] = [c for c in sfiles_classes if search_term in c.lower()]
        
        return success_response({
            "search_term": args["search_term"],
            "matches": matches,
            "total_matches": sum(len(m) for m in matches.values())
        })
    
    async def _get_hierarchy(self, args: dict) -> dict:
        """Get class inheritance hierarchy."""
        schema_type = args["schema_type"]
        root_class = args.get("root_class")
        max_depth = args.get("max_depth", 5)
        
        if schema_type == "dexpi":
            hierarchy = self._get_dexpi_hierarchy(root_class, max_depth)
        else:  # sfiles
            hierarchy = self._get_sfiles_hierarchy(root_class, max_depth)
        
        return success_response({
            "schema_type": schema_type,
            "root_class": root_class or "All",
            "hierarchy": hierarchy
        })
    
    def _get_dexpi_classes(self, category: str) -> List[str]:
        """Get DEXPI classes by category using ComponentRegistry."""
        registry = get_registry()

        if category == "all":
            # Combine all categories
            classes = []
            for comp_type in [ComponentType.EQUIPMENT, ComponentType.PIPING, ComponentType.INSTRUMENTATION]:
                defs = registry.get_all_by_type(comp_type)
                classes.extend([d.dexpi_class.__name__ for d in defs])
            return sorted(list(set(classes)))
        elif category == "equipment":
            defs = registry.get_all_by_type(ComponentType.EQUIPMENT)
            return sorted([d.dexpi_class.__name__ for d in defs])
        elif category == "piping":
            defs = registry.get_all_by_type(ComponentType.PIPING)
            return sorted([d.dexpi_class.__name__ for d in defs])
        elif category == "instrumentation":
            defs = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
            return sorted([d.dexpi_class.__name__ for d in defs])
        else:
            return []
    
    def _get_sfiles_classes(self) -> List[str]:
        """Get SFILES classes."""
        if 'all' in self._sfiles_cache:
            return self._sfiles_cache['all']
        
        classes = [
            name for name, obj in inspect.getmembers(sfiles_module)
            if inspect.isclass(obj) and not name.startswith('_')
        ]
        
        self._sfiles_cache['all'] = sorted(classes)
        return self._sfiles_cache['all']
    
    def _describe_dexpi_class(self, class_name: str, include_inherited: bool) -> Optional[Dict]:
        """Describe a DEXPI class using existing introspector."""
        # First try to get detailed description from introspector
        for category in ['equipment', 'piping', 'instrumentation']:
            description = self.dexpi_introspector.describe_class(class_name, category)
            if description:
                # Get class attributes from introspector
                attrs = self.dexpi_introspector.get_class_attributes(class_name, category)
                if attrs:
                    return {
                        "name": class_name,
                        "category": category,
                        "description": description,
                        "composition_attributes": attrs.get("composition_attributes", []),
                        "reference_attributes": attrs.get("reference_attributes", []),
                        "data_attributes": attrs.get("data_attributes", []),
                        "all_attributes": attrs.get("all_attributes", {}),
                        "include_inherited": include_inherited
                    }
        return None
    
    def _describe_sfiles_class(self, class_name: str, include_inherited: bool) -> Optional[Dict]:
        """Describe a SFILES class."""
        if hasattr(sfiles_module, class_name):
            cls = getattr(sfiles_module, class_name)
            return self._extract_class_info(cls, include_inherited, "sfiles")
        return None
    
    def _extract_class_info(self, cls: type, include_inherited: bool, schema_type: str) -> Dict:
        """Extract detailed information about a class."""
        info = {
            "name": cls.__name__,
            "module": cls.__module__,
            "docstring": inspect.getdoc(cls),
            "bases": [base.__name__ for base in cls.__bases__],
            "attributes": {},
            "methods": {},
            "properties": {}
        }
        
        # Get all members
        for name, member in inspect.getmembers(cls):
            if name.startswith('_') and not name.startswith('__'):
                continue  # Skip private members
            
            # Check if inherited
            is_inherited = any(hasattr(base, name) for base in cls.__bases__)
            if is_inherited and not include_inherited:
                continue
            
            if inspect.ismethod(member) or inspect.isfunction(member):
                info["methods"][name] = {
                    "signature": str(inspect.signature(member)) if hasattr(member, '__call__') else "N/A",
                    "docstring": inspect.getdoc(member),
                    "inherited": is_inherited
                }
            elif isinstance(member, property):
                info["properties"][name] = {
                    "docstring": inspect.getdoc(member),
                    "inherited": is_inherited
                }
            elif not callable(member):
                info["attributes"][name] = {
                    "type": type(member).__name__,
                    "value": str(member)[:100] if not inspect.isclass(member) else member.__name__,
                    "inherited": is_inherited
                }
        
        # Add schema-specific info
        if schema_type == "dexpi":
            # Add DEXPI-specific metadata if available
            if hasattr(cls, '__annotations__'):
                info["type_hints"] = {
                    k: str(v) for k, v in cls.__annotations__.items()
                }
        
        return info
    
    def _get_dexpi_hierarchy(self, root_class: Optional[str], max_depth: int) -> Dict:
        """Get DEXPI class hierarchy using introspector data."""
        hierarchy = {}
        
        if root_class:
            # Get class info from introspector
            for category in ['equipment', 'piping', 'instrumentation']:
                attrs = self.dexpi_introspector.get_class_attributes(root_class, category)
                if attrs:
                    hierarchy[root_class] = {
                        "category": category,
                        "attributes": attrs,
                        "depth": max_depth
                    }
                    break
        else:
            # Build full hierarchy using ComponentRegistry for type enumeration
            registry = get_registry()
            category_map = {
                "equipment": ComponentType.EQUIPMENT,
                "piping": ComponentType.PIPING,
                "instrumentation": ComponentType.INSTRUMENTATION
            }
            for category, comp_type in category_map.items():
                hierarchy[category] = {}
                defs = registry.get_all_by_type(comp_type)
                for defn in defs:
                    class_name = defn.dexpi_class.__name__
                    # Use introspector for attribute introspection (unique functionality)
                    attrs = self.dexpi_introspector.get_class_attributes(class_name, category)
                    if attrs:
                        hierarchy[category][class_name] = {
                            "composition": len(attrs.get("composition_attributes", [])),
                            "reference": len(attrs.get("reference_attributes", [])),
                            "data": len(attrs.get("data_attributes", []))
                        }
        
        return hierarchy
    
    def _get_sfiles_hierarchy(self, root_class: Optional[str], max_depth: int) -> Dict:
        """Get SFILES class hierarchy."""
        hierarchy = {}
        
        if root_class and hasattr(sfiles_module, root_class):
            cls = getattr(sfiles_module, root_class)
            hierarchy[root_class] = self._build_hierarchy_tree(cls, max_depth)
        else:
            # Build full hierarchy
            for name, cls in inspect.getmembers(sfiles_module, inspect.isclass):
                if not name.startswith('_'):
                    hierarchy[name] = [b.__name__ for b in cls.__bases__]
        
        return hierarchy
    
    def _build_hierarchy_tree(self, cls: type, max_depth: int, current_depth: int = 0) -> Dict:
        """Build hierarchy tree for a class."""
        if current_depth >= max_depth:
            return {"bases": [b.__name__ for b in cls.__bases__]}
        
        tree = {
            "bases": [b.__name__ for b in cls.__bases__],
            "subclasses": {}
        }
        
        # Find subclasses
        for subclass in cls.__subclasses__():
            tree["subclasses"][subclass.__name__] = self._build_hierarchy_tree(
                subclass, max_depth, current_depth + 1
            )

        return tree

    async def _unified_query(self, args: dict) -> dict:
        """
        Unified schema query handler - dispatches to appropriate operation.

        Consolidates all schema_* tools into a single entry point.
        """
        operation = args.get("operation")

        if not operation:
            return error_response(
                "Missing required parameter: operation",
                code="MISSING_OPERATION"
            )

        # Dispatch to appropriate handler based on operation
        operation_map = {
            "list_classes": self._list_classes,
            "describe_class": self._describe_class,
            "find_class": self._find_class,
            "get_hierarchy": self._get_hierarchy
        }

        handler = operation_map.get(operation)
        if not handler:
            return error_response(
                f"Invalid operation: {operation}. Must be one of: {', '.join(operation_map.keys())}",
                code="INVALID_OPERATION"
            )

        # Call the appropriate handler with the full args dict
        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"Error in schema_query operation '{operation}': {e}", exc_info=True)
            return error_response(
                f"Operation '{operation}' failed: {str(e)}",
                code="OPERATION_ERROR"
            )