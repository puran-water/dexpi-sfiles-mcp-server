"""
Template deployment tools for MCP.

Provides high-level tools for template discovery and instantiation.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from mcp import Tool
from pydexpi.dexpi_classes.dexpiModel import DexpiModel

from ..templates import ParametricTemplate, TemplateLoadError
from ..utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class TemplateTools:
    """Handles template-related MCP tools."""

    def __init__(
        self,
        dexpi_models: Dict[str, DexpiModel],
        flowsheets: Dict[str, Any],
        template_library_path: Path = None
    ):
        """
        Initialize template tools.

        Args:
            dexpi_models: DEXPI model store
            flowsheets: SFILES flowsheet store
            template_library_path: Path to template library (default: library/patterns/)
        """
        self.dexpi_models = dexpi_models
        self.flowsheets = flowsheets

        # Template library path
        if template_library_path is None:
            # Default to library/patterns/ relative to project root
            project_root = Path(__file__).parent.parent.parent
            template_library_path = project_root / "library" / "patterns"

        self.template_library_path = template_library_path
        self._template_cache: Dict[str, ParametricTemplate] = {}

    def get_tools(self) -> List[Tool]:
        """Return all template tools."""
        return [
            Tool(
                name="template_list",
                description="List available templates from the library",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category (piping, storage, heat_transfer, etc.)",
                            "default": "all"
                        }
                    }
                }
            ),
            Tool(
                name="template_get_schema",
                description="Get parameter schema and metadata for a template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Name of the template (without .yaml extension)"
                        }
                    },
                    "required": ["template_name"]
                }
            ),
            Tool(
                name="area_deploy",
                description="Deploy a template into a model (STRATEGIC operation - replaces 50+ atomic calls)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Target model ID (DEXPI or SFILES)"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Model type"
                        },
                        "template_name": {
                            "type": "string",
                            "description": "Name of the template to deploy"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Template parameters (validated against template schema)"
                        },
                        "connection_point": {
                            "type": "string",
                            "description": "Optional connection point for template attachment"
                        }
                    },
                    "required": ["model_id", "model_type", "template_name", "parameters"]
                }
            ),
        ]

    async def handle_tool_call(self, tool_name: str, args: dict) -> dict:
        """
        Route tool calls to appropriate handler.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Response dict
        """
        handlers = {
            "template_list": self._template_list,
            "template_get_schema": self._template_get_schema,
            "area_deploy": self._area_deploy,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return error_response(f"Unknown tool: {tool_name}")

        try:
            return await handler(args)
        except Exception as e:
            logger.exception(f"Template tool error: {tool_name}")
            return error_response(str(e))

    # ========================================================================
    # Tool Handlers
    # ========================================================================

    async def _template_list(self, args: dict) -> dict:
        """
        List available templates from the library.

        Args:
            args: {"category": "piping" | "storage" | "heat_transfer" | "all"}

        Returns:
            Response with template list
        """
        category_filter = args.get("category", "all")

        try:
            # Find all .yaml files in template library
            if not self.template_library_path.exists():
                return error_response(
                    f"Template library not found: {self.template_library_path}"
                )

            yaml_files = list(self.template_library_path.glob("*.yaml"))

            templates = []
            for yaml_file in yaml_files:
                try:
                    # Load template to get metadata
                    template = ParametricTemplate.from_yaml(yaml_file)

                    # Filter by category if specified
                    if category_filter != "all" and template.category != category_filter:
                        continue

                    templates.append({
                        "name": template.name,
                        "version": template.version,
                        "category": template.category,
                        "description": template.description,
                        "file": yaml_file.name,
                        "parameters": len(template.parameters),
                        "components": len(template.components),
                    })

                except Exception as e:
                    logger.warning(f"Failed to load template {yaml_file.name}: {e}")
                    continue

            message = f"Found {len(templates)} templates" + \
                     (f" in category '{category_filter}'" if category_filter != "all" else "")

            return success_response(
                data={
                    "message": message,
                    "templates": templates,
                    "count": len(templates),
                    "library_path": str(self.template_library_path)
                }
            )

        except Exception as e:
            return error_response(f"Failed to list templates: {e}")

    async def _template_get_schema(self, args: dict) -> dict:
        """
        Get parameter schema and metadata for a template.

        Args:
            args: {"template_name": "pump_station_n_plus_1"}

        Returns:
            Response with template schema
        """
        template_name = args["template_name"]

        try:
            # Load template
            template = self._load_template(template_name)

            # Build schema response
            schema_data = {
                "name": template.name,
                "version": template.version,
                "category": template.category,
                "description": template.description,
                "parameters": template.parameters,
                "components": [
                    {
                        "name": comp.get("name"),
                        "type": comp.get("type"),
                        "count": comp.get("count", 1),
                    }
                    for comp in template.components
                ],
                "metadata": template.metadata,
            }

            schema_data["message"] = f"Schema for template '{template_name}'"
            return success_response(data=schema_data)

        except TemplateLoadError as e:
            return error_response(f"Template not found: {e}")
        except Exception as e:
            return error_response(f"Failed to get schema: {e}")

    async def _area_deploy(self, args: dict) -> dict:
        """
        Deploy a template into a model.

        This is a STRATEGIC operation that replaces 50+ atomic tool calls
        with a single parametric template instantiation.

        Args:
            args: {
                "model_id": "model_123",
                "model_type": "dexpi" | "sfiles",
                "template_name": "pump_station_n_plus_1",
                "parameters": {...},
                "connection_point": "optional"
            }

        Returns:
            Response with instantiation result
        """
        model_id = args["model_id"]
        model_type = args["model_type"]
        template_name = args["template_name"]
        parameters = args["parameters"]
        connection_point = args.get("connection_point")

        try:
            # Get target model
            if model_type == "dexpi":
                if model_id not in self.dexpi_models:
                    return error_response(f"DEXPI model not found: {model_id}")
                target_model = self.dexpi_models[model_id]
            elif model_type == "sfiles":
                if model_id not in self.flowsheets:
                    return error_response(f"SFILES flowsheet not found: {model_id}")
                target_model = self.flowsheets[model_id]
            else:
                return error_response(f"Invalid model_type: {model_type}")

            # Load template
            template = self._load_template(template_name)

            # Instantiate template
            result = template.instantiate(
                target_model=target_model,
                parameters=parameters,
                model_type=model_type,
                connection_point=connection_point
            )

            if result.success:
                return success_response(
                    data={
                        "message": f"Template '{template_name}' deployed successfully",
                        "template": template_name,
                        "model_id": model_id,
                        "model_type": model_type,
                        "components_added": result.instantiated_components,
                        "component_count": len(result.instantiated_components),
                        "validation_errors": result.validation_errors,
                        "metadata": result.metadata
                    }
                )
            else:
                return error_response(
                    message=f"Template deployment failed: {result.message}",
                    details={
                        "validation_errors": result.validation_errors
                    }
                )

        except TemplateLoadError as e:
            return error_response(f"Template not found: {e}")
        except Exception as e:
            logger.exception("Template deployment failed")
            return error_response(f"Deployment failed: {e}")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _load_template(self, template_name: str) -> ParametricTemplate:
        """
        Load a template by name (with caching).

        Args:
            template_name: Template name (without .yaml extension)

        Returns:
            ParametricTemplate instance

        Raises:
            TemplateLoadError: If template not found or invalid
        """
        # Check cache
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # Find template file
        template_file = self.template_library_path / f"{template_name}.yaml"

        if not template_file.exists():
            raise TemplateLoadError(
                f"Template '{template_name}' not found in {self.template_library_path}"
            )

        # Load template
        template = ParametricTemplate.from_yaml(template_file)

        # Cache it
        self._template_cache[template_name] = template

        return template
