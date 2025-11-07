"""Tests for graph_modify_tools.py - v1 (6 core actions)."""

import pytest
from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.dexpi_classes.metaData import MetaData
from pydexpi.dexpi_classes.equipment import Tank

from src.tools.graph_modify_tools import GraphModifyTools, GraphAction, TargetKind
from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools
from src.adapters.sfiles_adapter import create_flowsheet


@pytest.fixture
def model_stores():
    """Create empty model stores."""
    dexpi_models = {}
    flowsheets = {}
    return dexpi_models, flowsheets


@pytest.fixture
def graph_modify_tools(model_stores):
    """Create GraphModifyTools instance."""
    dexpi_models, flowsheets = model_stores
    dexpi_tools = DexpiTools(dexpi_models, flowsheets)
    sfiles_tools = SfilesTools(flowsheets, dexpi_models)

    return GraphModifyTools(
        dexpi_models,
        flowsheets,
        dexpi_tools,
        sfiles_tools,
        None  # search_tools
    )


@pytest.fixture
def sample_dexpi_model(model_stores):
    """Create a sample DEXPI model."""
    dexpi_models, _ = model_stores

    model = DexpiModel()
    model.meta = MetaData()
    model.meta.projectName = "Test Project"
    model.meta.drawingNumber = "TEST-001"

    model_id = "test-dexpi-01"
    dexpi_models[model_id] = model

    return model_id, model


@pytest.fixture
def sample_sfiles_model(model_stores):
    """Create a sample SFILES flowsheet."""
    _, flowsheets = model_stores

    flowsheet = create_flowsheet()
    flowsheet_id = "test-sfiles-01"
    flowsheets[flowsheet_id] = flowsheet

    return flowsheet_id, flowsheet


# ========== ACTION 1: insert_component ==========

@pytest.mark.asyncio
async def test_insert_component_dexpi(graph_modify_tools, sample_dexpi_model):
    """Test insert_component action for DEXPI."""
    model_id, model = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": GraphAction.INSERT_COMPONENT.value,
        "target": {
            "kind": TargetKind.MODEL.value,
            "identifier": model_id
        },
        "payload": {
            "component_type": "Tank",
            "tag": "TK-101",
            "attributes": {
                "capacity": 5000
            }
        },
        "options": {
            "create_transaction": False,  # Disable for simpler testing
            "validate_before": False
        }
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert result.get("ok") or result.get("status") == "success"
    assert "TK-101" in result.get("data", {}).get("mutated_entities", [])


@pytest.mark.asyncio
async def test_insert_component_sfiles(graph_modify_tools, sample_sfiles_model):
    """Test insert_component action for SFILES."""
    model_id, flowsheet = sample_sfiles_model

    args = {
        "model_id": model_id,
        "action": GraphAction.INSERT_COMPONENT.value,
        "target": {
            "kind": TargetKind.MODEL.value,
            "identifier": model_id
        },
        "payload": {
            "component_type": "reactor",
            "tag": "R-01",
            "attributes": {
                "volume": 100
            }
        },
        "options": {
            "create_transaction": False,
            "validate_before": False
        }
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert result.get("ok") or result.get("status") == "success"
    assert "R-01" in result.get("data", {}).get("mutated_entities", [])


# ========== ACTION 2: update_component ==========

@pytest.mark.asyncio
async def test_update_component_dexpi(graph_modify_tools, sample_dexpi_model):
    """Test update_component action for DEXPI."""
    model_id, model = sample_dexpi_model

    # First add a component
    tank = Tank()
    tank.tagName = "TK-101"
    tank.capacity = 5000
    model.equipments = [tank]

    # Now update it
    args = {
        "model_id": model_id,
        "action": GraphAction.UPDATE_COMPONENT.value,
        "target": {
            "kind": TargetKind.COMPONENT.value,
            "identifier": "TK-101"
        },
        "payload": {
            "attributes": {
                "capacity": 10000
            },
            "merge": True
        },
        "options": {
            "create_transaction": False,
            "validate_before": False
        }
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert result.get("ok") or result.get("status") == "success"
    assert tank.capacity == 10000


# ========== ACTION 6: set_tag_properties ==========

@pytest.mark.asyncio
async def test_set_tag_properties_dexpi(graph_modify_tools, sample_dexpi_model):
    """Test set_tag_properties action for DEXPI."""
    model_id, model = sample_dexpi_model

    # Add a component
    tank = Tank()
    tank.tagName = "TK-101"
    model.equipments = [tank]

    # Rename it
    args = {
        "model_id": model_id,
        "action": GraphAction.SET_TAG_PROPERTIES.value,
        "target": {
            "kind": TargetKind.COMPONENT.value,
            "identifier": "TK-101"
        },
        "payload": {
            "new_tag": "TK-101A",
            "metadata": {
                "description": "Primary storage tank"
            }
        },
        "options": {
            "create_transaction": False,
            "validate_before": False
        }
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert result.get("ok") or result.get("status") == "success"
    assert tank.tagName == "TK-101A"
    assert "new_tags" in result.get("data", {})


# ========== ERROR HANDLING ==========

@pytest.mark.asyncio
async def test_model_not_found(graph_modify_tools):
    """Test error handling for non-existent model."""
    args = {
        "model_id": "nonexistent",
        "action": GraphAction.INSERT_COMPONENT.value,
        "target": {"kind": "model", "identifier": "nonexistent"},
        "payload": {"component_type": "Tank", "tag": "TK-101"}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_invalid_action(graph_modify_tools, sample_dexpi_model):
    """Test error handling for invalid action."""
    model_id, _ = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": "invalid_action",
        "target": {"kind": "model", "identifier": model_id},
        "payload": {}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "INVALID_ACTION"


@pytest.mark.asyncio
async def test_action_not_applicable(graph_modify_tools, sample_sfiles_model):
    """Test ACTION_NOT_APPLICABLE for SFILES-specific action on DEXPI."""
    model_id, _ = sample_sfiles_model

    args = {
        "model_id": model_id,
        "action": GraphAction.INSERT_INLINE_COMPONENT.value,  # DEXPI only
        "target": {"kind": "segment", "identifier": "SEG-01"},
        "payload": {"component_type": "CheckValve", "tag": "CV-01"},
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "ACTION_NOT_APPLICABLE"


# ========== V2 ACTIONS (NOT IMPLEMENTED) ==========

@pytest.mark.asyncio
async def test_v2_action_not_implemented(graph_modify_tools, sample_dexpi_model):
    """Test that v2 actions return NOT_IMPLEMENTED."""
    model_id, _ = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": GraphAction.SPLIT_SEGMENT.value,  # V2 action
        "target": {"kind": "segment", "identifier": "SEG-01"},
        "payload": {"split_point": 0.5},
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "NOT_IMPLEMENTED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
