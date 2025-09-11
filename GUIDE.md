# Extending Engineering MCP Server with pyflowsheet Visualizations

This guide explains how to extend the engineering-mcp server to support custom instrumentation symbols and enhanced visualizations using pyflowsheet.

## Overview

The engineering-mcp server has been extended to support ISA S5.1 instrumentation symbols in SFILES flowsheets. This implementation provides:

1. **Attachment semantics** for controls (stream vs unit attachment)
2. **Custom instrument symbols** (bubbles) that inherit from pyflowsheet's UnitOperation
3. **Enhanced visualization** that overlays instruments on process flow diagrams
4. **Dual output strategy** (SVG via pyflowsheet, HTML via Plotly)

## Architecture

### 1. Control Attachment Semantics

Controls can be attached to either streams or units for proper visualization:

```python
# Flow control attached to stream
attachment_target = {"type": "stream", "ref": "S-001"}

# Level control attached to unit  
attachment_target = {"type": "unit", "ref": "Tank-1"}
```

The attachment metadata is stored in the NetworkX graph but does NOT change the graph structure - it's purely for visualization.

### 2. Instrument Symbol Classes

Located in `src/visualization/instrument_symbols.py`:

```python
class InstrumentBubble(UnitOperation):
    """ISA S5.1 instrument bubble (circle with tag)."""
    
    def __init__(self, id, tag_text=None, position=(0, 0), size=(50, 50), **kwargs):
        # Size 50x50 to accommodate full ISA tags like "101-FIT-01"
        super().__init__(id, name=tag_text or id, position=position, size=size)
        self.ports = {}  # Initialize ports dictionary
        self.ports["In"] = Port("In", self, (0, 0.5), (-1, 0))
        self.ports["Out"] = Port("Out", self, (1, 0.5), (1, 0), intent="out")
    
    def draw(self, ctx):
        # Draw circle using SvgContext
        rect = [(self.position[0], self.position[1]), 
                (self.position[0] + self.size[0], self.position[1] + self.size[1])]
        ctx.circle(rect, (255, 255, 255, 255), (0, 0, 0, 255), 1.5)
        
        # Draw tag text with proper ISA format (XXX-ISA-YY)
        # Multi-line display for long tags
    
    def drawTextLayer(self, ctx, showPorts=False):
        # Required by pyflowsheet but text is drawn in draw()
        pass
```

### 3. Enhanced Visualization Wrapper

Located in `src/visualization/enhanced_visualization.py`:

```python
def visualize_flowsheet_with_instruments(flowsheet, pfd_path, pfd_block=False, add_positions=True):
    """Enhanced visualization with instrumentation."""
    
    # 1. Create pyflowsheet object
    pfd = PyFlowsheet(id, name, description)
    
    # 2. Add regular unit operations
    for node in graph.nodes:
        if node['unit_type'] != 'Control':
            unit = _create_unit_operation(node)
            pfd.addUnits([unit])
    
    # 3. Add control instruments with positioning
    for node in graph.nodes:
        if node['unit_type'] == 'Control':
            instrument = _create_instrument(node, attachment_target)
            pfd.addUnits([instrument])
    
    # 4. Connect process streams (skip control edges)
    for edge in graph.edges:
        if not is_control_edge(edge):
            pfd.connect(stream_id, from_port, to_port)
    
    # 5. Render to SVG
    ctx = SvgContext(svg_path)
    pfd.draw(ctx)
    ctx.render()  # Actually save the file
```

## ISA Tag Format

Tags follow the ISA S5.1 format: **XXX-ISA-YY**

- **XXX**: Area code (e.g., 101, 201)
- **ISA**: Instrument code (e.g., FIC, LIT, DO)
- **YY**: Sequence number (e.g., 01, 02)

Supported control types:
- **Flow**: FC, FIC, FCV (control valve)
- **Level**: LC, LIC, LCV (control valve)
- **Temperature**: TC, TIC, TCV (control valve)
- **Pressure**: PC, PIC, PCV (control valve)
- **Analytical**: AC, AIC, ACV (with pH/DO/ORP annotation)

## Extending with New Instrument Types

### Step 1: Define the Control Type Mapping

