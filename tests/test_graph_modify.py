"""Tests for graph_modify_tools.py - v1 (6 core actions)."""

import pytest
from pydexpi.dexpi_classes.dexpiModel import DexpiModel
from pydexpi.dexpi_classes.metaData import MetaData
from pydexpi.dexpi_classes.equipment import Tank
from pydexpi.dexpi_classes.pydantic_classes import (
    ConceptualModel,
    MultiLanguageString,
    SingleLanguageString,
    Volume,
    VolumeUnit,
)

from src.tools.graph_modify_tools import GraphModifyTools, GraphAction, TargetKind
from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools
from src.adapters.sfiles_adapter import get_flowsheet_class


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
    model_id = "test-dexpi-01"
    dexpi_models[model_id] = model

    return model_id, model


@pytest.fixture
def sample_sfiles_model(model_stores):
    """Create a sample SFILES flowsheet."""
    _, flowsheets = model_stores

    try:
        Flowsheet = get_flowsheet_class()
        flowsheet = Flowsheet()
        flowsheet_id = "test-sfiles-01"
        flowsheets[flowsheet_id] = flowsheet

        return flowsheet_id, flowsheet
    except ImportError:
        pytest.skip("SFILES not available")


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
                "nominalCapacityVolume": {"value": 5000.0, "unit": "MetreCubed"}
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
    conceptual = ConceptualModel()
    model.conceptualModel = conceptual

    tank = Tank()
    tank.tagName = "TK-101"
    tank.equipmentDescription = MultiLanguageString(
        singleLanguageStrings=[
            SingleLanguageString(language="en", value="Original description")
        ]
    )
    conceptual.taggedPlantItems = [tank]

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
                "equipmentDescription": "Updated description"
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
    # Verify the description was updated
    assert isinstance(tank.equipmentDescription, MultiLanguageString)
    assert (
        tank.equipmentDescription.singleLanguageStrings[0].value
        == "Updated description"
    )


