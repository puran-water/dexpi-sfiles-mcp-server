"""Tests for sfiles_tools.py - SFILES-specific functionality."""

import pytest
from src.tools.sfiles_tools import SfilesTools
from src.adapters.sfiles_adapter import get_flowsheet_class


@pytest.fixture
def model_stores():
    """Create empty model stores."""
    flowsheets = {}
    dexpi_models = {}
    return flowsheets, dexpi_models


@pytest.fixture
def sfiles_tools(model_stores):
    """Create SfilesTools instance with stores."""
    flowsheets, dexpi_models = model_stores
    return SfilesTools(flowsheets, dexpi_models)


@pytest.mark.asyncio
async def test_generalize_simple_units_via_handle_tool(sfiles_tools):
    """Test generalization with simple numbered units via handle_tool."""
    result = await sfiles_tools.handle_tool("sfiles_generalize", {
        "sfiles_string": "(reactor-1)(distcol-2)(hex-3)"
    })

    assert result.get('ok') is True
    assert result['data']['original'] == '(reactor-1)(distcol-2)(hex-3)'
    assert result['data']['generalized'] == '(reactor)(distcol)(hex)'
    assert result['data']['token_count'] == 3


@pytest.mark.asyncio
async def test_generalize_with_tags_via_handle_tool(sfiles_tools):
    """Test generalization preserves tags while removing unit numbers."""
    result = await sfiles_tools.handle_tool("sfiles_generalize", {
        "sfiles_string": "(pump-101)(tank-201){FC}(valve-301)"
    })

    assert result.get('ok') is True
    assert result['data']['generalized'] == '(pump)(tank){FC}(valve)'
    assert result['data']['token_count'] == 4


@pytest.mark.asyncio
async def test_generalize_complex_sfiles_via_handle_tool(sfiles_tools):
    """Test generalization with complex SFILES structure."""
    result = await sfiles_tools.handle_tool("sfiles_generalize", {
        "sfiles_string": "(raw)(pp)<1(splt)[(hex)(flash)<&|(raw)&|]"
    })

    assert result.get('ok') is True
    # Units without numbers remain unchanged
    assert result['data']['generalized'] == '(raw)(pp)<1(splt)[(hex)(flash)<&|(raw)&|]'
    assert result['data']['token_count'] == 11


@pytest.mark.asyncio
async def test_generalize_missing_input_via_handle_tool(sfiles_tools):
    """Test error handling when no input provided."""
    result = await sfiles_tools.handle_tool("sfiles_generalize", {})

    assert result.get('ok') is False
    assert result['error']['code'] == 'MISSING_INPUT'


@pytest.mark.asyncio
async def test_generalize_use_case_via_handle_tool(sfiles_tools):
    """Test that result includes use case information."""
    result = await sfiles_tools.handle_tool("sfiles_generalize", {
        "sfiles_string": "(reactor-1)(tank-2)"
    })

    assert result.get('ok') is True
    assert result['data']['use_case'] == 'Pattern matching and template creation'


@pytest.mark.asyncio
async def test_generalize_with_flowsheet_id(sfiles_tools, model_stores):
    """Test generalization using stored flowsheet_id."""
    flowsheets, _ = model_stores

    # Create a flowsheet with SFILES representation
    Flowsheet = get_flowsheet_class()
    flowsheet = Flowsheet(sfiles_in="(reactor-1)(distcol-2)(hex-3)")

    flowsheet_id = "test-flowsheet-01"
    flowsheets[flowsheet_id] = flowsheet

    # Generalize via flowsheet_id
    result = await sfiles_tools.handle_tool("sfiles_generalize", {
        "flowsheet_id": flowsheet_id
    })

    assert result.get('ok') is True
    assert result['data']['original'] == "(reactor-1)(distcol-2)(hex-3)"
    assert result['data']['generalized'] == "(reactor)(distcol)(hex)"
    assert result['data']['token_count'] == 3


@pytest.mark.asyncio
async def test_generalize_flowsheet_not_found(sfiles_tools):
    """Test error handling for non-existent flowsheet_id."""
    result = await sfiles_tools.handle_tool("sfiles_generalize", {
        "flowsheet_id": "nonexistent-flowsheet"
    })

    assert result.get('ok') is False
    assert result['error']['code'] == 'FLOWSHEET_NOT_FOUND'
    assert 'nonexistent-flowsheet' in result['error']['message']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