Add to `CONTROL_TYPE_TO_BUBBLE` in `instrument_symbols.py`:

```python
CONTROL_TYPE_TO_BUBBLE = {
    # Existing types...
    "SC": ControllerBubble,  # Speed Controller
    "WIC": ControllerBubble,  # Weight Indicator Controller
}
```

### Step 2: Create Custom Bubble Class (if needed)

```python
class AnalyticalBubble(InstrumentBubble):
    """Specialized bubble for analytical instruments."""
    
    def draw(self, ctx):
        super().draw(ctx)
        # Add custom annotations (e.g., pH, DO)
        if self.analytical_param:
            ctx.text((x, y), self.analytical_param, "Arial", 
                    (0, 0, 0, 255), fontSize=6)
```

### Step 3: Handle Special Positioning

For control valves mounted on streams:

```python
def _create_control_valve_with_bubble(node_id, control_type, attachment_target, positions):
    # Create valve at stream midpoint
    valve_pos = _calculate_valve_position(attachment_target, positions)
    valve = Valve(id=f"{node_id}_valve", position=valve_pos)
    
    # Mount bubble above valve
    bubble_pos = (valve_pos[0], valve_pos[1] - 40)
    bubble = ControllerBubble(node_id, position=bubble_pos)
    
    return valve, bubble
```

## Compatibility Notes

### pyflowsheet Version

The implementation requires:
- **pyflowsheet**: 0.2.2
- **pathfinding**: 1.0.1 (NOT 1.0.17 due to API changes)

### SvgContext API

Key method signatures for pyflowsheet 0.2.2:

```python
# Circle: rect as [(x1,y1), (x2,y2)], colors as RGBA tuples
ctx.circle(rect, fillColor, lineColor, lineSize)

# Rectangle: same format
ctx.rectangle(rect, fillColor, lineColor, lineSize)

# Text: insert as tuple, explicit parameter order
ctx.text(insert, text, fontFamily, textColor, fontSize=12, textAnchor='middle')
```

## Troubleshooting

### SVG Not Generating

1. Check pathfinding version: `pip show pathfinding`
2. Ensure `ctx.render()` is called after `pfd.draw(ctx)`
3. Verify all instruments have proper `ports` dictionary
4. Check that `drawTextLayer(ctx, showPorts=False)` is implemented

### Instruments Not Appearing

1. Verify control nodes have `unit_type='Control'` in graph
2. Check attachment_target is properly set
3. Ensure instruments are added with `pfd.addUnits([instrument])`
4. Control edges should have `tags={'signal': True}` to skip stream connection

### Position Calculation

Default positioning strategies:
- **Unit attachment**: offset right and up from unit center
- **Stream attachment**: perpendicular offset from stream midpoint
- **Control valves**: directly on stream at midpoint

## Future Enhancements

1. **Signal Lines**: Implement dashed lines between instruments
2. **Tap Lines**: Show connection points for inline instruments  
3. **JSON Configuration**: Load ISA codes and styles from config
4. **Animation**: Support for dynamic flow indication
5. **3D Visualization**: Integration with three.js for 3D P&IDs

## Example Usage

```python
from src.visualization.enhanced_visualization import visualize_flowsheet_with_instruments
from Flowsheet_Class.flowsheet import Flowsheet

# Create flowsheet with instrumentation
fs = Flowsheet()
fs.add_unit("Tank-1", unit_type="reactor")
fs.add_stream("Feed-0", "Tank-1", stream_name="S-001")

# Add control with attachment
graph = fs.state
graph.add_node("C-101", unit_type="Control", control_type="FC",
               attachment_target={"type": "stream", "ref": "S-001"})
graph.add_edge("Feed-0", "C-101", tags={"signal": True})

# Generate enhanced visualization
svg_path = visualize_flowsheet_with_instruments(
    fs, 
    "/path/to/output",
    pfd_block=False,  # Use symbols not blocks
    add_positions=True
)
```

## References

- ISA S5.1 Standard: Instrumentation Symbols and Identification
- pyflowsheet Documentation: https://github.com/Nukleon84/pyflowsheet
- NetworkX Graph Library: https://networkx.org/