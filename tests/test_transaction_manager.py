"""
Comprehensive test suite for TransactionManager.

Tests cover:
- Snapshot strategy selection
- ACID transaction lifecycle
- Rollback scenarios
- Validation integration
- Error handling
- Concurrent transaction prevention
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict

from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.dexpi_classes.metaData import MetaData
from pydexpi.dexpi_classes.equipment import Tank, Pump

from src.managers.transaction_manager import (
    TransactionManager,
    Transaction,
    TransactionStatus,
    SnapshotStrategy,
    OperationRecord,
    StructuralDiff,
    CommitResult,
    ValidationResult,
    TransactionError,
    TransactionNotFound,
    TransactionAlreadyActive,
    TransactionNotActive,
    OperationExecutionError,
    ValidationError,
    ModelNotFound,
    estimate_model_size,
    select_snapshot_strategy,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def small_dexpi_model():
    """Create a small DEXPI model (<1MB)."""
    conceptual = ConceptualModel(
        metaData=MetaData(title="Test Model", description="Small test")
    )
    model = DexpiModel(conceptualModel=conceptual)

    # Add a few components (< threshold)
    tank = Tank(componentName="Tank", tagName="T-101")
    pump = Pump(componentName="Pump", tagName="P-101")

    conceptual.taggedPlantItems.extend([tank, pump])

    return model


@pytest.fixture
def large_dexpi_model():
    """Create a large DEXPI model (>1MB simulated)."""
    conceptual = ConceptualModel(
        metaData=MetaData(title="Large Model", description="Large test")
    )
    model = DexpiModel(conceptualModel=conceptual)

    # Add many components to exceed threshold
    for i in range(600):  # 600 * 2KB = 1.2MB
        tank = Tank(componentName=f"Tank{i}", tagName=f"T-{i:03d}")
        conceptual.taggedPlantItems.append(tank)

    return model


@pytest.fixture
def dexpi_models():
    """Shared DEXPI models dictionary."""
    return {}


@pytest.fixture
def flowsheets():
    """Shared flowsheets dictionary."""
    return {}


@pytest.fixture
def transaction_manager(dexpi_models, flowsheets):
    """Create TransactionManager instance."""
    return TransactionManager(dexpi_models, flowsheets)


# ============================================================================
# Snapshot Strategy Tests
# ============================================================================

def test_estimate_small_model_size(small_dexpi_model):
    """Test size estimation for small model."""
    size = estimate_model_size(small_dexpi_model)

    # Should be ~2 components * 2KB = 4KB
    assert size < 1 * 1024 * 1024  # Less than 1MB
    assert size > 0


def test_estimate_large_model_size(large_dexpi_model):
    """Test size estimation for large model."""
    size = estimate_model_size(large_dexpi_model)

    # Should be ~600 components * 2KB = 1.2MB
    assert size >= 1 * 1024 * 1024  # At least 1MB


def test_select_deepcopy_strategy_for_small_model(small_dexpi_model):
    """Test that small models use deepcopy strategy."""
    strategy = select_snapshot_strategy(small_dexpi_model)

    assert strategy == SnapshotStrategy.DEEPCOPY


def test_select_serialize_strategy_for_large_model(large_dexpi_model):
    """Test that large models use serialize strategy."""
    strategy = select_snapshot_strategy(large_dexpi_model)

    assert strategy == SnapshotStrategy.SERIALIZE


# ============================================================================
# Transaction Lifecycle Tests
# ============================================================================

@pytest.mark.asyncio
async def test_begin_transaction_success(transaction_manager, dexpi_models, small_dexpi_model):
    """Test successful transaction start."""
    # Add model to store
    model_id = "test_model_1"
    dexpi_models[model_id] = small_dexpi_model

    # Begin transaction
    tx_id = await transaction_manager.begin(model_id)

    # Verify transaction created
    assert tx_id is not None
    assert tx_id in transaction_manager.transactions

    tx = transaction_manager.transactions[tx_id]
    assert tx.model_id == model_id
    assert tx.status == TransactionStatus.ACTIVE
    assert tx.snapshot_strategy == SnapshotStrategy.DEEPCOPY


@pytest.mark.asyncio
async def test_begin_transaction_with_metadata(transaction_manager, dexpi_models, small_dexpi_model):
    """Test transaction start with custom metadata."""
    model_id = "test_model_2"
    dexpi_models[model_id] = small_dexpi_model

    metadata = {"user": "test_user", "purpose": "testing"}
    tx_id = await transaction_manager.begin(model_id, metadata=metadata)

    tx = transaction_manager.transactions[tx_id]
    assert tx.metadata == metadata


@pytest.mark.asyncio
async def test_begin_transaction_model_not_found(transaction_manager):
    """Test transaction start with non-existent model."""
    with pytest.raises(ModelNotFound):
        await transaction_manager.begin("nonexistent_model")


@pytest.mark.asyncio
async def test_begin_transaction_already_active(transaction_manager, dexpi_models, small_dexpi_model):
    """Test prevention of concurrent transactions on same model."""
    model_id = "test_model_3"
    dexpi_models[model_id] = small_dexpi_model

    # Begin first transaction
    tx_id_1 = await transaction_manager.begin(model_id)

    # Try to begin second transaction on same model
    with pytest.raises(TransactionAlreadyActive):
        await transaction_manager.begin(model_id)


@pytest.mark.asyncio
async def test_apply_operation_success(transaction_manager, dexpi_models, small_dexpi_model):
    """Test applying operation within transaction."""
    model_id = "test_model_4"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    # Apply operation
    result = await transaction_manager.apply(
        tx_id,
        operation_name="add_equipment",
        params={"tag_name": "T-102", "type": "Tank"}
    )

    assert result is not None

    # Verify operation recorded
    tx = transaction_manager.transactions[tx_id]
    assert len(tx.operations) == 1
    assert tx.operations[0].operation == "add_equipment"
    assert tx.operations[0].success is True


@pytest.mark.asyncio
async def test_apply_operation_with_executor(transaction_manager, dexpi_models, small_dexpi_model):
    """Test applying operation with custom executor."""
    model_id = "test_model_5"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    # Custom executor
    def add_tank(model, params):
        tank = Tank(componentName="NewTank", tagName=params["tag_name"])
        model.conceptualModel.taggedPlantItems.append(tank)
        return {"status": "success", "tag": params["tag_name"]}

    result = await transaction_manager.apply(
        tx_id,
        operation_name="add_tank",
        params={"tag_name": "T-103"},
        executor=add_tank
    )

    assert result["status"] == "success"
    assert result["tag"] == "T-103"


@pytest.mark.asyncio
async def test_apply_operation_failure(transaction_manager, dexpi_models, small_dexpi_model):
    """Test operation failure handling."""
    model_id = "test_model_6"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    # Failing executor
    def failing_operation(model, params):
        raise ValueError("Intentional failure")

    with pytest.raises(OperationExecutionError):
        await transaction_manager.apply(
            tx_id,
            operation_name="failing_op",
            params={},
            executor=failing_operation
        )

    # Verify operation recorded with error
    tx = transaction_manager.transactions[tx_id]
    assert len(tx.operations) == 1
    assert tx.operations[0].success is False
    assert "Intentional failure" in tx.operations[0].error


@pytest.mark.asyncio
async def test_commit_transaction_success(transaction_manager, dexpi_models, small_dexpi_model):
    """Test successful transaction commit."""
    model_id = "test_model_7"
    original_model = small_dexpi_model
    dexpi_models[model_id] = original_model

    tx_id = await transaction_manager.begin(model_id)

    # Apply operations
    await transaction_manager.apply(
        tx_id,
        operation_name="add_equipment",
        params={"tag_name": "T-104"}
    )

    # Commit
    result = await transaction_manager.commit(tx_id, validate=False)

    assert isinstance(result, CommitResult)
    assert result.transaction_id == tx_id
    assert result.operations_applied == 1

    # Verify transaction cleaned up
    assert tx_id not in transaction_manager.transactions


@pytest.mark.asyncio
async def test_commit_with_validation(transaction_manager, dexpi_models, small_dexpi_model):
    """Test commit with validation enabled."""
    model_id = "test_model_8"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    # Apply operation
    await transaction_manager.apply(
        tx_id,
        operation_name="add_equipment",
        params={"tag_name": "T-105"}
    )

    # Commit with validation
    result = await transaction_manager.commit(tx_id, validate=True)

    assert result.validation is not None
    assert isinstance(result.validation, ValidationResult)


@pytest.mark.asyncio
async def test_rollback_transaction(transaction_manager, dexpi_models, small_dexpi_model):
    """Test transaction rollback."""
    model_id = "test_model_9"
    original_model = small_dexpi_model
    dexpi_models[model_id] = original_model

    # Get initial equipment count
    initial_count = len(original_model.conceptualModel.taggedPlantItems)

    tx_id = await transaction_manager.begin(model_id)

    # Apply operation
    await transaction_manager.apply(
        tx_id,
        operation_name="add_equipment",
        params={"tag_name": "T-106"}
    )

    # Rollback
    await transaction_manager.rollback(tx_id)

    # Verify original model unchanged
    assert len(dexpi_models[model_id].conceptualModel.taggedPlantItems) == initial_count

    # Verify transaction cleaned up
    assert tx_id not in transaction_manager.transactions


@pytest.mark.asyncio
async def test_diff_preview(transaction_manager, dexpi_models, small_dexpi_model):
    """Test diff preview during transaction."""
    model_id = "test_model_10"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    # Apply add operation
    await transaction_manager.apply(
        tx_id,
        operation_name="add_equipment",
        params={"tag_name": "T-107"}
    )

    # Get diff
    diff = await transaction_manager.diff(tx_id)

    assert isinstance(diff, StructuralDiff)
    assert "T-107" in diff.added


@pytest.mark.asyncio
async def test_get_status(transaction_manager, dexpi_models, small_dexpi_model):
    """Test getting transaction status."""
    model_id = "test_model_11"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    # Get status
    status = await transaction_manager.get_status(tx_id)

    assert status["transaction_id"] == tx_id
    assert status["model_id"] == model_id
    assert status["model_type"] == "dexpi"
    assert status["status"] == "active"
    assert status["operations_count"] == 0


# ============================================================================
# Snapshot Strategy Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_deepcopy_snapshot_for_small_model(transaction_manager, dexpi_models, small_dexpi_model):
    """Test that small models use deepcopy snapshot."""
    model_id = "test_model_12"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    tx = transaction_manager.transactions[tx_id]
    assert tx.snapshot_strategy == SnapshotStrategy.DEEPCOPY
    assert isinstance(tx.snapshot, DexpiModel)  # Snapshot is model object


@pytest.mark.asyncio
async def test_serialize_snapshot_for_large_model(transaction_manager, dexpi_models, large_dexpi_model):
    """Test that large models use serialized snapshot."""
    model_id = "test_model_13"
    dexpi_models[model_id] = large_dexpi_model

    tx_id = await transaction_manager.begin(model_id)

    tx = transaction_manager.transactions[tx_id]
    assert tx.snapshot_strategy == SnapshotStrategy.SERIALIZE
    assert isinstance(tx.snapshot, bytes)  # Snapshot is serialized


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_transaction_not_found(transaction_manager):
    """Test TransactionNotFound exception."""
    with pytest.raises(TransactionNotFound):
        await transaction_manager.apply("nonexistent_tx", "op", {})


@pytest.mark.asyncio
async def test_apply_to_non_active_transaction(transaction_manager, dexpi_models, small_dexpi_model):
    """Test applying operation to committed transaction."""
    model_id = "test_model_14"
    dexpi_models[model_id] = small_dexpi_model

    tx_id = await transaction_manager.begin(model_id)
    await transaction_manager.commit(tx_id, validate=False)

    # Transaction is now cleaned up, should raise TransactionNotFound
    with pytest.raises(TransactionNotFound):
        await transaction_manager.apply(tx_id, "op", {})


# ============================================================================
# Structural Diff Tests
# ============================================================================

def test_structural_diff_is_empty():
    """Test StructuralDiff.is_empty()."""
    diff = StructuralDiff()
    assert diff.is_empty()

    diff.added.append("T-101")
    assert not diff.is_empty()


def test_structural_diff_tracks_additions():
    """Test diff tracking for additions."""
    diff = StructuralDiff()
    diff.added.extend(["T-101", "P-102"])

    assert len(diff.added) == 2
    assert "T-101" in diff.added


def test_structural_diff_tracks_modifications():
    """Test diff tracking for modifications."""
    diff = StructuralDiff()
    diff.modified.append("T-101")

    assert len(diff.modified) == 1
    assert not diff.is_empty()


# ============================================================================
# Validation Tests
# ============================================================================

def test_validation_result_is_valid():
    """Test ValidationResult with no errors."""
    result = ValidationResult(is_valid=True)
    assert result.is_valid
    assert len(result.errors) == 0


def test_validation_result_with_errors():
    """Test ValidationResult with errors."""
    result = ValidationResult(
        is_valid=False,
        errors=["Error 1", "Error 2"]
    )
    assert not result.is_valid
    assert len(result.errors) == 2


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_transaction_workflow(transaction_manager, dexpi_models, small_dexpi_model):
    """Test complete transaction workflow: begin -> apply -> commit."""
    model_id = "test_model_15"
    dexpi_models[model_id] = small_dexpi_model

    # Begin
    tx_id = await transaction_manager.begin(model_id, metadata={"test": "integration"})
    assert tx_id is not None

    # Apply multiple operations
    await transaction_manager.apply(tx_id, "add_tank", {"tag_name": "T-201"})
    await transaction_manager.apply(tx_id, "add_pump", {"tag_name": "P-201"})

    # Check diff
    diff = await transaction_manager.diff(tx_id)
    assert "T-201" in diff.added
    assert "P-201" in diff.added

    # Check status
    status = await transaction_manager.get_status(tx_id)
    assert status["operations_count"] == 2

    # Commit
    result = await transaction_manager.commit(tx_id, validate=False)
    assert result.operations_applied == 2
    assert len(result.diff.added) == 2

    # Verify cleanup
    assert tx_id not in transaction_manager.transactions


@pytest.mark.asyncio
async def test_transaction_isolation(transaction_manager, dexpi_models, small_dexpi_model):
    """Test that multiple models can have concurrent transactions."""
    model_id_1 = "model_1"
    model_id_2 = "model_2"

    dexpi_models[model_id_1] = small_dexpi_model
    dexpi_models[model_id_2] = small_dexpi_model

    # Begin transactions on different models
    tx_id_1 = await transaction_manager.begin(model_id_1)
    tx_id_2 = await transaction_manager.begin(model_id_2)

    # Both should succeed
    assert tx_id_1 != tx_id_2
    assert len(transaction_manager.transactions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
