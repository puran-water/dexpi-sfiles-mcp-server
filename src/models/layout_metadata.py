"""Layout metadata for persisting graph node positions and edge routing.

This module provides schemas for persisting layout information including:
- Node positions (x, y coordinates)
- Port layouts (positions and constraints)
- Edge routing (orthogonal sections with bend points)
- Labels (positions for text annotations)

Architecture Decision (Codex Consensus #019adb91):
    - Separate layout layer from topology (DEXPI/SFILES = topology, Layout = coordinates)
    - Store ELK-native coordinates (top-left origin, mm)
    - Use etag-based optimistic concurrency
    - Persist edge sections with startPoint/endPoint/bendPoints

Upstream Integration:
    - ELK via elkjs: Provides orthogonal edge routing and port-aware layout
    - SFILES2: Uses _add_positions(g, layout='spring') for spring layout
    - pyDEXPI: MLGraphLoader for DEXPI model positioning
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class NodePosition(BaseModel):
    """Position of a single node in 2D layout space.

    BFD/PFD/P&ID diagrams are strictly 2D - no depth coordinate needed.

    Attributes:
        x: Horizontal coordinate
        y: Vertical coordinate
    """

    x: float = Field(..., description="Horizontal coordinate")
    y: float = Field(..., description="Vertical coordinate")

    @classmethod
    def from_list(cls, pos: List[float]) -> "NodePosition":
        """Create NodePosition from [x, y] list.

        Args:
            pos: Position as [x, y]

        Returns:
            NodePosition instance

        Raises:
            ValueError: If pos doesn't have exactly 2 elements
        """
        if len(pos) != 2:
            raise ValueError(f"Position must be [x, y], got {len(pos)} elements")
        return cls(x=pos[0], y=pos[1])

    def to_list(self) -> List[float]:
        """Convert to list format [x, y].

        Returns:
            Position as [x, y] list
        """
        return [self.x, self.y]


class BoundingBox(BaseModel):
    """Bounding box for a node or entire graph.

    Attributes:
        min_x: Minimum x coordinate
        max_x: Maximum x coordinate
        min_y: Minimum y coordinate
        max_y: Maximum y coordinate
        width: Computed width (max_x - min_x)
        height: Computed height (max_y - min_y)
    """

    min_x: float = Field(..., description="Minimum x coordinate")
    max_x: float = Field(..., description="Maximum x coordinate")
    min_y: float = Field(..., description="Minimum y coordinate")
    max_y: float = Field(..., description="Maximum y coordinate")

    @property
    def width(self) -> float:
        """Computed width of bounding box."""
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Computed height of bounding box."""
        return self.max_y - self.min_y

    @property
    def center(self) -> Tuple[float, float]:
        """Computed center point of bounding box."""
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )

    @classmethod
    def from_positions(cls, positions: Dict[str, NodePosition]) -> "BoundingBox":
        """Compute bounding box from node positions.

        Args:
            positions: Dictionary of node_id -> NodePosition

        Returns:
            BoundingBox encompassing all positions

        Raises:
            ValueError: If positions is empty
        """
        if not positions:
            raise ValueError("Cannot compute bounding box from empty positions")

        x_coords = [pos.x for pos in positions.values()]
        y_coords = [pos.y for pos in positions.values()]

        return cls(
            min_x=min(x_coords),
            max_x=max(x_coords),
            min_y=min(y_coords),
            max_y=max(y_coords)
        )


# =============================================================================
# New Schema Classes (Codex Consensus #019adb91)
# =============================================================================


class LabelPosition(BaseModel):
    """Position and properties for a text label.

    Used for node labels, edge labels (line numbers), and port labels.
    """

    x: float = Field(..., description="X coordinate of label")
    y: float = Field(..., description="Y coordinate of label")
    width: float = Field(default=0.0, description="Label width (for bounding)")
    height: float = Field(default=0.0, description="Label height (for bounding)")
    text: str = Field(default="", description="Label text content")
    rotation: float = Field(default=0.0, description="Rotation angle in degrees")
    rotation_origin: Literal["center", "top-left"] = Field(
        default="center", description="Point around which rotation is applied"
    )
    kind: Literal["node", "edge", "port"] = Field(
        default="node", description="Owner type of this label"
    )


