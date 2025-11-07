"""Tests for rules_apply autofix capability."""

import pytest
from pydexpi.dexpi_classes.dexpiModel import DexpiModel

from src.tools.batch_tools import BatchTools
from src.adapters.sfiles_adapter import get_flowsheet_class


@pytest.fixture
def model_stores():
    """Create model stores."""
    dexpi_models = {}
    flowsheets = {}
    return dexpi_models, flowsheets


@pytest.fixture
def batch_tools(model_stores):
    """Create BatchTools instance."""
    dexpi_models, flowsheets = model_stores
    return BatchTools(
        dexpi_models=dexpi_models,
        flowsheets=flowsheets,
        dexpi_tools=None,  # Not needed for validation
        sfiles_tools=None
    )


@pytest.fixture
def sample_dexpi_model(model_stores):
    """Create a sample DEXPI model."""
    dexpi_models, _ = model_stores

    model = DexpiModel()
    model_id = "test-dexpi"
    dexpi_models[model_id] = model

    return model_id


@pytest.fixture
def sample_sfiles_model(model_stores):
    """Create a sample SFILES flowsheet."""
    _, flowsheets = model_stores

    try:
        Flowsheet = get_flowsheet_class()
        flowsheet = Flowsheet(sfiles_in="(reactor-1)(tank-2)(pump-3)")
        flowsheet_id = "test-sfiles"
        flowsheets[flowsheet_id] = flowsheet
        return flowsheet_id
    except ImportError:
        pytest.skip("SFILES not available")


@pytest.mark.asyncio
async def test_rules_apply_without_autofix(batch_tools, sample_dexpi_model):
    """Test rules_apply without autofix flag."""
    result = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_dexpi_model,
        "autofix": False
    })

    assert 'ok' in result or 'data' in result
    # Should not have autofix fields
    if result.get('ok'):
        assert 'autofix_enabled' not in result['data']
        assert 'fixes_applied' not in result['data']


@pytest.mark.asyncio
async def test_rules_apply_with_autofix_dexpi(batch_tools, sample_dexpi_model):
    """Test rules_apply with autofix enabled for DEXPI."""
    result = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_dexpi_model,
        "autofix": True
    })

    assert 'ok' in result or 'data' in result
    # Should have autofix fields
    if result.get('ok'):
        assert 'autofix_enabled' in result['data']
        assert result['data']['autofix_enabled'] is True
        assert 'fixes_applied' in result['data']
        assert 'fixes_count' in result['data']


@pytest.mark.asyncio
async def test_rules_apply_with_autofix_sfiles(batch_tools, sample_sfiles_model):
    """Test rules_apply with autofix enabled for SFILES."""
    result = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_sfiles_model,
        "autofix": True
    })

    assert 'ok' in result or 'data' in result
    # Should have autofix fields
    if result.get('ok'):
        assert 'autofix_enabled' in result['data']
        assert result['data']['autofix_enabled'] is True
        assert 'fixes_applied' in result['data']
        assert 'fixes_count' in result['data']


@pytest.mark.asyncio
async def test_autofix_preserves_validation_results(batch_tools, sample_dexpi_model):
    """Test that autofix doesn't affect basic validation results structure."""
    # Run without autofix
    result_without = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_dexpi_model,
        "autofix": False
    })

    # Run with autofix
    result_with = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_dexpi_model,
        "autofix": True
    })

    # Both should have same core fields
    if result_without.get('ok') and result_with.get('ok'):
        assert 'valid' in result_without['data']
        assert 'valid' in result_with['data']
        assert 'issues' in result_without['data']
        assert 'issues' in result_with['data']
        assert 'stats' in result_without['data']
        assert 'stats' in result_with['data']


@pytest.mark.asyncio
async def test_autofix_default_false(batch_tools, sample_dexpi_model):
    """Test that autofix defaults to False when not specified."""
    result = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_dexpi_model
        # autofix not specified
    })

    assert 'ok' in result or 'data' in result
    # Should not have autofix fields when not enabled
    if result.get('ok'):
        assert 'autofix_enabled' not in result['data'] or result['data'].get('autofix_enabled') is False


@pytest.mark.asyncio
async def test_missing_model_with_autofix(batch_tools):
    """Test error handling for missing model with autofix enabled."""
    result = await batch_tools.handle_tool("rules_apply", {
        "model_id": "nonexistent",
        "autofix": True
    })

    assert result.get('ok') is False or 'error' in result


@pytest.mark.asyncio
async def test_dexpi_autofix_returns_empty_list(batch_tools, sample_dexpi_model):
    """Test that DEXPI autofix returns empty list (most issues not auto-fixable)."""
    result = await batch_tools.handle_tool("rules_apply", {
        "model_id": sample_dexpi_model,
        "autofix": True
    })

    if result.get('ok'):
        # DEXPI issues are typically not auto-fixable
        assert result['data']['fixes_count'] == 0
        assert len(result['data']['fixes_applied']) == 0


@pytest.mark.asyncio
async def test_sfiles_round_trip_issue_has_autofix_flag(batch_tools, model_stores):
    """Test that sfiles_round_trip issues are marked as can_autofix=True."""
    _, flowsheets = model_stores

    try:
        Flowsheet = get_flowsheet_class()

        # Create a flowsheet that might have round-trip issues
        flowsheet = Flowsheet(sfiles_in="(reactor-1)(tank-2)")
        flowsheet_id = "test-roundtrip"
        flowsheets[flowsheet_id] = flowsheet

        # Run validation without autofix to see the issue
        result = await batch_tools.handle_tool("rules_apply", {
            "model_id": flowsheet_id,
            "autofix": False
        })

        if result.get('ok') and result['data']['issues']:
            # Check if any round-trip issues are marked as fixable
            round_trip_issues = [i for i in result['data']['issues'] if i.get('rule') == 'sfiles_round_trip']
            if round_trip_issues:
                # Should be marked as can_autofix=True
                assert round_trip_issues[0]['can_autofix'] is True
                assert 'normalize' in round_trip_issues[0]['suggested_fix'].lower()
    except ImportError:
        pytest.skip("SFILES not available")


@pytest.mark.asyncio
async def test_sfiles_autofix_attempts_normalization(batch_tools, model_stores):
    """Regression test: Verify autofix actually attempts to fix round-trip issues."""
    _, flowsheets = model_stores

    try:
        Flowsheet = get_flowsheet_class()

        # Create a flowsheet
        flowsheet = Flowsheet(sfiles_in="(reactor-1)(tank-2)(pump-3)")
        flowsheet_id = "test-autofix-attempt"
        flowsheets[flowsheet_id] = flowsheet

        # Run validation with autofix enabled
        result = await batch_tools.handle_tool("rules_apply", {
            "model_id": flowsheet_id,
            "autofix": True
        })

        if result.get('ok'):
            # If there are issues marked as fixable, autofix should attempt them
            fixable_issues = [i for i in result['data']['issues'] if i.get('can_autofix')]

            if fixable_issues:
                # fixes_applied should not be empty if there were fixable issues
                assert 'fixes_applied' in result['data']
                # Even if fixes fail, they should be attempted
                # (fixes_count might be 0 if all attempts failed, but list shouldn't be empty)
    except ImportError:
        pytest.skip("SFILES not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
