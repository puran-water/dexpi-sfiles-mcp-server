"""Graph metadata validators for NetworkX graphs from pyDEXPI and SFILES2.

This module provides Pydantic schemas that VALIDATE (not replace) the attribute
dictionaries produced by:
- pyDEXPI: pydexpi.loaders.ml_graph_loader.MLGraphLoader
- SFILES2: Flowsheet_Class.flowsheet.Flowsheet.state (NetworkX DiGraph)

Architecture Principle:
    Build thin validation layer over proven upstream libraries. These schemas
    ensure deterministic serialization (sorted keys) for git-friendly storage
    without reinventing the metadata formats.

Upstream Attribute Examples:
    pyDEXPI node attributes:
        {
            "dexpi_class": "Tank",
            "pos": [100, 200],
            "equipment_tag": "TK-101",
            "unit_type": "Vessel",
            # ... other pyDEXPI-specific attributes
        }

    SFILES2 node attributes:
        {
            "unit_type": "reactor",
            "unit_type_specific": {...},
            "unit": <Unit object>,
            "pos": [50, 150],
            # ... other SFILES-specific attributes
        }

    SFILES2 edge attributes:
        {
            "tags": {"he": ["HX-101"], "col": []},
            "processstream_name": "S1",
            # ... other stream properties
        }
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import networkx as nx

logger = logging.getLogger(__name__)


class NodeMetadata(BaseModel):
    """Validates node attribute dictionaries from pyDEXPI/SFILES2 graphs.

    This schema is permissive—it validates common attributes but allows
    arbitrary additional fields to preserve upstream-specific metadata.

    Common Attributes (across both pyDEXPI and SFILES2):
        pos: Node position as [x, y] coordinates (from _add_positions utility)

    pyDEXPI-specific:
        dexpi_class: Equipment class name (e.g., "Tank", "Pump")
        equipment_tag: Tag name (e.g., "TK-101")

    SFILES2-specific:
        unit_type: Process function type (e.g., "reactor", "pump")
        unit_type_specific: Dict of unit-specific parameters
        unit: Reference to Unit object (not serialized directly)
    """

    model_config = ConfigDict(extra="allow")  # Allow upstream-specific fields

    # Common attributes
    pos: Optional[List[float]] = Field(
        None,
        description="Node position [x, y] from _add_positions utility"
    )

    # pyDEXPI attributes (optional - only present in DEXPI graphs)
    dexpi_class: Optional[str] = Field(
        None,
        description="Equipment class name from pyDEXPI (e.g., 'Tank', 'Pump')"
    )
    equipment_tag: Optional[str] = Field(
        None,
        description="Equipment tag from pyDEXPI (e.g., 'TK-101')"
    )

    # SFILES2 attributes (optional - only present in SFILES graphs)
    unit_type: Optional[str] = Field(
        None,
        description="Process function type from SFILES2 (e.g., 'reactor', 'pump')"
    )
    unit_type_specific: Optional[Dict[str, Any]] = Field(
        None,
        description="Unit-specific parameters from SFILES2"
    )

    @field_validator("pos")
    @classmethod
    def validate_position(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate position is [x, y] coordinate pair."""
        if v is not None and len(v) != 2:
            raise ValueError("Position must be [x, y] coordinate pair")
        return v

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Export to dict with deterministic key ordering for git-friendly diffs.

        Args:
            exclude_none: If True, exclude None values from output

        Returns:
            Dictionary with sorted keys for deterministic serialization
        """
        data = self.model_dump(exclude_none=exclude_none)
        # Sort keys for deterministic serialization
        return dict(sorted(data.items()))


class EdgeMetadata(BaseModel):
    """Validates edge attribute dictionaries from pyDEXPI/SFILES2 graphs.

    SFILES2-specific:
        tags: Dict with "he" (heat exchanger) and "col" (column) tag lists
        processstream_name: Name of the process stream

    pyDEXPI-specific:
        piping_class: Pipe class (e.g., "CS150")
        line_number: Piping line number
    """

    model_config = ConfigDict(extra="allow")  # Allow upstream-specific fields

    # SFILES2 attributes
    tags: Optional[Dict[str, List[str]]] = Field(
        None,
        description="SFILES2 tags dict with 'he' and 'col' lists"
    )
    processstream_name: Optional[str] = Field(
        None,
        description="SFILES2 process stream name"
    )

    # pyDEXPI attributes
    piping_class: Optional[str] = Field(
        None,
        description="pyDEXPI piping class (e.g., 'CS150')"
    )
    line_number: Optional[str] = Field(
        None,
        description="pyDEXPI line number"
    )

    @field_validator("tags")
    @classmethod
    def validate_sfiles_tags(cls, v: Optional[Dict[str, List[str]]]) -> Optional[Dict[str, List[str]]]:
        """Validate SFILES2 tags structure."""
        if v is not None:
            if "he" not in v or "col" not in v:
                raise ValueError("SFILES2 tags must have 'he' and 'col' keys")
            if not isinstance(v["he"], list) or not isinstance(v["col"], list):
                raise ValueError("SFILES2 tag values must be lists")
        return v

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Export to dict with deterministic key ordering.

        Args:
            exclude_none: If True, exclude None values from output

        Returns:
            Dictionary with sorted keys for deterministic serialization
        """
        data = self.model_dump(exclude_none=exclude_none)
        return dict(sorted(data.items()))


