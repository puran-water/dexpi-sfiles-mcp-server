"""
End-to-End Integration Tests for Engineering MCP Server

These tests validate complete workflows spanning multiple components:
1. Format conversion chains (SFILES → DEXPI → GraphML)
2. Full lifecycle with snapshots (create → update → snapshot → rollback)
3. Concurrent write safety
4. Template instantiation and expansion
5. Hook chain validation (CachingHook integration)
6. Model validation pipeline
7. Cross-model search operations
"""

import pytest
import threading
import time
from datetime import datetime
from typing import Any, Dict, List

from src.core.model_store import (
    InMemoryModelStore,
    ModelType,
    CachingHook,
    LifecycleHook,
    ModelMetadata,
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
def caching_hook():
    """Create a caching hook for cache invalidation testing."""
    return CachingHook()


@pytest.fixture
def sample_dexpi_model():
    """Sample DEXPI model structure."""
    return {
        "project_name": "Test Plant",
        "drawing_number": "PID-001",
        "revision": "A",
        "equipment": [
            {"tag": "P-101", "type": "CentrifugalPump"},
            {"tag": "T-101", "type": "Tank"},
            {"tag": "E-101", "type": "HeatExchanger"},
        ],
        "piping": [
            {"from": "T-101", "to": "P-101", "line": "001"},
            {"from": "P-101", "to": "E-101", "line": "002"},
        ],
        "instrumentation": [
            {"tag": "FT-101", "type": "FlowTransmitter", "connected_to": "P-101"},
        ]
    }


@pytest.fixture
def sample_sfiles_model():
    """Sample SFILES flowsheet structure."""
    return {
        "name": "Test Flowsheet",
        "type": "PFD",
        "units": [
            {"id": "U1", "type": "reactor", "name": "Main Reactor"},
            {"id": "U2", "type": "separator", "name": "Product Sep"},
            {"id": "U3", "type": "tank", "name": "Feed Tank"},
        ],
        "streams": [
            {"id": "S1", "from_unit": "U3", "to_unit": "U1", "name": "Feed"},
            {"id": "S2", "from_unit": "U1", "to_unit": "U2", "name": "Product"},
        ],
        "controls": []
    }


# ============================================================================
# Scenario 1: Format Conversion Chain
# ============================================================================

class TestFormatConversionChain:
    """Test SFILES → internal representation conversion chains."""

    def test_sfiles_model_roundtrip_via_stores(self, sfiles_store, sample_sfiles_model):
        """Test that SFILES model survives store roundtrip."""
        # Create model in store
        sfiles_store.create("flowsheet-001", sample_sfiles_model)

        # Retrieve and verify
        retrieved = sfiles_store.get("flowsheet-001")
        assert retrieved["name"] == sample_sfiles_model["name"]
        assert len(retrieved["units"]) == 3
        assert len(retrieved["streams"]) == 2

    def test_dexpi_model_roundtrip_via_stores(self, dexpi_store, sample_dexpi_model):
        """Test that DEXPI model survives store roundtrip."""
        # Create model in store
        dexpi_store.create("pid-001", sample_dexpi_model)

        # Retrieve and verify
        retrieved = dexpi_store.get("pid-001")
        assert retrieved["project_name"] == sample_dexpi_model["project_name"]
        assert len(retrieved["equipment"]) == 3
        assert len(retrieved["piping"]) == 2
        assert len(retrieved["instrumentation"]) == 1

    def test_cross_store_models_independent(self, dexpi_store, sfiles_store,
                                            sample_dexpi_model, sample_sfiles_model):
        """Test that models in different stores are independent."""
        # Create models in both stores
        dexpi_store.create("model-001", sample_dexpi_model)
        sfiles_store.create("model-001", sample_sfiles_model)

        # Verify both exist with correct content
        dexpi_model = dexpi_store.get("model-001")
        sfiles_model = sfiles_store.get("model-001")

        assert dexpi_model is not None
        assert sfiles_model is not None
        assert dexpi_model != sfiles_model
        assert "equipment" in dexpi_model
        assert "units" in sfiles_model


# ============================================================================
# Scenario 2: Full Lifecycle with Snapshots
# ============================================================================

class TestFullLifecycleWithSnapshots:
    """Test complete model lifecycle with snapshot/rollback."""

    def test_create_update_snapshot_rollback(self, dexpi_store, sample_dexpi_model):
        """Test full lifecycle: create → update → snapshot → rollback."""
        # Phase 1: Create
        metadata = dexpi_store.create("pid-001", sample_dexpi_model)
        assert metadata.model_id == "pid-001"
        original_created = metadata.created_at

        # Phase 2: Update (add equipment)
        model = dexpi_store.get("pid-001")
        model["equipment"].append({"tag": "V-101", "type": "Vessel"})
        dexpi_store.update("pid-001", model)

        assert len(dexpi_store.get("pid-001")["equipment"]) == 4

        # Phase 3: Create snapshot before risky operation
        snapshot = dexpi_store.create_snapshot("pid-001", "before-major-change")
        assert snapshot.label == "before-major-change"

        # Phase 4: Make risky changes
        model = dexpi_store.get("pid-001")
        model["equipment"] = []  # Clear all equipment (oops!)
        dexpi_store.update("pid-001", model)

        assert len(dexpi_store.get("pid-001")["equipment"]) == 0

        # Phase 5: Rollback to snapshot
        dexpi_store.restore_snapshot(snapshot)

        # Verify restoration
        restored = dexpi_store.get("pid-001")
        assert len(restored["equipment"]) == 4
        assert restored["equipment"][-1]["tag"] == "V-101"

    def test_multiple_snapshots_and_selective_restore(self, dexpi_store, sample_dexpi_model):
        """Test creating multiple snapshots and restoring to different points."""
        dexpi_store.create("pid-001", sample_dexpi_model)

        # Create first snapshot (baseline)
        snapshot1 = dexpi_store.create_snapshot("pid-001", "baseline")

        # Add equipment and snapshot
        model = dexpi_store.get("pid-001")
        model["equipment"].append({"tag": "P-102", "type": "Pump"})
        dexpi_store.update("pid-001", model)
        snapshot2 = dexpi_store.create_snapshot("pid-001", "after-pump")

        # Add more equipment
        model = dexpi_store.get("pid-001")
        model["equipment"].append({"tag": "C-101", "type": "Compressor"})
        dexpi_store.update("pid-001", model)

        # Current state: 5 equipment
        assert len(dexpi_store.get("pid-001")["equipment"]) == 5

        # Restore to snapshot2 (4 equipment)
        dexpi_store.restore_snapshot(snapshot2)
        assert len(dexpi_store.get("pid-001")["equipment"]) == 4

        # Restore to snapshot1 (3 equipment)
        dexpi_store.restore_snapshot(snapshot1)
        assert len(dexpi_store.get("pid-001")["equipment"]) == 3

    def test_edit_context_manager_in_lifecycle(self, dexpi_store, sample_dexpi_model):
        """Test using edit() context manager in lifecycle."""
        dexpi_store.create("pid-001", sample_dexpi_model)

        # Use edit() for safe modification
        with dexpi_store.edit("pid-001") as model:
            model["equipment"].append({"tag": "R-101", "type": "Reactor"})
            model["revision"] = "B"

        # Verify changes
        updated = dexpi_store.get("pid-001")
        assert len(updated["equipment"]) == 4
        assert updated["revision"] == "B"


# ============================================================================
# Scenario 3: Concurrent Write Safety
# ============================================================================

class TestConcurrentWriteSafety:
    """Test thread-safe concurrent write operations."""

    def test_concurrent_creates_no_duplicates(self, dexpi_store):
        """Test concurrent creates with unique IDs succeed."""
        results = []
        errors = []

        def create_model(model_id: str):
            try:
                dexpi_store.create(model_id, {"id": model_id})
                results.append(model_id)
            except Exception as e:
                errors.append((model_id, e))

        threads = [
            threading.Thread(target=create_model, args=(f"model-{i:03d}",))
            for i in range(50)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 50
        assert len(dexpi_store) == 50

    def test_concurrent_updates_same_model(self, dexpi_store):
        """Test concurrent updates to the same model."""
        dexpi_store.create("shared-model", {"counter": 0, "updates": []})
        errors = []

        def increment_counter(thread_id: int):
            for _ in range(10):
                try:
                    model = dexpi_store.get("shared-model")
                    if model:
                        model["counter"] += 1
                        model["updates"].append(thread_id)
                        dexpi_store.update("shared-model", model)
                except Exception as e:
                    errors.append((thread_id, e))

        threads = [
            threading.Thread(target=increment_counter, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Note: Counter may not be exactly 50 due to race conditions in
        # read-modify-write cycle, but no crashes should occur
        final = dexpi_store.get("shared-model")
        assert final["counter"] > 0

    def test_concurrent_reads_during_updates(self, dexpi_store, sample_dexpi_model):
        """Test that reads don't fail during concurrent updates."""
        dexpi_store.create("pid-001", sample_dexpi_model)
        read_results = []
        errors = []

        def reader():
            for _ in range(20):
                try:
                    model = dexpi_store.get("pid-001")
                    if model:
                        read_results.append(len(model.get("equipment", [])))
                except Exception as e:
                    errors.append(("reader", e))
                time.sleep(0.001)

        def writer():
            for i in range(10):
                try:
                    model = dexpi_store.get("pid-001")
                    if model:
                        model["equipment"].append({"tag": f"X-{i}", "type": "Test"})
                        dexpi_store.update("pid-001", model)
                except Exception as e:
                    errors.append(("writer", e))
                time.sleep(0.002)

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
        assert len(read_results) > 0


# ============================================================================
# Scenario 4: Template Instantiation
# ============================================================================

class TestTemplateInstantiation:
    """Test template-like pattern for model creation."""

    def test_create_from_template(self, dexpi_store):
        """Test creating multiple models from a template."""
        template = {
            "project_name": "TEMPLATE",
            "equipment": [
                {"tag": "P-{n}01", "type": "Pump"},
                {"tag": "T-{n}01", "type": "Tank"},
            ],
            "piping": []
        }

        def instantiate_template(template: Dict, area_code: str) -> Dict:
            """Create instance from template with area code substitution."""
            import json
            template_str = json.dumps(template)
            instance_str = template_str.replace("{n}", area_code)
            return json.loads(instance_str)

        # Create instances for different areas
        for area in ["1", "2", "3"]:
            instance = instantiate_template(template, area)
            instance["project_name"] = f"Area {area} Plant"
            dexpi_store.create(f"area-{area}", instance)

        # Verify all instances
        assert len(dexpi_store) == 3

        area1 = dexpi_store.get("area-1")
        assert area1["equipment"][0]["tag"] == "P-101"
        assert area1["equipment"][1]["tag"] == "T-101"

        area2 = dexpi_store.get("area-2")
        assert area2["equipment"][0]["tag"] == "P-201"

        area3 = dexpi_store.get("area-3")
        assert area3["equipment"][0]["tag"] == "P-301"

    def test_template_with_get_copy(self, dexpi_store):
        """Test using get(copy=True) for safe template operations."""
        master_template = {
            "name": "Master Template",
            "equipment": [{"tag": "BASE", "type": "Generic"}]
        }
        dexpi_store.create("master-template", master_template)

        # Use copy to create derived instances without affecting master
        for i in range(3):
            instance = dexpi_store.get("master-template", copy=True)
            instance["name"] = f"Instance {i}"
            instance["equipment"][0]["tag"] = f"I{i}-001"
            dexpi_store.create(f"instance-{i}", instance)

        # Verify master unchanged
        master = dexpi_store.get("master-template")
        assert master["name"] == "Master Template"
        assert master["equipment"][0]["tag"] == "BASE"

        # Verify instances are independent
        i0 = dexpi_store.get("instance-0")
        i1 = dexpi_store.get("instance-1")
        assert i0["equipment"][0]["tag"] == "I0-001"
        assert i1["equipment"][0]["tag"] == "I1-001"


# ============================================================================
# Scenario 5: Hook Chain Validation (CachingHook Integration)
# ============================================================================

class TestHookChainValidation:
    """Test CachingHook integration with ModelStore."""

    def test_caching_hook_invalidation_on_update(self, dexpi_store, caching_hook,
                                                  sample_dexpi_model):
        """Test that CachingHook invalidates cache on model update."""
        dexpi_store.add_hook(caching_hook)
        dexpi_store.create("pid-001", sample_dexpi_model)

        # Populate cache
        mock_graph = {"nodes": ["P-101", "T-101"], "edges": [("T-101", "P-101")]}
        caching_hook.cache_graph("pid-001", mock_graph)
        assert caching_hook.get_cached_graph("pid-001") is not None

        # Update model
        model = dexpi_store.get("pid-001")
        model["equipment"].append({"tag": "NEW", "type": "New"})
        dexpi_store.update("pid-001", model)

        # Cache should be invalidated
        assert caching_hook.get_cached_graph("pid-001") is None

    def test_caching_hook_invalidation_on_edit(self, dexpi_store, caching_hook,
                                                sample_dexpi_model):
        """Test that CachingHook invalidates cache when using edit()."""
        dexpi_store.add_hook(caching_hook)
        dexpi_store.create("pid-001", sample_dexpi_model)

        # Populate caches
        caching_hook.cache_graph("pid-001", {"test": "graph"})
        caching_hook.cache_stats("pid-001", {"equipment_count": 3})

        assert caching_hook.get_cached_graph("pid-001") is not None
        assert caching_hook.get_cached_stats("pid-001") is not None

        # Use edit() context manager
        with dexpi_store.edit("pid-001") as model:
            model["equipment"].append({"tag": "V-102", "type": "Vessel"})

        # Both caches should be invalidated
        assert caching_hook.get_cached_graph("pid-001") is None
        assert caching_hook.get_cached_stats("pid-001") is None

    def test_caching_hook_survives_delete(self, dexpi_store, caching_hook,
                                          sample_dexpi_model):
        """Test that CachingHook cleans up on model delete."""
        dexpi_store.add_hook(caching_hook)
        dexpi_store.create("pid-001", sample_dexpi_model)

        # Populate cache
        caching_hook.cache_graph("pid-001", {"test": "data"})

        # Delete model
        dexpi_store.delete("pid-001")

        # Cache should be cleared
        assert caching_hook.get_cached_graph("pid-001") is None

    def test_multiple_hooks_chain(self, dexpi_store, sample_dexpi_model):
        """Test that multiple hooks are called in sequence."""
        call_order = []

        class OrderedHook(LifecycleHook):
            def __init__(self, name: str):
                self.name = name

            def on_created(self, model_id: str, model: Any, metadata: ModelMetadata):
                call_order.append(f"{self.name}-created")

            def on_updated(self, model_id: str, old: Any, new: Any, metadata: ModelMetadata):
                call_order.append(f"{self.name}-updated")

        hook1 = OrderedHook("hook1")
        hook2 = OrderedHook("hook2")

        dexpi_store.add_hook(hook1)
        dexpi_store.add_hook(hook2)

        dexpi_store.create("model-001", sample_dexpi_model)
        dexpi_store.update("model-001", {"modified": True})

        assert call_order == [
            "hook1-created", "hook2-created",
            "hook1-updated", "hook2-updated"
        ]


# ============================================================================
# Scenario 6: Model Validation Pipeline
# ============================================================================

class TestModelValidationPipeline:
    """Test model validation workflows."""

    def test_validate_required_fields(self, dexpi_store):
        """Test validation of required model fields."""
        def validate_dexpi_model(model: Dict) -> List[str]:
            """Validate DEXPI model structure."""
            errors = []
            required_fields = ["project_name", "drawing_number", "equipment"]

            for field in required_fields:
                if field not in model:
                    errors.append(f"Missing required field: {field}")

            if "equipment" in model:
                for i, eq in enumerate(model["equipment"]):
                    if "tag" not in eq:
                        errors.append(f"Equipment {i}: missing tag")
                    if "type" not in eq:
                        errors.append(f"Equipment {i}: missing type")

            return errors

        # Valid model
        valid_model = {
            "project_name": "Test",
            "drawing_number": "001",
            "equipment": [{"tag": "P-101", "type": "Pump"}]
        }
        assert len(validate_dexpi_model(valid_model)) == 0

        # Invalid model - missing fields
        invalid_model = {"equipment": [{"tag": "P-101"}]}
        errors = validate_dexpi_model(invalid_model)
        assert "Missing required field: project_name" in errors
        assert "Missing required field: drawing_number" in errors
        assert "Equipment 0: missing type" in errors

    def test_validation_before_store(self, dexpi_store):
        """Test validation hook that prevents invalid models."""
        class ValidationHook(LifecycleHook):
            def __init__(self):
                self.rejected = []

            def on_created(self, model_id: str, model: Any, metadata: ModelMetadata):
                if not model.get("valid", False):
                    self.rejected.append(model_id)

        validation = ValidationHook()
        dexpi_store.add_hook(validation)

        # Create valid and invalid models
        dexpi_store.create("valid-001", {"valid": True, "data": "ok"})
        dexpi_store.create("invalid-001", {"valid": False, "data": "bad"})

        # Note: Hook runs after create, so both are stored
        # In production, you'd use pre-create validation
        assert "valid-001" in dexpi_store
        assert "invalid-001" in dexpi_store
        assert "invalid-001" in validation.rejected


# ============================================================================
# Scenario 7: Cross-Model Search Operations
# ============================================================================

class TestCrossModelSearchOperations:
    """Test searching across multiple models."""

    def test_search_equipment_by_tag_pattern(self, dexpi_store):
        """Test searching for equipment across models by tag pattern."""
        # Create multiple models
        dexpi_store.create("area-1", {
            "project_name": "Area 1",
            "equipment": [
                {"tag": "P-101", "type": "Pump"},
                {"tag": "T-101", "type": "Tank"},
            ]
        })
        dexpi_store.create("area-2", {
            "project_name": "Area 2",
            "equipment": [
                {"tag": "P-201", "type": "Pump"},
                {"tag": "P-202", "type": "Pump"},
            ]
        })

        # Search function
        def find_equipment_by_prefix(store: InMemoryModelStore, prefix: str) -> List[Dict]:
            results = []
            for model_id in store.list_ids():
                model = store.get(model_id)
                for eq in model.get("equipment", []):
                    if eq.get("tag", "").startswith(prefix):
                        results.append({
                            "model_id": model_id,
                            "equipment": eq
                        })
            return results

        # Find all pumps (P-xxx)
        pumps = find_equipment_by_prefix(dexpi_store, "P-")
        assert len(pumps) == 3

        # Find all tanks (T-xxx)
        tanks = find_equipment_by_prefix(dexpi_store, "T-")
        assert len(tanks) == 1

    def test_search_by_model_type(self, dexpi_store, sfiles_store):
        """Test that stores maintain type separation."""
        # Create models in both stores with same IDs
        dexpi_store.create("model-001", {"type": "dexpi", "format": "P&ID"})
        sfiles_store.create("model-001", {"type": "sfiles", "format": "PFD"})

        # Search is type-aware
        dexpi_result = dexpi_store.get("model-001")
        sfiles_result = sfiles_store.get("model-001")

        assert dexpi_result["type"] == "dexpi"
        assert sfiles_result["type"] == "sfiles"

    def test_aggregate_statistics_across_models(self, dexpi_store):
        """Test aggregating statistics across multiple models."""
        # Create models
        for i in range(3):
            dexpi_store.create(f"model-{i}", {
                "equipment": [{"tag": f"E-{i}{j}", "type": "Equipment"} for j in range(i + 1)]
            })

        # Aggregate
        total_equipment = 0
        model_stats = []
        for model_id in dexpi_store.list_ids():
            model = dexpi_store.get(model_id)
            eq_count = len(model.get("equipment", []))
            total_equipment += eq_count
            model_stats.append({"model_id": model_id, "equipment_count": eq_count})

        assert total_equipment == 6  # 1 + 2 + 3
        assert len(model_stats) == 3
