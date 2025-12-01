"""Base layout engine protocol.

Defines the interface that all layout engines must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.models.layout_metadata import LayoutMetadata


class LayoutEngine(ABC):
    """Abstract base class for layout engines.

    Layout engines convert graph topology into positioned layouts
    with node coordinates, port positions, and edge routing.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name (e.g., 'elk', 'spring')."""
        ...

    @property
    @abstractmethod
    def supports_orthogonal_routing(self) -> bool:
        """Whether engine supports orthogonal (Manhattan) edge routing."""
        ...

    @property
    @abstractmethod
    def supports_ports(self) -> bool:
        """Whether engine supports port-aware layout."""
        ...

    @abstractmethod
    async def layout(
        self,
        graph: Any,
        options: Optional[Dict[str, Any]] = None,
    ) -> LayoutMetadata:
        """Compute layout for a graph.

        Args:
            graph: Graph to layout (NetworkX DiGraph or similar)
            options: Engine-specific layout options

        Returns:
            LayoutMetadata with positions, edges, ports
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if engine is available (dependencies installed).

        Returns:
            True if engine can be used
        """
        ...
