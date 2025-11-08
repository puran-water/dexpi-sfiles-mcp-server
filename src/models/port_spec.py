"""Port specification wrappers for DEXPI enumerations.

This module provides convenience wrappers around pyDEXPI's port classifications
without replacing them. It maps DEXPI's official enumerations to cardinal
directions (N/S/E/W) for layout purposes while preserving the upstream spec.

Architecture Decision (Codex Review #3):
    "Import NumberOfPortsClassification, PortStatusClassification from pyDEXPI.
    Creating a separate PortSpec model with N/S/E/W might conflict with DEXPI's
    enumerations. Prefer exposing the existing enums."

DEXPI Port Enumerations (from pydexpi.dexpi_classes.pydantic_classes):
    - NumberOfPortsClassification: Standard, Special
    - PortStatusClassification: FullyOpen, FullyClosed, etc.

This module adds DERIVED cardinal direction hints for layout, not canonical values.
"""

import logging
from enum import Enum
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field

# Import DEXPI official enumerations from centralized module
from .dexpi_enums import (
    DEXPI_AVAILABLE,
    NumberOfPortsClassification,
    PortStatusClassification,
)

logger = logging.getLogger(__name__)


class CardinalDirection(str, Enum):
    """Cardinal directions for port layout (DERIVED from DEXPI, not canonical).

    These are convenience hints for automatic layout algorithms (like elkjs).
    The CANONICAL port classification comes from DEXPI's enumerations.
    """
    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"


class PortSpec(BaseModel):
    """Port specification wrapping DEXPI enumerations with layout hints.

    This model wraps (not replaces) DEXPI's official port classifications
    and adds OPTIONAL cardinal direction hints for layout purposes.

    Attributes:
        dexpi_classification: Official DEXPI port classification (CANONICAL)
        dexpi_status: Official DEXPI port status (CANONICAL)
        cardinal_direction: DERIVED layout hint (N/S/E/W) - OPTIONAL
        sub_tag: Optional port sub-tag (e.g., "N1", "N2" for nozzles)
        nominal_diameter: Optional nominal diameter (DN)
        nominal_pressure: Optional nominal pressure (PN)

    Architecture:
        - DEXPI enums are CANONICAL values (preserved in serialization)
        - Cardinal directions are DERIVED hints (can be recomputed)
        - This is an ADAPTER pattern, not a replacement
    """

    # CANONICAL DEXPI attributes
    dexpi_classification: NumberOfPortsClassification = Field(
        ...,
        description="Official DEXPI port classification (CANONICAL)"
    )
    dexpi_status: Optional[PortStatusClassification] = Field(
        None,
        description="Official DEXPI port status (CANONICAL)"
    )

    # DERIVED layout hints (optional)
    cardinal_direction: Optional[CardinalDirection] = Field(
        None,
        description="Derived layout hint (N/S/E/W) for automatic layout - OPTIONAL"
    )

    # Additional port attributes
    sub_tag: Optional[str] = Field(
        None,
        description="Port sub-tag (e.g., 'N1', 'N2' for nozzles)"
    )
    nominal_diameter: Optional[str] = Field(
        None,
        description="Nominal diameter (e.g., 'DN50')"
    )
    nominal_pressure: Optional[str] = Field(
        None,
        description="Nominal pressure (e.g., 'PN16')"
    )

    def to_dict(self) -> dict:
        """Export to dict with DEXPI enums as strings.

        Returns:
            Dictionary with deterministic key ordering
        """
        data = self.model_dump(exclude_none=True)
        # Convert enums to strings for JSON serialization
        if isinstance(data.get("dexpi_classification"), Enum):
            data["dexpi_classification"] = data["dexpi_classification"].value
        if isinstance(data.get("dexpi_status"), Enum):
            data["dexpi_status"] = data["dexpi_status"].value
        if isinstance(data.get("cardinal_direction"), Enum):
            data["cardinal_direction"] = data["cardinal_direction"].value
        return dict(sorted(data.items()))

    @classmethod
    def from_dexpi_nozzle(
        cls,
        sub_tag: str,
        nominal_diameter: Optional[str] = None,
        nominal_pressure: Optional[str] = None,
        cardinal_hint: Optional[CardinalDirection] = None
    ) -> "PortSpec":
        """Create PortSpec from DEXPI nozzle attributes.

        Args:
            sub_tag: Nozzle sub-tag (e.g., "N1")
            nominal_diameter: Nominal diameter (e.g., "DN50")
            nominal_pressure: Nominal pressure (e.g., "PN16")
            cardinal_hint: Optional cardinal direction hint for layout

        Returns:
            PortSpec instance with Standard classification
        """
        return cls(
            dexpi_classification=NumberOfPortsClassification.TwoPortValve,
            sub_tag=sub_tag,
            nominal_diameter=nominal_diameter,
            nominal_pressure=nominal_pressure,
            cardinal_direction=cardinal_hint
        )


class PortLayout:
    """Helper for computing port positions on equipment based on cardinal directions.

    This utility maps cardinal directions to relative positions on equipment
    bounding boxes for layout algorithms (like elkjs).

    Not a replacement for DEXPI's port system - just a layout helper.
    """

    @staticmethod
    def get_port_offset(
        direction: CardinalDirection,
        equipment_width: float,
        equipment_height: float
    ) -> Tuple[float, float]:
        """Compute port offset relative to equipment center.

        Args:
            direction: Cardinal direction (N/S/E/W)
            equipment_width: Equipment bounding box width
            equipment_height: Equipment bounding box height

        Returns:
            (x_offset, y_offset) relative to equipment center
        """
        offsets = {
            CardinalDirection.NORTH: (0, -equipment_height / 2),
            CardinalDirection.SOUTH: (0, equipment_height / 2),
            CardinalDirection.EAST: (equipment_width / 2, 0),
            CardinalDirection.WEST: (-equipment_width / 2, 0),
        }
        return offsets.get(direction, (0, 0))

    @staticmethod
    def distribute_ports(
        count: int,
        direction: CardinalDirection,
        equipment_width: float,
        equipment_height: float,
        spacing: float = 20.0
    ) -> List[Tuple[float, float]]:
        """Distribute multiple ports along one side of equipment.

        Args:
            count: Number of ports to distribute
            direction: Side of equipment (N/S/E/W)
            equipment_width: Equipment bounding box width
            equipment_height: Equipment bounding box height
            spacing: Spacing between ports

        Returns:
            List of (x_offset, y_offset) positions relative to equipment center
        """
        if count == 0:
            return []

        base_x, base_y = PortLayout.get_port_offset(
            direction, equipment_width, equipment_height
        )

        if count == 1:
            return [(base_x, base_y)]

        # Distribute along the appropriate axis
        positions = []
        if direction in [CardinalDirection.NORTH, CardinalDirection.SOUTH]:
            # Distribute along X axis
            total_width = (count - 1) * spacing
            start_x = base_x - total_width / 2
            for i in range(count):
                positions.append((start_x + i * spacing, base_y))
        else:
            # Distribute along Y axis
            total_height = (count - 1) * spacing
            start_y = base_y - total_height / 2
            for i in range(count):
                positions.append((base_x, start_y + i * spacing))

        return positions


# Re-export DEXPI enums for convenience
__all__ = [
    "NumberOfPortsClassification",
    "PortStatusClassification",
    "CardinalDirection",
    "PortSpec",
    "PortLayout",
]
