"""Unified project management tools for DEXPI and SFILES models."""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Tool
from ..persistence.project_persistence import ProjectPersistence
from ..utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class ProjectTools:
    """Handles unified project operations for both DEXPI and SFILES models."""
    
    def __init__(self, dexpi_store: Dict[str, Any], sfiles_store: Dict[str, Any]):
        """Initialize with references to both model stores.
        
        Args:
            dexpi_store: Dictionary storing DEXPI models
            sfiles_store: Dictionary storing SFILES flowsheets
        """
        self.dexpi_models = dexpi_store
        self.flowsheets = sfiles_store
        self.persistence = ProjectPersistence()
    
    def get_tools(self) -> List[Tool]:
        """Return all project management tools."""
        return [
            Tool(
                name="project_init",
                description="Initialize a new git-tracked project for engineering models",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path where project should be created"
                        },
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional project description",
                            "default": ""
                        }
                    },
                    "required": ["project_path", "project_name"]
                }
            ),
            Tool(
                name="project_save",
                description="Save a model to a git project with version control",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to save"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Name for saved model (without extension)"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Type of model (auto-detect if not specified)",
                            "default": "auto"
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "Optional git commit message"
                        }
                    },
                    "required": ["project_path", "model_id", "model_name"]
                }
            ),
            Tool(
                name="project_load",
                description="Load a model from a git project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Name of model to load (without extension)"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Type of model (auto-detect if not specified)",
                            "default": "auto"
                        },
                        "model_id": {
                            "type": "string",
                            "description": "Optional ID for loaded model"
                        }
                    },
                    "required": ["project_path", "model_name"]
                }
            ),
            Tool(
                name="project_list",
                description="List all models in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to project root"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "all"],
                            "description": "Filter by model type",
                            "default": "all"
                        }
                    },
                    "required": ["project_path"]
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
            "project_init": self._init_project,
            "project_save": self._save_model,
            "project_load": self._load_model,
            "project_list": self._list_models
        }
        
        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown project tool: {name}", code="UNKNOWN_TOOL")
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return error_response(str(e), code="TOOL_ERROR")
    
    async def _init_project(self, args: dict) -> dict:
        """Initialize a new project."""
        try:
            metadata = self.persistence.init_project(
                args["project_path"],
                args["project_name"],
                args.get("description", "")
            )
            
            return success_response({
                "project_metadata": metadata,
                "project_path": args["project_path"]
            })
        except Exception as e:
            return error_response(f"Failed to initialize project: {str(e)}", code="INIT_ERROR")
    
    async def _save_model(self, args: dict) -> dict:
        """Save a model to project."""
        model_id = args["model_id"]
        model_type = args.get("model_type", "auto")
        
        # Auto-detect model type if needed
        if model_type == "auto":
            if model_id in self.dexpi_models:
                model_type = "dexpi"
            elif model_id in self.flowsheets:
                model_type = "sfiles"
            else:
                return error_response(f"Model {model_id} not found", code="MODEL_NOT_FOUND")
        
        try:
            if model_type == "dexpi":
                if model_id not in self.dexpi_models:
                    return error_response(f"DEXPI model {model_id} not found", code="MODEL_NOT_FOUND")
                
                model = self.dexpi_models[model_id]
                saved_paths = self.persistence.save_dexpi(
                    model,
                    args["project_path"],
                    args["model_name"],
                    args.get("commit_message")
                )
            else:  # sfiles
                if model_id not in self.flowsheets:
                    return error_response(f"SFILES flowsheet {model_id} not found", code="MODEL_NOT_FOUND")
                
                flowsheet = self.flowsheets[model_id]
                saved_paths = self.persistence.save_sfiles(
                    flowsheet,
                    args["project_path"],
                    args["model_name"],
                    args.get("commit_message")
                )
            
            return success_response({
                "saved_paths": saved_paths,
                "model_id": model_id,
                "model_type": model_type
            })
        except Exception as e:
            return error_response(f"Failed to save model: {str(e)}", code="SAVE_ERROR")
    
    async def _load_model(self, args: dict) -> dict:
        """Load a model from project."""
        model_type = args.get("model_type", "auto")
        
        # Auto-detect model type if needed
        if model_type == "auto":
            models = self.persistence.list_models(args["project_path"])
            model_name = args["model_name"]
            
            # Check which type exists
            dexpi_exists = model_name in models.get("dexpi", [])
            sfiles_exists = model_name in models.get("sfiles", [])
            
            if dexpi_exists and not sfiles_exists:
                model_type = "dexpi"
            elif sfiles_exists and not dexpi_exists:
                model_type = "sfiles"
            elif dexpi_exists and sfiles_exists:
                return error_response(
                    f"Model {model_name} exists in both DEXPI and SFILES formats. Specify model_type.",
                    code="AMBIGUOUS_TYPE"
                )
            else:
                return error_response(f"Model {model_name} not found", code="MODEL_NOT_FOUND")
        
        try:
            if model_type == "dexpi":
                model = self.persistence.load_dexpi(
                    args["project_path"],
                    args["model_name"]
                )
                
                # Assign ID and store
                model_id = args.get("model_id", f"loaded_{args['model_name']}")
                self.dexpi_models[model_id] = model
                
                return success_response({
                    "model_id": model_id,
                    "model_type": "dexpi",
                    "equipment_count": len(model.conceptualModel.taggedPlantItems) if model.conceptualModel else 0
                })
            else:  # sfiles
                flowsheet = self.persistence.load_sfiles(
                    args["project_path"],
                    args["model_name"]
                )
                
                # Assign ID and store
                model_id = args.get("model_id", f"loaded_{args['model_name']}")
                self.flowsheets[model_id] = flowsheet
                
                return success_response({
                    "model_id": model_id,
                    "model_type": "sfiles",
                    "num_nodes": flowsheet.state.number_of_nodes(),
                    "num_edges": flowsheet.state.number_of_edges()
                })
        except Exception as e:
            return error_response(f"Failed to load model: {str(e)}", code="LOAD_ERROR")
    
    async def _list_models(self, args: dict) -> dict:
        """List all models in project."""
        try:
            models = self.persistence.list_models(args["project_path"])
            model_type = args.get("model_type", "all")
            
            if model_type == "dexpi":
                result = {"dexpi": models.get("dexpi", [])}
            elif model_type == "sfiles":
                result = {"sfiles": models.get("sfiles", [])}
            else:  # all
                result = models
            
            # Add counts
            summary = {
                "total": sum(len(v) for v in result.values()),
                "by_type": {k: len(v) for k, v in result.items()}
            }
            
            return success_response({
                "models": result,
                "summary": summary
            })
        except Exception as e:
            return error_response(f"Failed to list models: {str(e)}", code="LIST_ERROR")