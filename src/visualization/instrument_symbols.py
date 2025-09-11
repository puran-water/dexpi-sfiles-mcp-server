"""
Instrument symbols for pyflowsheet integration.
Implements ISA S5.1 standard instrument bubbles as pyflowsheet UnitOperation classes.
"""

from pyflowsheet.unitoperation import UnitOperation
from pyflowsheet.core import Port
from pyflowsheet.enums import HorizontalLabelAlignment, VerticalLabelAlignment


class InstrumentBubble(UnitOperation):
    """
    ISA S5.1 instrument bubble (circle with tag).
    Used for displaying control instrumentation on P&IDs.
    """
    
    def __init__(self, id, tag_text=None, position=(0, 0), size=(50, 50), **kwargs):
        """
        Initialize instrument bubble.
        
        Args:
            id: Unique identifier for the instrument
            tag_text: Tag to display (e.g., "101-FIC-01", "201-LIT-02")
                     Format: XXX-ISA-YY where XXX=area, ISA=instrument code, YY=sequence
            position: (x, y) position on the flowsheet
            size: (width, height) of the bubble (typically square for circle)
                  Default 50x50 to accommodate full tags
            **kwargs: Additional attributes stored as metadata
        """
        super().__init__(id, name=tag_text or id, position=position, size=size)
        
        self.tag_text = tag_text or id
        self.control_type = kwargs.get('control_type', '')
        self.attachment_target = kwargs.get('attachment_target', None)
        self.analytical_param = kwargs.get('analytical_param', None)  # pH, DO, ORP, etc.
        
        # Initialize ports dictionary (required by pyflowsheet)
        self.ports = {}
        # Create standard In/Out ports for compatibility with pyflowsheet connections
        self.ports["In"] = Port("In", self, (0, 0.5), (-1, 0))
        self.ports["Out"] = Port("Out", self, (1, 0.5), (1, 0), intent="out")
        
        # Set text anchor to center of bubble
        self.setTextAnchor(
            HorizontalLabelAlignment.Center, 
            VerticalLabelAlignment.Center, 
            (0, 0)
        )
    
    def draw(self, ctx):
        """
        Draw the instrument bubble as a circle.
        
        Args:
            ctx: SvgContext for drawing
        """
        # Get center and radius
        cx = self.position[0] + self.size[0] / 2
        cy = self.position[1] + self.size[1] / 2
        r = min(self.size[0], self.size[1]) / 2
        
        # Draw circle using SvgContext circle method
        # rect format: [(x1, y1), (x2, y2)] for bounding box
        rect = [(self.position[0], self.position[1]), 
                (self.position[0] + self.size[0], self.position[1] + self.size[1])]
        # Colors as RGBA tuples
        ctx.circle(rect, (255, 255, 255, 255), (0, 0, 0, 255), 1.5)
        
        # Draw analytical parameter annotation (pH, DO, ORP) if applicable
        if self.analytical_param and self.control_type.startswith('A'):
            # Draw parameter in small text at top-left of bubble
            param_x = cx - r * 0.7
            param_y = cy - r * 0.7
            ctx.text((param_x, param_y), self.analytical_param, 
                    "Arial", (0, 0, 0, 255), fontSize=6, textAnchor="start")
        
        # Draw tag text - adjust font size based on tag length
        if self.tag_text:
            # For tags like "101-FIT-02" (10 chars), use smaller font
            # For shorter tags, can use larger font
            font_size = 7 if len(self.tag_text) > 8 else 9
            
            # Split tag if it contains hyphens for multi-line display
            if '-' in self.tag_text and len(self.tag_text) > 10:
                parts = self.tag_text.split('-')
                if len(parts) == 3:  # XXX-ISA-YY format
                    # Display as two lines: XXX-ISA on top, YY below
                    line1 = f"{parts[0]}-{parts[1]}"
                    line2 = parts[2]
                    ctx.text((cx, cy - 5), line1, "Arial", (0, 0, 0, 255), 
                            fontSize=font_size, textAnchor="middle")
                    ctx.text((cx, cy + 5), line2, "Arial", (0, 0, 0, 255),
                            fontSize=font_size, textAnchor="middle")
                else:
                    ctx.text((cx, cy), self.tag_text, "Arial", (0, 0, 0, 255),
                            fontSize=font_size, textAnchor="middle")
            else:
                ctx.text((cx, cy), self.tag_text, "Arial", (0, 0, 0, 255),
                        fontSize=font_size, textAnchor="middle")
        
        # Don't call parent draw - we handle everything ourselves
        # super().draw(ctx)
    
    def drawTextLayer(self, ctx, showPorts=False):
        """
        Draw text layer (called separately by pyflowsheet).
        For instrument bubbles, text is already drawn in draw() method.
        
        Args:
            ctx: SvgContext for drawing
            showPorts: Whether to show ports (ignored for instruments)
        """
        pass