class EdgeSection(BaseModel):
    """A segment of an edge route.

    ELK uses sections to represent edge routing, especially for long edges
    that may have multiple segments. Each section has a start point, end point,
    and optional bend points for orthogonal routing.
    """

    id: Optional[str] = Field(default=None, description="Section ID (ELK may omit)")
    startPoint: Tuple[float, float] = Field(..., description="Start point (x, y)")
    endPoint: Tuple[float, float] = Field(..., description="End point (x, y)")
    bendPoints: List[Tuple[float, float]] = Field(
        default_factory=list, description="Bend points for orthogonal routing"
    )

    def get_all_points(self) -> List[Tuple[float, float]]:
        """Get all points in order: start -> bends -> end."""
        return [self.startPoint] + self.bendPoints + [self.endPoint]


class EdgeRoute(BaseModel):
    """Complete routing data for an edge/connection.

    Contains one or more sections that define the visual path of an edge,
    plus metadata about source/target ports and labels.
    """

    sections: List[EdgeSection] = Field(
        default_factory=list, description="Edge sections (segments)"
    )
    source_port: Optional[str] = Field(
        default=None, description="Source port ID"
    )
    target_port: Optional[str] = Field(
        default=None, description="Target port ID"
    )
    sourcePoint: Optional[Tuple[float, float]] = Field(
        default=None, description="Overall edge start point"
    )
    targetPoint: Optional[Tuple[float, float]] = Field(
        default=None, description="Overall edge end point"
    )
    labels: List[LabelPosition] = Field(
        default_factory=list, description="Edge labels (line numbers, etc.)"
    )

    def get_all_points(self) -> List[Tuple[float, float]]:
        """Get all points from all sections in order."""
        points = []
        for section in self.sections:
            section_points = section.get_all_points()
            # Avoid duplicate points at section boundaries
            if points and section_points and points[-1] == section_points[0]:
                section_points = section_points[1:]
            points.extend(section_points)
        return points


class PortLayout(BaseModel):
    """Position and constraint data for a port.

    Ports are connection points on equipment nodes. Their positions
    are computed by ELK based on constraints like side and order.
    """

    id: str = Field(..., description="Port ID")
    x: float = Field(..., description="X position relative to parent node")
    y: float = Field(..., description="Y position relative to parent node")
    width: float = Field(default=8.0, description="Port width")
    height: float = Field(default=8.0, description="Port height")
    side: Literal["NORTH", "SOUTH", "EAST", "WEST"] = Field(
        ..., description="Side of parent node where port is placed"
    )
    index: int = Field(
        default=0, description="Order index for stable port ordering"
    )
    anchor: Optional[Tuple[float, float]] = Field(
        default=None, description="Anchor point relative to node (for high-fidelity)"
    )


class ModelReference(BaseModel):
    """Reference to a source model (DEXPI or SFILES).

    Links a layout to its source topology model.
    """

    # Allow model_id field name
    model_config = {"protected_namespaces": ()}

    type: Literal["dexpi", "sfiles"] = Field(
        ..., description="Model type"
    )
    model_id: str = Field(..., description="Model ID in the store")


