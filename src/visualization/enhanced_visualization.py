"""
Enhanced visualization wrapper for SFILES flowsheets with instrumentation.
This module provides an alternative to the default visualize_flowsheet method
that includes instrument bubbles and proper control valve placement.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import networkx as nx

# Import the visualization utilities from SFILES2
from Flowsheet_Class.utils_visualization import (
    plot_flowsheet_pyflowsheet,
    _add_positions
)
from pyflowsheet import Flowsheet as PyFlowsheet
from pyflowsheet.unitoperations import (
    BlackBox, Vessel, Distillation, HeatExchanger,
    Pump, Valve, Mixer, Splitter, StreamFlag
)
from pyflowsheet.enums import HorizontalLabelAlignment, VerticalLabelAlignment
from pyflowsheet.core import Port
from pyflowsheet.svgcontext import SvgContext

from ..visualization.instrument_symbols import (
    get_instrument_bubble,
    InstrumentBubble,
    ControllerBubble
)

logger = logging.getLogger(__name__)


def visualize_flowsheet_with_instruments(
    flowsheet,
    pfd_path: str = "plots/flowsheet",
    pfd_block: bool = False,
    add_positions: bool = True
) -> Optional[Path]:
    """
    Enhanced visualization of SFILES flowsheet with proper instrumentation.
    
    This replaces the default visualize_flowsheet method to include:
    - Instrument bubbles positioned based on attachment metadata
    - Control valves with mounted controller bubbles
    - Dashed signal lines between instruments
    
    Args:
        flowsheet: SFILES Flowsheet object
        pfd_path: Path for SVG output (without extension)
        pfd_block: If True, use block diagrams; if False, use unit symbols
        add_positions: If True, calculate positions automatically
        
    Returns:
        Path to generated SVG file or None if failed
    """
    
    try:
        # Log key dependency versions to help diagnose environment mismatches
        try:
            import importlib.metadata as _ilmd
            _pf_ver = _ilmd.version('pyflowsheet')
            _pfnd_ver = _ilmd.version('pathfinding')
            logger.info(f"pyflowsheet={_pf_ver}, pathfinding={_pfnd_ver}")
            if _pf_ver == '0.2.2' and _pfnd_ver != '1.0.1':
                logger.warning(
                    "Detected pathfinding %s with pyflowsheet 0.2.2; recommended is 1.0.1.",
                    _pfnd_ver
                )
        except Exception:
            pass
        # Get the graph from flowsheet
        graph = flowsheet.state
        flowsheet_size = graph.number_of_nodes()
        
        logger.info(f"Starting enhanced visualization for flowsheet with {flowsheet_size} nodes")
        
        # Add positions if needed
        if add_positions:
            graph = _add_positions(graph, flowsheet_size)
            logger.info("Positions added to graph")
        
        # Get positions for all nodes
        pos = nx.get_node_attributes(graph, "pos")
        
        # Create pyflowsheet object
        pfd = PyFlowsheet(
            id="enhanced_pfd",
            name="Enhanced Process Flow Diagram",
            description="PFD with instrumentation"
        )
        
        # Dictionary to store unit operations
        unit_dict = {}
        control_valves = {}  # Track control valves separately
        
        # First pass: Create regular unit operations (non-controls)
        feed_count = 1
        product_count = 1
        
        for node_id, node_data in graph.nodes(data=True):
            # Skip control nodes for now
            if node_data.get('unit_type') == 'Control':
                continue
                
            # Handle feeds (no incoming edges)
            if graph.in_degree(node_id) == 0:
                feed_name = f"Feed {feed_count}"
                feed = StreamFlag(node_id, name=feed_name, position=node_data["pos"])
                feed.setTextAnchor(HorizontalLabelAlignment.Center, 
                                 VerticalLabelAlignment.Center, (0, 5))
                feed_count += 1
                unit_dict[node_id] = feed
                
            # Handle products (no outgoing edges)
            elif graph.out_degree(node_id) == 0 and node_id[0] == "I":
                product_name = f"Product {product_count}"
                product = StreamFlag(node_id, name=product_name, position=node_data["pos"])
                product.setTextAnchor(HorizontalLabelAlignment.Center,
                                     VerticalLabelAlignment.Center, (0, 5))
                product_count += 1
                unit_dict[node_id] = product
                
            else:  # Regular unit operations
                unit = _create_unit_operation(node_id, node_data, pfd_block)
                unit_dict[node_id] = unit
        
        # Second pass: Create control instruments and valves
        for node_id, node_data in graph.nodes(data=True):
            if node_data.get('unit_type') != 'Control':
                continue
                
            control_type = node_data.get('control_type', '')
            attachment_target = node_data.get('attachment_target')
            
            # Create tag text
            tag_text = f"{node_id}/{control_type}" if control_type else node_id
            
            # Check if this is a control valve
            is_control_valve = control_type.endswith('CV') or control_type == 'XV'
            
            if is_control_valve:
                # Create valve and mounted bubble
                valve, bubble = _create_control_valve_with_bubble(
                    node_id, node_data, control_type, tag_text,
                    attachment_target, pos, graph
                )
                
                if valve and bubble:
                    control_valves[f"{node_id}_valve"] = valve
                    unit_dict[node_id] = bubble
                    # Update positions
                    pos[f"{node_id}_valve"] = valve.position
                    pos[node_id] = bubble.position
            else:
                # Regular instrument
                instrument = _create_instrument(
                    node_id, node_data, tag_text,
                    attachment_target, pos, graph
                )
                
                if instrument:
                    unit_dict[node_id] = instrument
                    pos[node_id] = instrument.position
        
        # Add all units to flowsheet
        pfd.addUnits(unit_dict.values())
        pfd.addUnits(control_valves.values())
        
        # Connect units with streams (process streams only, not signals)
        # Keep simple port allocation to avoid relying on class-specific names
        stream_count = 1
        port_usage_out: Dict[str, int] = {}
        port_usage_in: Dict[str, int] = {}
        for edge in graph.edges(data=True):
            edge_data = edge[2]
            tags = edge_data.get('tags', {})
            
            # Skip signal edges
            if 'signal' in tags and tags['signal']:
                continue
            
            # Skip edges involving control nodes
            from_node_data = graph.nodes.get(edge[0], {})
            to_node_data = graph.nodes.get(edge[1], {})
            if from_node_data.get('unit_type') == 'Control' or to_node_data.get('unit_type') == 'Control':
                continue
                
            from_unit = unit_dict.get(edge[0])
            to_unit = unit_dict.get(edge[1])
            
            if from_unit and to_unit:
                stream_id = f"stream-{stream_count}"
                
                # Determine ports based on available intents and usage counters
                from_port = _allocate_port(from_unit, desired_intent="out", 
                                           unit_id=edge[0], usage_map=port_usage_out)
                to_port = _allocate_port(to_unit, desired_intent="in", 
                                         unit_id=edge[1], usage_map=port_usage_in)
                
                # Connect the stream
                try:
                    pfd.connect(stream_id, from_unit[from_port], to_unit[to_port])
                except Exception:
                    # As a last resort, try common fallbacks
                    fallback_from = "Out" if "Out" in from_unit.ports else list(from_unit.ports.keys())[0]
                    fallback_to = "In" if "In" in to_unit.ports else list(to_unit.ports.keys())[0]
                    pfd.connect(stream_id, from_unit[fallback_from], to_unit[fallback_to])
                
                # Set stream label position
                pos0 = pos[edge[0]]
                pos1 = pos[edge[1]]
                if pos0[1] > pos1[1]:
                    pfd.streams[stream_id].labelOffset = (15, 10)
                else:
                    pfd.streams[stream_id].labelOffset = (15, -10)
                    
                stream_count += 1
        
        # Add signal streams (dashed lines)
        _add_signal_streams(graph, pfd, unit_dict, pos)
        
        # Save as SVG
        svg_path = Path(pfd_path).with_suffix(".svg")
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        
        ctx = SvgContext(str(svg_path))
        pfd.draw(ctx)
        ctx.render()  # Actually save the SVG to file
        
        logger.info(f"Enhanced flowsheet saved to {svg_path}")
        return svg_path
        
    except Exception as e:
        logger.error(f"Enhanced visualization failed: {e}", exc_info=True)
        return None


def _create_unit_operation(node_id: str, node_data: Dict, pfd_block: bool):
    """Create appropriate unit operation based on type."""
    
    position = node_data.get("pos", (0, 0))
    unit_type = node_data.get("unit_type", "")
    
    if pfd_block:
        # Block diagram - all units are boxes
        unit = BlackBox(node_id, name=node_id, size=(80, 60), position=position)
        unit.setTextAnchor(HorizontalLabelAlignment.Center,
                          VerticalLabelAlignment.Center, (0, 5))
    else:
        # Use specific unit symbols
        if unit_type in ["hex", "heatexchanger"]:
            unit = HeatExchanger(node_id, name=node_id, position=position)
        elif unit_type in ["reactor", "tank", "vessel"]:
            unit = Vessel(node_id, name=node_id, position=position, angle=90)
            unit.setTextAnchor(HorizontalLabelAlignment.Center,
                              VerticalLabelAlignment.Center, (0, 5))
        elif unit_type in ["col", "column", "distillation", "distcol"]:
            unit = Distillation(node_id, name=node_id, position=position,
                               hasReboiler=False, hasCondenser=False)
            unit.setTextAnchor(HorizontalLabelAlignment.Center,
                              VerticalLabelAlignment.Center, (0, 5))
        elif unit_type == "pump":
            unit = Pump(node_id, name=node_id, position=position)
        elif unit_type == "valve":
            unit = Valve(node_id, name=node_id, position=position)
        elif unit_type == "mixer":
            unit = Mixer(node_id, name=node_id, position=position)
        elif unit_type == "splitter":
            unit = Splitter(node_id, name=node_id, position=position)
        else:
            # Default to black box
            unit = BlackBox(node_id, name=node_id, position=position, size=(80, 60))
            unit.setTextAnchor(HorizontalLabelAlignment.Center,
                              VerticalLabelAlignment.Center, (0, 5))
    
    return unit


def _create_control_valve_with_bubble(
    node_id, node_data, control_type, tag_text,
    attachment_target, positions, graph
):
    """Create a control valve with mounted controller bubble."""
    
    # Determine valve position
    valve_pos = _calculate_valve_position(attachment_target, positions, graph, node_id)
    
    if not valve_pos:
        # Default position if we can't determine
        valve_pos = node_data.get("pos", (100, 100))
    
    # Create valve
    valve = Valve(
        id=f"{node_id}_valve",
        name="",  # Don't label the valve itself
        position=valve_pos,
        size=(30, 30)
    )
    
    # Create controller bubble mounted on valve
    # Position bubble directly above valve
    bubble_pos = (valve_pos[0], valve_pos[1] - 40)
    
    # Determine if analytical instrument
    analytical_param = None
    if control_type.startswith('A'):
        analytical_param = node_data.get('analytical_param')
    
    bubble = get_instrument_bubble(
        control_type,
        node_id,
        tag_text=tag_text,
        position=bubble_pos,
        control_type=control_type,
        attachment_target=attachment_target,
        analytical_param=analytical_param
    )
    
    return valve, bubble


def _create_instrument(
    node_id, node_data, tag_text,
    attachment_target, positions, graph
):
    """Create a regular instrument (non-valve)."""
    
    control_type = node_data.get('control_type', '')
    
    # Calculate position based on attachment
    position = _calculate_instrument_position(
        attachment_target, positions, graph, node_id
    )
    
    if not position:
        position = node_data.get("pos", (100, 100))
    
    # Check for analytical parameter
    analytical_param = None
    if control_type.startswith('A'):
        analytical_param = node_data.get('analytical_param')
    
    instrument = get_instrument_bubble(
        control_type,
        node_id,
        tag_text=tag_text,
        position=position,
        attachment_target=attachment_target,
        analytical_param=analytical_param
    )
    
    return instrument


def _calculate_valve_position(attachment_target, positions, graph, node_id):
    """Calculate position for a control valve."""
    
    if attachment_target and attachment_target.get('type') == 'stream':
        # Find the stream and place valve at midpoint
        stream_ref = attachment_target.get('ref')
        
        for edge in graph.edges(data=True):
            edge_data = edge[2]
            if (edge_data.get('processstream_name') == stream_ref or
                edge_data.get('stream_name') == stream_ref):
                
                from_pos = positions.get(edge[0])
                to_pos = positions.get(edge[1])
                
                if from_pos and to_pos:
                    # Midpoint of stream
                    return ((from_pos[0] + to_pos[0]) / 2,
                           (from_pos[1] + to_pos[1]) / 2)
    
    return None


def _calculate_instrument_position(attachment_target, positions, graph, node_id):
    """Calculate position for an instrument."""
    
    if not attachment_target:
        return None
        
    att_type = attachment_target.get('type')
    att_ref = attachment_target.get('ref')
    
    if att_type == 'unit' and att_ref in positions:
        # Position near the unit
        base_pos = positions[att_ref]
        return (base_pos[0] + 60, base_pos[1] - 20)
        
    elif att_type == 'stream':
        # Find stream and position perpendicular to it
        for edge in graph.edges(data=True):
            edge_data = edge[2]
            if (edge_data.get('processstream_name') == att_ref or
                edge_data.get('stream_name') == att_ref):
                
                from_pos = positions.get(edge[0])
                to_pos = positions.get(edge[1])
                
                if from_pos and to_pos:
                    mid_x = (from_pos[0] + to_pos[0]) / 2
                    mid_y = (from_pos[1] + to_pos[1]) / 2
                    
                    # Perpendicular offset
                    dx = to_pos[0] - from_pos[0]
                    dy = to_pos[1] - from_pos[1]
                    length = (dx**2 + dy**2)**0.5
                    
                    if length > 0:
                        perp_x = -dy / length * 30
                        perp_y = dx / length * 30
                        return (mid_x + perp_x, mid_y + perp_y)
                    
                    return (mid_x, mid_y - 30)
    
    return None


def _allocate_port(unit, desired_intent: str, unit_id: str, usage_map: Dict[str, int]) -> str:
    """Pick a port name on a unit based on intent and round-robin usage.

    This avoids hard-coding class-specific port names (which vary across
    pyflowsheet unit operations) and improves robustness when using
    pfd_block=False.
    """
    # Prefer ports that explicitly declare the desired intent
    ports_with_intent = [name for name, p in unit.ports.items()
                         if getattr(p, "intent", None) == desired_intent]

    if ports_with_intent:
        ports_with_intent.sort()
        idx = usage_map.get(unit_id, 0) % len(ports_with_intent)
        usage_map[unit_id] = usage_map.get(unit_id, 0) + 1
        return ports_with_intent[idx]

    # Fallbacks for common names
    if desired_intent == "out" and "Out" in unit.ports:
        return "Out"
    if desired_intent == "in" and "In" in unit.ports:
        return "In"

    # Absolute fallback: first available port
    return next(iter(unit.ports.keys()))


def _get_input_port(unit, node_data):
    """Deprecated: retained for compatibility (not used)."""
    return _allocate_port(unit, desired_intent="in", unit_id=getattr(unit, "id", "_"), usage_map={})


def _add_signal_streams(graph, pfd, unit_dict, positions):
    """Add dashed signal lines between instruments."""
    
    signal_count = 1
    
    for edge in graph.edges(data=True):
        edge_data = edge[2]
        tags = edge_data.get('tags', {})
        
        # Check if this is a signal edge
        if 'signal' in tags and tags['signal']:
            from_unit = unit_dict.get(edge[0])
            to_unit = unit_dict.get(edge[1])
            
            if from_unit and to_unit:
                stream_id = f"signal-{signal_count}"
                
                # Try to connect signal ports
                try:
                    # Use generic ports for signals
                    pfd.connect(stream_id, from_unit["Out"], to_unit["In"])
                    
                    # Style as dashed signal line
                    signal_stream = pfd.streams[stream_id]
                    signal_stream.dashArray = [5, 5]
                    signal_stream.strokeColor = "#666666"
                    signal_stream.strokeWidth = 1
                    
                    signal_count += 1
                except:
                    # If ports don't exist, skip this signal
                    pass
