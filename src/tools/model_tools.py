"""Unified model lifecycle tools - Phase 4 consolidation.

Provides unified entry points for model creation, import, and export
that work across both DEXPI and SFILES model types.

These tools operate on in-memory models (not git-backed projects).
Use project_* tools for git-versioned persistence.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Tool
from ..utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class ModelTools:
    """Unified model lifecycle operations (create/load/save)."""

    def __init__(
        self,
        dexpi_store: Dict[str, Any],
        sfiles_store: Dict[str, Any],
        dexpi_tools: Any,
        sfiles_tools: Any
    ):
        """Initialize with model stores and existing tool handlers.

        Args:
            dexpi_store: Dictionary storing DEXPI models
            sfiles_store: Dictionary storing SFILES flowsheets
            dexpi_tools: DexpiTools instance for reusing logic
            sfiles_tools: SfilesTools instance for reusing logic
        """
        self.dexpi_models = dexpi_store
        self.flowsheets = sfiles_store
        self.dexpi_tools = dexpi_tools
        self.sfiles_tools = sfiles_tools

    def get_tools(self) -> List[Tool]:
        """Return unified model lifecycle tools."""
        return [
            Tool(
                name="model_combine",
                description="Merge multiple DEXPI models into one combined model. Combines all tagged plant items, instrumentation, and piping from source models.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_model_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of DEXPI model IDs to combine (minimum 2)",
                            "minItems": 2
                        },
                        "target_model_id": {
                            "type": "string",
                            "description": "ID for the combined model (auto-generated if not provided)"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata for the combined model",
                            "properties": {
                                "project_name": {"type": "string"},
                                "drawing_number": {"type": "string"},
                                "revision": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        }
                    },
                    "required": ["source_model_ids"]
                }
            ),
            Tool(
                name="model_create",
                description="Create a new model (DEXPI P&ID or SFILES flowsheet) - Replaces dexpi_create_pid and sfiles_create_flowsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Type of model to create"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Model-specific metadata",
                            "properties": {
                                # DEXPI metadata
                                "project_name": {"type": "string"},
                                "drawing_number": {"type": "string"},
                                "revision": {"type": "string", "default": "A"},
                                "description": {"type": "string", "default": ""},
                                # SFILES metadata
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["BFD", "PFD"], "default": "PFD"}
                            }
                        }
                    },
                    "required": ["model_type", "metadata"]
                }
            ),
            Tool(
                name="model_load",
                description="Import a model from various formats (JSON, Proteus XML, SFILES string) - Replaces dexpi_import_json, dexpi_import_proteus_xml, sfiles_from_string",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Type of model being imported"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "proteus_xml", "sfiles_string"],
                            "description": "Import format"
                        },
                        "content": {
                            "type": "string",
                            "description": "Serialized model content (JSON string, XML, or SFILES notation)"
                        },
                        "directory_path": {
                            "type": "string",
                            "description": "Directory path (for proteus_xml format only)"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Filename (for proteus_xml format only)"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Optional ID for imported model (auto-generated if not provided)"
                        }
                    },
                    "required": ["model_type", "format"]
                }
            ),
            Tool(
                name="model_save",
                description="Export a model to various formats (JSON, GraphML, SFILES string) - Replaces dexpi_export_json, dexpi_export_graphml, sfiles_to_string",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to export"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "graphml", "sfiles_string"],
                            "description": "Export format"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles"],
                            "description": "Model type (optional - auto-detected if not provided, required if model exists in both stores)"
                        },
                        "options": {
                            "type": "object",
                            "description": "Format-specific export options",
                            "properties": {
                                # GraphML options (DEXPI only)
                                "include_msr": {"type": "boolean", "default": True, "description": "Include measurement/control/regulation units in GraphML (DEXPI only)"},
                                # SFILES options
                                "canonical": {"type": "boolean", "default": True, "description": "Generate canonical SFILES format (SFILES only)"},
                                "version": {"type": "string", "enum": ["v1", "v2"], "default": "v2", "description": "SFILES version (SFILES only)"}
                            }
                        }
                    },
                    "required": ["model_id", "format"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Standardized response
        """
        handlers = {
            "model_create": self._create_model,
            "model_load": self._load_model,
            "model_save": self._save_model,
            "model_combine": self._combine_models
        }

        handler = handlers.get(name)
        if not handler:
            return error_response(
                f"Unknown model tool: {name}",
                "UNKNOWN_TOOL"
            )

        try:
            return await handler(arguments)
        except Exception as e:
            logger.exception(f"Error in {name}")
            return error_response(
                str(e),
                "TOOL_EXECUTION_ERROR",
                details={"tool": name, "arguments": arguments}
            )

    async def _create_model(self, args: dict) -> dict:
        """Create a new model (unified DEXPI/SFILES).

        Args:
            args: {
                "model_type": "dexpi" | "sfiles",
                "metadata": {
                    # DEXPI: project_name, drawing_number, revision, description
                    # SFILES: name, type, description
                }
            }

        Returns:
            Success response with model_id and metadata
        """
        model_type = args["model_type"]
        metadata = args["metadata"]

        if model_type == "dexpi":
            # Validate DEXPI metadata
            if "project_name" not in metadata or "drawing_number" not in metadata:
                return error_response(
                    "DEXPI models require 'project_name' and 'drawing_number' in metadata",
                    "INVALID_METADATA"
                )

            # Delegate to existing DexpiTools logic
            dexpi_args = {
                "project_name": metadata["project_name"],
                "drawing_number": metadata["drawing_number"],
                "revision": metadata.get("revision", "A"),
                "description": metadata.get("description", "")
            }
            return await self.dexpi_tools._create_pid(dexpi_args)

        elif model_type == "sfiles":
            # Validate SFILES metadata
            if "name" not in metadata:
                return error_response(
                    "SFILES models require 'name' in metadata",
                    "INVALID_METADATA"
                )

            # Delegate to existing SfilesTools logic
            sfiles_args = {
                "name": metadata["name"],
                "type": metadata.get("type", "PFD"),
                "description": metadata.get("description", "")
            }
            return await self.sfiles_tools._create_flowsheet(sfiles_args)

        else:
            return error_response(
                f"Unknown model_type: {model_type}",
                "INVALID_MODEL_TYPE"
            )

    async def _load_model(self, args: dict) -> dict:
        """Import a model from various formats.

        Args:
            args: {
                "model_type": "dexpi" | "sfiles",
                "format": "json" | "proteus_xml" | "sfiles_string",
                "content": str (for json/sfiles_string),
                "directory_path": str (for proteus_xml),
                "filename": str (for proteus_xml),
                "model_id": str (optional)
            }

        Returns:
            Success response with model_id and imported data
        """
        model_type = args["model_type"]
        format_type = args["format"]

        if model_type == "dexpi":
            if format_type == "json":
                if "content" not in args:
                    return error_response(
                        "JSON import requires 'content' parameter",
                        "MISSING_CONTENT"
                    )

                import_args = {
                    "json_content": args["content"],
                    "model_id": args.get("model_id")
                }
                return await self.dexpi_tools._import_json(import_args)

            elif format_type == "proteus_xml":
                if "directory_path" not in args or "filename" not in args:
                    return error_response(
                        "Proteus XML import requires 'directory_path' and 'filename' parameters",
                        "MISSING_PARAMETERS"
                    )

                import_args = {
                    "directory_path": args["directory_path"],
                    "filename": args["filename"],
                    "model_id": args.get("model_id")
                }
                return await self.dexpi_tools._import_proteus_xml(import_args)

            else:
                return error_response(
                    f"Invalid format '{format_type}' for DEXPI models. Use 'json' or 'proteus_xml'",
                    "INVALID_FORMAT"
                )

        elif model_type == "sfiles":
            if format_type == "sfiles_string":
                if "content" not in args:
                    return error_response(
                        "SFILES string import requires 'content' parameter",
                        "MISSING_CONTENT"
                    )

                import_args = {
                    "sfiles_string": args["content"],
                    "flowsheet_id": args.get("model_id")
                }
                return await self.sfiles_tools._from_string(import_args)

            else:
                return error_response(
                    f"Invalid format '{format_type}' for SFILES models. Use 'sfiles_string'",
                    "INVALID_FORMAT"
                )

        else:
            return error_response(
                f"Unknown model_type: {model_type}",
                "INVALID_MODEL_TYPE"
            )

    async def _save_model(self, args: dict) -> dict:
        """Export a model to various formats.

        Args:
            args: {
                "model_id": str,
                "format": "json" | "graphml" | "sfiles_string",
                "model_type": "dexpi" | "sfiles" (optional),
                "options": {
                    "include_msr": bool (for graphml),
                    "canonical": bool (for sfiles_string),
                    "version": "v1" | "v2" (for sfiles_string)
                }
            }

        Returns:
            Success response with exported content
        """
        model_id = args["model_id"]
        format_type = args["format"]
        model_type_hint = args.get("model_type")
        options = args.get("options", {})

        # Determine model type by checking which store contains it
        is_dexpi = model_id in self.dexpi_models
        is_sfiles = model_id in self.flowsheets

        if not is_dexpi and not is_sfiles:
            return error_response(
                f"Model {model_id} not found in either DEXPI or SFILES stores",
                "MODEL_NOT_FOUND",
                details={"model_id": model_id}
            )

        # Check for ambiguous model ID (exists in both stores)
        if is_dexpi and is_sfiles:
            # If model_type provided, use it to disambiguate
            if model_type_hint:
                if model_type_hint == "dexpi":
                    is_sfiles = False  # Ignore SFILES copy
                elif model_type_hint == "sfiles":
                    is_dexpi = False  # Ignore DEXPI copy
            else:
                return error_response(
                    f"Model ID {model_id} exists in both DEXPI and SFILES stores. "
                    "Please specify model_type parameter to disambiguate",
                    "AMBIGUOUS_MODEL_ID",
                    details={
                        "model_id": model_id,
                        "in_dexpi": True,
                        "in_sfiles": True,
                        "suggestion": "Add model_type='dexpi' or model_type='sfiles' parameter"
                    }
                )

        if is_dexpi:
            if format_type == "json":
                export_args = {"model_id": model_id}
                return await self.dexpi_tools._export_json(export_args)

            elif format_type == "graphml":
                export_args = {
                    "model_id": model_id,
                    "include_msr": options.get("include_msr", True)
                }
                return await self.dexpi_tools._export_graphml(export_args)

            else:
                return error_response(
                    f"Invalid format '{format_type}' for DEXPI models. Use 'json' or 'graphml'",
                    "INVALID_FORMAT"
                )

        else:  # is_sfiles
            if format_type == "sfiles_string":
                export_args = {
                    "flowsheet_id": model_id,
                    "canonical": options.get("canonical", True),
                    "version": options.get("version", "v2")
                }
                return await self.sfiles_tools._to_string(export_args)

            elif format_type == "graphml":
                export_args = {"flowsheet_id": model_id}
                return await self.sfiles_tools._export_graphml(export_args)

            else:
                return error_response(
                    f"Invalid format '{format_type}' for SFILES models. Use 'sfiles_string' or 'graphml'",
                    "INVALID_FORMAT"
                )

    async def _combine_models(self, args: dict) -> dict:
        """Combine multiple DEXPI models into one.

        Uses pydexpi.toolkits.model_toolkit.combine_dexpi_models() to merge
        models, combining all list attributes from conceptual models.

        Args:
            args: {
                "source_model_ids": list[str],  # Minimum 2 models
                "target_model_id": str (optional),
                "metadata": dict (optional)
            }

        Returns:
            Success response with combined model info
        """
        from pydexpi.toolkits.model_toolkit import combine_dexpi_models

        source_model_ids = args["source_model_ids"]
        target_model_id = args.get("target_model_id", str(uuid4()))
        metadata = args.get("metadata", {})

        # Validate minimum number of models
        if len(source_model_ids) < 2:
            return error_response(
                "At least 2 source models are required for combination",
                "INSUFFICIENT_MODELS",
                details={"provided": len(source_model_ids), "required": 2}
            )

        # Collect models from store
        models = []
        missing_models = []
        for model_id in source_model_ids:
            if model_id in self.dexpi_models:
                models.append(self.dexpi_models[model_id])
            else:
                missing_models.append(model_id)

        if missing_models:
            return error_response(
                f"Models not found: {', '.join(missing_models)}",
                "MODELS_NOT_FOUND",
                details={"missing": missing_models}
            )

        # Check if target_model_id already exists
        if target_model_id in self.dexpi_models:
            return error_response(
                f"Target model ID '{target_model_id}' already exists. Choose a different ID.",
                "MODEL_ID_EXISTS",
                details={"target_model_id": target_model_id}
            )

        try:
            # Combine models using pyDEXPI toolkit
            combined = combine_dexpi_models(models, **metadata)

            # Store the combined model
            self.dexpi_models[target_model_id] = combined

            # Count items in combined model
            stats = {
                "equipment_count": 0,
                "instrumentation_count": 0,
                "piping_count": 0
            }

            if combined.conceptualModel:
                if combined.conceptualModel.taggedPlantItems:
                    stats["equipment_count"] = len(combined.conceptualModel.taggedPlantItems)
                if combined.conceptualModel.processInstrumentationFunctions:
                    stats["instrumentation_count"] = len(combined.conceptualModel.processInstrumentationFunctions)
                if combined.conceptualModel.pipingNetworkSystems:
                    stats["piping_count"] = len(combined.conceptualModel.pipingNetworkSystems)

            return success_response({
                "target_model_id": target_model_id,
                "source_model_ids": source_model_ids,
                "source_count": len(source_model_ids),
                "statistics": stats
            })

        except NotImplementedError as e:
            # pyDEXPI raises this if models have diagram/shapeCatalog attributes
            return error_response(
                f"Cannot combine models with diagram data: {str(e)}. "
                "Models must not have diagram or shapeCatalogue attributes.",
                "DIAGRAM_NOT_SUPPORTED",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.exception(f"Model combination failed")
            return error_response(
                f"Model combination failed: {str(e)}",
                "COMBINATION_FAILED",
                details={"error": str(e)}
            )
