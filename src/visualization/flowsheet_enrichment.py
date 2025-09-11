"""
Flowsheet enrichment module for adding instrumentation to pyflowsheet visualizations.
Hooks into existing SFILES2 visualization pipeline to add instrument bubbles and signal lines.
"""

import logging
from typing import Dict, Any, Tuple, Optional
import networkx as nx
from pyflowsheet import Flowsheet as PyFlowsheet
from pyflowsheet.unitoperations import Valve
from pyflowsheet.core import Stream

from .instrument_symbols import (
    get_instrument_bubble,
    create_tap_line,
    create_signal_line,
    InstrumentBubble,
    ControllerBubble
)

logger = logging.getLogger(__name__)


def enrich_flowsheet_with_instruments(
    sfiles_flowsheet,
    pyflowsheet_obj: PyFlowsheet,
    unit_positions: Dict[str, Tuple[float, float]]
) -> PyFlowsheet:
    """
    Enrich a pyflowsheet object with instrument bubbles and signal lines.
    
    This function is called after the base flowsheet is created by SFILES2's
    visualize_flowsheet method. It adds instrumentation based on metadata.
    
    Args:
        sfiles_flowsheet: The SFILES Flowsheet object with graph data
        pyflowsheet_obj: The pyflowsheet Flowsheet object to enrich
        unit_positions: Dictionary mapping unit IDs to (x, y) positions
        
    Returns:
        Enriched pyflowsheet object
    """
    
    # Get the NetworkX graph from SFILES flowsheet
    graph = sfiles_flowsheet.state
    
    # Track control valves that need to be created
    control_valves = {}
    
    # Process all control nodes in the graph
    for node_id, node_data in graph.nodes(data=True):
        if node_data.get('unit_type') == 'Control':
            control_type = node_data.get('control_type', '')
            attachment_target = node_data.get('attachment_target')
            
            # Determine tag text - extract from node_id or use control_type
            tag_text = node_id  # e.g., "C-101"
            if control_type:
                # Create full ISA tag if we have the control type
                # This could be enhanced with area codes from JSON config
                tag_text = f"{node_id}/{control_type}"
            
            # Check if this is a control valve (ends with CV)
            is_control_valve = control_type.endswith('CV') or control_type == 'XV'
            
            if is_control_valve:
                # Control valves need special handling
                # The bubble should be mounted on the valve symbol
                _handle_control_valve(
                    graph, pyflowsheet_obj, node_id, node_data,
                    control_type, tag_text, attachment_target,
                    unit_positions, control_valves
                )
            else:
                # Regular instruments (transmitters, controllers, etc.)
                _handle_regular_instrument(
                    graph, pyflowsheet_obj, node_id, node_data,
                    control_type, tag_text, attachment_target,
                    unit_positions
                )
    
    # Add any control valves to the flowsheet
    for valve_id, valve_obj in control_valves.items():
        pyflowsheet_obj.addUnits([valve_obj])
    
    # Add signal lines between instruments and their targets
    _add_signal_lines(graph, pyflowsheet_obj, unit_positions)
    
    return pyflowsheet_obj


