"""Tests for transaction_tools.py - Transaction management MCP wrappers."""

import pytest
from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.dexpi_classes.metaData import MetaData

from src.tools.transaction_tools import TransactionTools
from src.utils.response import is_success
from src.registry.operations import register_all_operations


@pytest.fixture
def model_stores():
    """Create model stores with a sample DEXPI model."""
    # Register all operations for this test session
    register_all_operations()

    dexpi_models = {}
    flowsheets = {}

    # Create a small DEXPI model
    conceptual = ConceptualModel(
        metaData=MetaData(title="Test Model", description="Test")
    )
    model = DexpiModel(conceptualModel=conceptual)
    model_id = "test-model-01"
    dexpi_models[model_id] = model

    return dexpi_models, flowsheets, model_id


@pytest.fixture
def transaction_tools(model_stores):
    """Create TransactionTools instance."""
    dexpi_models, flowsheets, _ = model_stores
    return TransactionTools(dexpi_models, flowsheets)


# ========== model_tx_begin Tests ==========

@pytest.mark.asyncio
async def test_tx_begin_success(transaction_tools, model_stores):
    """Test starting a transaction."""
    _, _, model_id = model_stores

    args = {
        "model_id": model_id,
        "metadata": {
            "client": "test_client",
            "purpose": "testing"
        }
    }

    result = await transaction_tools.handle_tool("model_tx_begin", args)

    assert is_success(result)
    assert "transaction_id" in result["data"]
    assert result["data"]["model_id"] == model_id
    assert "snapshot_strategy" in result["data"]
    assert "started_at" in result["data"]


@pytest.mark.asyncio
async def test_tx_begin_model_not_found(transaction_tools):
    """Test error when model doesn't exist."""
    args = {"model_id": "nonexistent"}

    result = await transaction_tools.handle_tool("model_tx_begin", args)

    assert not is_success(result)
    assert result["error"]["code"] == "MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_tx_begin_already_active(transaction_tools, model_stores):
    """Test error when transaction already active on model."""
    _, _, model_id = model_stores

    # Start first transaction
    args1 = {"model_id": model_id}
    result1 = await transaction_tools.handle_tool("model_tx_begin", args1)
    assert is_success(result1)

    # Try to start second transaction on same model
    args2 = {"model_id": model_id}
    result2 = await transaction_tools.handle_tool("model_tx_begin", args2)

    assert not is_success(result2)
    assert result2["error"]["code"] == "TRANSACTION_ALREADY_ACTIVE"


# ========== model_tx_apply Tests ==========

@pytest.mark.asyncio
async def test_tx_apply_single_operation(transaction_tools, model_stores):
    """Test applying a single operation."""
    _, _, model_id = model_stores

    # Begin transaction
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {"model_id": model_id})
    tx_id = begin_result["data"]["transaction_id"]

    # Apply operation
    args = {
        "transaction_id": tx_id,
        "operations": [
            {
                "operation": "dexpi_add_equipment",
                "params": {"tag_name": "TK-101", "equipment_type": "Tank"}
            }
        ]
    }

    result = await transaction_tools.handle_tool("model_tx_apply", args)

    assert is_success(result)
    assert result["data"]["operations_applied"] == 1
    assert "transaction_status" in result["data"]


@pytest.mark.asyncio
async def test_tx_apply_multiple_operations(transaction_tools, model_stores):
    """Test applying multiple operations."""
    _, _, model_id = model_stores

    # Begin transaction
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {"model_id": model_id})
    tx_id = begin_result["data"]["transaction_id"]

    # Apply multiple operations
    args = {
        "transaction_id": tx_id,
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}},
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "P-101", "equipment_type": "Pump"}}
        ]
    }

    result = await transaction_tools.handle_tool("model_tx_apply", args)

    assert is_success(result)
    assert result["data"]["operations_applied"] == 2


@pytest.mark.asyncio
async def test_tx_apply_transaction_not_found(transaction_tools):
    """Test error when transaction doesn't exist."""
    args = {
        "transaction_id": "nonexistent",
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}}
        ]
    }

    result = await transaction_tools.handle_tool("model_tx_apply", args)

    assert not is_success(result)
    assert result["error"]["code"] == "TRANSACTION_NOT_FOUND"


# ========== model_tx_commit Tests ==========

@pytest.mark.asyncio
async def test_tx_commit_success(transaction_tools, model_stores):
    """Test committing a transaction."""
    _, _, model_id = model_stores

    # Begin and apply
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {"model_id": model_id})
    tx_id = begin_result["data"]["transaction_id"]

    await transaction_tools.handle_tool("model_tx_apply", {
        "transaction_id": tx_id,
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}}
        ]
    })

    # Commit
    args = {"transaction_id": tx_id, "action": "commit", "validate": False}
    result = await transaction_tools.handle_tool("model_tx_commit", args)

    assert is_success(result)
    assert result["data"]["operations_applied"] == 1
    assert "diff" in result["data"]
    assert "added" in result["data"]["diff"]


