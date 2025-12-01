"""
Core Model Store Module - Unified Model Storage Abstraction

This module provides a thread-safe abstraction for model storage with:
- Full CRUD operations (create, get, update, delete, exists, list)
- Lifecycle hooks for caching, validation, and event propagation
- Snapshot/rollback capability for transaction support
- Metadata tracking (created_at, modified_at, access patterns)

Week 7 Implementation: Replaces dict-based storage in server.py with
proper abstraction supporting future persistence backends.

Usage:
    from src.core.model_store import InMemoryModelStore, ModelType

    # Create stores
    dexpi_store = InMemoryModelStore(ModelType.DEXPI)
    sfiles_store = InMemoryModelStore(ModelType.SFILES)

    # CRUD operations
    metadata = dexpi_store.create("model-123", model)
    model = dexpi_store.get("model-123")
    dexpi_store.update("model-123", updated_model)

    # Snapshots for transactions
    snapshot = dexpi_store.create_snapshot("model-123", "before-changes")
    # ... make changes ...
    dexpi_store.restore_snapshot(snapshot)  # rollback
"""

import logging
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Enums and Types
# ============================================================================

class ModelType(Enum):
    """Model type identifiers for storage categorization."""
    DEXPI = "dexpi"
    SFILES = "sfiles"


@dataclass
class ModelMetadata:
    """Metadata tracked for each stored model.

    Attributes:
        model_id: Unique identifier for the model
        model_type: Type of model (DEXPI or SFILES)
        created_at: Timestamp when model was created
        modified_at: Timestamp of last modification
        access_count: Number of times model was accessed
        last_accessed: Timestamp of last access
        tags: User-defined key-value tags for organization
    """
    model_id: str
    model_type: ModelType
    created_at: datetime
    modified_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "model_id": self.model_id,
            "model_type": self.model_type.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "tags": self.tags
        }


@dataclass
class Snapshot:
    """Immutable snapshot of a model state for rollback support.

    Snapshots are created before potentially destructive operations
    (like batch updates or transactions) and can be restored if needed.

    Attributes:
        model_id: ID of the model this snapshot belongs to
        timestamp: When the snapshot was created
        state: Deep copy of the model state
        label: Optional human-readable label for the snapshot
    """
    model_id: str
    timestamp: datetime
    state: Any  # Deep copy of model
    label: Optional[str] = None


# ============================================================================
# Lifecycle Hooks
# ============================================================================