def _handle_control_valve(
    graph, pyflowsheet_obj, node_id, node_data,
    control_type, tag_text, attachment_target,
    unit_positions, control_valves
):
    """
    Handle control valve placement with bubble mounted on valve symbol.
    
    Control valves (FCV, TCV, PCV, LCV, ACV, XV) are shown as:
    1. A valve symbol on the stream
    2. A controller bubble mounted directly on the valve
    """
    
    # Determine valve position based on attachment_target
    if attachment_target:
        att_type = attachment_target.get('type')
        att_ref = attachment_target.get('ref')
        
        if att_type == 'stream':
            # Valve should be placed on this stream
            # Find the stream edges in the graph
            stream_edge = _find_stream_edge(graph, att_ref)
            if stream_edge:
                # Calculate midpoint of stream for valve placement
                from_pos = unit_positions.get(stream_edge[0])
                to_pos = unit_positions.get(stream_edge[1])
                
                if from_pos and to_pos:
                    valve_x = (from_pos[0] + to_pos[0]) / 2
                    valve_y = (from_pos[1] + to_pos[1]) / 2
                    
                    # Create valve object
                    valve = Valve(
                        id=f"{node_id}_valve",
                        name=tag_text,
                        position=(valve_x, valve_y),
                        size=(30, 30)
                    )
                    control_valves[node_id] = valve
                    
                    # Create controller bubble mounted on valve
                    # Position slightly above the valve
                    bubble = get_instrument_bubble(
                        control_type,
                        node_id,
                        tag_text=tag_text,
                        position=(valve_x - 10, valve_y - 40),  # Offset above valve
                        control_type=control_type,
                        attachment_target=attachment_target
                    )
                    pyflowsheet_obj.addUnits([bubble])
                    
                    # Store positions for signal line drawing
                    unit_positions[node_id] = (valve_x - 10, valve_y - 40)
                    unit_positions[f"{node_id}_valve"] = (valve_x, valve_y)
    else:
        # No attachment specified, place near connected unit
        connected_unit = _get_connected_unit(graph, node_id)
        if connected_unit and connected_unit in unit_positions:
            base_pos = unit_positions[connected_unit]
            # Place valve and bubble near the connected unit
            valve_x = base_pos[0] + 60
            valve_y = base_pos[1]
            
            valve = Valve(
                id=f"{node_id}_valve",
                name=tag_text,
                position=(valve_x, valve_y),
                size=(30, 30)
            )
            control_valves[node_id] = valve
            
            bubble = get_instrument_bubble(
                control_type,
                node_id,
                tag_text=tag_text,
                position=(valve_x - 10, valve_y - 40),
                control_type=control_type
            )
            pyflowsheet_obj.addUnits([bubble])
            
            unit_positions[node_id] = (valve_x - 10, valve_y - 40)
            unit_positions[f"{node_id}_valve"] = (valve_x, valve_y)


def _handle_regular_instrument(
    graph, pyflowsheet_obj, node_id, node_data,
    control_type, tag_text, attachment_target,
    unit_positions
):
    """
    Handle regular instrument placement (non-valve instruments).
    
    These can be attached to units or streams based on attachment_target.
    """
    
    # Check for analytical instruments that need parameter annotation
    analytical_param = None
    if control_type.startswith('A'):
        # Extract analytical parameter from node data if available
        # This could be enhanced to parse from tag or metadata
        analytical_param = node_data.get('analytical_param')
    
    # Determine instrument position based on attachment_target
    position = _calculate_instrument_position(
        graph, node_id, attachment_target, unit_positions
    )
    
    if position:
        # Create instrument bubble
        bubble = get_instrument_bubble(
            control_type,
            node_id,
            tag_text=tag_text,
            position=position,
            control_type=control_type,
            attachment_target=attachment_target,
            analytical_param=analytical_param
        )
        
        # Add to pyflowsheet
        pyflowsheet_obj.addUnits([bubble])
        
        # Store position for signal line drawing
        unit_positions[node_id] = position
        
        # If attached to stream, add tap line
        if attachment_target and attachment_target.get('type') == 'stream':
            # This would require access to the SVG context
            # For now, we'll skip the tap line as it needs to be drawn
            # during the render phase, not during object creation
            pass


