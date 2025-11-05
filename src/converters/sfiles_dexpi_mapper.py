"""Bidirectional mapper between SFILES and DEXPI formats."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from ..adapters.sfiles_adapter import get_flowsheet_class

# Safe import with helpful error messages
Flowsheet = get_flowsheet_class()

from pydexpi.dexpi_classes.equipment import (
    Tank, CentrifugalPump, HeatExchanger, ProcessColumn,
    Equipment, Vessel, Nozzle
)
from pydexpi.dexpi_classes.piping import (
    PipingNetworkSystem, PipingNetworkSegment, 
    Pipe, PipingNode, ElectromagneticFlowMeter,
    CustomInlinePrimaryElement
)
from pydexpi.dexpi_classes.instrumentation import (
    ProcessInstrumentationFunction, ProcessControlFunction,
    ProcessSignalGeneratingFunction, ActuatingFunction
)
from pydexpi.dexpi_classes.pydantic_classes import CustomStringAttribute
from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.toolkits import piping_toolkit as pt
import networkx as nx

logger = logging.getLogger(__name__)


class SfilesDexpiMapper:
    """Maps between SFILES notation and DEXPI P&ID models."""
    
    def __init__(self):
        """Initialize the mapper with token mappings."""
        # SFILES unit type to DEXPI equipment class mapping
        self.unit_to_equipment = {
            'feed': Tank,
            'product': Tank,
            'tank': Tank,
            'pump': CentrifugalPump,
            'hex': HeatExchanger,
            'heater': HeatExchanger,
            'cooler': HeatExchanger,
            'distcol': ProcessColumn,
            'column': ProcessColumn,
            'reactor': Vessel,
            'separator': Vessel,
            'vessel': Vessel
        }
        
        # DEXPI equipment class to SFILES unit type mapping (reverse)
        self.equipment_to_unit = {
            'Tank': 'tank',
            'CentrifugalPump': 'pump',
            'HeatExchanger': 'hex',
            'ProcessColumn': 'distcol',
            'Vessel': 'vessel',
            'Reactor': 'reactor',
            'Separator': 'separator'
        }
        
        # Control type mappings
        self.control_to_instrumentation = {
            'FC': 'Flow',
            'LC': 'Level',
            'TC': 'Temperature',
            'PC': 'Pressure'
        }
    
    def sfiles_to_dexpi(self, flowsheet: Flowsheet) -> DexpiModel:
        """Convert SFILES flowsheet to DEXPI P&ID model.
        
        Args:
            flowsheet: SFILES flowsheet object
            
        Returns:
            DexpiModel with equipment, piping, and instrumentation
        """
        # Create new DEXPI model
        model = DexpiModel()
        model.conceptualModel = ConceptualModel()
        model.conceptualModel.taggedPlantItems = []
        model.conceptualModel.pipingNetworkSystems = []
        model.conceptualModel.processInstrumentationFunctions = []
        
        # Track equipment for connection mapping
        equipment_map = {}
        
        # Convert units to equipment
        for node_id, node_data in flowsheet.state.nodes(data=True):
            # Determine if it's a control unit
            # Controls are marked with unit_type="Control" or have control_type attribute
            is_control = (node_data.get('unit_type') == 'Control' or 
                         'control_type' in node_data or
                         (isinstance(node_id, str) and node_id.startswith("C-")))
            
            if not is_control:
                # Infer unit type from node name or data
                unit_type = node_data.get('unit_type')
                if not unit_type:
                    # Parse from node name (e.g., "tank-1" -> "tank")
                    if isinstance(node_id, str):
                        if '-' in node_id:
                            unit_type = node_id.split('-')[0]
                        else:
                            unit_type = node_id  # e.g., "raw", "prod"
                
                # Skip creating equipment for raw/prod nodes
                if unit_type not in ['raw', 'prod', 'IO']:
                    equipment = self._create_equipment_from_unit(
                        node_id, 
                        unit_type or 'vessel',
                        node_data
                    )
                    if equipment:
                        model.conceptualModel.taggedPlantItems.append(equipment)
                        equipment_map[node_id] = equipment
        
        # Create piping system
        piping_system = PipingNetworkSystem(
            id="main_piping_system",
            segments=[]
        )
        model.conceptualModel.pipingNetworkSystems.append(piping_system)
        
        # Convert streams to piping segments
        for edge_id, (from_node, to_node, edge_data) in enumerate(flowsheet.state.edges(data=True)):
            if from_node in equipment_map and to_node in equipment_map:
                segment = self._create_piping_segment(
                    f"segment_{edge_id}",
                    equipment_map[from_node],
                    equipment_map[to_node],
                    edge_data
                )
                if segment:
                    piping_system.segments.append(segment)
        
        # Convert controls to instrumentation
        for node_id, node_data in flowsheet.state.nodes(data=True):
            # Check if it's a control - using updated detection logic
            is_control = (node_data.get('unit_type') == 'Control' or 
                         'control_type' in node_data or
                         (isinstance(node_id, str) and node_id.startswith("C-")))
            
            if is_control:
                # Get control type from node data (stored as metadata)
                control_type = node_data.get('control_type', 'FC')
                
                # Find connected unit by checking edges with signal tags
                connected_unit = None
                edge_attrs = nx.get_edge_attributes(flowsheet.state, 'tags')
                for (u, v), tags in edge_attrs.items():
                    # Look for measurement signal edges going to the control
                    if v == node_id and tags.get('signal') == ["not_next_unitop"]:
                        connected_unit = u
                        break
                
                # If no signal edge found, fall back to any edge
                if not connected_unit:
                    for u, v in flowsheet.state.edges():
                        if v == node_id:
                            connected_unit = u
                            break
                
                if connected_unit and connected_unit in equipment_map:
                    instrumentation = self._create_instrumentation_from_control(
                        node_id,
                        control_type,
                        equipment_map[connected_unit]
                    )
                    if instrumentation:
                        model.conceptualModel.processInstrumentationFunctions.append(
                            instrumentation
                        )
        
        return model
    
    def dexpi_to_sfiles(self, model: DexpiModel) -> Flowsheet:
        """Convert DEXPI P&ID model to SFILES flowsheet.
        
        Args:
            model: DEXPI model with equipment and piping
            
        Returns:
            Flowsheet object with units and streams
        """
        flowsheet = Flowsheet()
        
        # Track equipment to node ID mapping
        node_map = {}
        
        # Convert equipment to units
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            for equipment in model.conceptualModel.taggedPlantItems:
                unit_type = self._get_unit_type_from_equipment(equipment)
                tag_name = getattr(equipment, 'tagName', f"unit_{len(node_map)}")
                
                # Add unit to flowsheet with proper parameter names
                flowsheet.add_unit(unique_name=tag_name, unit_type=unit_type)
                node_map[equipment] = tag_name
        
        # Convert piping segments to streams
        if model.conceptualModel and model.conceptualModel.pipingNetworkSystems:
            for system in model.conceptualModel.pipingNetworkSystems:
                if hasattr(system, 'segments'):
                    for segment in system.segments:
                        # Find source and target equipment
                        source_equipment = self._find_connected_equipment(
                            segment, 'source', model
                        )
                        target_equipment = self._find_connected_equipment(
                            segment, 'target', model
                        )
                        
                        if source_equipment and target_equipment:
                            if source_equipment in node_map and target_equipment in node_map:
                                flowsheet.add_stream(
                                    node1=node_map[source_equipment],
                                    node2=node_map[target_equipment]
                                )
        
        # Convert instrumentation to controls
        if model.conceptualModel and model.conceptualModel.processInstrumentationFunctions:
            for idx, pif in enumerate(model.conceptualModel.processInstrumentationFunctions):
                control_type = self._get_control_type_from_instrumentation(pif)
                original_tag = getattr(pif, 'tagName', f"control_{idx+1}")
                
                # For canonical SFILES, use simple C-# notation
                # The control type is stored as metadata
                import re
                num_match = re.search(r'\d+', original_tag)
                num = num_match.group() if num_match else str(idx+1)
                tag_name = f"C-{num}"
                
                # Add control as a unit with proper naming
                flowsheet.add_unit(
                    unique_name=tag_name,
                    unit_type="Control",
                    control_type=control_type
                )
                
                # Find connected equipment and add signal edge
                connected_equipment = self._find_instrumentation_target(pif, model)
                if connected_equipment and connected_equipment in node_map:
                    flowsheet.add_stream(
                        node1=node_map[connected_equipment],
                        node2=tag_name,
                        tags={"signal": ["not_next_unitop"], "he": [], "col": []},
                        signal_type="measurement"
                    )
        
        return flowsheet
    
    def _create_equipment_from_unit(
        self, 
        unit_id: str, 
        unit_type: str,
        node_data: Dict[str, Any]
    ) -> Optional[Equipment]:
        """Create DEXPI equipment from SFILES unit.
        
        Args:
            unit_id: Unit identifier
            unit_type: SFILES unit type
            node_data: Additional unit data
            
        Returns:
            Equipment object or None
        """
        equipment_class = self.unit_to_equipment.get(unit_type)
        if not equipment_class:
            logger.warning(f"Unknown unit type: {unit_type}")
            equipment_class = Vessel  # Default to vessel
        
        # Create equipment instance
        equipment = equipment_class(
            tagName=unit_id
        )
        
        # Add standard nozzles for connectivity
        # Most equipment needs at least inlet/outlet
        nozzles = []
        
        # Inlet nozzle
        inlet_nozzle = Nozzle(
            id=f"nozzle_inlet_{unit_id}",
            subTagName="N1"
        )
        inlet_node = PipingNode(
            nominalDiameterRepresentation="DN100",
            nominalDiameterNumericalValueRepresentation="100"
        )
        inlet_nozzle.nodes = [inlet_node]
        nozzles.append(inlet_nozzle)
        
        # Outlet nozzle
        outlet_nozzle = Nozzle(
            id=f"nozzle_outlet_{unit_id}",
            subTagName="N2"
        )
        outlet_node = PipingNode(
            nominalDiameterRepresentation="DN100",
            nominalDiameterNumericalValueRepresentation="100"
        )
        outlet_nozzle.nodes = [outlet_node]
        nozzles.append(outlet_nozzle)
        
        # Add extra nozzles for columns (top/bottom/side)
        if unit_type in ['distcol', 'column']:
            side_nozzle = Nozzle(
                id=f"nozzle_side_{unit_id}",
                subTagName="N3"
            )
            side_node = PipingNode(
                nominalDiameterRepresentation="DN50",
                nominalDiameterNumericalValueRepresentation="50"
            )
            side_nozzle.nodes = [side_node]
            nozzles.append(side_nozzle)
        
        equipment.nozzles = nozzles
        
        return equipment
    
    def _create_piping_segment(
        self,
        segment_id: str,
        from_equipment: Equipment,
        to_equipment: Equipment,
        stream_data: Dict[str, Any]
    ) -> Optional[PipingNetworkSegment]:
        """Create piping segment between equipment.
        
        Args:
            segment_id: Segment identifier
            from_equipment: Source equipment
            to_equipment: Target equipment
            stream_data: Stream properties
            
        Returns:
            PipingNetworkSegment or None
        """
        # Get nozzles
        from_nozzle = from_equipment.nozzles[-1] if from_equipment.nozzles else None
        to_nozzle = to_equipment.nozzles[0] if to_equipment.nozzles else None
        
        if not from_nozzle or not to_nozzle:
            logger.warning(f"Cannot create segment {segment_id}: missing nozzles")
            return None
        
        # Create pipe connection
        pipe = Pipe(
            id=f"pipe_{segment_id}",
            tagName=stream_data.get('tag', segment_id)
        )
        
        # Create segment
        segment = PipingNetworkSegment(
            id=segment_id,
            pipingClassArtefact="CS150"
        )
        segment.connections = [pipe]
        segment.items = []
        
        # Connect using piping toolkit
        try:
            pt.connect_piping_network_segment(segment, from_nozzle, as_source=True)
            pt.connect_piping_network_segment(segment, to_nozzle, as_source=False)
        except Exception as e:
            logger.error(f"Failed to connect segment {segment_id}: {e}")
            return None
        
        return segment
    
    def _create_instrumentation_from_control(
        self,
        control_id: str,
        control_type: str,
        connected_equipment: Equipment
    ) -> Optional[ProcessInstrumentationFunction]:
        """Create instrumentation function from SFILES control.
        
        Args:
            control_id: Control identifier
            control_type: FC, LC, TC, PC
            connected_equipment: Equipment being controlled
            
        Returns:
            ProcessInstrumentationFunction or None
        """
        variable = self.control_to_instrumentation.get(control_type, 'Flow')
        
        # Create instrumentation function (controller)
        pif = ProcessInstrumentationFunction(
            tagName=control_id
        )
        
        # Store control type as custom attribute for round-trip preservation
        control_type_attr = CustomStringAttribute(
            attributeName="ControlType",
            value=control_type
        )
        if not hasattr(pif, 'customAttributes'):
            pif.customAttributes = []
        pif.customAttributes.append(control_type_attr)
        
        # Add signal generating function (sensor)
        sensor = ProcessSignalGeneratingFunction(
            tagName=f"{control_id}_sensor"
        )
        
        # Set sensor type for standard compliance
        sensor.sensorType = variable  # "Flow", "Level", "Temperature", "Pressure"
        
        # Determine appropriate sensing location
        sensing_location = self._determine_sensing_location(connected_equipment, control_type)
        if sensing_location:
            sensor.sensingLocation = sensing_location
        
        # Add actuating function (for control valve)
        actuator = ActuatingFunction(
            tagName=f"{control_id}_valve"
        )
        
        # Assign to correct attributes
        pif.processSignalGeneratingFunctions = [sensor]
        pif.actuatingFunctions = [actuator]
        
        return pif
    
    def _determine_sensing_location(self, connected_item: Equipment, control_type: str):
        """Determine appropriate sensing location based on context.
        
        Args:
            connected_item: Equipment or piping component
            control_type: FC, LC, TC, PC
            
        Returns:
            Appropriate sensing location (Nozzle or InlinePrimaryElement)
        """
        # For equipment with nozzles (tanks, vessels, columns)
        if hasattr(connected_item, 'nozzles') and connected_item.nozzles:
            # For level control on tanks, use first nozzle
            # For temperature/pressure, use appropriate nozzle
            return connected_item.nozzles[0]
        
        # For inline instruments on piping segments
        # This would be expanded based on actual piping segment handling
        # For now, return None to maintain backward compatibility
        return None
    
    def _get_unit_type_from_equipment(self, equipment: Equipment) -> str:
        """Get SFILES unit type from DEXPI equipment.
        
        Args:
            equipment: DEXPI equipment object
            
        Returns:
            SFILES unit type string
        """
        class_name = equipment.__class__.__name__
        return self.equipment_to_unit.get(class_name, 'vessel')
    
    def _find_connected_equipment(
        self,
        segment: PipingNetworkSegment,
        connection_type: str,
        model: DexpiModel
    ) -> Optional[Equipment]:
        """Find equipment connected to segment.
        
        Args:
            segment: Piping segment
            connection_type: 'source' or 'target'
            model: DEXPI model
            
        Returns:
            Connected equipment or None
        """
        # Check segment's sourceItem/targetItem
        item_attr = f"{connection_type}Item"
        item = getattr(segment, item_attr, None)
        
        if not item:
            return None
        
        # If it's a nozzle, find its parent equipment
        if hasattr(item, '__class__') and item.__class__.__name__ == 'Nozzle':
            # Search for equipment with this nozzle
            if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                for equipment in model.conceptualModel.taggedPlantItems:
                    if hasattr(equipment, 'nozzles'):
                        if item in equipment.nozzles:
                            return equipment
        
        # If it's a string ID, search by ID
        if isinstance(item, str):
            if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                for equipment in model.conceptualModel.taggedPlantItems:
                    if hasattr(equipment, 'nozzles'):
                        for nozzle in equipment.nozzles:
                            if getattr(nozzle, 'id', None) == item:
                                return equipment
        
        return None
    
    def _find_instrumentation_target(
        self,
        pif: ProcessInstrumentationFunction,
        model: DexpiModel
    ) -> Optional[Equipment]:
        """Find equipment targeted by instrumentation.
        
        Args:
            pif: Process instrumentation function
            model: DEXPI model
            
        Returns:
            Target equipment or None
        """
        # Check for sensing location in signal generating functions
        if hasattr(pif, 'processSignalGeneratingFunctions'):
            for sgf in pif.processSignalGeneratingFunctions:
                if hasattr(sgf, 'sensingLocation') and sgf.sensingLocation:
                    location = sgf.sensingLocation
                    
                    # If location is a Nozzle, find the equipment that owns it
                    if hasattr(location, '__class__') and location.__class__.__name__ == 'Nozzle':
                        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                            for equipment in model.conceptualModel.taggedPlantItems:
                                if hasattr(equipment, 'nozzles') and location in equipment.nozzles:
                                    return equipment
                    
                    # If location is an InlinePrimaryElement or PipingComponent,
                    # we might need to trace through piping segments
                    # For now, return None for inline instruments
                    # This maintains the separation between equipment-mounted and inline
        
        # Default: try to parse from tag name (e.g., "FIC-101" might control P-101)
        # This is a heuristic and might need refinement
        return None
    
    def _get_control_type_from_instrumentation(
        self,
        pif: ProcessInstrumentationFunction
    ) -> str:
        """Get SFILES control type from instrumentation.
        
        Args:
            pif: Process instrumentation function
            
        Returns:
            Control type (FC, LC, TC, PC)
        """
        # First check custom attributes for stored control type
        if hasattr(pif, 'customAttributes'):
            for attr in pif.customAttributes:
                if hasattr(attr, 'attributeName') and attr.attributeName == "ControlType":
                    return attr.value
        
        # Check sensor type in signal generating functions
        if hasattr(pif, 'processSignalGeneratingFunctions'):
            for sgf in pif.processSignalGeneratingFunctions:
                if hasattr(sgf, 'sensorType') and sgf.sensorType:
                    type_map = {
                        'Flow': 'FC',
                        'Level': 'LC', 
                        'Temperature': 'TC',
                        'Pressure': 'PC'
                    }
                    for key, value in type_map.items():
                        if key in sgf.sensorType:
                            return value
                
                # Fallback to measuredVariable
                if hasattr(sgf, 'measuredVariable'):
                    variable = sgf.measuredVariable
                    if 'Flow' in variable:
                        return 'FC'
                    elif 'Level' in variable:
                        return 'LC'
                    elif 'Temperature' in variable:
                        return 'TC'
                    elif 'Pressure' in variable:
                        return 'PC'
        
        # Default to flow control
        return 'FC'