class GraphMetadata(BaseModel):
    """Validates graph-level metadata for BFD/PFD/P&ID hierarchical system.

    Attributes:
        diagram_type: Type of diagram (BFD, PFD, PID)
        diagram_level: Abstraction level (0=BFD, 1=PFD, 2=P&ID)
        source_format: Origin format (dexpi, sfiles, networkx)
        project_name: Optional project name
        drawing_number: Optional drawing number (P&ID)
        traceability: Optional parent diagram references for hierarchical tracing
    """

    model_config = ConfigDict(extra="allow")

    diagram_type: str = Field(
        ...,
        description="Diagram type: BFD, PFD, or PID",
        pattern="^(BFD|PFD|PID)$"
    )
    diagram_level: int = Field(
        ...,
        description="Abstraction level: 0=BFD, 1=PFD, 2=P&ID",
        ge=0,
        le=2
    )
    source_format: str = Field(
        ...,
        description="Origin format: dexpi, sfiles, or networkx",
        pattern="^(dexpi|sfiles|networkx)$"
    )
    project_name: Optional[str] = Field(
        None,
        description="Project name for grouping related diagrams"
    )
    drawing_number: Optional[str] = Field(
        None,
        description="Drawing number (typically for P&ID)"
    )
    traceability: Optional[List[str]] = Field(
        None,
        description="Parent diagram IDs for hierarchical tracing (BFD→PFD→P&ID)"
    )

    def model_post_init(self, __context) -> None:
        """Validate diagram_level matches diagram_type after initialization."""
        expected = {"BFD": 0, "PFD": 1, "PID": 2}
        if self.diagram_type in expected and self.diagram_level != expected[self.diagram_type]:
            raise ValueError(f"{self.diagram_type} must have diagram_level={expected[self.diagram_type]}")

    def to_dict(self) -> Dict[str, Any]:
        """Export to dict with deterministic key ordering."""
        data = self.model_dump(exclude_none=True)
        return dict(sorted(data.items()))