def _calculate_instrument_position(
    graph, node_id, attachment_target, unit_positions
) -> Optional[Tuple[float, float]]:
    """
    Calculate the position for an instrument based on its attachment target.
    
    Returns:
        (x, y) position tuple or None if position cannot be determined
    """
    
    if attachment_target:
        att_type = attachment_target.get('type')
        att_ref = attachment_target.get('ref')
        
        if att_type == 'unit':
            # Attach to unit - position near the unit
            if att_ref in unit_positions:
                base_pos = unit_positions[att_ref]
                # Offset to the right and slightly up
                return (base_pos[0] + 60, base_pos[1] - 20)
                
        elif att_type == 'stream':
            # Attach to stream - position at midpoint of stream
            stream_edge = _find_stream_edge(graph, att_ref)
            if stream_edge:
                from_pos = unit_positions.get(stream_edge[0])
                to_pos = unit_positions.get(stream_edge[1])
                
                if from_pos and to_pos:
                    # Position at midpoint, offset perpendicular to stream
                    mid_x = (from_pos[0] + to_pos[0]) / 2
                    mid_y = (from_pos[1] + to_pos[1]) / 2
                    
                    # Calculate perpendicular offset
                    dx = to_pos[0] - from_pos[0]
                    dy = to_pos[1] - from_pos[1]
                    length = (dx**2 + dy**2)**0.5
                    
                    if length > 0:
                        # Perpendicular vector
                        perp_x = -dy / length * 30  # 30 pixels offset
                        perp_y = dx / length * 30
                        
                        return (mid_x + perp_x, mid_y + perp_y)
                    else:
                        return (mid_x, mid_y - 30)
    
    # No attachment target specified, place near connected unit
    connected_unit = _get_connected_unit(graph, node_id)
    if connected_unit and connected_unit in unit_positions:
        base_pos = unit_positions[connected_unit]
        # Default offset
        return (base_pos[0] + 60, base_pos[1] - 20)
    
    return None


def _find_stream_edge(graph, stream_ref: str):
    """
    Find the edge in the graph corresponding to a stream reference.
    
    Args:
        graph: NetworkX graph
        stream_ref: Stream reference (name or ID)
        
    Returns:
        Edge tuple (from_node, to_node) or None
    """
    
    for edge in graph.edges(data=True):
        edge_data = edge[2]
        # Check if stream name matches
        if edge_data.get('processstream_name') == stream_ref:
            return (edge[0], edge[1])
        # Also check other possible stream identifiers
        if edge_data.get('stream_name') == stream_ref:
            return (edge[0], edge[1])
    
    return None


def _get_connected_unit(graph, control_node_id: str) -> Optional[str]:
    """
    Get the unit that a control is connected to via signal edge.
    
    Args:
        graph: NetworkX graph
        control_node_id: ID of the control node
        
    Returns:
        ID of connected unit or None
    """
    
    # Look for incoming signal edges (measurement signals)
    for edge in graph.in_edges(control_node_id, data=True):
        edge_data = edge[2]
        if 'signal' in edge_data.get('tags', {}).get('signal', []):
            return edge[0]  # Source of the signal edge
    
    return None


def _add_signal_lines(graph, pyflowsheet_obj, unit_positions):
    """
    Add dashed signal lines between control elements.
    
    Signal lines connect:
    1. Measurement points to controllers/transmitters
    2. Controllers to actuators/valves
    """
    
    # Process all edges looking for signal connections
    for edge in graph.edges(data=True):
        edge_data = edge[2]
        tags = edge_data.get('tags', {})
        
        # Check if this is a signal edge
        if 'signal' in tags and tags['signal']:
            from_node = edge[0]
            to_node = edge[1]
            
            from_pos = unit_positions.get(from_node)
            to_pos = unit_positions.get(to_node)
            
            if from_pos and to_pos:
                # Create a dashed stream for signal line
                signal_stream = Stream(
                    id=f"signal_{from_node}_{to_node}",
                    name="",
                    source=from_node,
                    sink=to_node
                )
                
                # Set dashed style for signal
                signal_stream.dashArray = [5, 5]
                signal_stream.strokeColor = "#666666"
                signal_stream.strokeWidth = 1
                
                # Add to flowsheet
                # Note: This might need adjustment based on pyflowsheet API
                # for adding streams after units are added
                pass