class ControllerBubble(InstrumentBubble):
    """
    Controller bubble with additional indication for setpoint control.
    Extends InstrumentBubble with a small square inside the circle.
    """
    
    def __init__(self, id, tag_text=None, position=(0, 0), size=(55, 55), **kwargs):
        """
        Initialize controller bubble.
        Slightly larger than basic instrument to accommodate controller indication.
        Size increased to 55x55 to accommodate full ISA tags like "101-FIC-01".
        """
        super().__init__(id, tag_text, position, size, **kwargs)
        self.is_controller = True
    
    def draw(self, ctx):
        """
        Draw controller bubble with internal square.
        
        Args:
            ctx: SvgContext for drawing
        """
        # Draw base circle
        super().draw(ctx)
        
        # Add small square in center to indicate controller
        cx = self.position[0] + self.size[0] / 2
        cy = self.position[1] + self.size[1] / 2
        square_size = min(self.size[0], self.size[1]) / 4
        
        # Draw square using SvgContext rectangle method
        # rect format: [(x1, y1), (x2, y2)]
        rect = [(cx - square_size/2, cy - square_size/2), 
                (cx + square_size/2, cy + square_size/2)]
        ctx.rectangle(rect, None, (0, 0, 0, 255), 1)


class TransmitterBubble(InstrumentBubble):
    """
    Transmitter bubble for measurement instruments.
    Similar to InstrumentBubble but with different default styling.
    """
    
    def __init__(self, id, tag_text=None, position=(0, 0), size=(50, 50), **kwargs):
        """
        Initialize transmitter bubble.
        """
        super().__init__(id, tag_text, position, size, **kwargs)
        self.is_transmitter = True


def create_tap_line(stream_point, instrument_position, ctx):
    """
    Create a short tap line from a stream to an instrument.
    Used for showing where inline instruments connect to pipes.
    
    Args:
        stream_point: (x, y) point on the stream where tap connects
        instrument_position: (x, y) position of the instrument
        ctx: SvgContext for drawing
    
    Returns:
        None (draws directly to context)
    """
    # Draw a short perpendicular line from stream to instrument
    ctx.line(
        stream_point[0], stream_point[1],
        instrument_position[0], instrument_position[1],
        stroke="black",
        stroke_width=1,
        stroke_dasharray=None  # Solid tap line
    )
    
    # Optionally add a small circle at the tap point
    ctx.circle(stream_point[0], stream_point[1], 2, fill="black")


def create_signal_line(from_pos, to_pos, ctx, dashed=True):
    """
    Create a signal line between control elements.
    
    Args:
        from_pos: (x, y) starting position
        to_pos: (x, y) ending position
        ctx: SvgContext for drawing
        dashed: Whether to draw as dashed line (default True for signals)
    
    Returns:
        None (draws directly to context)
    """
    stroke_dasharray = "3,3" if dashed else None
    
    ctx.line(
        from_pos[0], from_pos[1],
        to_pos[0], to_pos[1],
        stroke="#666",  # Gray for signals
        stroke_width=1,
        stroke_dasharray=stroke_dasharray
    )
    
    # Add small arrowhead at the end
    # Simple triangle for arrow
    arrow_size = 5
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    length = (dx**2 + dy**2)**0.5
    
    if length > 0:
        # Normalize direction
        dx /= length
        dy /= length
        
        # Arrow points
        arrow_tip = to_pos
        arrow_base1 = (
            to_pos[0] - arrow_size * dx - arrow_size * dy / 2,
            to_pos[1] - arrow_size * dy + arrow_size * dx / 2
        )
        arrow_base2 = (
            to_pos[0] - arrow_size * dx + arrow_size * dy / 2,
            to_pos[1] - arrow_size * dy - arrow_size * dx / 2
        )
        
        ctx.polygon(
            [arrow_tip, arrow_base1, arrow_base2],
            fill="#666",
            stroke="none"
        )