class GraphMetadataSerializer:
    """Handles serialization/deserialization of NetworkX graphs with metadata.

    This class provides git-friendly JSON serialization with:
    - Deterministic key ordering (sorted)
    - Validation against upstream attribute schemas
    - Round-trip guarantees (NetworkX ↔ JSON)

    Usage:
        >>> serializer = GraphMetadataSerializer()
        >>> json_str = serializer.to_json(nx_graph, graph_metadata)
        >>> nx_graph, metadata = serializer.from_json(json_str)
    """

    def __init__(self):
        """Initialize serializer."""
        pass

    def to_json(
        self,
        graph: nx.Graph,
        metadata: GraphMetadata,
        validate: bool = True
    ) -> str:
        """Serialize NetworkX graph to JSON with metadata validation.

        Args:
            graph: NetworkX graph (from pyDEXPI or SFILES2)
            metadata: Graph-level metadata
            validate: If True, validate node/edge attributes against schemas

        Returns:
            JSON string with deterministic ordering for git diffs

        Raises:
            ValidationError: If validation enabled and attributes don't match schemas
        """
        # Extract graph structure
        nodes_data = []
        for node_id, attrs in graph.nodes(data=True):
            if validate:
                # Validate against schema (but preserve all fields)
                validated = NodeMetadata(**attrs)
                node_dict = validated.to_dict()
            else:
                node_dict = dict(sorted(attrs.items()))

            nodes_data.append({
                "id": node_id,
                "attributes": node_dict
            })

        edges_data = []
        for u, v, attrs in graph.edges(data=True):
            if validate:
                validated = EdgeMetadata(**attrs)
                edge_dict = validated.to_dict()
            else:
                edge_dict = dict(sorted(attrs.items()))

            edges_data.append({
                "source": u,
                "target": v,
                "attributes": edge_dict
            })

        # Build complete structure
        data = {
            "metadata": metadata.to_dict(),
            "graph": {
                "directed": graph.is_directed(),
                "nodes": nodes_data,
                "edges": edges_data
            }
        }

        # Serialize with deterministic ordering
        return json.dumps(data, indent=2, sort_keys=True)

    def from_json(
        self,
        json_str: str,
        validate: bool = True
    ) -> Tuple[nx.Graph, GraphMetadata]:
        """Deserialize JSON to NetworkX graph with metadata.

        Args:
            json_str: JSON string from to_json()
            validate: If True, validate against schemas during deserialization

        Returns:
            Tuple of (NetworkX graph, GraphMetadata)

        Raises:
            ValidationError: If validation enabled and data doesn't match schemas
        """
        data = json.loads(json_str)

        # Reconstruct metadata
        metadata = GraphMetadata(**data["metadata"])

        # Reconstruct graph
        graph_data = data["graph"]
        if graph_data["directed"]:
            graph = nx.DiGraph()
        else:
            graph = nx.Graph()

        # Add nodes
        for node_entry in graph_data["nodes"]:
            node_id = node_entry["id"]
            attrs = node_entry["attributes"]

            if validate:
                # Validate but preserve all fields
                validated = NodeMetadata(**attrs)
                attrs = validated.to_dict(exclude_none=False)

            graph.add_node(node_id, **attrs)

        # Add edges
        for edge_entry in graph_data["edges"]:
            u = edge_entry["source"]
            v = edge_entry["target"]
            attrs = edge_entry["attributes"]

            if validate:
                validated = EdgeMetadata(**attrs)
                attrs = validated.to_dict(exclude_none=False)

            graph.add_edge(u, v, **attrs)

        return graph, metadata

    def validate_graph(self, graph: nx.Graph) -> Dict[str, Any]:
        """Validate all node and edge attributes in graph.

        Args:
            graph: NetworkX graph to validate

        Returns:
            Validation report with success status and any errors

        """
        report = {
            "valid": True,
            "errors": [],
            "nodes_validated": 0,
            "edges_validated": 0
        }

        # Validate nodes
        for node_id, attrs in graph.nodes(data=True):
            try:
                NodeMetadata(**attrs)
                report["nodes_validated"] += 1
            except Exception as e:
                report["valid"] = False
                report["errors"].append({
                    "type": "node",
                    "id": node_id,
                    "error": str(e)
                })

        # Validate edges
        for u, v, attrs in graph.edges(data=True):
            try:
                EdgeMetadata(**attrs)
                report["edges_validated"] += 1
            except Exception as e:
                report["valid"] = False
                report["errors"].append({
                    "type": "edge",
                    "source": u,
                    "target": v,
                    "error": str(e)
                })

        return report