@pytest.mark.asyncio
async def test_update_component_dexpi_quantity_coercion(
    graph_modify_tools, sample_dexpi_model
):
    """Ensure numeric scalars are converted into full quantity objects."""
    model_id, model = sample_dexpi_model

    conceptual = ConceptualModel()
    model.conceptualModel = conceptual

    tank = Tank()
    tank.tagName = "TK-101"
    tank.nominalCapacityVolume = Volume(
        value=1.0,
        unit=VolumeUnit.MetreCubed,
    )
    conceptual.taggedPlantItems = [tank]

    args = {
        "model_id": model_id,
        "action": GraphAction.UPDATE_COMPONENT.value,
        "target": {
            "kind": TargetKind.COMPONENT.value,
            "identifier": "TK-101",
        },
        "payload": {
            "attributes": {"nominalCapacityVolume": 5000},
        },
        "options": {
            "create_transaction": False,
            "validate_before": False,
        },
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert result.get("ok")
    assert tank.nominalCapacityVolume.value == 5000.0
    assert tank.nominalCapacityVolume.unit == VolumeUnit.MetreCubed


@pytest.mark.asyncio
async def test_update_component_dexpi_rejects_bad_values(
    graph_modify_tools, sample_dexpi_model
):
    """Invalid scalar input should surface informative errors."""
    model_id, model = sample_dexpi_model

    conceptual = ConceptualModel()
    model.conceptualModel = conceptual

    tank = Tank()
    tank.tagName = "TK-101"
    conceptual.taggedPlantItems = [tank]

    args = {
        "model_id": model_id,
        "action": GraphAction.UPDATE_COMPONENT.value,
        "target": {
            "kind": TargetKind.COMPONENT.value,
            "identifier": "TK-101",
        },
        "payload": {
            "attributes": {"nominalCapacityVolume": "not-a-number"},
        },
        "options": {
            "create_transaction": False,
            "validate_before": False,
        },
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result["error"]["code"] == "ATTRIBUTE_VALIDATION_FAILED"


# ========== ACTION 6: set_tag_properties ==========

@pytest.mark.asyncio
async def test_set_tag_properties_dexpi(graph_modify_tools, sample_dexpi_model):
    """Test set_tag_properties action for DEXPI."""
    model_id, model = sample_dexpi_model

    # Add a component
    conceptual = ConceptualModel()
    model.conceptualModel = conceptual

    tank = Tank()
    tank.tagName = "TK-101"
    conceptual.taggedPlantItems = [tank]

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


# ========== V2 ACTIONS (4 additional operations) ==========

@pytest.mark.asyncio
async def test_split_segment_returns_not_implemented(graph_modify_tools, sample_dexpi_model):
    """Test split_segment action returns NOT_IMPLEMENTED with helpful guidance."""
    model_id, _ = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": GraphAction.SPLIT_SEGMENT.value,
        "target": {"kind": "segment", "identifier": "SEG-01"},
        "payload": {"split_point": 0.5},
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    # Should return NOT_IMPLEMENTED with alternative guidance
    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "NOT_IMPLEMENTED"
    assert "insert_inline_component" in result.get("error", {}).get("message", "")
    assert "alternative" in result.get("error", {}).get("details", {})


@pytest.mark.asyncio
async def test_split_segment_sfiles_not_applicable(graph_modify_tools, sample_sfiles_model):
    """Test split_segment on SFILES returns ACTION_NOT_APPLICABLE."""
    model_id, _ = sample_sfiles_model

    args = {
        "model_id": model_id,
        "action": GraphAction.SPLIT_SEGMENT.value,
        "target": {"kind": "segment", "identifier": "SEG-01"},
        "payload": {"split_point": 0.5},
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "ACTION_NOT_APPLICABLE"


@pytest.mark.asyncio
async def test_merge_segments_returns_not_implemented(graph_modify_tools, sample_dexpi_model):
    """Test merge_segments action returns NOT_IMPLEMENTED with helpful guidance."""
    model_id, _ = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": GraphAction.MERGE_SEGMENTS.value,
        "target": {"kind": "segment", "identifier": "SEG-01"},
        "payload": {"second_segment_id": "SEG-02"},
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    # Should return NOT_IMPLEMENTED with alternative guidance
    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "NOT_IMPLEMENTED"
    message = result.get("error", {}).get("message", "")
    assert "remove" in message.lower() and "rewire" in message.lower()
    assert "alternative" in result.get("error", {}).get("details", {})


@pytest.mark.asyncio
async def test_update_stream_properties_sfiles(graph_modify_tools, sample_sfiles_model):
    """Test update_stream_properties action for SFILES."""
    model_id, flowsheet = sample_sfiles_model

    # First add two units and connect them using NetworkX
    import networkx as nx
    flowsheet.state = nx.DiGraph()
    flowsheet.state.add_node("reactor-1", unit_type="reactor")
    flowsheet.state.add_node("tank-2", unit_type="tank")
    flowsheet.state.add_edge("reactor-1", "tank-2")

    args = {
        "model_id": model_id,
        "action": GraphAction.UPDATE_STREAM_PROPERTIES.value,
        "target": {
            "kind": TargetKind.STREAM.value,
            "identifier": "reactor-1->tank-2"
        },
        "payload": {
            "properties": {
                "flow": 150,
                "temperature": 25,
                "pressure": 2.5
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
    # Check that properties were updated
    data = result.get("data", {})
    assert "stream" in data
    assert "properties_updated" in data
    assert "flow" in data["properties_updated"]


@pytest.mark.asyncio
async def test_update_stream_properties_dexpi_not_applicable(graph_modify_tools, sample_dexpi_model):
    """Test update_stream_properties on DEXPI returns ACTION_NOT_APPLICABLE."""
    model_id, _ = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": GraphAction.UPDATE_STREAM_PROPERTIES.value,
        "target": {"kind": "stream", "identifier": "stream-1"},
        "payload": {"properties": {"flow": 100}},
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "ACTION_NOT_APPLICABLE"


@pytest.mark.asyncio
async def test_toggle_instrumentation_returns_not_implemented(graph_modify_tools, sample_dexpi_model):
    """Test toggle_instrumentation returns NOT_IMPLEMENTED with helpful guidance."""
    model_id, _ = sample_dexpi_model

    args = {
        "model_id": model_id,
        "action": GraphAction.TOGGLE_INSTRUMENTATION.value,
        "target": {"kind": "component", "identifier": "TK-101"},
        "payload": {
            "operation": "add",
            "instrument_type": "FlowTransmitter",
            "tag": "FT-101"
        },
        "options": {"create_transaction": False}
    }

    result = await graph_modify_tools.handle_tool("graph_modify", args)

    # Should return NOT_IMPLEMENTED with alternative guidance
    assert not result.get("ok")
    assert result.get("error", {}).get("code") == "NOT_IMPLEMENTED"
    assert "dexpi_add_instrumentation" in result.get("error", {}).get("message", "")
    assert "alternative" in result.get("error", {}).get("details", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