# Mapping of control types to bubble classes
# Full ISA code mapping - will be extended via JSON config in future
CONTROL_TYPE_TO_BUBBLE = {
    # Flow instruments
    "FE": InstrumentBubble,      # Flow Element (primary)
    "FT": TransmitterBubble,     # Flow Transmitter
    "FI": TransmitterBubble,     # Flow Indicator
    "FIT": TransmitterBubble,    # Flow Indicating Transmitter
    "FC": ControllerBubble,      # Flow Controller
    "FIC": ControllerBubble,     # Flow Indicator Controller
    "FCV": ControllerBubble,     # Flow Control Valve (bubble mounted on valve symbol)
    
    # Level instruments
    "LE": InstrumentBubble,      # Level Element
    "LT": TransmitterBubble,     # Level Transmitter
    "LI": TransmitterBubble,     # Level Indicator
    "LIT": TransmitterBubble,    # Level Indicating Transmitter
    "LC": ControllerBubble,      # Level Controller
    "LIC": ControllerBubble,     # Level Indicator Controller
    "LICA": ControllerBubble,    # Level Indicator Controller with Alarm
    "LCV": ControllerBubble,     # Level Control Valve
    
    # Temperature instruments
    "TE": InstrumentBubble,      # Temperature Element
    "TT": TransmitterBubble,     # Temperature Transmitter
    "TI": TransmitterBubble,     # Temperature Indicator
    "TIT": TransmitterBubble,    # Temperature Indicating Transmitter
    "TC": ControllerBubble,      # Temperature Controller
    "TIC": ControllerBubble,     # Temperature Indicator Controller
    "TCV": ControllerBubble,     # Temperature Control Valve (bubble mounted on valve symbol)
    
    # Pressure instruments
    "PE": InstrumentBubble,      # Pressure Element
    "PT": TransmitterBubble,     # Pressure Transmitter
    "PI": TransmitterBubble,     # Pressure Indicator
    "PIT": TransmitterBubble,    # Pressure Indicating Transmitter
    "PC": ControllerBubble,      # Pressure Controller
    "PIC": ControllerBubble,     # Pressure Indicator Controller
    "PCV": ControllerBubble,     # Pressure Control Valve (bubble mounted on valve symbol)
    "PSV": InstrumentBubble,     # Pressure Safety Valve
    
    # Analytical instruments (pH, DO, ORP, conductivity, turbidity, etc.)
    # For analytical, the specific parameter (pH, DO, etc.) is shown as annotation
    "AE": InstrumentBubble,      # Analytical Element
    "AT": TransmitterBubble,     # Analytical Transmitter
    "AI": TransmitterBubble,     # Analytical Indicator
    "AIT": TransmitterBubble,    # Analytical Indicating Transmitter
    "AC": ControllerBubble,      # Analytical Controller
    "AIC": ControllerBubble,     # Analytical Indicator Controller
    "ACV": ControllerBubble,     # Analytical Control Valve (bubble mounted on valve symbol)
    
    # Speed instruments (for rotating equipment only)
    "SC": ControllerBubble,      # Speed Controller
    "SIC": ControllerBubble,     # Speed Indicator Controller
    "SIT": TransmitterBubble,    # Speed Indicating Transmitter
    
    # On/Off valves
    "XV": ControllerBubble,      # On/Off Valve (automated, bubble mounted on valve symbol)
}


def get_instrument_bubble(control_type, id, **kwargs):
    """
    Factory function to get appropriate instrument bubble for control type.
    
    Args:
        control_type: Type of control (FC, LC, TC, etc.)
        id: Unique identifier for the instrument
        **kwargs: Additional parameters for the bubble
    
    Returns:
        InstrumentBubble or subclass instance
    """
    # Determine if it's a controller based on suffix
    if control_type.endswith('C') or control_type.endswith('IC'):
        bubble_class = ControllerBubble
    elif control_type.endswith('I'):
        bubble_class = TransmitterBubble
    else:
        # Default to controller for base types
        bubble_class = ControllerBubble
    
    return bubble_class(id, **kwargs)