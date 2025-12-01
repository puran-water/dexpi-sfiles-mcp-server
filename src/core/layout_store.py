"""Layout Store Module - Persistent Storage for Layout Metadata.

This module provides storage abstraction for layout metadata with:
- In-memory caching for fast access
- File-based persistence (JSON) in project directories
- Etag-based optimistic concurrency control
- Model reference linking (layouts tied to DEXPI/SFILES models)

Architecture Decision (Codex Consensus #019adb91):
    - Layouts stored alongside models in project structure
    - Etag computed from canonical content (excludes timestamps)
    - File format: {model_name}.layout.json

Usage:
    from src.core.layout_store import LayoutStore

    # Create store
    store = LayoutStore()

    # Store layout with model reference
    layout_id = store.save(layout, model_ref=ModelReference(type="dexpi", model_id="P-101"))

    # Get layout by ID
    layout = store.get(layout_id)

    # Save to project file
    store.save_to_file(layout_id, project_path="/projects/plant", model_name="reactor_pid")

    # Load from project file
    layout = store.load_from_file(project_path="/projects/plant", model_name="reactor_pid")
"""

import hashlib
import json
import logging
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.layout_metadata import (
    LayoutMetadata,
    ModelReference,
    NodePosition,
    EdgeRoute,
    EdgeSection,
    PortLayout,
    LabelPosition,
)

logger = logging.getLogger(__name__)


class OptimisticLockError(Exception):
    """Raised when etag mismatch indicates concurrent modification."""

    def __init__(self, layout_id: str, expected_etag: str, actual_etag: str):
        self.layout_id = layout_id
        self.expected_etag = expected_etag
        self.actual_etag = actual_etag
        super().__init__(
            f"Layout {layout_id} was modified (expected etag {expected_etag[:8]}..., "
            f"got {actual_etag[:8]}...)"
        )


class LayoutNotFoundError(Exception):
    """Raised when layout is not found in store."""

    def __init__(self, layout_id: str):
        self.layout_id = layout_id
        super().__init__(f"Layout {layout_id} not found")