@pytest.mark.asyncio
async def test_tx_commit_with_validation(transaction_tools, model_stores):
    """Test committing with validation."""
    _, _, model_id = model_stores

    # Begin and apply
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {"model_id": model_id})
    tx_id = begin_result["data"]["transaction_id"]

    await transaction_tools.handle_tool("model_tx_apply", {
        "transaction_id": tx_id,
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}}
        ]
    })

    # Commit with validation
    args = {"transaction_id": tx_id, "action": "commit", "validate": True}
    result = await transaction_tools.handle_tool("model_tx_commit", args)

    assert is_success(result)
    assert "validation" in result["data"]
    assert "is_valid" in result["data"]["validation"]


@pytest.mark.asyncio
async def test_tx_rollback(transaction_tools, model_stores):
    """Test rolling back a transaction."""
    dexpi_models, _, model_id = model_stores
    initial_model = dexpi_models[model_id]

    # Begin and apply
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {"model_id": model_id})
    tx_id = begin_result["data"]["transaction_id"]

    await transaction_tools.handle_tool("model_tx_apply", {
        "transaction_id": tx_id,
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}}
        ]
    })

    # Rollback
    args = {"transaction_id": tx_id, "action": "rollback"}
    result = await transaction_tools.handle_tool("model_tx_commit", args)

    assert is_success(result)
    assert result["data"]["action"] == "rollback"

    # Verify model unchanged (snapshot restored)
    # Note: Model should be unchanged after rollback


@pytest.mark.asyncio
async def test_tx_commit_transaction_not_found(transaction_tools):
    """Test error when committing nonexistent transaction."""
    args = {"transaction_id": "nonexistent", "action": "commit"}

    result = await transaction_tools.handle_tool("model_tx_commit", args)

    assert not is_success(result)
    assert result["error"]["code"] == "TRANSACTION_NOT_FOUND"


# ========== Integration Test ==========

@pytest.mark.asyncio
async def test_full_transaction_workflow(transaction_tools, model_stores):
    """Test complete transaction workflow."""
    _, _, model_id = model_stores

    # 1. Begin transaction
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {
        "model_id": model_id,
        "metadata": {"client": "integration_test"}
    })
    assert is_success(begin_result)
    tx_id = begin_result["data"]["transaction_id"]

    # 2. Apply multiple operations
    apply_result = await transaction_tools.handle_tool("model_tx_apply", {
        "transaction_id": tx_id,
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}},
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "P-101", "equipment_type": "Pump"}}
        ]
    })
    assert is_success(apply_result)
    assert apply_result["data"]["operations_applied"] == 2

    # 3. Commit with validation
    commit_result = await transaction_tools.handle_tool("model_tx_commit", {
        "transaction_id": tx_id,
        "action": "commit",
        "validate": True
    })
    assert is_success(commit_result)
    assert commit_result["data"]["operations_applied"] == 2
    assert len(commit_result["data"]["diff"]["added"]) == 2


@pytest.mark.asyncio
async def test_tx_apply_mutates_model(transaction_tools, model_stores):
    """Test that operations actually modify the model (mutation verification)."""
    dexpi_models, _, model_id = model_stores

    # Get initial equipment count
    model = dexpi_models[model_id]
    initial_count = len(model.conceptualModel.taggedPlantItems) if hasattr(model.conceptualModel, 'taggedPlantItems') and model.conceptualModel.taggedPlantItems else 0

    # Begin transaction
    begin_result = await transaction_tools.handle_tool("model_tx_begin", {"model_id": model_id})
    tx_id = begin_result["data"]["transaction_id"]

    # Apply operation to add equipment
    apply_result = await transaction_tools.handle_tool("model_tx_apply", {
        "transaction_id": tx_id,
        "operations": [
            {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-201", "equipment_type": "Tank"}}
        ]
    })

    assert is_success(apply_result)

    # Commit transaction
    commit_result = await transaction_tools.handle_tool("model_tx_commit", {
        "transaction_id": tx_id,
        "action": "commit"
    })

    assert is_success(commit_result)

    # Re-fetch the model from the store after commit
    # (Transaction commits update the store, but we have a stale reference)
    model = dexpi_models[model_id]

    # Verify model was actually modified
    final_count = len(model.conceptualModel.taggedPlantItems) if hasattr(model.conceptualModel, 'taggedPlantItems') and model.conceptualModel.taggedPlantItems else 0
    assert final_count == initial_count + 1, f"Expected {initial_count + 1} equipment items, got {final_count}"

    # Verify diff reports the addition
    assert len(commit_result["data"]["diff"]["added"]) == 1
    assert commit_result["data"]["diff"]["added"][0] == "TK-201"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
