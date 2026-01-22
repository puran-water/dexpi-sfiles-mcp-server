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
from pydexpi.dexpi_classes.instrumentation import ProcessInstrumentationFunction, ProcessSignalGeneratingFunction
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
        self.proteus_serializer = ProteusSerializer()
        self.graph_loader = MLGraphLoader()
        self.introspector = DexpiIntrospector()
    
    def get_tools(self) -> List[Tool]:
        """Return all DEXPI tools."""
        # Dynamically generate types from ComponentRegistry (Phase 2.2 - all 272 classes)
        from src.core.components import get_registry, ComponentType, ComponentCategory

        registry = get_registry()

        # Get all aliases AND class names for each component type (Codex fix)
        # This allows both SFILES aliases ('pump') and DEXPI class names ('CentrifugalPump')
        equipment_components = registry.get_all_by_type(ComponentType.EQUIPMENT)
        equipment_types = sorted(list(set(
            [c.sfiles_alias for c in equipment_components] +
            [c.dexpi_class.__name__ for c in equipment_components]
        )))

        # Get valve-specific types (both aliases and class names)
        valve_components = registry.get_all_by_category(ComponentCategory.VALVE)
        valve_types = sorted(list(set(
            [c.sfiles_alias for c in valve_components] +
            [c.dexpi_class.__name__ for c in valve_components]
        )))

        # Get all piping types (includes valves, flow measurement, fittings, etc.)
        piping_components = registry.get_all_by_type(ComponentType.PIPING)
        piping_types = sorted(list(set(
            [c.sfiles_alias for c in piping_components] +
            [c.dexpi_class.__name__ for c in piping_components]
        )))

        # Get instrumentation types (both aliases and class names)
        instrumentation_components = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
        instrumentation_types = sorted(list(set(
            [c.sfiles_alias for c in instrumentation_components] +
            [c.dexpi_class.__name__ for c in instrumentation_components]
        )))
        
        return [
            Tool(
                name="dexpi_create_pid",
                description="[Consolidated into model_create] Initialize a new DEXPI P&ID model with metadata. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description=f"[Available via model_tx_apply or direct call] Add equipment to the P&ID model (159 types available). "
                           f"Supports both SFILES aliases and DEXPI class names. "
                           f"Examples: 'pump' (CentrifugalPump), 'boiler' (Boiler), 'conveyor' (Conveyor), "
                           f"'steam_generator' (SteamGenerator), 'crusher' (Crusher). "
                           f"See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "equipment_type": {
                            "type": "string",
                            "enum": equipment_types,
                            "description": "Equipment type (SFILES alias or DEXPI class name). "
                                          "Examples: 'pump' (CentrifugalPump), 'boiler' (Boiler), "
                                          "'conveyor' (Conveyor), 'steam_generator' (SteamGenerator). "
                                          f"Total {len(equipment_types)} types available."
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
                description=f"[Available via model_tx_apply or direct call] Add piping component to the P&ID model (79 types available). "
                           f"Supports both SFILES aliases and DEXPI class names. "
                           f"Includes valves, flow measurement, connections, fittings, etc. "
                           f"Examples: 'pipe' (Pipe), 'electromagnetic_flow_meter' (ElectromagneticFlowMeter), "
                           f"'flange' (Flange), 'orifice_plate' (OrificeFlowMeter). "
                           f"See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "segment_id": {"type": "string"},
                        "piping_type": {
                            "type": "string",
                            "enum": piping_types,
                            "default": "pipe",
                            "description": "Piping component type (SFILES alias or DEXPI class name). "
                                          "Examples: 'pipe' (Pipe), 'electromagnetic_flow_meter' (ElectromagneticFlowMeter), "
                                          "'flange' (Flange), 'orifice_plate' (OrificeFlowMeter). "
                                          f"Total {len(piping_types)} types available."
                        },
                        "pipe_class": {"type": "string", "default": "CS150"},
                        "nominal_diameter": {"type": "number", "default": 50},
                        "material": {"type": "string", "default": "Carbon Steel"}
                    },
                    "required": ["model_id", "segment_id"]
                }
            ),
            Tool(
                name="dexpi_add_instrumentation",
                description=f"[Available via model_tx_apply or direct call] Add instrumentation to the P&ID model (34 types available). "
                           f"Supports both SFILES aliases and DEXPI class names. "
                           f"Examples: 'transmitter' (Transmitter), 'positioner' (Positioner), "
                           f"'actuator' (ControlledActuator), 'signal_conveying_function' (SignalConveyingFunction). "
                           f"See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "instrument_type": {
                            "type": "string",
                            "enum": instrumentation_types,
                            "description": "Instrument type (SFILES alias or DEXPI class name). "
                                          "Examples: 'transmitter' (Transmitter), 'positioner' (Positioner), "
                                          "'actuator' (ControlledActuator). "
                                          f"Total {len(instrumentation_types)} types available."
                        },
                        "tag_name": {"type": "string"},
                        "connected_equipment": {"type": "string", "description": "Tag of connected equipment"}
                    },
                    "required": ["model_id", "instrument_type", "tag_name"]
                }
            ),
            Tool(
                name="dexpi_add_control_loop",
                description="[Available via model_tx_apply or direct call] Add complete control loop with signal generating, control, and actuating functions. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description="[Available via model_tx_apply or direct call] Create piping connections between equipment and instruments. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description="[Available via model_tx_apply or direct call] Validate P&ID for engineering rules and referential integrity. NOTE: Requires at least one piping connection (will fail with 'null graph' error on models with no connections). See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description="[Consolidated into model_save] Export P&ID model as JSON. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description="[Consolidated into model_save] Export P&ID topology as machine-readable GraphML. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description="[Consolidated into model_load] Import P&ID model from JSON. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description="[Consolidated into model_load] Import P&ID model from Proteus 4.2 XML file. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
                description=f"[DEPRECATED] Add valve to the P&ID model - Use dexpi_add_valve_between_components instead. "
                           f"22 valve types available.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "valve_type": {
                            "type": "string",
                            "enum": valve_types,
                            "description": "Valve type (SFILES alias or DEXPI class name). "
                                          "Examples: 'ball_valve' (BallValve), 'butterfly_valve' (ButterflyValve), "
                                          "'safety_valve' (SpringLoadedGlobeSafetyValve), 'needle_valve' (NeedleValve). "
                                          f"Total {len(valve_types)} types available."
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
                name="dexpi_add_valve_between_components",
                description=f"[Available via model_tx_apply or direct call] Add a valve between two components (22 valve types available). "
                           f"Supports both SFILES aliases and DEXPI class names. "
                           f"Examples: 'ball_valve' (BallValve), 'butterfly_valve' (ButterflyValve), "
                           f"'safety_valve' (SpringLoadedGlobeSafetyValve), 'check_valve' (CheckValve). "
                           f"See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "from_component": {"type": "string", "description": "Tag of source component"},
                        "to_component": {"type": "string", "description": "Tag of target component"},
                        "valve_type": {
                            "type": "string",
                            "enum": valve_types,
                            "description": "Valve type (SFILES alias or DEXPI class name). "
                                          "Examples: 'ball_valve' (BallValve), 'butterfly_valve' (ButterflyValve), "
                                          "'safety_valve' (SpringLoadedGlobeSafetyValve). "
                                          f"Total {len(valve_types)} types available."
                        },
                        "valve_tag": {"type": "string", "description": "Tag for the valve"},
                        "line_number": {"type": "string", "description": "Optional line number (auto-generated if not provided)"},
                        "pipe_class": {"type": "string", "default": "CS150"},
                        "at_position": {"type": "number", "default": 0.5, "description": "Position along segment (0.0 to 1.0)"}
                    },
                    "required": ["model_id", "from_component", "to_component", "valve_type", "valve_tag"]
                }
            ),
            Tool(
                name="dexpi_insert_valve_in_segment",
                description=f"[Available via model_tx_apply or direct call] Insert valve inline within an existing piping segment (22 valve types available). "
                           f"Supports both SFILES aliases and DEXPI class names. "
                           f"See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "segment_id": {"type": "string", "description": "ID of segment to split"},
                        "valve_type": {
                            "type": "string",
                            "enum": valve_types,
                            "description": "Valve type (SFILES alias or DEXPI class name). "
                                          f"Total {len(valve_types)} types available."
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
                description="[Available via model_tx_apply or direct call] Convert SFILES flowsheet to DEXPI P&ID model. See docs/FEATURE_PARITY_MATRIX.md for migration guide.",
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
            "dexpi_add_valve_between_components": self._add_valve_between_components,
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
        
        # Create empty DEXPI model and ConceptualModel with metadata
        model = DexpiModel()
        model.conceptualModel = ConceptualModel(metaData=metadata)
        
        # Store model
        self.models[model_id] = model
        
        return success_response({
            "model_id": model_id,
            "project_name": args["project_name"],
            "drawing_number": args["drawing_number"]
        })
    
    async def _add_equipment(self, args: dict) -> dict:
        """Add equipment to P&ID model with mandatory nozzles.

        Phase 2.2: Supports all 159 equipment types from ComponentRegistry.
        Accepts both SFILES aliases (e.g., 'pump') and DEXPI class names (e.g., 'CentrifugalPump').
        Uses core equipment factory for type validation and nozzle creation.
        """
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        model = self.models[model_id]
        equipment_type = args["equipment_type"]
        tag_name = args["tag_name"]
        specs = args.get("specifications", {})
        nozzle_configs = args.get("nozzles", [])

        # Use core equipment factory (Phase 1 migration)
        from src.core.equipment import get_factory, UnknownEquipmentTypeError

        factory = get_factory()

        try:
            # Create equipment via core factory
            # Factory handles type validation and nozzle creation
            equipment = factory.create(
                equipment_type=equipment_type,
                tag=tag_name,
                params=specs,
                nozzles=nozzle_configs if nozzle_configs else None
            )
        except UnknownEquipmentTypeError as e:
            # Return error with available types for MCP client
            return error_response(
                f"Invalid equipment type '{equipment_type}'. {str(e)}"
            )

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
            "nozzles_created": len(equipment.nozzles) if hasattr(equipment, 'nozzles') else 0
        })
    
    async def _add_piping(self, args: dict) -> dict:
        """Add piping component to model (Phase 2.2 - supports all 79 piping types)."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        model = self.models[model_id]
        piping_type = args.get("piping_type", "pipe")

        # Use ComponentRegistry to create piping component (Phase 2.2)
        from src.core.components import get_registry, ComponentType

        registry = get_registry()
        component_def = registry.get_by_alias(piping_type)

        # If not found, try as DEXPI class name
        if not component_def:
            try:
                dexpi_class = registry.get_dexpi_class(piping_type)
                component_def = registry.get_by_class(dexpi_class)
            except Exception:
                return error_response(
                    f"Invalid piping type '{piping_type}'. "
                    f"Use ComponentRegistry to see available types."
                )

        # Validate it's a piping component
        if component_def.component_type != ComponentType.PIPING:
            return error_response(
                f"Type '{piping_type}' is not a piping component. "
                f"Expected ComponentType.PIPING, got {component_def.component_type}."
            )

        # Create the piping component instance
        piping_component = component_def.dexpi_class(
            nominalDiameter=args.get("nominal_diameter", 50),
            material=args.get("material", "Carbon Steel")
        )

        # Create piping segment
        segment = PipingNetworkSegment(
            id=args["segment_id"],
            pipingClassCode=args.get("pipe_class", "CS150")
        )

        # Use connections instead of pipingNetworkSegmentItems (which doesn't exist)
        from pydexpi.dexpi_classes.piping import PipingConnection, PipingNetworkSystem
        segment.connections = [PipingConnection(pipingItem=piping_component)]
        
        # Add to model within a PipingNetworkSystem
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        if not model.conceptualModel.pipingNetworkSystems:
            # Create a new piping network system
            system = PipingNetworkSystem(
                id=f"PNS_{args['segment_id']}",
                segments=[segment]
            )
            model.conceptualModel.pipingNetworkSystems = [system]
        else:
            # Add to existing system
            if hasattr(model.conceptualModel.pipingNetworkSystems[0], 'segments'):
                model.conceptualModel.pipingNetworkSystems[0].segments.append(segment)
            else:
                # Create new system if first one is invalid
                system = PipingNetworkSystem(
                    id=f"PNS_{args['segment_id']}",
                    segments=[segment]
                )
                model.conceptualModel.pipingNetworkSystems.append(system)
        
        return success_response({
            "segment_id": args["segment_id"],
            "piping_type": piping_type,
            "pipe_class": args.get("pipe_class", "CS150"),
            "model_id": model_id
        })
    
    async def _add_instrumentation(self, args: dict) -> dict:
        """Add instrumentation to P&ID model.

        Phase 2.2 FIX (Codex review): Now uses ComponentRegistry to instantiate actual pyDEXPI classes.
        Supports all 34 instrumentation types from ComponentRegistry.
        Accepts both SFILES aliases (e.g., 'transmitter') and DEXPI class names (e.g., 'Transmitter').
        Includes signal generating, control, and actuating functions.
        """
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        model = self.models[model_id]
        instrument_type = args["instrument_type"]
        tag_name = args["tag_name"]
        connected_equipment = args.get("connected_equipment")

        # Use ComponentRegistry to create instrumentation component (Codex fix)
        from src.core.components import get_registry, ComponentType

        registry = get_registry()

        # Map legacy instrument type names to ComponentRegistry aliases for backward compatibility
        legacy_mappings = {
            "LevelTransmitter": "transmitter",
            "PressureTransmitter": "transmitter",
            "TemperatureTransmitter": "transmitter",
            "FlowTransmitter": "transmitter",
            "FlowDetector": "flow_detector",
            "ControlledActuator": "controlled_actuator",
            "Positioner": "positioner",
        }

        # Apply legacy mapping if needed
        lookup_type = legacy_mappings.get(instrument_type, instrument_type)
        component_def = registry.get_by_alias(lookup_type)

        # If not found, try as DEXPI class name
        if not component_def:
            try:
                dexpi_class = registry.get_dexpi_class(lookup_type)
                component_def = registry.get_by_class(dexpi_class)
            except Exception:
                # Fallback to ProcessInstrumentationFunction for unknown legacy types
                from pydexpi import ProcessInstrumentationFunction
                instrument = ProcessInstrumentationFunction(
                    tagName=tag_name,
                    instrumentationType=instrument_type
                )
                model.processInstrumentationFunctions.append(instrument)

                return success_response(
                    message=f"Added instrumentation {tag_name} (fallback to ProcessInstrumentationFunction)",
                    data={"tag_name": tag_name, "type": instrument_type, "class": "ProcessInstrumentationFunction"}
                )

        # Validate it's an instrumentation component
        if component_def.component_type != ComponentType.INSTRUMENTATION:
            return error_response(
                f"Type '{instrument_type}' is not an instrumentation component. "
                f"Expected ComponentType.INSTRUMENTATION, got {component_def.component_type}."
            )

        # Create the actual pyDEXPI instrumentation instance
        instrument = component_def.dexpi_class(
            tagName=tag_name
        )

        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()

        if not model.conceptualModel.processInstrumentationFunctions:
            model.conceptualModel.processInstrumentationFunctions = []

        # PHASE 2.3 FIX: Use instrumentation_toolkit when connecting to equipment
        # This creates proper signal connections like _add_control_loop does
        signal_connection_created = False
        if connected_equipment:
            try:
                from pydexpi.toolkits import instrumentation_toolkit as it
                from pydexpi.dexpi_classes.instrumentation import (
                    ProcessInstrumentationFunction,
                    ProcessSignalGeneratingFunction,
                    MeasuringLineFunction
                )

                # Create a parent ProcessInstrumentationFunction if this is a transmitter
                is_transmitter = (
                    "transmitter" in instrument_type.lower() or
                    instrument_type in ["LevelTransmitter", "PressureTransmitter",
                                       "TemperatureTransmitter", "FlowTransmitter"]
                )

                if is_transmitter:
                    # Create signal generating function for transmitter
                    signal_gen = ProcessSignalGeneratingFunction(
                        tagName=tag_name,
                        signalType="4-20mA"
                    )

                    # Create measuring line
                    measuring_line = MeasuringLineFunction(
                        id=f"measuring_line_{tag_name}"
                    )

                    # Create parent loop function
                    loop_function = ProcessInstrumentationFunction(
                        id=f"loop_{tag_name}"
                    )

                    # Use toolkit to establish connection
                    it.add_signal_generating_function_to_instrumentation_function(
                        loop_function, signal_gen, measuring_line
                    )

                    model.conceptualModel.processInstrumentationFunctions.append(loop_function)
                    signal_connection_created = True
                else:
                    # For non-transmitters, just append to the list
                    model.conceptualModel.processInstrumentationFunctions.append(instrument)

            except ImportError as e:
                logger.warning(f"instrumentation_toolkit not available: {e}")
                model.conceptualModel.processInstrumentationFunctions.append(instrument)
            except Exception as e:
                logger.warning(f"Failed to create signal connection: {e}")
                model.conceptualModel.processInstrumentationFunctions.append(instrument)
        else:
            model.conceptualModel.processInstrumentationFunctions.append(instrument)

        # Check if this is a transmitter for backward compatibility
        is_transmitter = instrument_type in ["LevelTransmitter", "PressureTransmitter", "TemperatureTransmitter", "FlowTransmitter"] or "transmitter" in instrument_type.lower()

        return success_response({
            "instrument_type": instrument_type,
            "tag_name": tag_name,
            "connected_equipment": connected_equipment,
            "model_id": model_id,
            "pyDEXPI_class": component_def.dexpi_class.__name__,
            "signal_generating": is_transmitter,
            "signal_connection_created": signal_connection_created
        })
    
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
        
        # Create signal connections using instrumentation_toolkit
        # This provides automatic validation and consistency checks
        from pydexpi.toolkits import instrumentation_toolkit as it

        # Measuring line from sensor to controller
        measuring_line = MeasuringLineFunction(
            id=f"measuring_line_{sensor_tag}_to_{controller_tag}"
        )

        # Signal line from controller to valve
        signal_line = SignalLineFunction(
            id=f"signal_line_{controller_tag}_to_{control_valve_tag}"
        )
        
        # Add to model
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        # Initialize collections if needed
        if not model.conceptualModel.processInstrumentationFunctions:
            model.conceptualModel.processInstrumentationFunctions = []
        
        # Create main instrumentation function for the loop
        # Note: Components and signal lines are added by toolkit calls below
        # The toolkit adds them to the appropriate collections AND sets source/target
        # Use ID with loop_tag for identification (ProcessInstrumentationFunction has no tagName field)
        loop_function = ProcessInstrumentationFunction(
            id=loop_tag,
            processControlFunctions=[controller]  # Only controller goes in constructor
        )

        # Use toolkit to establish validated signal connections
        # This adds proper source/target references AND adds lines to loop.signalConveyingFunctions
        # CRITICAL: Pass loop_function (ProcessInstrumentationFunction), not controller
        it.add_signal_generating_function_to_instrumentation_function(
            loop_function, signal_gen, measuring_line
        )
        it.add_actuating_function_to_instrumentation_function(
            loop_function, actuator, signal_line
        )

        model.conceptualModel.processInstrumentationFunctions.append(loop_function)
        
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
        
        # Import piping toolkit and model toolkit for component lookup
        from pydexpi.toolkits import piping_toolkit, model_toolkit as mt
        from pydexpi.dexpi_classes.piping import (
            PipingNetworkSegment,
            PipingNetworkSystem,
            PipingConnection,
            Pipe,
            PipingNode
        )

        # Helper function to find any component (equipment or valve) by tag name
        # Uses model_toolkit for more robust attribute-based search
        def _find_component_by_tag(tag_name: str):
            """Search for a component using model_toolkit attribute search."""
            # First search by tagName attribute
            matches = mt.get_instances_with_attribute(
                model,
                attribute_name="tagName",
                target_value=tag_name
            )
            if matches:
                return matches[0]

            # Fallback: search by pipingComponentName (for piping components)
            matches = mt.get_instances_with_attribute(
                model,
                attribute_name="pipingComponentName",
                target_value=tag_name
            )
            return matches[0] if matches else None
        
        # Find components (equipment or valves) by tag name
        from_equipment = _find_component_by_tag(from_component)
        to_equipment = _find_component_by_tag(to_component)
        
        if not from_equipment:
            raise ValueError(f"Component '{from_component}' not found (searched equipment and valves)")
        if not to_equipment:
            raise ValueError(f"Component '{to_component}' not found (searched equipment and valves)")
        
        # Track nozzles used in this connection operation
        # Note: pyDEXPI Nozzle class has 'nodes' attribute, not 'pipingConnection'
        _used_nozzles_in_model = getattr(model, '_used_nozzles', set())
        model._used_nozzles = _used_nozzles_in_model

        # Helper to check if a nozzle is already used in a piping connection
        def _nozzle_is_connected(noz) -> bool:
            if noz is None:
                return False
            # Use tracking set since Nozzle doesn't have pipingConnection attribute
            return id(noz) in _used_nozzles_in_model

        # Helper to find an available nozzle or create a new one
        def _get_or_create_nozzle(equipment, tag_prefix: str, prefer_end: str = "last"):
            if not hasattr(equipment, 'nozzles') or equipment.nozzles is None:
                equipment.nozzles = []

            # Try to reuse an existing unconnected nozzle
            # Prefer order based on expected flow direction
            ordered = (
                list(equipment.nozzles)[::-1] if prefer_end == "last" else list(equipment.nozzles)
            )
            for noz in ordered:
                if not _nozzle_is_connected(noz):
                    # Mark as used before returning
                    _used_nozzles_in_model.add(id(noz))
                    return noz

            # If all existing nozzles are used, create a new one
            next_index = len(equipment.nozzles) + 1
            new_nozzle = Nozzle(
                id=f"nozzle_{tag_prefix}_{equipment.tagName}_{next_index}",
                subTagName=f"{tag_prefix}{next_index}"
            )
            equipment.nozzles.append(new_nozzle)
            # Mark the new nozzle as used
            _used_nozzles_in_model.add(id(new_nozzle))
            return new_nozzle

        # Get source (from) nozzle: prefer last (often outlet)
        from_nozzle = _get_or_create_nozzle(from_equipment, tag_prefix="N_OUT_", prefer_end="last")

        # Get target (to) nozzle: prefer first (often inlet). Create new if needed.
        to_nozzle = _get_or_create_nozzle(to_equipment, tag_prefix="N_IN_", prefer_end="first")
        
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
            pipingClassCode=pipe_class
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
            "segment_id": f"segment_{line_number}",  # Add segment_id for inline valve insertion
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
        if not model.conceptualModel or not model.conceptualModel.metaData:
            issues.append("Missing metadata")
        
        if not model.conceptualModel:
            issues.append("Empty conceptual model")
        else:
            if not model.conceptualModel.taggedPlantItems:
                issues.append("No equipment defined")
        
        # Comprehensive validation would include graph validation
        # PHASE 2.2 FIX: Standardize on MLGraphLoader behavior
        if validation_level == "comprehensive":
            try:
                # Convert to graph using MLGraphLoader
                graph = self.graph_loader.dexpi_to_graph(model)

                # Validate graph format - handle different API signatures
                if hasattr(self.graph_loader, 'validate_graph_format'):
                    # Try without args first (newer API)
                    try:
                        self.graph_loader.validate_graph_format()
                    except TypeError:
                        # Fall back to passing graph (older API)
                        self.graph_loader.validate_graph_format(graph)

                # Additional topology checks
                import networkx as nx
                if not nx.is_weakly_connected(graph):
                    issues.append(f"Graph has {nx.number_weakly_connected_components(graph)} disconnected components")
                if list(nx.isolates(graph)):
                    issues.append(f"Graph has {len(list(nx.isolates(graph)))} isolated nodes")

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
        """
        Import model from JSON.

        Handles both raw JSON strings and double-encoded strings from MCP responses.
        Uses in-memory parsing to avoid temp file issues.
        """
        import json

        json_content = args["json_content"]
        model_id = args.get("model_id", str(uuid4()))

        # Fast path: If already valid JSON object, skip double-encoding check
        stripped = json_content.strip()
        if not (stripped.startswith('{') or stripped.startswith('[')):
            # Detect and handle double-encoded JSON (from MCP response wrapping)
            # If content starts/ends with quotes or contains literal \n, it's double-encoded
            if (json_content.startswith('"') and json_content.endswith('"')) or '\\n' in json_content:
                try:
                    # First decode to get the actual JSON string
                    json_content = json.loads(json_content)
                    logger.info("Detected and unwrapped double-encoded JSON")
                except json.JSONDecodeError:
                    # If that fails, assume it's actually single-encoded
                    pass

        # Parse JSON string to dict
        try:
            model_dict = json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return error_response(
                f"Invalid JSON format: {str(e)}",
                "JSON_PARSE_ERROR",
                details={"error": str(e)}
            )

        # Convert dict to DEXPI model using pyDEXPI's dict_to_model
        try:
            model = self.json_serializer.dict_to_model(model_dict)
        except Exception as e:
            logger.error(f"Failed to convert dict to DEXPI model: {e}")
            return error_response(
                f"Failed to construct DEXPI model from JSON: {str(e)}",
                "MODEL_CONSTRUCTION_ERROR",
                details={"error": str(e)}
            )

        # Store model
        self.models[model_id] = model

        return success_response({
            "model_id": model_id,
            "project_name": model.conceptualModel.metaData.projectName if model.conceptualModel and model.conceptualModel.metaData else "Unknown"
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
            if model.conceptualModel and model.conceptualModel.metaData:
                project_name = model.conceptualModel.metaData.projectName or "Unknown"
                drawing_number = model.conceptualModel.metaData.drawingNumber or "Unknown"
            
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
        """
        Add valve to P&ID model.
        
        DEPRECATED: This creates an isolated valve that cannot be connected properly.
        Use 'dexpi_add_valve_between_components' or 'dexpi_insert_valve_in_segment' instead.
        """
        import warnings
        warnings.warn(
            "dexpi_add_valve is deprecated. Valves cannot be connected as standalone components. "
            "Use 'dexpi_add_valve_between_components' to add a valve between two components, "
            "or connect components first then use 'dexpi_insert_valve_in_segment'.",
            DeprecationWarning,
            stacklevel=2
        )
        
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        valve_type = args["valve_type"]
        tag_name = args["tag_name"]
        piping_class = args.get("piping_class", "CS150")
        nominal_diameter = args.get("nominal_diameter", "DN50")
        operation = args.get("operation", "manual")

        # Use ComponentRegistry to resolve valve type (supports both aliases and class names)
        from src.core.components import get_registry, ComponentCategory

        registry = get_registry()
        component_def = registry.get_by_alias(valve_type)

        # If not found by alias, try as DEXPI class name
        if not component_def:
            try:
                dexpi_class = registry.get_dexpi_class(valve_type)
                component_def = registry.get_by_class(dexpi_class)
            except Exception:
                raise ValueError(
                    f"Unknown valve type: {valve_type}. "
                    f"Use either SFILES alias (e.g., 'gate_valve') or DEXPI class name (e.g., 'GateValve')."
                )

        # Validate it's a valve component
        if component_def.category != ComponentCategory.VALVE:
            raise ValueError(
                f"Type '{valve_type}' is not a valve. "
                f"Expected ComponentCategory.VALVE, got {component_def.category}."
            )

        valve_class = component_def.dexpi_class
        
        # Create valve instance with tagName for consistency
        # Don't pass operation parameter since it causes validation errors
        valve_kwargs = {
            "tagName": tag_name,  # Use tagName for consistency with equipment
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
            pipingClassCode=piping_class
        )
        # Valves are PipingNetworkSegmentItems, so they go in items
        segment.items = [valve]
        segment.connections = []  # No connections yet
        
        system.segments.append(segment)
        
        return success_response({
            "valve_type": valve_type,
            "tag_name": tag_name,
            "model_id": model_id,
            "operation": operation
        })
    
    async def _add_valve_between_components(self, args: dict) -> dict:
        """Add a valve between two components by connecting them first, then inserting the valve."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        from_component = args["from_component"]
        to_component = args["to_component"]
        valve_type = args["valve_type"]
        valve_tag = args["valve_tag"]
        line_number = args.get("line_number", f"{from_component}_to_{to_component}")
        pipe_class = args.get("pipe_class", "CS150")
        at_position = args.get("at_position", 0.5)  # Position along the segment for valve
        
        # Step 1: Connect the two components first to create a segment
        connect_result = await self._connect_components({
            "model_id": model_id,
            "from_component": from_component,
            "to_component": to_component,
            "line_number": line_number,
            "pipe_class": pipe_class
        })
        
        if not connect_result.get("ok"):
            return error_response(f"Failed to connect components: {connect_result.get('error', 'Unknown error')}")
        
        # Step 2: Get the segment_id from the connection
        segment_id = connect_result.get("data", {}).get("segment_id")
        if not segment_id:
            return error_response("Failed to get segment_id from connection")
        
        # Step 3: Insert the valve into the created segment
        insert_result = await self._insert_valve_in_segment({
            "model_id": model_id,
            "segment_id": segment_id,
            "valve_type": valve_type,
            "tag_name": valve_tag,
            "at_position": at_position
        })
        
        if not insert_result.get("ok"):
            return error_response(f"Failed to insert valve: {insert_result.get('error', 'Unknown error')}")
        
        return success_response({
            "from_component": from_component,
            "to_component": to_component,
            "valve_tag": valve_tag,
            "valve_type": valve_type,
            "line_number": line_number,
            "segment_id": segment_id,
            "model_id": model_id,
            "message": f"Successfully connected {from_component} to {to_component} with {valve_tag} valve"
        })
    
    async def _insert_valve_in_segment(self, args: dict) -> dict:
        """Insert valve inline within an existing piping segment using pyDEXPI's piping_toolkit."""
        model_id = args["model_id"]
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        segment_id = args["segment_id"]
        valve_type = args["valve_type"]
        tag_name = args["tag_name"]
        at_position = args.get("at_position", 0.5)
        
        # Import required classes and toolkit
        from pydexpi.dexpi_classes.piping import (
            PipingNetworkSegment,
            PipingNode,
            Pipe
        )
        from pydexpi.toolkits import piping_toolkit as pt

        # Use ComponentRegistry to resolve valve type (supports both aliases and class names)
        from src.core.components import get_registry, ComponentCategory

        registry = get_registry()
        component_def = registry.get_by_alias(valve_type)

        # If not found by alias, try as DEXPI class name
        if not component_def:
            try:
                dexpi_class = registry.get_dexpi_class(valve_type)
                component_def = registry.get_by_class(dexpi_class)
            except Exception:
                raise ValueError(
                    f"Unknown valve type: {valve_type}. "
                    f"Use either SFILES alias (e.g., 'gate_valve') or DEXPI class name (e.g., 'GateValve')."
                )

        # Validate it's a valve component
        if component_def.category != ComponentCategory.VALVE:
            raise ValueError(
                f"Type '{valve_type}' is not a valve. "
                f"Expected ComponentCategory.VALVE, got {component_def.category}."
            )

        valve_class = component_def.dexpi_class

        # Find the segment to modify
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
        
        # Create valve instance with nodes
        valve = valve_class(
            id=f"valve_{tag_name}",
            tagName=tag_name
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
        
        # Create a new pipe connection for the valve
        new_pipe = Pipe(
            id=f"pipe_after_{tag_name}",
            tagName=f"pipe_after_{tag_name}"
        )
        
        # Use pyDEXPI's insert_item_to_segment function
        # This properly handles all the connections and updates
        if target_segment.connections and len(target_segment.connections) > 0:
            # Segment has connections - it's already connected to equipment
            # We need to insert the valve inline
            
            # For a connected segment with just a pipe and no items yet,
            # we insert at position 0 (the first/only connection)
            if not target_segment.items or len(target_segment.items) == 0:
                # No items yet - insert valve at the beginning
                insert_position = 0
            else:
                # Has items - insert relative to existing items count
                insert_position = min(int(len(target_segment.items) * at_position), 
                                     len(target_segment.items))
            
            # Use insert_item_to_segment which works with connected segments
            pt.insert_item_to_segment(
                the_segment=target_segment,
                position=insert_position,  # Position in connections list
                the_item=valve,
                the_connection=new_pipe,
                item_source_node_index=0,  # Inlet is node 0
                item_target_node_index=1,  # Outlet is node 1
                insert_before=True  # Insert before the position
            )
            
            message = f"Valve inserted inline in segment"
        else:
            # If segment has no connections yet, just add the valve as an item
            if not target_segment.items:
                target_segment.items = []
            target_segment.items.append(valve)
            message = "Valve added to segment (segment had no connections)"
        
        return success_response({
            "valve_type": valve_type,
            "tag_name": tag_name,
            "segment_id": segment_id,
            "insertion_position": at_position,
            "model_id": model_id,
            "message": message
        })
    
    async def _list_available_types(self, args: dict) -> dict:
        """List all available element types using ComponentRegistry."""
        category = args.get("category", "all")

        # Use ComponentRegistry for type enumeration
        from src.core.components import get_registry, ComponentType, ComponentCategory
        registry = get_registry()

        result = {}

        if category in ["all", "equipment"]:
            defs = registry.get_all_by_type(ComponentType.EQUIPMENT)
            result["equipment"] = sorted([d.dexpi_class.__name__ for d in defs])

        if category in ["all", "valves"]:
            defs = registry.get_all_by_category(ComponentCategory.VALVE)
            result["valves"] = sorted([d.dexpi_class.__name__ for d in defs])

        if category in ["all", "piping"]:
            defs = registry.get_all_by_type(ComponentType.PIPING)
            result["piping"] = sorted([d.dexpi_class.__name__ for d in defs])

        if category in ["all", "instrumentation"]:
            defs = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
            result["instrumentation"] = sorted([d.dexpi_class.__name__ for d in defs])

        # Also include equipment that support nozzles (using nozzle_count_default > 0)
        if category in ["all", "equipment"]:
            defs = registry.get_all_by_type(ComponentType.EQUIPMENT)
            result["equipment_with_nozzles"] = sorted([
                d.dexpi_class.__name__ for d in defs if d.nozzle_count_default > 0
            ])

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
    # Schema introspection methods removed - now handled by unified SchemaTools
    async def _convert_from_sfiles(self, args: dict) -> dict:
        """Convert SFILES flowsheet to DEXPI P&ID model.

        Phase 1 Migration: Now uses core conversion engine instead of legacy mapper.
        """
        # Use safe import adapter for SFILES2
        from ..adapters.sfiles_adapter import get_flowsheet_class
        Flowsheet = get_flowsheet_class()
        
        flowsheet_id = args["flowsheet_id"]
        model_id = args.get("model_id", None)
        
        # Use the flowsheet store from instance
        if flowsheet_id not in self.flowsheets:
            return {
                "status": "error",
                "error": f"Flowsheet {flowsheet_id} not found"
            }
        
        flowsheet = self.flowsheets[flowsheet_id]

        # Convert to DEXPI (Phase 1 migration: use core engine)
        from src.core.conversion import get_engine

        engine = get_engine()
        try:
            # Handle SFILES2 API: flowsheet.convert_to_sfiles() sets flowsheet.sfiles
            if hasattr(flowsheet, 'sfiles') and flowsheet.sfiles:
                sfiles_string = flowsheet.sfiles
            elif hasattr(flowsheet, 'convert_to_sfiles'):
                flowsheet.convert_to_sfiles()
                sfiles_string = flowsheet.sfiles
            else:
                # Fallback: try str(flowsheet)
                sfiles_string = str(flowsheet)

            # Parse SFILES and convert to DEXPI via core engine
            sfiles_model = engine.parse_sfiles(sfiles_string)
            dexpi_model = engine.sfiles_to_dexpi(sfiles_model)
            
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
