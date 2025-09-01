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
from ..utils.response import success_response, error_response, validation_response, create_issue

logger = logging.getLogger(__name__)


class DexpiTools:
    """Handles all DEXPI-related MCP tools."""
    
    def __init__(self, model_store: Dict[str, DexpiModel], flowsheet_store: Dict[str, Any] = None):
        """Initialize with references to both model stores."""
        self.models = model_store
        self.flowsheets = flowsheet_store if flowsheet_store is not None else {}
        self.json_serializer = JsonSerializer()
        self.graph_loader = MLGraphLoader()
        self.introspector = DexpiIntrospector()
    
    def get_tools(self) -> List[Tool]:
        """Return all DEXPI tools."""
        # Dynamically generate equipment types from introspector
        equipment_types = self.introspector.generate_dynamic_enum("equipment")
        valve_types = self.introspector.generate_dynamic_enum("valves")
        instrumentation_types = self.introspector.generate_dynamic_enum("instrumentation")
        
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
                description=f"Add equipment to the P&ID model ({len(equipment_types)} types available)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "equipment_type": {
                            "type": "string", 
                            "enum": equipment_types,  # Dynamic!
                            "description": f"Equipment type (one of {len(equipment_types)} available)"
                        },
                        "tag_name": {"type": "string"},
                        "specifications": {
                            "type": "object",
                            "description": "Equipment-specific specifications (use dexpi_describe_class to see valid attributes)"
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
                            "enum": instrumentation_types  # Dynamic from introspector
                        },
                        "tag_name": {"type": "string"},
                        "connected_equipment": {"type": "string", "description": "Tag of connected equipment"}
                    },
                    "required": ["model_id", "instrument_type", "tag_name"]
                }
            ),
            Tool(
                name="dexpi_add_control_loop",
                description="Add complete control loop with signal generating, control, and actuating functions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "loop_tag": {"type": "string", "description": "Control loop tag (e.g., FIC-101)"},
                        "controlled_variable": {
                            "type": "string",
                            "enum": ["Flow", "Level", "Temperature", "Pressure"],
                            "description": "Variable being controlled"
                        },
                        "sensor_tag": {"type": "string", "description": "Sensor/transmitter tag"},
                        "controller_tag": {"type": "string", "description": "Controller tag"},
                        "control_valve_tag": {"type": "string", "description": "Control valve tag"},
                        "sensing_location": {"type": "string", "description": "Equipment tag where sensor is located"},
                        "actuating_location": {"type": "string", "description": "Piping segment where valve is located"}
                    },
                    "required": ["model_id", "loop_tag", "controlled_variable", "sensor_tag", "controller_tag", "control_valve_tag"]
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
                name="dexpi_import_proteus_xml",
                description="Import P&ID model from Proteus 4.2 XML file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Directory path containing the XML file"},
                        "filename": {"type": "string", "description": "Name of the Proteus XML file"},
                        "model_id": {"type": "string", "description": "Optional ID for imported model"}
                    },
                    "required": ["directory_path", "filename"]
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
                            "enum": valve_types  # Dynamic from introspector
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
                name="dexpi_insert_valve_in_segment",
                description="Insert valve inline within an existing piping segment by splitting it",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "segment_id": {"type": "string", "description": "ID of segment to split"},
                        "valve_type": {
                            "type": "string",
                            "enum": valve_types  # Dynamic from introspector
                        },
                        "tag_name": {"type": "string"},
                        "at_position": {"type": "number", "description": "Position along segment (0.0 to 1.0)", "default": 0.5}
                    },
                    "required": ["model_id", "segment_id", "valve_type", "tag_name"]
                }
            ),
            # Schema tools removed - now handled by unified SchemaTools:
            # - dexpi_list_available_types -> use schema_list_classes
            # - dexpi_describe_class -> use schema_describe_class
            # - dexpi_list_class_attributes -> use schema_describe_class
            # Validation tools removed - now handled by unified ValidationTools:
            # - dexpi_check_connectivity -> use validate_model
            Tool(
                name="dexpi_convert_from_sfiles",
                description="Convert SFILES flowsheet to DEXPI P&ID model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {"type": "string", "description": "ID of SFILES flowsheet to convert"},
                        "model_id": {"type": "string", "description": "Optional ID for the created DEXPI model"}
                    },
                    "required": ["flowsheet_id"]
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
            "dexpi_add_control_loop": self._add_control_loop,
            "dexpi_connect_components": self._connect_components,
            "dexpi_validate_model": self._validate_model,
            "dexpi_export_json": self._export_json,
            "dexpi_export_graphml": self._export_graphml,
            "dexpi_import_json": self._import_json,
            "dexpi_import_proteus_xml": self._import_proteus_xml,
            "dexpi_add_valve": self._add_valve,
            "dexpi_insert_valve_in_segment": self._insert_valve_in_segment,
            # Removed duplicate handlers - now handled by SchemaTools and ValidationTools:
            # "dexpi_list_available_types": use schema_list_classes
            # "dexpi_check_connectivity": use validate_model
            # "dexpi_describe_class": use schema_describe_class
            # "dexpi_list_class_attributes": use schema_describe_class
            "dexpi_convert_from_sfiles": self._convert_from_sfiles,
            # Removed duplicate handlers:
            # - dexpi_validate_connections (now in ValidationTools)
            # - dexpi_validate_graph (now in ValidationTools)
            # - dexpi_save_to_project (now in ProjectTools)
            # - dexpi_load_from_project (now in ProjectTools)
            # - dexpi_init_project (now in ProjectTools)
            # - dexpi_list_project_models (now in ProjectTools)
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
        
        return success_response({
            "model_id": model_id,
            "project_name": args["project_name"],
            "drawing_number": args["drawing_number"]
        })
    
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
        
        return success_response({
            "equipment_type": equipment_type,
            "tag_name": tag_name,
            "model_id": model_id,
            "nozzles_created": len(nozzles)
        })
    
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
        """Add instrumentation to model with enhanced signal support."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        instrument_type = args["instrument_type"]
        tag_name = args["tag_name"]
        connected_equipment = args.get("connected_equipment")
        
        # Import instrumentation classes
        from pydexpi.dexpi_classes.instrumentation import (
            ProcessInstrumentationFunction,
            ProcessSignalGeneratingFunction,
            ProcessSignalGeneratingSystem
        )
        
        # Create instrumentation function
        instrument = ProcessInstrumentationFunction(
            tagName=tag_name,
            instrumentationType=instrument_type
        )
        
        # If this is a transmitter/sensor, create signal generating function
        if instrument_type in ["LevelTransmitter", "PressureTransmitter", "TemperatureTransmitter", "FlowTransmitter"]:
            signal_gen = ProcessSignalGeneratingFunction(
                tagName=f"{tag_name}_SG",
                signalType="4-20mA"
            )
            
            # Set sensing location if equipment is specified
            if connected_equipment:
                # Find the equipment
                if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                    for item in model.conceptualModel.taggedPlantItems:
                        if hasattr(item, 'tagName') and item.tagName == connected_equipment:
                            # Link to equipment nozzle if available
                            if hasattr(item, 'nozzles') and item.nozzles:
                                signal_gen.sensingLocation = item.nozzles[0]
                            break
            
            # Add signal generating function to instrumentation
            instrument.processSignalGeneratingFunctions = [signal_gen]
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.processInstrumentationFunctions:
            model.conceptualModel.processInstrumentationFunctions = []
        
        model.conceptualModel.processInstrumentationFunctions.append(instrument)
        
        return {
            "status": "success",
            "instrument_type": instrument_type,
            "tag_name": tag_name,
            "connected_equipment": connected_equipment,
            "model_id": model_id,
            "signal_generating": instrument_type.endswith("Transmitter")
        }
    
    async def _add_control_loop(self, args: dict) -> dict:
        """Add complete control loop with signal connections."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        # Import required classes
        from pydexpi.dexpi_classes.instrumentation import (
            ProcessInstrumentationFunction,
            ProcessControlFunction,
            ProcessSignalGeneratingFunction,
            ActuatingFunction,
            SignalConveyingFunction,
            MeasuringLineFunction,
            SignalLineFunction
        )
        from pydexpi.dexpi_classes.instrumentation import ActuatingSystem
        
        loop_tag = args["loop_tag"]
        controlled_variable = args["controlled_variable"]
        sensor_tag = args["sensor_tag"]
        controller_tag = args["controller_tag"]
        control_valve_tag = args["control_valve_tag"]
        sensing_location = args.get("sensing_location")
        actuating_location = args.get("actuating_location")
        
        # Create signal generating function (sensor/transmitter)
        signal_gen = ProcessSignalGeneratingFunction(
            tagName=sensor_tag,
            signalType="4-20mA",
            measuredVariable=controlled_variable
        )
        
        # Create control function (controller)
        controller = ProcessControlFunction(
            tagName=controller_tag,
            controllerType="PID",
            controlledVariable=controlled_variable
        )
        
        # Create actuating function (control valve)
        actuator = ActuatingFunction(
            tagName=control_valve_tag,
            actuatorType="ControlValve"
        )
        
        # Create signal connections
        # Measuring line from sensor to controller
        measuring_line = MeasuringLineFunction(
            tagName=f"{sensor_tag}_to_{controller_tag}",
            source=signal_gen,
            target=controller
        )
        
        # Signal line from controller to valve
        signal_line = SignalLineFunction(
            tagName=f"{controller_tag}_to_{control_valve_tag}",
            source=controller,
            target=actuator
        )
        
        # Create main instrumentation function for the loop
        loop_function = ProcessInstrumentationFunction(
            tagName=loop_tag,
            instrumentationType="ControlLoop",
            processSignalGeneratingFunctions=[signal_gen],
            processControlFunctions=[controller],
            actuatingFunctions=[actuator],
            signalConveyingFunctions=[measuring_line, signal_line]
        )
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.processInstrumentationFunctions:
            model.conceptualModel.processInstrumentationFunctions = []
        
        model.conceptualModel.processInstrumentationFunctions.append(loop_function)
        
        # Also add individual functions for visibility
        model.conceptualModel.processInstrumentationFunctions.extend([
            ProcessInstrumentationFunction(tagName=sensor_tag, instrumentationType=f"{controlled_variable}Transmitter"),
            ProcessInstrumentationFunction(tagName=controller_tag, instrumentationType=f"{controlled_variable}Controller"),
            ProcessInstrumentationFunction(tagName=control_valve_tag, instrumentationType="ControlValve")
        ])
        
        return success_response({
            "loop_tag": loop_tag,
            "controlled_variable": controlled_variable,
            "components": {
                "sensor": sensor_tag,
                "controller": controller_tag,
                "control_valve": control_valve_tag
            },
            "signal_connections": [
                f"{sensor_tag} -> {controller_tag} (measuring)",
                f"{controller_tag} -> {control_valve_tag} (control)"
            ],
            "model_id": model_id
        })
    
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
        
        return success_response({
            "from": from_component,
            "to": to_component,
            "line_number": line_number,
            "pipe_class": pipe_class,
            "model_id": model_id,
            "validation": validation_result
        })
    
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
        
        # Use validation_response for structured validation output
        status = "ok" if not issues else "warning"
        validation_issues = [create_issue("warning", issue) for issue in issues]
        
        return validation_response(
            status=status,
            issues=validation_issues,
            metrics={"validation_level": validation_level, "model_id": model_id}
        )
    
    async def _export_json(self, args: dict) -> dict:
        """Export model as JSON."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        # Use model_to_dict() to convert to dictionary, then to JSON string
        import json
        
        model_dict = self.json_serializer.model_to_dict(model)
        json_content = json.dumps(model_dict, indent=4, ensure_ascii=False, sort_keys=True)
        
        return success_response({
            "model_id": model_id,
            "json": json_content
        })
    
    async def _export_graphml(self, args: dict) -> dict:
        """Export model as GraphML."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        include_msr = args.get("include_msr", True)
        
        # Use UnifiedGraphConverter for consistent GraphML export with sanitization
        from ..converters.graph_converter import UnifiedGraphConverter
        converter = UnifiedGraphConverter()
        
        # Convert to GraphML with proper sanitization
        graphml_content = converter.dexpi_to_graphml(model, include_msr=include_msr)
        
        return success_response({
            "model_id": model_id,
            "include_msr": include_msr,
            "graphml": graphml_content
        })
    
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
        
        return success_response({
            "model_id": model_id,
            "project_name": model.metadata.projectData.projectName if model.metadata else "Unknown"
        })
    
    async def _import_proteus_xml(self, args: dict) -> dict:
        """Import model from Proteus XML using pyDEXPI's ProteusSerializer."""
        directory_path = args["directory_path"]
        filename = args["filename"]
        model_id = args.get("model_id", str(uuid4()))
        
        try:
            # Use pyDEXPI's ProteusSerializer to load the XML
            model = self.proteus_serializer.load(directory_path, filename)
            
            # Store model
            self.models[model_id] = model
            
            # Extract basic info from the loaded model
            project_name = "Unknown"
            drawing_number = "Unknown"
            if model.metaData:
                project_name = model.metaData.projectName or "Unknown"
                drawing_number = model.metaData.drawingNumber or "Unknown"
            
            # Count loaded elements
            equipment_count = 0
            piping_count = 0
            instrumentation_count = 0
            
            if model.conceptualModel:
                if model.conceptualModel.taggedPlantItems:
                    equipment_count = len(model.conceptualModel.taggedPlantItems)
                if model.conceptualModel.pipingNetworkSystems:
                    for system in model.conceptualModel.pipingNetworkSystems:
                        if hasattr(system, 'segments'):
                            piping_count += len(system.segments) if system.segments else 0
                if model.conceptualModel.processInstrumentationFunctions:
                    instrumentation_count = len(model.conceptualModel.processInstrumentationFunctions)
            
            return success_response({
                "model_id": model_id,
                "project_name": project_name,
                "drawing_number": drawing_number,
                "statistics": {
                    "equipment_count": equipment_count,
                    "piping_segments": piping_count,
                    "instrumentation_functions": instrumentation_count
                },
                "note": "Graphics elements are not parsed by pyDEXPI's ProteusSerializer"
            })
        except Exception as e:
            return error_response(
                f"Failed to import Proteus XML: {str(e)}",
                code="IMPORT_ERROR",
                details={"hint": "Ensure the file is a valid Proteus 4.2 XML file"}
            )
    
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
    
    async def _insert_valve_in_segment(self, args: dict) -> dict:
        """Insert valve inline within an existing piping segment."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        segment_id = args["segment_id"]
        valve_type = args["valve_type"]
        tag_name = args["tag_name"]
        at_position = args.get("at_position", 0.5)
        
        # Import required classes
        from pydexpi.dexpi_classes import piping as piping_module
        from pydexpi.dexpi_classes.piping import (
            PipingNetworkSegment,
            PipingNode,
            Pipe
        )
        
        # Find the segment to split
        target_segment = None
        system = None
        
        if model.conceptualModel and model.conceptualModel.pipingNetworkSystems:
            for sys in model.conceptualModel.pipingNetworkSystems:
                if hasattr(sys, 'segments'):
                    for seg in sys.segments:
                        if hasattr(seg, 'id') and seg.id == segment_id:
                            target_segment = seg
                            system = sys
                            break
                if target_segment:
                    break
        
        if not target_segment:
            raise ValueError(f"Segment {segment_id} not found")
        
        # Get the valve class
        valve_class = getattr(piping_module, valve_type, None)
        if not valve_class:
            raise ValueError(f"Unknown valve type: {valve_type}")
        
        # Create valve instance
        valve = valve_class(
            pipingComponentName=tag_name,
            pipingClassCode=target_segment.pipingClassArtefact or "CS150"
        )
        
        # Create piping nodes for valve connections
        valve_inlet = PipingNode(
            id=f"{tag_name}_inlet",
            nominalDiameterRepresentation="DN50",
            nominalDiameterNumericalValueRepresentation="50"
        )
        valve_outlet = PipingNode(
            id=f"{tag_name}_outlet",
            nominalDiameterRepresentation="DN50",
            nominalDiameterNumericalValueRepresentation="50"
        )
        valve.nodes = [valve_inlet, valve_outlet]
        
        # Strategy: Keep the existing segment but add the valve to its items
        # The valve will be inline within the segment
        if not target_segment.items:
            target_segment.items = []
        
        # Insert valve at the specified position in the items list
        insert_index = int(len(target_segment.items) * at_position)
        target_segment.items.insert(insert_index, valve)
        
        # If the segment has pipes in connections, ensure they're preserved
        # This maintains the segment's connectivity
        
        return {
            "status": "success",
            "valve_type": valve_type,
            "tag_name": tag_name,
            "segment_id": segment_id,
            "insertion_position": at_position,
            "model_id": model_id,
            "note": "Valve inserted inline within segment"
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
                for system in model.conceptualModel.pipingNetworkSystems:
                    if not hasattr(system, 'segments'):
                        continue
                    for segment in system.segments:
                        # Check segment-level connections (sourceItem/targetItem on segment)
                        for nozzle in nozzles:
                            nozzle_id = getattr(nozzle, 'id', None)
                            # Check if nozzle is connected at segment level
                            if (hasattr(segment, 'sourceItem') and (segment.sourceItem == nozzle or segment.sourceItem == nozzle_id)) or \
                               (hasattr(segment, 'targetItem') and (segment.targetItem == nozzle or segment.targetItem == nozzle_id)):
                                connected_nozzles += 1
                        
                        # Also check connection-level references
                        if hasattr(segment, 'connections'):
                            for conn in segment.connections:
                                for nozzle in nozzles:
                                    # Check both object references and ID references
                                    nozzle_id = getattr(nozzle, 'id', None)
                                    if (hasattr(conn, 'sourceNode') and conn.sourceNode == nozzle) or \
                                       (hasattr(conn, 'targetNode') and conn.targetNode == nozzle) or \
                                       (hasattr(conn, 'sourceItem') and conn.sourceItem == nozzle_id) or \
                                       (hasattr(conn, 'targetItem') and conn.targetItem == nozzle_id):
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
        
        return success_response({
            "model_id": model_id,
            "connectivity": connectivity_report,
            "summary": {
                "total_equipment": total_equipment,
                "fully_connected": fully_connected,
                "partially_connected": len(connectivity_report["partial_connections"]),
                "unconnected": len(connectivity_report["unconnected_equipment"]),
                "connectivity_percentage": (fully_connected / total_equipment * 100) if total_equipment > 0 else 0
            }
        })
    
    # Project tool handlers removed - now handled by unified ProjectTools
    # The following methods are deprecated:
    # - _save_to_project
    # - _load_from_project  
    # - _init_project
    # - _list_project_models
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
    
    async def _describe_class(self, args: dict) -> dict:
        """Get detailed description of a pyDEXPI class."""
        class_name = args["class_name"]
        category = args.get("category", None)
        
        description = self.introspector.describe_class(class_name, category)
        
        if "error" in description:
            return {
                "status": "error",
                "error": description["error"]
            }
        
        return {
            "status": "success",
            "class_description": description
        }
    
    async def _list_class_attributes(self, args: dict) -> dict:
        """List all attributes for a specific pyDEXPI class."""
        class_name = args["class_name"]
        category = args["category"]
        
        attrs = self.introspector.get_class_attributes(class_name, category)
        
        if attrs is None:
            return {
                "status": "error",
                "error": f"Class {class_name} not found in category {category}"
            }
        
        return {
            "status": "success",
            "attributes": attrs
        }
    
    async def _convert_from_sfiles(self, args: dict) -> dict:
        """Convert SFILES flowsheet to DEXPI P&ID model."""
        try:
            from ..converters.sfiles_dexpi_mapper import SfilesDexpiMapper
        except ImportError:
            from converters.sfiles_dexpi_mapper import SfilesDexpiMapper
        from Flowsheet_Class.flowsheet import Flowsheet
        
        flowsheet_id = args["flowsheet_id"]
        model_id = args.get("model_id", None)
        
        # Use the flowsheet store from instance
        if flowsheet_id not in self.flowsheets:
            return {
                "status": "error",
                "error": f"Flowsheet {flowsheet_id} not found"
            }
        
        flowsheet = self.flowsheets[flowsheet_id]
        
        # Convert to DEXPI
        mapper = SfilesDexpiMapper()
        try:
            dexpi_model = mapper.sfiles_to_dexpi(flowsheet)
            
            # Store the model
            if not model_id:
                import uuid
                model_id = str(uuid.uuid4())
            
            self.models[model_id] = dexpi_model
            
            return {
                "status": "success",
                "model_id": model_id,
                "flowsheet_id": flowsheet_id,
                "equipment_count": len(dexpi_model.conceptualModel.taggedPlantItems) if dexpi_model.conceptualModel else 0,
                "segment_count": sum(
                    len(sys.segments) if hasattr(sys, 'segments') else 0
                    for sys in (dexpi_model.conceptualModel.pipingNetworkSystems or [])
                    if dexpi_model.conceptualModel
                )
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Conversion failed: {str(e)}"
            }
