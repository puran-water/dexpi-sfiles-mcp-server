"""BFD (Block Flow Diagram) specific models and validation schemas.

This module provides Pydantic validation schemas for BFD operations integrated
with existing SFILES tools. Following Codex Review #6 guidance, these schemas
add type safety to existing functionality without creating wrapper tools.

Architecture Decision (Codex Review #6):
    "Adopt the minimal approach (1 new tool + BFD-aware validation in sfiles_*).
    Validation lives where the logic lives: Adding Pydantic schemas inside
    sfiles_tools keeps the validation right next to the code that actually
    manipulates Flowsheet objects."

Integration Pattern:
    These schemas are imported conditionally in sfiles_tools.py when type="BFD"
    to provide BFD-specific validation. NO separate BFD wrapper tools are created
    (avoiding "pure indirection").
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from .graph_metadata import NodeMetadata, EdgeMetadata


class BfdPortType(str, Enum):
    """Port types for BFD blocks."""
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"


class CardinalDirection(str, Enum):
    """Cardinal directions for BFD port layout (simplified from Sprint 1)."""
    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"


class BfdPortSpec(BaseModel):
    """BFD-specific port specification (simplified, not DEXPI-based).

    BFD operates at high level and doesn't need DEXPI classifications.
    This is a simpler port model optimized for BFD conceptual diagrams.

    Attributes:
        port_id: Unique port identifier
        direction: Cardinal direction for layout (N/S/E/W)
        port_type: BFD port type (input, output, bidirectional)
        stream_type: Optional stream classification (material, energy, information)
    """

    port_id: str = Field(
        ...,
        description="Unique port identifier"
    )

    direction: CardinalDirection = Field(
        ...,
        description="Cardinal direction for layout (N/S/E/W)"
    )

    port_type: BfdPortType = Field(
        ...,
        description="Port type: input, output, or bidirectional"
    )

    stream_type: Optional[str] = Field(
        None,
        description="Stream classification (material, energy, information)"
    )


class BfdCreateArgs(BaseModel):
    """Validation schema for BFD flowsheet creation.

    Used in sfiles_tools._create_flowsheet when type="BFD".
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Flowsheet name"
    )

    type: str = Field(
        default="BFD",
        pattern="^BFD$",
        description="Must be 'BFD' for this schema"
    )

    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional flowsheet description"
    )

    flowsheet_id: Optional[str] = Field(
        None,
        description="Optional ID for the flowsheet (auto-generated if not provided)"
    )


class BfdBlockArgs(BaseModel):
    """Validation schema for BFD block (process unit) addition.

    Used in sfiles_tools._add_unit when flowsheet.type=="BFD".
    Validates process type against hierarchy and ensures semantic ID generation.
    """

    flowsheet_id: str = Field(
        ...,
        description="ID of the BFD flowsheet"
    )

    unit_type: str = Field(
        ...,
        min_length=1,
        description="Process type (resolved via process_resolver.py)"
    )

    unit_name: Optional[str] = Field(
        None,
        description="Optional descriptive name (defaults to unit_type)"
    )

    sequence_number: Optional[int] = Field(
        None,
        ge=1,
        description="Optional sequence number (auto-increments if not provided)"
    )

    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Unit-specific parameters"
    )

    allow_custom: bool = Field(
        default=False,
        description="Allow custom process types not in hierarchy"
    )

    port_specs: Optional[List[BfdPortSpec]] = Field(
        None,
        description="Optional typed ports for the block"
    )


class BfdFlowArgs(BaseModel):
    """Validation schema for BFD flow (stream) addition.

    Used in sfiles_tools._add_stream when flowsheet.type=="BFD".
    """

    flowsheet_id: str = Field(
        ...,
        description="ID of the BFD flowsheet"
    )

    from_unit: str = Field(
        ...,
        description="Source block ID or tag"
    )

    to_unit: str = Field(
        ...,
        description="Target block ID or tag"
    )

    stream_name: Optional[str] = Field(
        None,
        description="Optional stream name"
    )

    stream_type: Optional[str] = Field(
        None,
        description="Stream classification (material, energy, information)"
    )

    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Stream properties (flow rate, temperature, etc.)"
    )


