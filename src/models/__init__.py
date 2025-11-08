"""Graph metadata models for BFD/PFD/P&ID hierarchical system.

This module provides Pydantic validation schemas for NetworkX graph metadata
produced by upstream libraries (pyDEXPI, SFILES2). It does NOT replace upstream
formats—it validates and serializes them in a git-friendly manner.

Architecture Decision (Codex Review #3):
    "Don't re-invent typed metadata classes. Leverage the existing Pydantic models
    and the graph loader's attribute schema."
"""

from .graph_metadata import (
    NodeMetadata,
    EdgeMetadata,
    GraphMetadata,
    GraphMetadataSerializer,
)
from .port_spec import (
    CardinalDirection,
    PortSpec,
    PortLayout,
)

# Re-export all DEXPI enumerations from centralized module
from . import dexpi_enums

__all__ = [
    # Graph metadata
    "NodeMetadata",
    "EdgeMetadata",
    "GraphMetadata",
    "GraphMetadataSerializer",

    # Port specifications
    "CardinalDirection",
    "PortSpec",
    "PortLayout",

    # DEXPI enumerations (re-export entire module)
    "dexpi_enums",
]