class GraphConversionResult(BaseModel):
    """Result of graph conversion including optional layout metadata.

    This is the metadata transport contract for the conversion pipeline.
    Converters return this result, and exporters can use the layout_metadata
    to inject Position/Extent/Presentation into Proteus XML.

    Attributes:
        graph_metadata: Graph-level metadata (diagram type, source format, etc.)
        layout_metadata: Optional layout positions for nodes
        has_positions: Whether graph nodes have position data
        component_count: Total number of components
    """

    model_config = ConfigDict(extra="allow")

    graph_metadata: GraphMetadata = Field(
        ...,
        description="Graph-level metadata"
    )

    layout_metadata: Optional[Any] = Field(  # LayoutMetadata from layout_metadata.py
        None,
        description="Optional layout positions for nodes"
    )

    has_positions: bool = Field(
        False,
        description="Whether graph nodes have position data"
    )

    component_count: int = Field(
        0,
        description="Total number of components (nodes)"
    )

    @classmethod
    def from_graph(
        cls,
        graph: nx.Graph,
        metadata: GraphMetadata,
        extract_layout: bool = True,
        layout_algorithm: str = "spring"
    ) -> "GraphConversionResult":
        """Create GraphConversionResult from NetworkX graph.

        Args:
            graph: NetworkX graph with optional 'pos' attributes
            metadata: Graph-level metadata
            extract_layout: Whether to extract layout from graph
            layout_algorithm: Name of layout algorithm used

        Returns:
            GraphConversionResult with metadata and optional layout

        Example:
            >>> result = GraphConversionResult.from_graph(
            ...     graph=nx_graph,
            ...     metadata=GraphMetadata(diagram_type="PID", ...),
            ...     layout_algorithm="spring"
            ... )
            >>> exporter.export(model, path, layout_metadata=result.layout_metadata)
        """
        # Check if positions exist
        has_positions = all(
            'pos' in attrs
            for _, attrs in graph.nodes(data=True)
        )

        # Extract layout metadata if positions exist
        layout_metadata = None
        if extract_layout and has_positions:
            layout_metadata = extract_layout_from_graph(
                graph,
                algorithm=layout_algorithm,
                generate_if_missing=False
            )

        return cls(
            graph_metadata=metadata,
            layout_metadata=layout_metadata,
            has_positions=has_positions,
            component_count=graph.number_of_nodes()
        )


def extract_layout_from_graph(
    graph: nx.Graph,
    algorithm: str = "spring",
    generate_if_missing: bool = False,
    seed: int = 42
) -> Optional[Any]:
    """Extract or generate layout metadata from graph.

    Args:
        graph: NetworkX graph
        algorithm: Algorithm name to record
        generate_if_missing: Whether to generate layout if positions missing
        seed: Random seed for reproducible layout generation

    Returns:
        LayoutMetadata if positions exist or were generated, None otherwise
    """
    # Import here to avoid circular imports
    from .layout_metadata import LayoutMetadata, NodePosition

    # Check if all nodes have positions
    all_have_pos = all('pos' in attrs for _, attrs in graph.nodes(data=True))

    if all_have_pos:
        return LayoutMetadata.from_networkx_graph(graph, algorithm=algorithm)

    if generate_if_missing:
        # Generate spring layout
        pos = nx.spring_layout(graph, seed=seed)

        # Convert to NodePosition format and scale up
        positions = {
            str(node_id): NodePosition(x=coords[0] * 500, y=coords[1] * 500)
            for node_id, coords in pos.items()
        }

        return LayoutMetadata(
            algorithm="spring (generated)",
            positions=positions,
            parameters={"seed": seed, "scale": 500}
        )

    return None
