"""
Tests for ModelStore - Thread-safe Model Storage Abstraction

Tests cover:
1. CRUD operations (create, get, update, delete)
2. Existence checks and listing
3. Metadata tracking (created_at, modified_at, access_count)
4. Snapshot creation and restoration
5. Lifecycle hooks (create, update, delete, access)
6. CachingHook for derived data cache invalidation
7. Thread safety
8. Backward compatibility methods (__contains__, __len__, etc.)
"""

import pytest
import threading
import time
from datetime import datetime
from typing import Any, List

from src.core.model_store import (
    ModelStore,
    InMemoryModelStore,
    ModelType,
    ModelMetadata,
    Snapshot,
    LifecycleHook,
    CachingHook,
    create_dexpi_store,
    create_sfiles_store,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def dexpi_store():
    """Create a fresh DEXPI store for testing."""
    return InMemoryModelStore(ModelType.DEXPI)


@pytest.fixture
def sfiles_store():
    """Create a fresh SFILES store for testing."""
    return InMemoryModelStore(ModelType.SFILES)


@pytest.fixture
def sample_model():
    """Sample model object for testing."""
    return {"name": "Test Model", "equipment": [], "connections": []}


@pytest.fixture
def tracking_hook():
    """Hook that tracks all lifecycle events."""
    class TrackingHook(LifecycleHook):
        def __init__(self):
            self.created = []
            self.updated = []
            self.deleted = []
            self.accessed = []

        def on_created(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
            self.created.append({"model_id": model_id, "model": model, "metadata": metadata})

        def on_updated(self, model_id: str, old_model: Any, new_model: Any,
                       metadata: ModelMetadata) -> None:
            self.updated.append({
                "model_id": model_id,
                "old_model": old_model,
                "new_model": new_model,
                "metadata": metadata
            })

        def on_deleted(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
            self.deleted.append({"model_id": model_id, "model": model, "metadata": metadata})

        def on_accessed(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
            self.accessed.append({"model_id": model_id, "model": model, "metadata": metadata})

    return TrackingHook()


# ============================================================================
# Basic CRUD Tests
# ============================================================================

class TestModelStoreCRUD:
    """Test basic create, read, update, delete operations."""

    def test_create_model(self, dexpi_store, sample_model):
        """Test creating a new model."""
        metadata = dexpi_store.create("model-001", sample_model)

        assert metadata.model_id == "model-001"
        assert metadata.model_type == ModelType.DEXPI
        assert isinstance(metadata.created_at, datetime)
        assert metadata.created_at == metadata.modified_at
        assert metadata.access_count == 0

    def test_create_with_tags(self, dexpi_store, sample_model):
        """Test creating model with custom tags."""
        tags = {"project": "test", "version": "1.0"}
        metadata = dexpi_store.create("model-001", sample_model, tags=tags)

        assert metadata.tags == tags

    def test_create_duplicate_raises_keyerror(self, dexpi_store, sample_model):
        """Test that creating duplicate model_id raises KeyError."""
        dexpi_store.create("model-001", sample_model)

        with pytest.raises(KeyError, match="already exists"):
            dexpi_store.create("model-001", {"different": "model"})

    def test_get_existing_model(self, dexpi_store, sample_model):
        """Test retrieving an existing model."""
        dexpi_store.create("model-001", sample_model)

        retrieved = dexpi_store.get("model-001")
        assert retrieved == sample_model

    def test_get_nonexistent_returns_none(self, dexpi_store):
        """Test that getting nonexistent model returns None."""
        assert dexpi_store.get("nonexistent") is None

    def test_update_existing_model(self, dexpi_store, sample_model):
        """Test updating an existing model."""
        dexpi_store.create("model-001", sample_model)

        updated_model = {"name": "Updated Model", "equipment": ["pump-1"]}
        metadata = dexpi_store.update("model-001", updated_model)

        assert metadata.modified_at > metadata.created_at
        assert dexpi_store.get("model-001") == updated_model

    def test_update_nonexistent_raises_keyerror(self, dexpi_store, sample_model):
        """Test that updating nonexistent model raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            dexpi_store.update("nonexistent", sample_model)

    def test_delete_existing_model(self, dexpi_store, sample_model):
        """Test deleting an existing model."""
        dexpi_store.create("model-001", sample_model)

        result = dexpi_store.delete("model-001")
        assert result is True
        assert dexpi_store.get("model-001") is None

    def test_delete_nonexistent_returns_false(self, dexpi_store):
        """Test that deleting nonexistent model returns False."""
        result = dexpi_store.delete("nonexistent")
        assert result is False


# ============================================================================
# Existence and Listing Tests
# ============================================================================

class TestModelStoreExistence:
    """Test exists() and list_ids() operations."""

    def test_exists_true_for_existing(self, dexpi_store, sample_model):
        """Test exists() returns True for existing model."""
        dexpi_store.create("model-001", sample_model)
        assert dexpi_store.exists("model-001") is True

    def test_exists_false_for_nonexistent(self, dexpi_store):
        """Test exists() returns False for nonexistent model."""
        assert dexpi_store.exists("nonexistent") is False

    def test_list_ids_empty_store(self, dexpi_store):
        """Test list_ids() on empty store."""
        assert dexpi_store.list_ids() == []

    def test_list_ids_with_models(self, dexpi_store, sample_model):
        """Test list_ids() with multiple models."""
        dexpi_store.create("model-001", sample_model)
        dexpi_store.create("model-002", sample_model)
        dexpi_store.create("model-003", sample_model)

        ids = dexpi_store.list_ids()
        assert len(ids) == 3
        assert set(ids) == {"model-001", "model-002", "model-003"}


# ============================================================================
# Metadata Tests
# ============================================================================

class TestModelStoreMetadata:
    """Test metadata tracking functionality."""

    def test_access_count_increments(self, dexpi_store, sample_model):
        """Test that access_count increments on each get()."""
        dexpi_store.create("model-001", sample_model)

        # Initial access count is 0
        metadata = dexpi_store.get_metadata("model-001")
        assert metadata.access_count == 0

        # Each get() increments count
        dexpi_store.get("model-001")
        metadata = dexpi_store.get_metadata("model-001")
        assert metadata.access_count == 1

        dexpi_store.get("model-001")
        dexpi_store.get("model-001")
        metadata = dexpi_store.get_metadata("model-001")
        assert metadata.access_count == 3

    def test_last_accessed_updates(self, dexpi_store, sample_model):
        """Test that last_accessed updates on get()."""
        dexpi_store.create("model-001", sample_model)

        # Initial last_accessed is None
        metadata = dexpi_store.get_metadata("model-001")
        assert metadata.last_accessed is None

        # After get(), last_accessed is set
        time.sleep(0.01)  # Ensure time difference
        dexpi_store.get("model-001")
        metadata = dexpi_store.get_metadata("model-001")
        assert metadata.last_accessed is not None
        assert metadata.last_accessed > metadata.created_at

    def test_modified_at_updates_on_update(self, dexpi_store, sample_model):
        """Test that modified_at updates on update()."""
        metadata1 = dexpi_store.create("model-001", sample_model)
        original_modified = metadata1.modified_at

        time.sleep(0.01)  # Ensure time difference
        metadata2 = dexpi_store.update("model-001", {"updated": True})

        assert metadata2.modified_at > original_modified

    def test_get_metadata_nonexistent_returns_none(self, dexpi_store):
        """Test get_metadata() returns None for nonexistent model."""
        assert dexpi_store.get_metadata("nonexistent") is None

    def test_metadata_to_dict(self, dexpi_store, sample_model):
        """Test ModelMetadata.to_dict() serialization."""
        tags = {"project": "test"}
        dexpi_store.create("model-001", sample_model, tags=tags)
        dexpi_store.get("model-001")  # Trigger access

        metadata = dexpi_store.get_metadata("model-001")
        d = metadata.to_dict()

        assert d["model_id"] == "model-001"
        assert d["model_type"] == "dexpi"
        assert d["access_count"] == 1
        assert d["tags"] == tags
        assert "created_at" in d
        assert "modified_at" in d
        assert d["last_accessed"] is not None


# ============================================================================
# Snapshot Tests
# ============================================================================

class TestModelStoreSnapshots:
    """Test snapshot creation and restoration."""

    def test_create_snapshot(self, dexpi_store, sample_model):
        """Test creating a snapshot."""
        dexpi_store.create("model-001", sample_model)

        snapshot = dexpi_store.create_snapshot("model-001", "before-changes")

        assert snapshot.model_id == "model-001"
        assert snapshot.label == "before-changes"
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.state == sample_model

    def test_snapshot_is_deep_copy(self, dexpi_store):
        """Test that snapshot contains a deep copy."""
        model = {"equipment": [{"id": "pump-1"}]}
        dexpi_store.create("model-001", model)

        snapshot = dexpi_store.create_snapshot("model-001")

        # Modify original model
        model["equipment"].append({"id": "pump-2"})
        dexpi_store.update("model-001", model)

        # Snapshot should be unchanged
        assert len(snapshot.state["equipment"]) == 1
        assert snapshot.state["equipment"][0]["id"] == "pump-1"

    def test_restore_snapshot(self, dexpi_store):
        """Test restoring a model from snapshot."""
        original = {"name": "Original", "version": 1}
        dexpi_store.create("model-001", original)

        snapshot = dexpi_store.create_snapshot("model-001", "v1")

        # Make changes
        dexpi_store.update("model-001", {"name": "Modified", "version": 2})
        assert dexpi_store.get("model-001")["version"] == 2

        # Restore snapshot
        dexpi_store.restore_snapshot(snapshot)

        restored = dexpi_store.get("model-001")
        assert restored["name"] == "Original"
        assert restored["version"] == 1

    def test_restore_snapshot_updates_modified_at(self, dexpi_store, sample_model):
        """Test that restoring snapshot updates modified_at."""
        dexpi_store.create("model-001", sample_model)
        snapshot = dexpi_store.create_snapshot("model-001")

        time.sleep(0.01)
        # Save the timestamp value, not the metadata object (which is mutable)
        original_modified_at = dexpi_store.get_metadata("model-001").modified_at

        time.sleep(0.01)
        dexpi_store.restore_snapshot(snapshot)

        new_metadata = dexpi_store.get_metadata("model-001")
        assert new_metadata.modified_at > original_modified_at

    def test_list_snapshots(self, dexpi_store, sample_model):
        """Test listing snapshots for a model."""
        dexpi_store.create("model-001", sample_model)

        dexpi_store.create_snapshot("model-001", "snapshot-1")
        dexpi_store.create_snapshot("model-001", "snapshot-2")
        dexpi_store.create_snapshot("model-001", "snapshot-3")

        snapshots = dexpi_store.list_snapshots("model-001")
        assert len(snapshots) == 3
        assert snapshots[0].label == "snapshot-1"
        assert snapshots[2].label == "snapshot-3"

    def test_create_snapshot_nonexistent_raises_keyerror(self, dexpi_store):
        """Test creating snapshot for nonexistent model raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            dexpi_store.create_snapshot("nonexistent")

    def test_restore_snapshot_nonexistent_raises_keyerror(self, dexpi_store, sample_model):
        """Test restoring snapshot for deleted model raises KeyError."""
        dexpi_store.create("model-001", sample_model)
        snapshot = dexpi_store.create_snapshot("model-001")

        dexpi_store.delete("model-001")

        with pytest.raises(KeyError, match="not found"):
            dexpi_store.restore_snapshot(snapshot)


# ============================================================================
# Lifecycle Hook Tests
# ============================================================================

class TestModelStoreHooks:
    """Test lifecycle hook functionality."""

    def test_on_created_hook(self, dexpi_store, sample_model, tracking_hook):
        """Test that on_created hook is called."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)

        assert len(tracking_hook.created) == 1
        assert tracking_hook.created[0]["model_id"] == "model-001"
        assert tracking_hook.created[0]["model"] == sample_model

    def test_on_updated_hook(self, dexpi_store, sample_model, tracking_hook):
        """Test that on_updated hook is called."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)

        updated = {"name": "Updated"}
        dexpi_store.update("model-001", updated)

        assert len(tracking_hook.updated) == 1
        assert tracking_hook.updated[0]["model_id"] == "model-001"
        assert tracking_hook.updated[0]["old_model"] == sample_model
        assert tracking_hook.updated[0]["new_model"] == updated

    def test_on_deleted_hook(self, dexpi_store, sample_model, tracking_hook):
        """Test that on_deleted hook is called."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)
        dexpi_store.delete("model-001")

        assert len(tracking_hook.deleted) == 1
        assert tracking_hook.deleted[0]["model_id"] == "model-001"
        assert tracking_hook.deleted[0]["model"] == sample_model

    def test_on_accessed_hook(self, dexpi_store, sample_model, tracking_hook):
        """Test that on_accessed hook is called."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)

        dexpi_store.get("model-001")
        dexpi_store.get("model-001")

        assert len(tracking_hook.accessed) == 2
        assert tracking_hook.accessed[0]["model_id"] == "model-001"

    def test_remove_hook(self, dexpi_store, sample_model, tracking_hook):
        """Test removing a hook."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)
        assert len(tracking_hook.created) == 1

        dexpi_store.remove_hook(tracking_hook)
        dexpi_store.create("model-002", sample_model)
        assert len(tracking_hook.created) == 1  # No new events

    def test_hook_exception_does_not_break_operation(self, dexpi_store, sample_model):
        """Test that hook exceptions don't break store operations."""
        class FailingHook(LifecycleHook):
            def on_created(self, model_id: str, model: Any, metadata: ModelMetadata) -> None:
                raise RuntimeError("Hook failed!")

        dexpi_store.add_hook(FailingHook())

        # Should not raise despite failing hook
        metadata = dexpi_store.create("model-001", sample_model)
        assert metadata is not None
        assert dexpi_store.get("model-001") == sample_model

    def test_restore_snapshot_triggers_updated_hook(self, dexpi_store, sample_model, tracking_hook):
        """Test that restoring snapshot triggers on_updated hook."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)
        snapshot = dexpi_store.create_snapshot("model-001")

        dexpi_store.update("model-001", {"changed": True})
        assert len(tracking_hook.updated) == 1

        dexpi_store.restore_snapshot(snapshot)
        assert len(tracking_hook.updated) == 2


# ============================================================================
# CachingHook Tests
# ============================================================================

class TestCachingHook:
    """Test CachingHook for derived data cache invalidation."""

    def test_cache_graph(self):
        """Test caching and retrieving graph data."""
        caching = CachingHook()
        graph = {"nodes": ["A", "B"], "edges": [("A", "B")]}

        caching.cache_graph("model-001", graph)
        assert caching.get_cached_graph("model-001") == graph

    def test_cache_stats(self):
        """Test caching and retrieving statistics."""
        caching = CachingHook()
        stats = {"equipment_count": 5, "connection_count": 10}

        caching.cache_stats("model-001", stats)
        assert caching.get_cached_stats("model-001") == stats

    def test_on_updated_invalidates_caches(self, dexpi_store, sample_model):
        """Test that on_updated invalidates cached data."""
        caching = CachingHook()
        dexpi_store.add_hook(caching)

        dexpi_store.create("model-001", sample_model)
        caching.cache_graph("model-001", {"graph": "data"})
        caching.cache_stats("model-001", {"stats": "data"})

        assert caching.get_cached_graph("model-001") is not None
        assert caching.get_cached_stats("model-001") is not None

        dexpi_store.update("model-001", {"updated": True})

        assert caching.get_cached_graph("model-001") is None
        assert caching.get_cached_stats("model-001") is None

    def test_on_deleted_invalidates_caches(self, dexpi_store, sample_model):
        """Test that on_deleted invalidates cached data."""
        caching = CachingHook()
        dexpi_store.add_hook(caching)

        dexpi_store.create("model-001", sample_model)
        caching.cache_graph("model-001", {"graph": "data"})

        dexpi_store.delete("model-001")

        assert caching.get_cached_graph("model-001") is None

    def test_clear_all(self):
        """Test clearing all cached data."""
        caching = CachingHook()
        caching.cache_graph("model-001", {"graph": "data"})
        caching.cache_stats("model-001", {"stats": "data"})
        caching.cache_graph("model-002", {"graph": "data"})

        caching.clear_all()

        assert caching.get_cached_graph("model-001") is None
        assert caching.get_cached_stats("model-001") is None
        assert caching.get_cached_graph("model-002") is None


# ============================================================================
# Thread Safety Tests
# ============================================================================

class TestModelStoreThreadSafety:
    """Test thread-safe behavior of InMemoryModelStore."""

    def test_concurrent_creates(self, dexpi_store):
        """Test concurrent model creation."""
        results = []
        errors = []

        def create_model(model_id):
            try:
                dexpi_store.create(model_id, {"id": model_id})
                results.append(model_id)
            except Exception as e:
                errors.append((model_id, e))

        threads = [
            threading.Thread(target=create_model, args=(f"model-{i:03d}",))
            for i in range(100)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 100
        assert len(dexpi_store) == 100

    def test_concurrent_reads_writes(self, dexpi_store):
        """Test concurrent reads and writes."""
        dexpi_store.create("model-001", {"version": 0})
        read_versions = []
        errors = []

        def reader():
            for _ in range(50):
                try:
                    model = dexpi_store.get("model-001")
                    if model:
                        read_versions.append(model.get("version", -1))
                except Exception as e:
                    errors.append(("reader", e))

        def writer():
            for i in range(50):
                try:
                    dexpi_store.update("model-001", {"version": i + 1})
                except Exception as e:
                    errors.append(("writer", e))

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All read versions should be valid (0-50)
        assert all(0 <= v <= 50 for v in read_versions)


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

class TestModelStoreBackwardCompatibility:
    """Test backward compatibility methods (__contains__, __len__, etc.)."""

    def test_getitem_existing(self, dexpi_store, sample_model):
        """Test store[model_id] syntax for existing model."""
        dexpi_store.create("model-001", sample_model)
        assert dexpi_store["model-001"] == sample_model

    def test_getitem_nonexistent_raises_keyerror(self, dexpi_store):
        """Test store[model_id] raises KeyError for nonexistent model."""
        with pytest.raises(KeyError):
            _ = dexpi_store["nonexistent"]

    def test_setitem_creates_new(self, dexpi_store, sample_model):
        """Test store[model_id] = model creates new model."""
        dexpi_store["model-001"] = sample_model

        assert dexpi_store.exists("model-001")
        assert dexpi_store.get("model-001") == sample_model

    def test_setitem_updates_existing(self, dexpi_store, sample_model):
        """Test store[model_id] = model updates existing model."""
        dexpi_store.create("model-001", sample_model)

        updated = {"name": "Updated"}
        dexpi_store["model-001"] = updated

        assert dexpi_store.get("model-001") == updated

    def test_delitem_existing(self, dexpi_store, sample_model):
        """Test del store[model_id] syntax."""
        dexpi_store.create("model-001", sample_model)

        del dexpi_store["model-001"]
        assert not dexpi_store.exists("model-001")

    def test_delitem_nonexistent_raises_keyerror(self, dexpi_store):
        """Test del store[model_id] raises KeyError for nonexistent model."""
        with pytest.raises(KeyError):
            del dexpi_store["nonexistent"]

    def test_contains_operator(self, dexpi_store, sample_model):
        """Test 'model_id in store' syntax."""
        assert "model-001" not in dexpi_store

        dexpi_store.create("model-001", sample_model)
        assert "model-001" in dexpi_store

    def test_len(self, dexpi_store, sample_model):
        """Test len(store)."""
        assert len(dexpi_store) == 0

        dexpi_store.create("model-001", sample_model)
        dexpi_store.create("model-002", sample_model)
        assert len(dexpi_store) == 2

    def test_iter(self, dexpi_store, sample_model):
        """Test iterating over store."""
        dexpi_store.create("model-001", sample_model)
        dexpi_store.create("model-002", sample_model)

        ids = list(dexpi_store)
        assert set(ids) == {"model-001", "model-002"}

    def test_items(self, dexpi_store, sample_model):
        """Test store.items()."""
        dexpi_store.create("model-001", sample_model)

        items = dexpi_store.items()
        assert len(items) == 1
        assert items[0][0] == "model-001"
        assert items[0][1] == sample_model

    def test_values(self, dexpi_store, sample_model):
        """Test store.values()."""
        dexpi_store.create("model-001", sample_model)

        values = dexpi_store.values()
        assert len(values) == 1
        assert values[0] == sample_model

    def test_keys(self, dexpi_store, sample_model):
        """Test store.keys()."""
        dexpi_store.create("model-001", sample_model)
        dexpi_store.create("model-002", sample_model)

        keys = dexpi_store.keys()
        assert set(keys) == {"model-001", "model-002"}

    def test_clear(self, dexpi_store, sample_model, tracking_hook):
        """Test store.clear()."""
        dexpi_store.add_hook(tracking_hook)
        dexpi_store.create("model-001", sample_model)
        dexpi_store.create("model-002", sample_model)

        dexpi_store.clear()

        assert len(dexpi_store) == 0
        assert len(tracking_hook.deleted) == 2  # Hooks triggered for each deletion


# ============================================================================
# Factory Function Tests
# ============================================================================

class TestFactoryFunctions:
    """Test factory functions for creating stores."""

    def test_create_dexpi_store(self):
        """Test create_dexpi_store factory."""
        store = create_dexpi_store()
        assert isinstance(store, InMemoryModelStore)
        assert store.model_type == ModelType.DEXPI

    def test_create_sfiles_store(self):
        """Test create_sfiles_store factory."""
        store = create_sfiles_store()
        assert isinstance(store, InMemoryModelStore)
        assert store.model_type == ModelType.SFILES


# ============================================================================
# Model Type Tests
# ============================================================================

class TestModelTypes:
    """Test model type handling."""

    def test_dexpi_store_type(self, dexpi_store, sample_model):
        """Test DEXPI store creates DEXPI metadata."""
        metadata = dexpi_store.create("model-001", sample_model)
        assert metadata.model_type == ModelType.DEXPI

    def test_sfiles_store_type(self, sfiles_store, sample_model):
        """Test SFILES store creates SFILES metadata."""
        metadata = sfiles_store.create("flowsheet-001", sample_model)
        assert metadata.model_type == ModelType.SFILES