class BfdBlockMetadata(NodeMetadata):
    """BFD-specific node metadata extending Sprint 1 NodeMetadata.

    Validates SFILES2 BFD output including process hierarchy attributes.
    Uses extra="allow" to preserve all SFILES-generated fields.

    BFD-specific attributes (from SFILES2 + process_resolver):
        unit_type: Process type from hierarchy
        equipment_tag: Semantic equipment tag (e.g., "101-AS-01")
        area_number: Process area number (100s, 200s, etc.)
        process_unit_id: Unit ID from hierarchy (e.g., "AS" for Aeration Tank)
        sequence_number: Sequential number within process type
        category: Major process category (e.g., "Secondary Treatment")
        subcategory: Process subcategory
        is_custom: Whether process type is custom (not in hierarchy)
    """

    # BFD-specific required fields (added by SFILES2 + process_resolver)
    equipment_tag: Optional[str] = Field(
        None,
        description="Semantic equipment tag (e.g., '101-AS-01')"
    )

    area_number: Optional[int] = Field(
        None,
        description="Process area number from hierarchy"
    )

    process_unit_id: Optional[str] = Field(
        None,
        description="Unit ID from hierarchy (e.g., 'AS')"
    )

    sequence_number: Optional[int] = Field(
        None,
        ge=1,
        description="Sequential number within process type"
    )

    category: Optional[str] = Field(
        None,
        description="Major process category from hierarchy"
    )

    subcategory: Optional[str] = Field(
        None,
        description="Process subcategory from hierarchy"
    )

    is_custom: Optional[bool] = Field(
        None,
        description="Whether process type is custom"
    )

    port_specs: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Typed ports for the block (stored as metadata)"
    )


class BfdFlowMetadata(EdgeMetadata):
    """BFD-specific edge metadata extending Sprint 1 EdgeMetadata.

    Validates SFILES2 BFD stream output.
    Uses extra="allow" to preserve all SFILES-generated fields.

    BFD-specific attributes:
        stream_type: Stream classification (material, energy, information)
        flow_direction: Flow direction indicator
    """

    stream_type: Optional[str] = Field(
        None,
        description="Stream classification"
    )

    flow_direction: Optional[str] = Field(
        None,
        description="Flow direction indicator"
    )


class BfdToPfdExpansionOption(BaseModel):
    """Single PFD expansion option for a BFD block.

    Used by bfd_to_pfd_plan tool to suggest equipment breakdowns.
    """

    equipment_type: str = Field(
        ...,
        description="PFD equipment type"
    )

    description: str = Field(
        ...,
        description="Description of this expansion option"
    )

    typical_count: int = Field(
        ...,
        ge=1,
        description="Typical number of units for this configuration"
    )

    configuration: Optional[str] = Field(
        None,
        description="Configuration details (series, parallel, etc.)"
    )


class BfdToPfdExpansionPlan(BaseModel):
    """Complete BFD-to-PFD expansion plan.

    Output schema for bfd_to_pfd_plan tool.
    """

    bfd_block: str = Field(
        ...,
        description="BFD block ID being expanded"
    )

    process_type: str = Field(
        ...,
        description="BFD process type"
    )

    pfd_options: List[BfdToPfdExpansionOption] = Field(
        ...,
        description="List of PFD expansion options"
    )

    recommended_option: Optional[int] = Field(
        None,
        ge=0,
        description="Index of recommended option (if applicable)"
    )


__all__ = [
    # Enums
    "BfdPortType",
    "CardinalDirection",

    # Port specifications
    "BfdPortSpec",

    # Validation schemas (for sfiles_tools integration)
    "BfdCreateArgs",
    "BfdBlockArgs",
    "BfdFlowArgs",

    # Metadata validators
    "BfdBlockMetadata",
    "BfdFlowMetadata",

    # Planning schemas (for bfd_to_pfd_plan tool)
    "BfdToPfdExpansionOption",
    "BfdToPfdExpansionPlan",
]
