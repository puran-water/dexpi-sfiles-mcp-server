"""Tests for model_tools.py - Unified model lifecycle operations."""

import pytest
from src.tools.model_tools import ModelTools
from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools
from src.utils.response import is_success


@pytest.fixture
def model_stores():
    """Create empty model stores."""
    dexpi_models = {}
    flowsheets = {}
    return dexpi_models, flowsheets


@pytest.fixture
def model_tools(model_stores):
    """Create ModelTools instance."""
    dexpi_models, flowsheets = model_stores
    dexpi_tools = DexpiTools(dexpi_models, flowsheets)
    sfiles_tools = SfilesTools(flowsheets, dexpi_models)

    return ModelTools(
        dexpi_models,
        flowsheets,
        dexpi_tools,
        sfiles_tools
    )


# ========== model_create Tests ==========

@pytest.mark.asyncio
async def test_model_create_dexpi(model_tools):
    """Test creating a DEXPI model."""
    args = {
        "model_type": "dexpi",
        "metadata": {
            "project_name": "Test Plant",
            "drawing_number": "PID-001",
            "revision": "A",
            "description": "Test P&ID"
        }
    }

    result = await model_tools.handle_tool("model_create", args)

    assert is_success(result)
    assert "model_id" in result["data"]
    assert result["data"]["project_name"] == "Test Plant"
    assert result["data"]["drawing_number"] == "PID-001"


@pytest.mark.asyncio
async def test_model_create_sfiles(model_tools):
    """Test creating a SFILES flowsheet."""
    args = {
        "model_type": "sfiles",
        "metadata": {
            "name": "Test Flowsheet",
            "type": "PFD",
            "description": "Test process flow diagram"
        }
    }

    result = await model_tools.handle_tool("model_create", args)

    assert is_success(result)
    assert "flowsheet_id" in result["data"]
    assert result["data"]["name"] == "Test Flowsheet"
    assert result["data"]["type"] == "PFD"


@pytest.mark.asyncio
async def test_model_create_invalid_type(model_tools):
    """Test error handling for invalid model type."""
    args = {
        "model_type": "invalid",
        "metadata": {"name": "Test"}
    }

    result = await model_tools.handle_tool("model_create", args)

    assert not is_success(result)
    assert result["error"]["code"] == "INVALID_MODEL_TYPE"


@pytest.mark.asyncio
async def test_model_create_missing_dexpi_metadata(model_tools):
    """Test error handling for missing DEXPI metadata."""
    args = {
        "model_type": "dexpi",
        "metadata": {"project_name": "Test"}  # Missing drawing_number
    }

    result = await model_tools.handle_tool("model_create", args)

    assert not is_success(result)
    assert result["error"]["code"] == "INVALID_METADATA"


# ========== model_load Tests ==========

@pytest.mark.asyncio
async def test_model_load_dexpi_json(model_tools, model_stores):
    """Test loading a DEXPI model from JSON."""
    dexpi_models, _ = model_stores

    # First create a model to export
    create_args = {
        "model_type": "dexpi",
        "metadata": {
            "project_name": "Test",
            "drawing_number": "PID-001"
        }
    }
    create_result = await model_tools.handle_tool("model_create", create_args)
    model_id = create_result["data"]["model_id"]

    # Export to JSON
    save_args = {
        "model_id": model_id,
        "format": "json"
    }
    save_result = await model_tools.handle_tool("model_save", save_args)
    json_content = save_result["data"]["json"]

    # Load from JSON
    load_args = {
        "model_type": "dexpi",
        "format": "json",
        "content": json_content
    }
    result = await model_tools.handle_tool("model_load", load_args)

    assert is_success(result)
    assert "model_id" in result["data"]


@pytest.mark.asyncio
async def test_model_load_sfiles_string(model_tools):
    """Test loading a SFILES model from string."""
    # Use a pre-made SFILES string (empty flowsheets can't be serialized)
    sfiles_content = "tank-1"  # Simple single-unit flowsheet

    # Load from SFILES string
    load_args = {
        "model_type": "sfiles",
        "format": "sfiles_string",
        "content": sfiles_content
    }
    result = await model_tools.handle_tool("model_load", load_args)

    assert is_success(result)
    assert "flowsheet_id" in result["data"]


@pytest.mark.asyncio
async def test_model_load_missing_content(model_tools):
    """Test error handling for missing content."""
    args = {
        "model_type": "dexpi",
        "format": "json"
        # Missing "content"
    }

    result = await model_tools.handle_tool("model_load", args)

    assert not is_success(result)
    assert result["error"]["code"] == "MISSING_CONTENT"


# ========== model_save Tests ==========

@pytest.mark.asyncio
async def test_model_save_dexpi_json(model_tools):
    """Test saving a DEXPI model to JSON."""
    # Create a model
    create_args = {
        "model_type": "dexpi",
        "metadata": {
            "project_name": "Test",
            "drawing_number": "PID-001"
        }
    }
    create_result = await model_tools.handle_tool("model_create", create_args)
    model_id = create_result["data"]["model_id"]

    # Save to JSON
    args = {
        "model_id": model_id,
        "format": "json"
    }
    result = await model_tools.handle_tool("model_save", args)

    assert is_success(result)
    assert "json" in result["data"]
    assert isinstance(result["data"]["json"], str)