class LifecycleHook:
    """Base class for model lifecycle event handlers.

    Subclass and override methods to respond to model lifecycle events.
    Common uses: cache invalidation, audit logging, validation triggers.

    Example:
        class LoggingHook(LifecycleHook):
            def on_created(self, model_id, model, metadata):
                logger.info(f"Model {model_id} created")
    """

    def on_created(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
        """Called after a model is created."""
        pass

    def on_updated(self, model_id: str, old_model: Any, new_model: Any,
                   metadata: ModelMetadata) -> None:
        """Called after a model is updated."""
        pass

    def on_deleted(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
        """Called after a model is deleted."""
        pass

    def on_accessed(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
        """Called after a model is accessed (get operation)."""
        pass


class CachingHook(LifecycleHook):
    """Lifecycle hook that maintains derived data caches.

    Automatically invalidates cached data when models are updated or deleted.
    Use this to cache expensive computations like graph analysis or statistics.

    Example:
        caching = CachingHook()
        store.add_hook(caching)

        # Cache expensive graph computation
        if not caching.get_cached_graph(model_id):
            graph = compute_graph(model)
            caching.cache_graph(model_id, graph)

        # Update model - cache auto-invalidated
        store.update(model_id, new_model)
        assert caching.get_cached_graph(model_id) is None
    """

    def __init__(self):
        self._graph_cache: Dict[str, Any] = {}
        self._stats_cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def on_updated(self, model_id: str, old_model: Any, new_model: Any,
                   metadata: ModelMetadata) -> None:
        """Invalidate caches when model is updated."""
        with self._lock:
            self._graph_cache.pop(model_id, None)
            self._stats_cache.pop(model_id, None)

    def on_deleted(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
        """Invalidate caches when model is deleted."""
        with self._lock:
            self._graph_cache.pop(model_id, None)
            self._stats_cache.pop(model_id, None)

    def get_cached_graph(self, model_id: str) -> Optional[Any]:
        """Get cached graph for a model, if available."""
        with self._lock:
            return self._graph_cache.get(model_id)

    def cache_graph(self, model_id: str, graph: Any) -> None:
        """Cache a graph for a model."""
        with self._lock:
            self._graph_cache[model_id] = graph

    def get_cached_stats(self, model_id: str) -> Optional[Dict]:
        """Get cached statistics for a model, if available."""
        with self._lock:
            return self._stats_cache.get(model_id)

    def cache_stats(self, model_id: str, stats: Dict) -> None:
        """Cache statistics for a model."""
        with self._lock:
            self._stats_cache[model_id] = stats

    def clear_all(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._graph_cache.clear()
            self._stats_cache.clear()


# ============================================================================
# Model Store Abstract Base Class
# ============================================================================

class ModelStore(ABC, Generic[T]):
    """Abstract base class for model storage with full lifecycle support.

    Implementations must provide thread-safe CRUD operations, snapshot
    management, and lifecycle hook dispatch.

    Type parameter T is the model type being stored (e.g., PlantModel for
    DEXPI or Flowsheet for SFILES).
    """

    @abstractmethod
    def create(self, model_id: str, model: T, **kwargs) -> ModelMetadata:
        """Create a new model in the store.

        Args:
            model_id: Unique identifier for the model
            model: The model object to store
            **kwargs: Additional metadata (tags, etc.)

        Returns:
            ModelMetadata for the created model

        Raises:
            KeyError: If model_id already exists
        """
        pass

    @abstractmethod
    def get(self, model_id: str, copy: bool = False) -> Optional[T]:
        """Retrieve a model by ID.

        Args:
            model_id: Model identifier
            copy: If True, return a deep copy (safe for mutation).
                  If False (default), return live reference (faster but mutable).

        Returns:
            The model if found, None otherwise
        """
        pass

    @abstractmethod
    def update(self, model_id: str, model: T) -> ModelMetadata:
        """Update an existing model.

        Args:
            model_id: Model identifier
            model: Updated model object

        Returns:
            Updated ModelMetadata

        Raises:
            KeyError: If model_id doesn't exist
        """
        pass

    @abstractmethod
    def delete(self, model_id: str) -> bool:
        """Delete a model from the store.

        Args:
            model_id: Model identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, model_id: str) -> bool:
        """Check if a model exists in the store.

        Args:
            model_id: Model identifier

        Returns:
            True if model exists, False otherwise
        """
        pass

    @abstractmethod
    def list_ids(self) -> List[str]:
        """List all model IDs in the store.

        Returns:
            List of model IDs
        """
        pass

    @abstractmethod
    def get_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get metadata for a model.

        Args:
            model_id: Model identifier

        Returns:
            ModelMetadata if found, None otherwise
        """
        pass

    # Snapshot operations
    @abstractmethod
    def create_snapshot(self, model_id: str, label: Optional[str] = None) -> Snapshot:
        """Create an immutable snapshot of the current model state.

        Args:
            model_id: Model identifier
            label: Optional human-readable label

        Returns:
            Snapshot object containing deep copy of model state

        Raises:
            KeyError: If model_id doesn't exist
        """
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot: Snapshot) -> None:
        """Restore a model to a previous snapshot state.

        Args:
            snapshot: Snapshot to restore from

        Raises:
            KeyError: If snapshot's model_id doesn't exist
        """
        pass

    @abstractmethod
    def list_snapshots(self, model_id: str) -> List[Snapshot]:
        """List all snapshots for a model.

        Args:
            model_id: Model identifier

        Returns:
            List of snapshots, oldest first
        """
        pass

    # Hook management
    @abstractmethod
    def add_hook(self, hook: LifecycleHook) -> None:
        """Register a lifecycle hook.

        Args:
            hook: LifecycleHook instance to register
        """
        pass

    @abstractmethod
    def remove_hook(self, hook: LifecycleHook) -> None:
        """Unregister a lifecycle hook.

        Args:
            hook: LifecycleHook instance to remove
        """
        pass

    # Edit context manager
    @abstractmethod
    def edit(self, model_id: str) -> Generator[T, None, None]:
        """Context manager for safe model mutation with auto-update.

        Yields the live model for in-place modifications. On successful exit,
        automatically calls update() to trigger hooks and update metadata.
        On exception, changes are NOT reverted (use snapshots for rollback).

        Example:
            with store.edit("model-123") as model:
                model.add_equipment(...)
                model.connect(...)
            # update() called automatically on exit

        Args:
            model_id: Model identifier

        Yields:
            The live model object for modification

        Raises:
            KeyError: If model_id doesn't exist
        """
        pass


# ============================================================================
# In-Memory Implementation
# ============================================================================

class InMemoryModelStore(ModelStore[T]):
    """Thread-safe in-memory implementation of ModelStore.

    Stores models in memory with full lifecycle hook support and
    snapshot/rollback capability. Suitable for development and
    single-process deployments.

    Example:
        store = InMemoryModelStore(ModelType.DEXPI)

        # Create model
        metadata = store.create("model-123", my_model, tags={"project": "test"})

        # Access model
        model = store.get("model-123")

        # Snapshot before changes
        snapshot = store.create_snapshot("model-123", "before-refactor")

        # Update
        store.update("model-123", modified_model)

        # Rollback if needed
        store.restore_snapshot(snapshot)
    """

    def __init__(self, model_type: ModelType):
        """Initialize the in-memory store.

        Args:
            model_type: Type of models this store holds (DEXPI or SFILES)
        """
        self._model_type = model_type
        self._models: Dict[str, T] = {}
        self._metadata: Dict[str, ModelMetadata] = {}
        self._snapshots: Dict[str, List[Snapshot]] = {}
        self._hooks: List[LifecycleHook] = []
        self._lock = threading.RLock()

    @property
    def model_type(self) -> ModelType:
        """Get the model type for this store."""
        return self._model_type

    def create(self, model_id: str, model: T, **kwargs) -> ModelMetadata:
        """Create a new model in the store."""
        with self._lock:
            if model_id in self._models:
                raise KeyError(f"Model {model_id} already exists")

            now = datetime.now()
            metadata = ModelMetadata(
                model_id=model_id,
                model_type=self._model_type,
                created_at=now,
                modified_at=now,
                tags=kwargs.get('tags', {})
            )

            self._models[model_id] = model
            self._metadata[model_id] = metadata
            self._snapshots[model_id] = []

            logger.debug(f"Created {self._model_type.value} model: {model_id}")

            # Dispatch hooks (outside lock to prevent deadlock)
            for hook in self._hooks:
                try:
                    hook.on_created(model_id, model, metadata)
                except Exception as e:
                    logger.warning(f"Hook on_created failed: {e}")

            return metadata

    def get(self, model_id: str, copy: bool = False) -> Optional[T]:
        """Retrieve a model by ID.

        Args:
            model_id: Model identifier
            copy: If True, return a deep copy (safe for mutation).
                  If False (default), return live reference (faster but mutable).
        """
        with self._lock:
            model = self._models.get(model_id)
            if model is None:
                return None

            # Update access metadata
            metadata = self._metadata[model_id]
            metadata.access_count += 1
            metadata.last_accessed = datetime.now()

            # Return copy if requested
            result = deepcopy(model) if copy else model

        # Dispatch hooks (outside lock)
        for hook in self._hooks:
            try:
                hook.on_accessed(model_id, model, metadata)
            except Exception as e:
                logger.warning(f"Hook on_accessed failed: {e}")

        return result

    def update(self, model_id: str, model: T) -> ModelMetadata:
        """Update an existing model."""
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model {model_id} not found")

            old_model = self._models[model_id]
            self._models[model_id] = model

            metadata = self._metadata[model_id]
            metadata.modified_at = datetime.now()

            logger.debug(f"Updated {self._model_type.value} model: {model_id}")

        # Dispatch hooks (outside lock)
        for hook in self._hooks:
            try:
                hook.on_updated(model_id, old_model, model, metadata)
            except Exception as e:
                logger.warning(f"Hook on_updated failed: {e}")

        return metadata

    def delete(self, model_id: str) -> bool:
        """Delete a model from the store."""
        with self._lock:
            if model_id not in self._models:
                return False

            model = self._models.pop(model_id)
            metadata = self._metadata.pop(model_id)
            self._snapshots.pop(model_id, None)

            logger.debug(f"Deleted {self._model_type.value} model: {model_id}")

        # Dispatch hooks (outside lock)
        for hook in self._hooks:
            try:
                hook.on_deleted(model_id, model, metadata)
            except Exception as e:
                logger.warning(f"Hook on_deleted failed: {e}")

        return True

    def exists(self, model_id: str) -> bool:
        """Check if a model exists."""
        with self._lock:
            return model_id in self._models

    def list_ids(self) -> List[str]:
        """List all model IDs."""
        with self._lock:
            return list(self._models.keys())

    def get_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get metadata for a model."""
        with self._lock:
            return self._metadata.get(model_id)

    def create_snapshot(self, model_id: str, label: Optional[str] = None) -> Snapshot:
        """Create an immutable snapshot of the current model state."""
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model {model_id} not found")

            snapshot = Snapshot(
                model_id=model_id,
                timestamp=datetime.now(),
                state=deepcopy(self._models[model_id]),
                label=label
            )
            self._snapshots[model_id].append(snapshot)

            logger.debug(f"Created snapshot for {model_id}: {label or 'unlabeled'}")

            return snapshot

    def restore_snapshot(self, snapshot: Snapshot) -> None:
        """Restore a model to a previous snapshot state."""
        with self._lock:
            if snapshot.model_id not in self._models:
                raise KeyError(f"Model {snapshot.model_id} not found")

            old_model = self._models[snapshot.model_id]
            self._models[snapshot.model_id] = deepcopy(snapshot.state)

            metadata = self._metadata[snapshot.model_id]
            metadata.modified_at = datetime.now()

            logger.debug(f"Restored {snapshot.model_id} to snapshot: {snapshot.label or snapshot.timestamp}")

        # Dispatch update hooks (snapshot restore is an update)
        for hook in self._hooks:
            try:
                hook.on_updated(snapshot.model_id, old_model, self._models[snapshot.model_id], metadata)
            except Exception as e:
                logger.warning(f"Hook on_updated failed during restore: {e}")

    def list_snapshots(self, model_id: str) -> List[Snapshot]:
        """List all snapshots for a model."""
        with self._lock:
            return list(self._snapshots.get(model_id, []))

    def add_hook(self, hook: LifecycleHook) -> None:
        """Register a lifecycle hook."""
        with self._lock:
            if hook not in self._hooks:
                self._hooks.append(hook)

    def remove_hook(self, hook: LifecycleHook) -> None:
        """Unregister a lifecycle hook."""
        with self._lock:
            if hook in self._hooks:
                self._hooks.remove(hook)

    @contextmanager
    def edit(self, model_id: str) -> Generator[T, None, None]:
        """Context manager for safe model mutation with auto-update.

        Yields the live model for in-place modifications. On successful exit,
        automatically calls update() to trigger hooks and update metadata.
        On exception, changes are NOT reverted (use snapshots for rollback).

        Example:
            with store.edit("model-123") as model:
                model.add_equipment(...)
                model.connect(...)
            # update() called automatically on exit
        """
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model {model_id} not found")
            model = self._models[model_id]

        try:
            yield model
        finally:
            # Always call update on successful yield exit (even if no explicit changes)
            # This ensures hooks are triggered and modified_at is updated
            self.update(model_id, model)

    # Convenience methods for backward compatibility with dict-like access
    def __getitem__(self, model_id: str) -> T:
        """Support store[model_id] syntax for dict-like access.

        Note: Unlike get(), this raises KeyError if not found and
        does NOT update access metadata (to match dict behavior).
        """
        with self._lock:
            if model_id not in self._models:
                raise KeyError(model_id)
            return self._models[model_id]

    def __setitem__(self, model_id: str, model: T) -> None:
        """Support store[model_id] = model syntax for dict-like assignment.

        Creates a new model if it doesn't exist, updates if it does.
        Triggers appropriate lifecycle hooks.
        """
        if self.exists(model_id):
            self.update(model_id, model)
        else:
            self.create(model_id, model)

    def __delitem__(self, model_id: str) -> None:
        """Support del store[model_id] syntax."""
        if not self.delete(model_id):
            raise KeyError(model_id)

    def __contains__(self, model_id: str) -> bool:
        """Support 'model_id in store' syntax."""
        return self.exists(model_id)

    def __len__(self) -> int:
        """Return number of models in store."""
        with self._lock:
            return len(self._models)

    def __iter__(self):
        """Iterate over model IDs."""
        return iter(self.list_ids())

    def items(self):
        """Return model ID, model pairs (snapshot to avoid mutation during iteration)."""
        with self._lock:
            return list(self._models.items())

    def values(self):
        """Return all models (snapshot to avoid mutation during iteration)."""
        with self._lock:
            return list(self._models.values())

    def keys(self):
        """Return all model IDs."""
        return self.list_ids()

    def clear(self) -> None:
        """Remove all models from the store."""
        with self._lock:
            model_ids = list(self._models.keys())

        # Delete each model to trigger hooks
        for model_id in model_ids:
            self.delete(model_id)


# ============================================================================
# Factory Functions
# ============================================================================

def create_dexpi_store() -> InMemoryModelStore:
    """Create an in-memory store for DEXPI models."""
    return InMemoryModelStore(ModelType.DEXPI)


def create_sfiles_store() -> InMemoryModelStore:
    """Create an in-memory store for SFILES models."""
    return InMemoryModelStore(ModelType.SFILES)