class LayoutMetadata(BaseModel):
    """Layout metadata for a graph with positioned nodes.

    This schema validates and persists layout information generated by upstream
    utilities (ELK, SFILES2's _add_positions, pyDEXPI's positioning, etc.).

    Extended in Codex Consensus #019adb91 to include:
    - Edge routing with orthogonal sections
    - Port layouts with side constraints
    - Labels with rotation
    - Versioning with etag for optimistic concurrency
    - Model reference for topology linkage

    Attributes:
        layout_id: Unique identifier for this layout
        model_ref: Reference to source model (DEXPI/SFILES)
        model_revision: Hash of source model when layout was created
        version: Layout version number
        etag: SHA-256 hash for optimistic concurrency (excludes timestamps)
        created_at: ISO 8601 timestamp when layout was created
        updated_at: ISO 8601 timestamp when layout was last modified
        created_by: Optional creator identifier
        algorithm: Layout algorithm used (e.g., 'elk', 'spring', 'manual')
        layout_options: Algorithm-specific options (e.g., ELK options)
        positions: Dictionary of node_id -> NodePosition
        port_layouts: Dictionary of port_id -> PortLayout
        edges: Dictionary of edge_id -> EdgeRoute
        labels: Dictionary of label_id -> LabelPosition (node labels)
        page_size: Page dimensions (width, height) in units
        units: Coordinate units (default 'mm')
        origin: Coordinate origin (default 'top-left')
        rotation: Dictionary of node_id -> rotation angle in degrees
        bounding_box: Overall bounding box (auto-computed)
        parameters: DEPRECATED - use layout_options
        timestamp: DEPRECATED - use created_at/updated_at
    """

    # Pydantic config to allow model_ref/model_revision field names
    model_config = {"protected_namespaces": ()}

    # Identity (new fields - optional for backward compatibility)
    layout_id: Optional[str] = Field(
        default=None, description="Unique layout identifier"
    )
    model_ref: Optional[ModelReference] = Field(
        default=None, description="Reference to source model"
    )
    model_revision: Optional[str] = Field(
        default=None, description="SHA-256 hash of source model when layout was created"
    )

    # Versioning (new fields)
    version: int = Field(default=1, description="Layout version number")
    etag: Optional[str] = Field(
        default=None, description="SHA-256 hash for optimistic concurrency"
    )
    created_at: Optional[str] = Field(
        default=None, description="ISO 8601 creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None, description="ISO 8601 last modification timestamp"
    )
    created_by: Optional[str] = Field(
        default=None, description="Creator identifier"
    )

    # Core layout data (existing field)
    algorithm: str = Field(
        ..., description="Layout algorithm used (elk, spring, hierarchical, manual)"
    )
    layout_options: Dict[str, Any] = Field(
        default_factory=dict, description="Algorithm-specific options (e.g., ELK options)"
    )
    positions: Dict[str, NodePosition] = Field(
        ..., description="Node positions keyed by node ID"
    )

    # Extended layout data (new fields)
    port_layouts: Dict[str, PortLayout] = Field(
        default_factory=dict, description="Port positions keyed by port ID"
    )
    edges: Dict[str, EdgeRoute] = Field(
        default_factory=dict, description="Edge routing keyed by edge ID"
    )
    labels: Dict[str, LabelPosition] = Field(
        default_factory=dict, description="Node labels keyed by label ID"
    )

    # Page settings (new fields)
    page_size: Tuple[float, float] = Field(
        default=(841.0, 594.0), description="Page dimensions (width, height) - A1 landscape"
    )
    units: str = Field(default="mm", description="Coordinate units")
    origin: str = Field(default="top-left", description="Coordinate origin")
    rotation: Dict[str, float] = Field(
        default_factory=dict, description="Node rotations keyed by node ID (degrees)"
    )

    # Computed fields (existing)
    bounding_box: Optional[BoundingBox] = Field(
        default=None, description="Overall bounding box (auto-computed if not provided)"
    )

    # DEPRECATED fields (kept for backward compatibility)
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="DEPRECATED: Use layout_options instead"
    )
    timestamp: Optional[str] = Field(
        default=None, description="DEPRECATED: Use created_at/updated_at instead"
    )

    @field_validator("positions")
    @classmethod
    def validate_positions_not_empty(
        cls, v: Dict[str, NodePosition]
    ) -> Dict[str, NodePosition]:
        """Validate that positions dictionary is not empty."""
        if not v:
            raise ValueError("Layout must have at least one positioned node")
        return v

    def model_post_init(self, __context) -> None:
        """Compute bounding box and etag if not provided."""
        # Auto-compute bounding box
        if self.bounding_box is None and self.positions:
            object.__setattr__(
                self, "bounding_box", BoundingBox.from_positions(self.positions)
            )

        # Auto-set timestamps
        now = datetime.now(timezone.utc).isoformat()
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", now)

        # Auto-compute etag if not provided
        if self.etag is None:
            object.__setattr__(self, "etag", self.compute_etag())

    def compute_etag(self) -> str:
        """Compute SHA-256 etag from canonical content (excludes timestamps).

        The etag is computed from a canonical JSON representation of:
        - positions, port_layouts, edges, labels, rotation
        - layout_options, algorithm
        - page_size, units, origin

        Timestamps are excluded so etag only changes on content changes.

        Returns:
            64-character hex string (SHA-256 hash)
        """
        # Build canonical content dict (sorted keys, no timestamps)
        canonical = {
            "algorithm": self.algorithm,
            "edges": {
                k: v.model_dump() for k, v in sorted(self.edges.items())
            },
            "labels": {
                k: v.model_dump() for k, v in sorted(self.labels.items())
            },
            "layout_options": dict(sorted(self.layout_options.items())),
            "origin": self.origin,
            "page_size": list(self.page_size),
            "port_layouts": {
                k: v.model_dump() for k, v in sorted(self.port_layouts.items())
            },
            "positions": {
                k: v.model_dump() for k, v in sorted(self.positions.items())
            },
            "rotation": dict(sorted(self.rotation.items())),
            "units": self.units,
        }

        # Serialize to canonical JSON (sorted, no spaces)
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode()).hexdigest()

    def touch(self) -> None:
        """Update timestamps and recompute etag after modification."""
        now = datetime.now(timezone.utc).isoformat()
        object.__setattr__(self, "updated_at", now)
        object.__setattr__(self, "etag", self.compute_etag())

    @classmethod
    def from_networkx_graph(
        cls,
        graph,
        algorithm: str = "spring",
        parameters: Optional[Dict[str, Any]] = None
    ) -> "LayoutMetadata":
        """Extract layout metadata from NetworkX graph with 'pos' attributes.

        Args:
            graph: NetworkX graph with 'pos' attributes on nodes
            algorithm: Layout algorithm name to record
            parameters: Optional algorithm parameters to record

        Returns:
            LayoutMetadata instance

        Raises:
            ValueError: If any node is missing 'pos' attribute
        """
        positions = {}

        for node_id, attrs in graph.nodes(data=True):
            if 'pos' not in attrs:
                raise ValueError(f"Node {node_id} is missing 'pos' attribute")

            pos_list = attrs['pos']
            positions[node_id] = NodePosition.from_list(pos_list)

        return cls(
            algorithm=algorithm,
            positions=positions,
            parameters=parameters
        )

    def apply_to_networkx_graph(self, graph) -> None:
        """Apply layout positions to NetworkX graph as 'pos' attributes.

        Args:
            graph: NetworkX graph to update

        Note:
            Only updates nodes that exist in both the layout and the graph.
            Logs a warning for any missing nodes.
        """
        for node_id, position in self.positions.items():
            if node_id not in graph.nodes:
                logger.warning(f"Layout has position for {node_id} but node not in graph")
                continue

            graph.nodes[node_id]['pos'] = position.to_list()

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Export to dict with deterministic key ordering.

        Args:
            exclude_none: If True, exclude None values from output

        Returns:
            Dictionary with sorted keys for git-friendly diffs
        """
        # Convert to dict
        data = self.model_dump(exclude_none=exclude_none)

        # Convert nested NodePosition objects to lists
        if 'positions' in data:
            data['positions'] = {
                node_id: NodePosition(**pos_data).to_list()
                for node_id, pos_data in data['positions'].items()
            }

        # Sort top-level keys
        return dict(sorted(data.items()))


class LayoutCollection(BaseModel):
    """Collection of multiple layouts for the same graph.

    Useful for storing different layout algorithms or user-customized versions.

    Attributes:
        default_layout: Name of the default layout to use
        layouts: Dictionary of layout_name -> LayoutMetadata
    """

    default_layout: str = Field(
        ...,
        description="Name of the default layout"
    )

    layouts: Dict[str, LayoutMetadata] = Field(
        ...,
        description="Available layouts keyed by name"
    )

    @field_validator('layouts')
    @classmethod
    def validate_layouts_not_empty(cls, v: Dict[str, LayoutMetadata]) -> Dict[str, LayoutMetadata]:
        """Validate that layouts dictionary is not empty."""
        if not v:
            raise ValueError("LayoutCollection must have at least one layout")
        return v

    def model_post_init(self, __context) -> None:
        """Validate that default_layout exists in layouts."""
        if self.default_layout not in self.layouts:
            raise ValueError(
                f"default_layout '{self.default_layout}' not found in layouts. "
                f"Available: {list(self.layouts.keys())}"
            )

    def get_default(self) -> LayoutMetadata:
        """Get the default layout.

        Returns:
            Default LayoutMetadata instance
        """
        return self.layouts[self.default_layout]

    def add_layout(self, name: str, layout: LayoutMetadata, set_as_default: bool = False) -> None:
        """Add a layout to the collection.

        Args:
            name: Name for the layout
            layout: LayoutMetadata to add
            set_as_default: If True, set this as the default layout
        """
        self.layouts[name] = layout
        if set_as_default:
            self.default_layout = name


__all__ = [
    # Core position types
    "NodePosition",
    "BoundingBox",
    # New schema types (Codex Consensus #019adb91)
    "LabelPosition",
    "EdgeSection",
    "EdgeRoute",
    "PortLayout",
    "ModelReference",
    # Layout metadata
    "LayoutMetadata",
    "LayoutCollection",
]