@pytest.mark.asyncio
async def test_model_save_dexpi_graphml(model_tools):
    """Test saving a DEXPI model to GraphML."""
    # Create a model
    create_args = {
        "model_type": "dexpi",
        "metadata": {
            "project_name": "Test",
            "drawing_number": "PID-001"
        }
    }
    create_result = await model_tools.handle_tool("model_create", create_args)
    model_id = create_result["data"]["model_id"]

    # Save to GraphML
    args = {
        "model_id": model_id,
        "format": "graphml",
        "options": {"include_msr": True}
    }
    result = await model_tools.handle_tool("model_save", args)

    assert is_success(result)
    assert "graphml" in result["data"]


@pytest.mark.asyncio
async def test_model_save_sfiles_graphml(model_tools):
    """Test saving a SFILES model to GraphML format."""
    # Create a flowsheet
    create_args = {
        "model_type": "sfiles",
        "metadata": {"name": "Test"}
    }
    create_result = await model_tools.handle_tool("model_create", create_args)
    flowsheet_id = create_result["data"]["flowsheet_id"]

    # Save to GraphML (works even for empty flowsheets)
    args = {
        "model_id": flowsheet_id,
        "format": "graphml"
    }
    result = await model_tools.handle_tool("model_save", args)

    assert is_success(result)
    assert "graphml" in result["data"]


@pytest.mark.asyncio
async def test_model_save_sfiles_string(model_tools, model_stores):
    """Test saving a SFILES model to SFILES string format."""
    from src.tools.sfiles_tools import SfilesTools

    _, flowsheets = model_stores
    sfiles_tools = SfilesTools(flowsheets, {})

    # Create a flowsheet with actual content
    create_result = await sfiles_tools.handle_tool("sfiles_create_flowsheet", {
        "name": "Test Flowsheet",
        "type": "PFD"
    })
    flowsheet_id = create_result["data"]["flowsheet_id"]

    # Add a unit so flowsheet isn't empty
    await sfiles_tools.handle_tool("sfiles_add_unit", {
        "flowsheet_id": flowsheet_id,
        "unit_type": "reactor",
        "unit_name": "R-101"
    })

    # Save to SFILES string using model_tools
    args = {
        "model_id": flowsheet_id,
        "format": "sfiles_string",
        "options": {
            "canonical": True,
            "version": "v2"
        }
    }
    result = await model_tools.handle_tool("model_save", args)

    assert is_success(result)
    assert "sfiles" in result["data"]
    assert isinstance(result["data"]["sfiles"], str)
    # SFILES output contains process type abbreviation
    assert len(result["data"]["sfiles"]) > 0


@pytest.mark.asyncio
async def test_model_save_ambiguous_with_type_hint(model_tools, model_stores):
    """Test saving when model exists in both stores with model_type hint."""
    dexpi_models, flowsheets = model_stores

    # Create models with same ID in both stores (migration scenario)
    from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
    from pydexpi.dexpi_classes.metaData import MetaData
    from src.adapters.sfiles_adapter import get_flowsheet_class

    model_id = "shared-model-01"

    # Add to DEXPI store
    conceptual = ConceptualModel(metaData=MetaData(title="Test"))
    dexpi_models[model_id] = DexpiModel(conceptualModel=conceptual)

    # Add to SFILES store
    Flowsheet = get_flowsheet_class()
    flowsheets[model_id] = Flowsheet()

    # Export DEXPI version with model_type hint
    save_result = await model_tools.handle_tool("model_save", {
        "model_id": model_id,
        "format": "json",
        "model_type": "dexpi"
    })

    assert is_success(save_result)
    assert "json" in save_result["data"]

    # Export SFILES version with model_type hint
    save_result2 = await model_tools.handle_tool("model_save", {
        "model_id": model_id,
        "format": "graphml",
        "model_type": "sfiles"
    })

    assert is_success(save_result2)
    assert "graphml" in save_result2["data"]


@pytest.mark.asyncio
async def test_model_save_ambiguous_without_hint_fails(model_tools, model_stores):
    """Test that saving ambiguous model without hint returns helpful error."""
    dexpi_models, flowsheets = model_stores

    from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
    from pydexpi.dexpi_classes.metaData import MetaData
    from src.adapters.sfiles_adapter import get_flowsheet_class

    model_id = "shared-model-02"

    # Add to both stores
    conceptual = ConceptualModel(metaData=MetaData(title="Test"))
    dexpi_models[model_id] = DexpiModel(conceptualModel=conceptual)

    Flowsheet = get_flowsheet_class()
    flowsheets[model_id] = Flowsheet()

    # Try to export without model_type hint
    save_result = await model_tools.handle_tool("model_save", {
        "model_id": model_id,
        "format": "json"
    })

    assert not is_success(save_result)
    assert save_result["error"]["code"] == "AMBIGUOUS_MODEL_ID"
    assert "model_type" in save_result["error"]["message"]


@pytest.mark.asyncio
async def test_model_save_model_not_found(model_tools):
    """Test error handling for nonexistent model."""
    args = {
        "model_id": "nonexistent",
        "format": "json"
    }

    result = await model_tools.handle_tool("model_save", args)

    assert not is_success(result)
    assert result["error"]["code"] == "MODEL_NOT_FOUND"


@pytest.mark.asyncio
async def test_model_save_invalid_format(model_tools):
    """Test error handling for invalid format."""
    # Create a model
    create_args = {
        "model_type": "dexpi",
        "metadata": {
            "project_name": "Test",
            "drawing_number": "PID-001"
        }
    }
    create_result = await model_tools.handle_tool("model_create", create_args)
    model_id = create_result["data"]["model_id"]

    # Try invalid format
    args = {
        "model_id": model_id,
        "format": "sfiles_string"  # Invalid for DEXPI
    }
    result = await model_tools.handle_tool("model_save", args)

    assert not is_success(result)
    assert result["error"]["code"] == "INVALID_FORMAT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
