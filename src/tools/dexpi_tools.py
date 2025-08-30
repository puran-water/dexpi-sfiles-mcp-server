"""DEXPI-based tools for P&ID generation and manipulation."""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mcp import Tool
from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.dexpi_classes.metaData import MetaData
from pydexpi.loaders import JsonSerializer, ProteusSerializer
from pydexpi.loaders.ml_graph_loader import MLGraphLoader
from pydexpi.syndata import SyntheticPIDGenerator
from pydexpi.toolkits import model_toolkit as mt
from pydexpi.toolkits import piping_toolkit as pt
from pydexpi.dexpi_classes.equipment import Tank, Pump, Compressor, Nozzle, HeatExchanger
from pydexpi.dexpi_classes.piping import PipingNetworkSegment, Pipe, PipingNode
from pydexpi.dexpi_classes.instrumentation import ProcessInstrumentationFunction
from .dexpi_introspector import DexpiIntrospector

logger = logging.getLogger(__name__)


class DexpiTools:
    """Handles all DEXPI-related MCP tools."""
    
    def __init__(self, model_store: Dict[str, DexpiModel]):
        """Initialize with a reference to the model store."""
        self.models = model_store
        self.json_serializer = JsonSerializer()
        self.graph_loader = MLGraphLoader()
        self.introspector = DexpiIntrospector()
    
    def get_tools(self) -> List[Tool]:
        """Return all DEXPI tools."""
        return [
            Tool(
                name="dexpi_create_pid",
                description="Initialize a new DEXPI P&ID model with metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "drawing_number": {"type": "string"},
                        "revision": {"type": "string", "default": "A"},
                        "description": {"type": "string", "default": ""}
                    },
                    "required": ["project_name", "drawing_number"]
                }
            ),
            Tool(
                name="dexpi_add_equipment",
                description="Add equipment (pump, tank, reactor, etc.) to the P&ID model with nozzles",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "equipment_type": {
                            "type": "string", 
                            "enum": ["Tank", "Pump", "Compressor", "Reactor", "HeatExchanger"]
                        },
                        "tag_name": {"type": "string"},
                        "specifications": {
                            "type": "object",
                            "description": "Equipment-specific specifications"
                        },
                        "nozzles": {
                            "type": "array",
                            "description": "Nozzle configurations (auto-created if not specified)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "subTagName": {"type": "string"},
                                    "nominalPressure": {"type": "string"},
                                    "nominalDiameter": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["model_id", "equipment_type", "tag_name"]
                }
            ),
            Tool(
                name="dexpi_add_piping",
                description="Add piping segment to the P&ID model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "segment_id": {"type": "string"},
                        "pipe_class": {"type": "string", "default": "CS150"},
                        "nominal_diameter": {"type": "number", "default": 50},
                        "material": {"type": "string", "default": "Carbon Steel"}
                    },
                    "required": ["model_id", "segment_id"]
                }
            ),
            Tool(
                name="dexpi_add_instrumentation",
                description="Add instrumentation to the P&ID model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "instrument_type": {
                            "type": "string",
                            "enum": ["PressureIndicator", "FlowController", "LevelTransmitter", 
                                    "TemperatureIndicator", "LevelController"]
                        },
                        "tag_name": {"type": "string"},
                        "connected_equipment": {"type": "string", "description": "Tag of connected equipment"}
                    },
                    "required": ["model_id", "instrument_type", "tag_name"]
                }
            ),
            Tool(
                name="dexpi_connect_components",
                description="Create piping connections between equipment and instruments",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "from_component": {"type": "string"},
                        "to_component": {"type": "string"},
                        "pipe_class": {"type": "string", "default": "CS150"},
                        "line_number": {"type": "string"}
                    },
                    "required": ["model_id", "from_component", "to_component"]
                }
            ),
            Tool(
                name="dexpi_validate_model",
                description="Validate P&ID for engineering rules and referential integrity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "validation_level": {
                            "type": "string", 
                            "enum": ["basic", "comprehensive"],
                            "default": "basic"
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="dexpi_export_json",
                description="Export P&ID model as JSON",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"}
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="dexpi_export_graphml",
                description="Export P&ID topology as machine-readable GraphML",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "include_msr": {
                            "type": "boolean", 
                            "default": True,
                            "description": "Include measurement/control/regulation units"
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="dexpi_import_json",
                description="Import P&ID model from JSON",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "json_content": {"type": "string", "description": "JSON string of DEXPI model"},
                        "model_id": {"type": "string", "description": "Optional ID for imported model"}
                    },
                    "required": ["json_content"]
                }
            ),
            Tool(
                name="dexpi_add_valve",
                description="Add valve to the P&ID model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "valve_type": {
                            "type": "string",
                            "enum": ["BallValve", "GateValve", "GlobeValve", "CheckValve", 
                                    "ButterflyValve", "NeedleValve", "PlugValve", "AngleValve"]
                        },
                        "tag_name": {"type": "string"},
                        "piping_class": {"type": "string", "default": "CS150"},
                        "nominal_diameter": {"type": "string", "default": "DN50"},
                        "operation": {"type": "string", "description": "Operation mode (optional - uses pyDEXPI defaults)"}
                    },
                    "required": ["model_id", "valve_type", "tag_name"]
                }
            ),
            Tool(
                name="dexpi_list_available_types",
                description="List all available equipment, valve, and instrumentation types",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["all", "equipment", "valves", "piping", "instrumentation"],
                            "default": "all"
                        }
                    }
                }
            ),
            Tool(
                name="dexpi_validate_connections",
                description="Validate all piping connections in the P&ID model using pyDEXPI's native validation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"}
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="dexpi_validate_graph",
                description="Validate P&ID graph structure using MLGraphLoader validation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "include_details": {"type": "boolean", "default": True}
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="dexpi_check_connectivity",
                description="Check if all equipment is properly connected in the P&ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"}
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="dexpi_init_project",
                description="Initialize a new git project for storing DEXPI and SFILES models",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path where project should be created"},
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "description": {"type": "string", "description": "Optional project description", "default": ""}
                    },
                    "required": ["project_path", "project_name"]
                }
            ),
            Tool(
                name="dexpi_save_to_project",
                description="Save DEXPI model to a git project with version control",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string", "description": "Model ID to save"},
                        "project_path": {"type": "string", "description": "Path to project root"},
                        "model_name": {"type": "string", "description": "Name for saved model (without extension)"},
                        "commit_message": {"type": "string", "description": "Optional git commit message"}
                    },
                    "required": ["model_id", "project_path", "model_name"]
                }
            ),
            Tool(
                name="dexpi_load_from_project",
                description="Load DEXPI model from a git project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path to project root"},
                        "model_name": {"type": "string", "description": "Name of model to load (without extension)"},
                        "model_id": {"type": "string", "description": "Optional ID for loaded model"}
                    },
                    "required": ["project_path", "model_name"]
                }
            ),
            Tool(
                name="dexpi_list_project_models",
                description="List all DEXPI and SFILES models in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path to project root"}
                    },
                    "required": ["project_path"]
                }
            )
        ]
    
    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler."""
        handlers = {
            "dexpi_create_pid": self._create_pid,
            "dexpi_add_equipment": self._add_equipment,
            "dexpi_add_piping": self._add_piping,
            "dexpi_add_instrumentation": self._add_instrumentation,
            "dexpi_connect_components": self._connect_components,
            "dexpi_validate_model": self._validate_model,
            "dexpi_export_json": self._export_json,
            "dexpi_export_graphml": self._export_graphml,
            "dexpi_import_json": self._import_json,
            "dexpi_add_valve": self._add_valve,
            "dexpi_list_available_types": self._list_available_types,
            "dexpi_validate_connections": self._validate_connections,
            "dexpi_validate_graph": self._validate_graph,
            "dexpi_check_connectivity": self._check_connectivity,
            "dexpi_save_to_project": self._save_to_project,
            "dexpi_load_from_project": self._load_from_project,
            "dexpi_init_project": self._init_project,
            "dexpi_list_project_models": self._list_project_models,
        }
        
        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown DEXPI tool: {name}")
        
        return await handler(arguments)
    
    async def _create_pid(self, args: dict) -> dict:
        """Create a new P&ID model."""
        model_id = str(uuid4())
        
        # Create metadata
        metadata = MetaData(
            projectName=args["project_name"],
            drawingNumber=args["drawing_number"],
            revision=args.get("revision", "A"),
            description=args.get("description", "")
        )
        
        # Create empty DEXPI model
        model = DexpiModel(metaData=metadata)
        
        # Store model
        self.models[model_id] = model
        
        return {
            "status": "success",
            "model_id": model_id,
            "project_name": args["project_name"],
            "drawing_number": args["drawing_number"]
        }
    
    async def _add_equipment(self, args: dict) -> dict:
        """Add equipment to P&ID model with mandatory nozzles."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        equipment_type = args["equipment_type"]
        tag_name = args["tag_name"]
        specs = args.get("specifications", {})
        nozzle_configs = args.get("nozzles", [])
        
        # Create equipment based on type
        if equipment_type == "Tank":
            equipment = Tank(tagName=tag_name, **specs)
        elif equipment_type == "Pump":
            equipment = Pump(tagName=tag_name, **specs)
        elif equipment_type == "Compressor":
            equipment = Compressor(tagName=tag_name, **specs)
        elif equipment_type == "HeatExchanger":
            equipment = HeatExchanger(tagName=tag_name, **specs)
        else:
            # Try to get the class dynamically from the introspector
            try:
                from pydexpi.dexpi_classes import equipment as eq_module
                equipment_class = getattr(eq_module, equipment_type, None)
                if equipment_class:
                    equipment = equipment_class(tagName=tag_name, **specs)
                else:
                    # Fallback to Tank
                    equipment = Tank(tagName=tag_name, **specs)
            except:
                equipment = Tank(tagName=tag_name, **specs)
        
        # Always create nozzles for equipment (critical for GraphML export)
        if not nozzle_configs:
            # Default nozzles if none specified
            nozzle_configs = [
                {"subTagName": "N1", "nominalPressure": "PN16", "nominalDiameter": "DN50"},
                {"subTagName": "N2", "nominalPressure": "PN16", "nominalDiameter": "DN50"}
            ]
        
        # Create nozzles
        nozzles = []
        for idx, nozzle_config in enumerate(nozzle_configs):
            nozzle = Nozzle(
                id=f"nozzle_{idx}_{tag_name}",
                subTagName=nozzle_config.get("subTagName", f"N{idx+1}"),
                nominalPressureRepresentation=nozzle_config.get("nominalPressure", "PN16"),
                nominalPressureNumericalValueRepresentation=nozzle_config.get("nominalPressure", "16").replace("PN", "")
            )
            
            # Add piping node to nozzle if diameter specified
            if "nominalDiameter" in nozzle_config:
                node = PipingNode(
                    nominalDiameterRepresentation=nozzle_config["nominalDiameter"],
                    nominalDiameterNumericalValueRepresentation=nozzle_config["nominalDiameter"].replace("DN", "")
                )
                nozzle.nodes = [node]
            
            nozzles.append(nozzle)
        
        # Assign nozzles to equipment
        equipment.nozzles = nozzles
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.taggedPlantItems:
            model.conceptualModel.taggedPlantItems = []
        
        model.conceptualModel.taggedPlantItems.append(equipment)
        
        return {
            "status": "success",
            "equipment_type": equipment_type,
            "tag_name": tag_name,
            "model_id": model_id,
            "nozzles_created": len(nozzles)
        }
    
    async def _add_piping(self, args: dict) -> dict:
        """Add piping segment to model."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        # Create piping segment
        segment = PipingNetworkSegment(
            id=args["segment_id"],
            pipingClassArtefact=args.get("pipe_class", "CS150")
        )
        
        # Create a pipe within the segment
        pipe = Pipe(
            nominalDiameter=args.get("nominal_diameter", 50),
            material=args.get("material", "Carbon Steel")
        )
        
        segment.pipingNetworkSegmentItems = [pipe]
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.pipingNetworkSystems:
            model.conceptualModel.pipingNetworkSystems = []
        
        model.conceptualModel.pipingNetworkSystems.append(segment)
        
        return {
            "status": "success",
            "segment_id": args["segment_id"],
            "pipe_class": args.get("pipe_class", "CS150"),
            "model_id": model_id
        }
    
    async def _add_instrumentation(self, args: dict) -> dict:
        """Add instrumentation to model."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        # Create instrumentation
        instrument = ProcessInstrumentationFunction(
            tagName=args["tag_name"],
            instrumentationType=args["instrument_type"]
        )
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.processInstrumentationFunctions:
            model.conceptualModel.processInstrumentationFunctions = []
        
        model.conceptualModel.processInstrumentationFunctions.append(instrument)
        
        return {
            "status": "success",
            "instrument_type": args["instrument_type"],
            "tag_name": args["tag_name"],
            "model_id": model_id
        }
    
    async def _connect_components(self, args: dict) -> dict:
        """Connect components with piping using pyDEXPI's native toolkit."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        from_component = args["from_component"]
        to_component = args["to_component"]
        line_number = args.get("line_number", f"{from_component}_to_{to_component}")
        pipe_class = args.get("pipe_class", "CS150")
        
        # Import piping toolkit and classes
        from pydexpi.toolkits import piping_toolkit
        from pydexpi.dexpi_classes.piping import (
            PipingNetworkSegment,
            PipingNetworkSystem, 
            PipingConnection,
            Pipe,
            PipingNode
        )
        
        # Find equipment by tag name
        from_equipment = None
        to_equipment = None
        
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            for item in model.conceptualModel.taggedPlantItems:
                if hasattr(item, 'tagName') and item.tagName == from_component:
                    from_equipment = item
                if hasattr(item, 'tagName') and item.tagName == to_component:
                    to_equipment = item
        
        if not from_equipment:
            raise ValueError(f"Equipment '{from_component}' not found")
        if not to_equipment:
            raise ValueError(f"Equipment '{to_component}' not found")
        
        # Get nozzles from equipment
        from_nozzle = None
        to_nozzle = None
        
        if hasattr(from_equipment, 'nozzles') and from_equipment.nozzles:
            from_nozzle = from_equipment.nozzles[-1]  # Use last nozzle as outlet
        if hasattr(to_equipment, 'nozzles') and to_equipment.nozzles:
            to_nozzle = to_equipment.nozzles[0]  # Use first nozzle as inlet
        
        if not from_nozzle:
            raise ValueError(f"Equipment '{from_component}' has no nozzles")
        if not to_nozzle:
            raise ValueError(f"Equipment '{to_component}' has no nozzles")
        
        # Use pyDEXPI piping_toolkit to create connections properly
        from pydexpi.toolkits import piping_toolkit as pt
        
        # Create a pipe for the connection
        # Pipe is a PipingConnection, not a PipingNetworkSegmentItem
        pipe = Pipe(
            id=f"pipe_{line_number}",
            tagName=line_number
        )
        
        # Create piping network segment with the pipe in connections
        segment = PipingNetworkSegment(
            id=f"segment_{line_number}",
            pipingClassArtefact=pipe_class
        )
        
        # Pipe goes in connections list, not items list
        # Items would be valves or other components
        segment.connections = [pipe]
        segment.items = []  # No intermediate components for simple connection
        
        # Connect the segment to the source nozzle (from_equipment)
        pt.connect_piping_network_segment(segment, from_nozzle, as_source=True)
        
        # Connect the segment to the target nozzle (to_equipment)  
        pt.connect_piping_network_segment(segment, to_nozzle, as_source=False)
        
        # Create a PipingNetworkSystem to hold segments
        # MLGraphLoader expects systems with segments attribute
        if not model.conceptualModel.pipingNetworkSystems:
            model.conceptualModel.pipingNetworkSystems = []
        
        # Find or create a piping system
        if len(model.conceptualModel.pipingNetworkSystems) == 0:
            system = PipingNetworkSystem(
                id="piping_system_main",
                segments=[]
            )
            model.conceptualModel.pipingNetworkSystems.append(system)
        else:
            # Get the first system (assuming single system for simplicity)
            system = model.conceptualModel.pipingNetworkSystems[0]
            if not hasattr(system, 'segments'):
                system.segments = []
        
        # Add segment to the system
        system.segments.append(segment)
        
        # Validate the connection using piping_toolkit
        try:
            validity_code, message = piping_toolkit.piping_network_segment_validity_check(segment)
            validation_result = {
                "valid": str(validity_code) == "PipingValidityCode.VALID",
                "message": message
            }
        except Exception as e:
            validation_result = {
                "valid": False,
                "message": str(e)
            }
        
        return {
            "status": "success",
            "from": from_component,
            "to": to_component,
            "line_number": line_number,
            "pipe_class": pipe_class,
            "model_id": model_id,
            "validation": validation_result
        }
    
    async def _validate_model(self, args: dict) -> dict:
        """Validate the P&ID model."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        validation_level = args.get("validation_level", "basic")
        
        issues = []
        
        # Basic validation
        if not model.metadata:
            issues.append("Missing metadata")
        
        if not model.conceptualModel:
            issues.append("Empty conceptual model")
        else:
            if not model.conceptualModel.taggedPlantItems:
                issues.append("No equipment defined")
        
        # Comprehensive validation would include graph validation
        if validation_level == "comprehensive":
            try:
                # Convert to graph and validate
                graph = self.graph_loader.dexpi_to_graph(model)
                self.graph_loader.validate_graph_format(graph)
            except Exception as e:
                issues.append(f"Graph validation failed: {str(e)}")
        
        return {
            "status": "success" if not issues else "warning",
            "validation_level": validation_level,
            "issues": issues,
            "model_id": model_id
        }
    
    async def _export_json(self, args: dict) -> dict:
        """Export model as JSON."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        # Use model_to_dict() to convert to dictionary, then to JSON string
        import json
        
        model_dict = self.json_serializer.model_to_dict(model)
        json_content = json.dumps(model_dict, indent=4, ensure_ascii=False)
        
        return {
            "status": "success",
            "model_id": model_id,
            "json": json_content
        }
    
    async def _export_graphml(self, args: dict) -> dict:
        """Export model as GraphML."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        include_msr = args.get("include_msr", True)
        
        # Convert to NetworkX graph
        graph = self.graph_loader.dexpi_to_graph(model)
        
        # Sanitize None values in graph attributes before GraphML export
        for node, attrs in graph.nodes(data=True):
            for key, value in list(attrs.items()):
                if value is None:
                    attrs[key] = ""  # Replace None with empty string
        
        for u, v, attrs in graph.edges(data=True):
            for key, value in list(attrs.items()):
                if value is None:
                    attrs[key] = ""  # Replace None with empty string
        
        # Convert to GraphML
        import networkx as nx
        from io import BytesIO
        
        graphml_buffer = BytesIO()
        nx.write_graphml(graph, graphml_buffer)
        graphml_buffer.seek(0)
        graphml_content = graphml_buffer.read().decode('utf-8')
        
        return {
            "status": "success",
            "model_id": model_id,
            "include_msr": include_msr,
            "graphml": graphml_content
        }
    
    async def _import_json(self, args: dict) -> dict:
        """Import model from JSON."""
        json_content = args["json_content"]
        model_id = args.get("model_id", str(uuid4()))
        
        # Save to temporary file and load
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name
        
        model = self.json_serializer.load(temp_path)
        os.unlink(temp_path)
        
        # Store model
        self.models[model_id] = model
        
        return {
            "status": "success",
            "model_id": model_id,
            "project_name": model.metadata.projectData.projectName if model.metadata else "Unknown"
        }
    
    async def _add_valve(self, args: dict) -> dict:
        """Add valve to P&ID model."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        valve_type = args["valve_type"]
        tag_name = args["tag_name"]
        piping_class = args.get("piping_class", "CS150")
        nominal_diameter = args.get("nominal_diameter", "DN50")
        operation = args.get("operation", "manual")
        
        # Import valve types
        from pydexpi.dexpi_classes import piping as piping_module
        
        # Get the valve class dynamically
        valve_class = getattr(piping_module, valve_type, None)
        if not valve_class:
            raise ValueError(f"Unknown valve type: {valve_type}")
        
        # Create valve instance
        # Don't pass operation parameter since it causes validation errors
        valve_kwargs = {
            "pipingComponentName": tag_name,
            "pipingClassCode": piping_class
        }
        # Only add operation if it's a valid pyDEXPI value
        if operation in ["continuous operation", "intermittent operation", "null"]:
            valve_kwargs["operation"] = operation
        
        valve = valve_class(**valve_kwargs)
        
        # Add piping nodes for connectivity
        inlet_node = PipingNode(
            nominalDiameterRepresentation=nominal_diameter,
            nominalDiameterNumericalValueRepresentation=nominal_diameter.replace("DN", "")
        )
        outlet_node = PipingNode(
            nominalDiameterRepresentation=nominal_diameter,
            nominalDiameterNumericalValueRepresentation=nominal_diameter.replace("DN", "")
        )
        valve.nodes = [inlet_node, outlet_node]
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.pipingNetworkSystems:
            model.conceptualModel.pipingNetworkSystems = []
        
        # Import PipingNetworkSystem
        from pydexpi.dexpi_classes.piping import PipingNetworkSystem
        
        # Find or create a piping system
        if len(model.conceptualModel.pipingNetworkSystems) == 0:
            system = PipingNetworkSystem(
                id="piping_system_main",
                segments=[]
            )
            model.conceptualModel.pipingNetworkSystems.append(system)
        else:
            system = model.conceptualModel.pipingNetworkSystems[0]
            if not hasattr(system, 'segments'):
                system.segments = []
        
        # Create a piping segment for the valve
        segment = PipingNetworkSegment(
            id=f"segment_valve_{tag_name}",
            pipingClassArtefact=piping_class
        )
        # Valves are PipingNetworkSegmentItems, so they go in items
        segment.items = [valve]
        segment.connections = []  # No connections yet
        
        system.segments.append(segment)
        
        return {
            "status": "success",
            "valve_type": valve_type,
            "tag_name": tag_name,
            "model_id": model_id,
            "operation": operation
        }
    
    async def _list_available_types(self, args: dict) -> dict:
        """List all available element types."""
        category = args.get("category", "all")
        
        result = {}
        
        if category in ["all", "equipment"]:
            result["equipment"] = self.introspector.get_available_types()["equipment"]
        
        if category in ["all", "valves"]:
            result["valves"] = self.introspector.get_valves()
        
        if category in ["all", "piping"]:
            result["piping"] = self.introspector.get_available_types()["piping"]
        
        if category in ["all", "instrumentation"]:
            result["instrumentation"] = self.introspector.get_available_types()["instrumentation"]
        
        # Also include equipment that support nozzles
        if category in ["all", "equipment"]:
            result["equipment_with_nozzles"] = self.introspector.get_equipment_with_nozzles()
        
        return {
            "status": "success",
            "category": category,
            "available_types": result,
            "total_count": sum(len(v) if isinstance(v, list) else 0 for v in result.values())
        }
    
    async def _validate_connections(self, args: dict) -> dict:
        """Validate all piping connections using pyDEXPI's native validation."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        from pydexpi.toolkits import piping_toolkit
        from pydexpi.toolkits.piping_toolkit import PipingValidityCode
        
        validation_results = []
        
        # Check all piping network segments
        if model.conceptualModel and model.conceptualModel.pipingNetworkSystems:
            for system in model.conceptualModel.pipingNetworkSystems:
                # Now we iterate through segments within each system
                if hasattr(system, 'segments') and system.segments:
                    for segment in system.segments:
                        try:
                            validity_code, message = piping_toolkit.piping_network_segment_validity_check(segment)
                            validation_results.append({
                                "segment_id": segment.id if hasattr(segment, 'id') else "unknown",
                                "valid": validity_code == PipingValidityCode.VALID,
                                "validity_code": str(validity_code),
                                "message": message
                            })
                        except Exception as e:
                            validation_results.append({
                                "segment_id": segment.id if hasattr(segment, 'id') else "unknown",
                                "valid": False,
                                "error": str(e)
                            })
        
        # Count validation results
        valid_count = sum(1 for r in validation_results if r.get("valid", False))
        total_count = len(validation_results)
        
        return {
            "status": "success",
            "model_id": model_id,
            "validation_results": validation_results,
            "summary": {
                "total_segments": total_count,
                "valid_segments": valid_count,
                "invalid_segments": total_count - valid_count,
                "all_valid": valid_count == total_count if total_count > 0 else False
            }
        }
    
    async def _validate_graph(self, args: dict) -> dict:
        """Validate P&ID graph structure using MLGraphLoader."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        include_details = args.get("include_details", True)
        
        try:
            # Convert to graph
            from pydexpi.loaders.ml_graph_loader import MLGraphLoader
            loader = MLGraphLoader(model)
            loader.parse_dexpi_to_graph()
            
            # Validate graph format
            validation_issues = []
            try:
                loader.validate_graph_format()
                graph_valid = True
            except Exception as e:
                graph_valid = False
                validation_issues.append(str(e))
            
            # Get graph statistics
            graph = loader.plant_graph
            stats = {
                "num_nodes": graph.number_of_nodes(),
                "num_edges": graph.number_of_edges(),
                "is_connected": nx.is_weakly_connected(graph) if graph.is_directed() else nx.is_connected(graph),
                "has_cycles": not nx.is_directed_acyclic_graph(graph) if graph.is_directed() else None
            }
            
            result = {
                "status": "success",
                "model_id": model_id,
                "graph_valid": graph_valid,
                "statistics": stats
            }
            
            if include_details:
                result["validation_issues"] = validation_issues
                
                # List node types
                node_types = {}
                for node, attrs in graph.nodes(data=True):
                    node_type = attrs.get("class", "unknown")
                    node_types[node_type] = node_types.get(node_type, 0) + 1
                result["node_types"] = node_types
                
                # List edge types
                edge_types = {}
                for u, v, attrs in graph.edges(data=True):
                    edge_type = attrs.get("class", "unknown")
                    edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
                result["edge_types"] = edge_types
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "model_id": model_id,
                "error": str(e)
            }
    
    async def _check_connectivity(self, args: dict) -> dict:
        """Check if all equipment is properly connected."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        connectivity_report = {
            "connected_equipment": [],
            "unconnected_equipment": [],
            "partial_connections": []
        }
        
        # Get all equipment
        all_equipment = []
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            all_equipment = [
                item for item in model.conceptualModel.taggedPlantItems
                if hasattr(item, 'tagName')
            ]
        
        # Check connections for each equipment
        for equipment in all_equipment:
            tag_name = equipment.tagName
            nozzles = getattr(equipment, 'nozzles', [])
            
            if not nozzles:
                connectivity_report["unconnected_equipment"].append({
                    "tag_name": tag_name,
                    "reason": "No nozzles defined"
                })
                continue
            
            # Check if nozzles are connected
            connected_nozzles = 0
            total_nozzles = len(nozzles)
            
            # Look for connections in piping segments
            if model.conceptualModel and model.conceptualModel.pipingNetworkSystems:
                for segment in model.conceptualModel.pipingNetworkSystems:
                    if hasattr(segment, 'connections'):
                        for conn in segment.connections:
                            for nozzle in nozzles:
                                if (hasattr(conn, 'sourceNode') and conn.sourceNode == nozzle) or \
                                   (hasattr(conn, 'targetNode') and conn.targetNode == nozzle):
                                    connected_nozzles += 1
            
            if connected_nozzles == 0:
                connectivity_report["unconnected_equipment"].append({
                    "tag_name": tag_name,
                    "reason": f"Has {total_nozzles} nozzles but none are connected"
                })
            elif connected_nozzles < total_nozzles:
                connectivity_report["partial_connections"].append({
                    "tag_name": tag_name,
                    "connected": connected_nozzles,
                    "total": total_nozzles
                })
            else:
                connectivity_report["connected_equipment"].append(tag_name)
        
        # Summary
        total_equipment = len(all_equipment)
        fully_connected = len(connectivity_report["connected_equipment"])
        
        return {
            "status": "success",
            "model_id": model_id,
            "connectivity": connectivity_report,
            "summary": {
                "total_equipment": total_equipment,
                "fully_connected": fully_connected,
                "partially_connected": len(connectivity_report["partial_connections"]),
                "unconnected": len(connectivity_report["unconnected_equipment"]),
                "connectivity_percentage": (fully_connected / total_equipment * 100) if total_equipment > 0 else 0
            }
        }
    
    async def _save_to_project(self, args: dict) -> dict:
        """Save DEXPI model to a git project."""
        from ..persistence import ProjectPersistence
        
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        project_path = args["project_path"]
        model_name = args.get("model_name", f"PID-{model_id[:8]}")
        commit_message = args.get("commit_message")
        
        persistence = ProjectPersistence()
        model = self.models[model_id]
        
        saved_paths = persistence.save_dexpi(
            model=model,
            project_path=project_path,
            model_name=model_name,
            commit_message=commit_message
        )
        
        return {
            "status": "success",
            "model_id": model_id,
            "model_name": model_name,
            "project_path": project_path,
            "saved_files": saved_paths
        }
    
    async def _load_from_project(self, args: dict) -> dict:
        """Load DEXPI model from a git project."""
        from ..persistence import ProjectPersistence
        
        project_path = args["project_path"]
        model_name = args["model_name"]
        
        persistence = ProjectPersistence()
        model = persistence.load_dexpi(project_path, model_name)
        
        # Store in memory with new ID
        model_id = str(uuid4())
        self.models[model_id] = model
        
        return {
            "status": "success",
            "model_id": model_id,
            "model_name": model_name,
            "project_path": project_path,
            "project_name": model.metadata.projectData.projectName if hasattr(model, 'metadata') and model.metadata else None,
            "drawing_number": model.metadata.drawingData.drawingNumber if hasattr(model, 'metadata') and model.metadata else None
        }
    
    async def _init_project(self, args: dict) -> dict:
        """Initialize a new git project for engineering models."""
        from ..persistence import ProjectPersistence
        
        project_path = args["project_path"]
        project_name = args["project_name"]
        description = args.get("description", "")
        
        persistence = ProjectPersistence()
        metadata = persistence.init_project(project_path, project_name, description)
        
        return {
            "status": "success",
            "project_path": project_path,
            "metadata": metadata
        }
    
    async def _list_project_models(self, args: dict) -> dict:
        """List all models in a project."""
        from ..persistence import ProjectPersistence
        
        project_path = args["project_path"]
        
        persistence = ProjectPersistence()
        models = persistence.list_models(project_path)
        
        return {
            "status": "success",
            "project_path": project_path,
            "models": models
        }