class LayoutStore:
    """Thread-safe storage for layout metadata with file persistence.

    Provides in-memory caching with optional file-based persistence.
    Supports etag-based optimistic concurrency for safe updates.

    Example:
        store = LayoutStore()

        # Create and store layout
        layout = ELKLayoutEngine().layout(graph)
        layout_id = store.save(layout, model_ref=ModelReference(type="dexpi", model_id="P-101"))

        # Update with concurrency check
        current = store.get(layout_id)
        modified = modify_layout(current)
        store.update(layout_id, modified, expected_etag=current.etag)

        # Persist to file
        store.save_to_file(layout_id, "/projects/plant", "reactor_pid")
    """

    def __init__(self):
        """Initialize the layout store."""
        self._layouts: Dict[str, LayoutMetadata] = {}
        self._lock = threading.RLock()

    def save(
        self,
        layout: LayoutMetadata,
        layout_id: Optional[str] = None,
        model_ref: Optional[ModelReference] = None,
    ) -> str:
        """Save a new layout to the store.

        Args:
            layout: LayoutMetadata to store
            layout_id: Optional ID (auto-generated if not provided)
            model_ref: Optional reference to source model

        Returns:
            Layout ID

        Raises:
            KeyError: If layout_id already exists
        """
        with self._lock:
            if layout_id is None:
                layout_id = f"layout_{uuid.uuid4().hex[:12]}"

            if layout_id in self._layouts:
                raise KeyError(f"Layout {layout_id} already exists. Use update() instead.")

            # Create a copy and set ID/reference
            stored = deepcopy(layout)
            object.__setattr__(stored, "layout_id", layout_id)

            if model_ref is not None:
                object.__setattr__(stored, "model_ref", model_ref)

            # Ensure timestamps and etag are set
            now = datetime.now(timezone.utc).isoformat()
            if stored.created_at is None:
                object.__setattr__(stored, "created_at", now)
            object.__setattr__(stored, "updated_at", now)
            object.__setattr__(stored, "etag", stored.compute_etag())

            self._layouts[layout_id] = stored
            logger.debug(f"Saved layout {layout_id} (etag: {stored.etag[:8]}...)")

            return layout_id

    def get(self, layout_id: str, copy: bool = True) -> LayoutMetadata:
        """Retrieve a layout by ID.

        Args:
            layout_id: Layout identifier
            copy: If True (default), return deep copy. If False, return live reference.

        Returns:
            LayoutMetadata

        Raises:
            LayoutNotFoundError: If layout not found
        """
        with self._lock:
            if layout_id not in self._layouts:
                raise LayoutNotFoundError(layout_id)

            layout = self._layouts[layout_id]
            return deepcopy(layout) if copy else layout

    def update(
        self,
        layout_id: str,
        layout: LayoutMetadata,
        expected_etag: Optional[str] = None,
    ) -> str:
        """Update an existing layout with optimistic concurrency control.

        Args:
            layout_id: Layout identifier
            layout: Updated LayoutMetadata
            expected_etag: If provided, update fails if current etag doesn't match

        Returns:
            New etag after update

        Raises:
            LayoutNotFoundError: If layout not found
            OptimisticLockError: If expected_etag doesn't match current etag
        """
        with self._lock:
            if layout_id not in self._layouts:
                raise LayoutNotFoundError(layout_id)

            current = self._layouts[layout_id]

            # Check optimistic lock
            if expected_etag is not None and current.etag != expected_etag:
                raise OptimisticLockError(layout_id, expected_etag, current.etag)

            # Create updated copy
            stored = deepcopy(layout)
            object.__setattr__(stored, "layout_id", layout_id)
            object.__setattr__(stored, "created_at", current.created_at)
            object.__setattr__(stored, "version", current.version + 1)
            object.__setattr__(stored, "updated_at", datetime.now(timezone.utc).isoformat())
            object.__setattr__(stored, "etag", stored.compute_etag())

            # Preserve model reference if not provided
            if stored.model_ref is None and current.model_ref is not None:
                object.__setattr__(stored, "model_ref", current.model_ref)

            self._layouts[layout_id] = stored
            logger.debug(
                f"Updated layout {layout_id} v{stored.version} (etag: {stored.etag[:8]}...)"
            )

            return stored.etag

    def delete(self, layout_id: str) -> bool:
        """Delete a layout from the store.

        Args:
            layout_id: Layout identifier

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if layout_id not in self._layouts:
                return False

            del self._layouts[layout_id]
            logger.debug(f"Deleted layout {layout_id}")
            return True

    def exists(self, layout_id: str) -> bool:
        """Check if a layout exists in the store.

        Args:
            layout_id: Layout identifier

        Returns:
            True if layout exists
        """
        with self._lock:
            return layout_id in self._layouts

    def list_ids(self) -> List[str]:
        """List all layout IDs in the store.

        Returns:
            List of layout IDs
        """
        with self._lock:
            return list(self._layouts.keys())

    def list_by_model(self, model_type: str, model_id: str) -> List[str]:
        """List all layouts for a specific model.

        Args:
            model_type: Model type ("dexpi" or "sfiles")
            model_id: Model identifier

        Returns:
            List of layout IDs for the model
        """
        with self._lock:
            result = []
            for layout_id, layout in self._layouts.items():
                if layout.model_ref is not None:
                    if layout.model_ref.type == model_type and layout.model_ref.model_id == model_id:
                        result.append(layout_id)
            return result

    def clear(self) -> int:
        """Remove all layouts from the store.

        Returns:
            Number of layouts removed
        """
        with self._lock:
            count = len(self._layouts)
            self._layouts.clear()
            logger.debug(f"Cleared {count} layouts from store")
            return count

    # =========================================================================
    # File Persistence
    # =========================================================================

    def save_to_file(
        self,
        layout_id: str,
        project_path: str,
        model_name: str,
        model_type: str = "pid",
    ) -> Path:
        """Save layout to project file.

        Saves layout as JSON file alongside the model:
        - DEXPI: {project_path}/pid/{model_name}.layout.json
        - SFILES PFD: {project_path}/pfd/{model_name}.layout.json
        - SFILES BFD: {project_path}/bfd/{model_name}.layout.json

        Args:
            layout_id: Layout ID in store
            project_path: Path to project root
            model_name: Model name (without extension)
            model_type: Directory type ("pid", "pfd", or "bfd")

        Returns:
            Path to saved file

        Raises:
            LayoutNotFoundError: If layout not found
        """
        layout = self.get(layout_id, copy=True)
        return self._write_layout_file(layout, project_path, model_name, model_type)

    def _write_layout_file(
        self,
        layout: LayoutMetadata,
        project_path: str,
        model_name: str,
        model_type: str,
    ) -> Path:
        """Write layout to file.

        Args:
            layout: LayoutMetadata to save
            project_path: Project root path
            model_name: Model name
            model_type: Directory type

        Returns:
            Path to saved file
        """
        path = Path(project_path)
        target_dir = path / model_type
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / f"{model_name}.layout.json"

        # Convert to dict with deterministic ordering
        data = layout.to_dict(exclude_none=True)

        # Write with sorted keys for git-friendly diffs
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

        logger.info(f"Saved layout to {file_path}")
        return file_path

    def load_from_file(
        self,
        project_path: str,
        model_name: str,
        model_type: Optional[str] = None,
        layout_id: Optional[str] = None,
    ) -> str:
        """Load layout from project file into store.

        Args:
            project_path: Path to project root
            model_name: Model name (without extension)
            model_type: Directory type ("pid", "pfd", "bfd") or None to auto-detect
            layout_id: Optional ID for loaded layout (auto-generated if not provided)

        Returns:
            Layout ID in store

        Raises:
            FileNotFoundError: If layout file not found
        """
        layout = self._read_layout_file(project_path, model_name, model_type)

        # Use provided ID or generate new one
        if layout_id is None:
            layout_id = layout.layout_id or f"loaded_{model_name}"

        # Store the loaded layout
        with self._lock:
            if layout_id in self._layouts:
                # Update existing
                self._layouts[layout_id] = layout
                logger.debug(f"Updated layout {layout_id} from file")
            else:
                # Create new
                object.__setattr__(layout, "layout_id", layout_id)
                self._layouts[layout_id] = layout
                logger.debug(f"Loaded layout {layout_id} from file")

        return layout_id

    def _read_layout_file(
        self,
        project_path: str,
        model_name: str,
        model_type: Optional[str],
    ) -> LayoutMetadata:
        """Read layout from file.

        Args:
            project_path: Project root path
            model_name: Model name
            model_type: Directory type or None to auto-detect

        Returns:
            LayoutMetadata

        Raises:
            FileNotFoundError: If file not found
        """
        path = Path(project_path)
        file_path: Optional[Path] = None

        if model_type is not None:
            file_path = path / model_type / f"{model_name}.layout.json"
            if not file_path.exists():
                raise FileNotFoundError(f"Layout file not found: {file_path}")
        else:
            # Auto-detect by searching directories
            for dir_name in ["pid", "pfd", "bfd"]:
                candidate = path / dir_name / f"{model_name}.layout.json"
                if candidate.exists():
                    file_path = candidate
                    break

            if file_path is None:
                raise FileNotFoundError(
                    f"Layout file for {model_name} not found in pid/, pfd/, or bfd/"
                )

        # Load JSON
        with open(file_path, "r") as f:
            data = json.load(f)

        # Convert to LayoutMetadata
        return self._dict_to_layout(data)

    def _dict_to_layout(self, data: Dict[str, Any]) -> LayoutMetadata:
        """Convert dictionary to LayoutMetadata.

        Handles nested object reconstruction and format conversion.

        Args:
            data: Dictionary from JSON file

        Returns:
            LayoutMetadata instance
        """
        # Convert positions (may be stored as [x, y] lists)
        positions = {}
        for node_id, pos in data.get("positions", {}).items():
            if isinstance(pos, list):
                positions[node_id] = NodePosition(x=pos[0], y=pos[1])
            elif isinstance(pos, dict):
                positions[node_id] = NodePosition(**pos)
            else:
                positions[node_id] = pos

        # Convert port layouts
        port_layouts = {}
        for port_id, port_data in data.get("port_layouts", {}).items():
            if isinstance(port_data, dict):
                port_layouts[port_id] = PortLayout(**port_data)
            else:
                port_layouts[port_id] = port_data

        # Convert edge routes
        edges = {}
        for edge_id, edge_data in data.get("edges", {}).items():
            if isinstance(edge_data, dict):
                # Convert sections
                sections = []
                for section_data in edge_data.get("sections", []):
                    # Convert points from lists to tuples
                    start_point = tuple(section_data["startPoint"])
                    end_point = tuple(section_data["endPoint"])
                    bend_points = [tuple(bp) for bp in section_data.get("bendPoints", [])]
                    sections.append(EdgeSection(
                        id=section_data.get("id"),
                        startPoint=start_point,
                        endPoint=end_point,
                        bendPoints=bend_points,
                    ))

                # Convert labels
                labels = []
                for label_data in edge_data.get("labels", []):
                    if isinstance(label_data, dict):
                        labels.append(LabelPosition(**label_data))
                    else:
                        labels.append(label_data)

                edges[edge_id] = EdgeRoute(
                    sections=sections,
                    source_port=edge_data.get("source_port"),
                    target_port=edge_data.get("target_port"),
                    sourcePoint=tuple(edge_data["sourcePoint"]) if edge_data.get("sourcePoint") else None,
                    targetPoint=tuple(edge_data["targetPoint"]) if edge_data.get("targetPoint") else None,
                    labels=labels,
                )
            else:
                edges[edge_id] = edge_data

        # Convert labels
        labels = {}
        for label_id, label_data in data.get("labels", {}).items():
            if isinstance(label_data, dict):
                labels[label_id] = LabelPosition(**label_data)
            else:
                labels[label_id] = label_data

        # Convert model reference
        model_ref = None
        if data.get("model_ref"):
            model_ref = ModelReference(**data["model_ref"])

        # Convert page_size if present (stored as list)
        page_size = data.get("page_size")
        if isinstance(page_size, list):
            page_size = tuple(page_size)

        # Build LayoutMetadata
        return LayoutMetadata(
            layout_id=data.get("layout_id"),
            model_ref=model_ref,
            model_revision=data.get("model_revision"),
            version=data.get("version", 1),
            etag=data.get("etag"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            created_by=data.get("created_by"),
            algorithm=data["algorithm"],
            layout_options=data.get("layout_options", {}),
            positions=positions,
            port_layouts=port_layouts,
            edges=edges,
            labels=labels,
            page_size=page_size if page_size else (841.0, 594.0),
            units=data.get("units", "mm"),
            origin=data.get("origin", "top-left"),
            rotation=data.get("rotation", {}),
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_etag(self, layout_id: str) -> str:
        """Get the current etag for a layout.

        Args:
            layout_id: Layout identifier

        Returns:
            Current etag

        Raises:
            LayoutNotFoundError: If layout not found
        """
        with self._lock:
            if layout_id not in self._layouts:
                raise LayoutNotFoundError(layout_id)
            return self._layouts[layout_id].etag

    def __contains__(self, layout_id: str) -> bool:
        """Support 'layout_id in store' syntax."""
        return self.exists(layout_id)

    def __len__(self) -> int:
        """Return number of layouts in store."""
        with self._lock:
            return len(self._layouts)

    def __iter__(self):
        """Iterate over layout IDs."""
        return iter(self.list_ids())


# Factory function
def create_layout_store() -> LayoutStore:
    """Create a new layout store instance.

    Returns:
        LayoutStore instance
    """
    return LayoutStore()


__all__ = [
    "LayoutStore",
    "LayoutNotFoundError",
    "OptimisticLockError",
    "create_layout_store",
]
