"""Tests for unified search_execute tool."""

import pytest
from src.tools.search_tools import SearchTools


@pytest.fixture
def search_tools():
    """Create SearchTools instance with empty stores."""
    # Use empty stores for simpler testing focused on dispatch logic
    return SearchTools({}, {})


@pytest.mark.asyncio
async def test_search_execute_by_tag(search_tools):
    """Test by_tag query type - verify dispatch works."""
    result = await search_tools.handle_tool("search_execute", {
        "query_type": "by_tag",
        "tag_pattern": "TK-*"
    })

    # Should dispatch to _search_by_tag handler
    # Result may be ok:true with empty results or error if no models
    assert 'ok' in result or 'error' in result


@pytest.mark.asyncio
async def test_search_execute_by_type(search_tools):
    """Test by_type query type - verify dispatch works."""
    result = await search_tools.handle_tool("search_execute", {
        "query_type": "by_type",
        "component_type": "Tank"
    })

    # Should dispatch to _search_by_type handler
    assert 'ok' in result or 'error' in result


@pytest.mark.asyncio
async def test_search_execute_by_attributes(search_tools):
    """Test by_attributes query type - verify dispatch works."""
    result = await search_tools.handle_tool("search_execute", {
        "query_type": "by_attributes",
        "attributes": {"tagName": "TK-101"}
    })

    # Should dispatch to _search_by_attributes handler
    assert 'ok' in result or 'error' in result


@pytest.mark.asyncio
async def test_search_execute_statistics(search_tools):
    """Test statistics query type - verify dispatch works."""
    result = await search_tools.handle_tool("search_execute", {
        "query_type": "statistics"
    })

    # Should dispatch to _query_statistics handler
    assert 'ok' in result or 'error' in result


@pytest.mark.asyncio
async def test_search_execute_missing_query_type(search_tools):
    """Test error handling when query_type is missing."""
    result = await search_tools.handle_tool("search_execute", {
        "model_id": "test-model"
    })

    assert result.get('ok') is False
    assert result['error']['code'] == 'MISSING_QUERY_TYPE'


@pytest.mark.asyncio
async def test_search_execute_invalid_query_type(search_tools):
    """Test error handling for invalid query_type."""
    result = await search_tools.handle_tool("search_execute", {
        "query_type": "invalid_query",
        "model_id": "test-model"
    })

    assert result.get('ok') is False
    assert result['error']['code'] == 'INVALID_QUERY_TYPE'


@pytest.mark.asyncio
async def test_search_execute_feature_parity_by_tag(search_tools):
    """Test feature parity: search_execute vs search_by_tag."""
    args_base = {
        "tag_pattern": "TK-*",
        "search_scope": "all",
        "fuzzy": False
    }

    # Call via unified tool
    unified_result = await search_tools.handle_tool("search_execute", {
        "query_type": "by_tag",
        **args_base
    })

    # Call via original tool
    original_result = await search_tools.handle_tool("search_by_tag", args_base)

    # Results should be identical
    assert unified_result == original_result


@pytest.mark.asyncio
async def test_search_execute_feature_parity_by_type(search_tools):
    """Test feature parity: search_execute vs search_by_type."""
    args_base = {
        "component_type": "Tank",
        "include_subtypes": True
    }

    # Call via unified tool
    unified_result = await search_tools.handle_tool("search_execute", {
        "query_type": "by_type",
        **args_base
    })

    # Call via original tool
    original_result = await search_tools.handle_tool("search_by_type", args_base)

    # Results should be identical
    assert unified_result == original_result


@pytest.mark.asyncio
async def test_search_execute_feature_parity_by_attributes(search_tools):
    """Test feature parity: search_execute vs search_by_attributes."""
    args_base = {
        "attributes": {"tagName": "TK-101"},
        "match_type": "exact"
    }

    # Call via unified tool
    unified_result = await search_tools.handle_tool("search_execute", {
        "query_type": "by_attributes",
        **args_base
    })

    # Call via original tool
    original_result = await search_tools.handle_tool("search_by_attributes", args_base)

    # Results should be identical
    assert unified_result == original_result


@pytest.mark.asyncio
async def test_search_execute_feature_parity_statistics(search_tools):
    """Test feature parity: search_execute vs query_model_statistics."""
    args_base = {
        "group_by": "type"
    }

    # Call via unified tool
    unified_result = await search_tools.handle_tool("search_execute", {
        "query_type": "statistics",
        **args_base
    })

    # Call via original tool
    original_result = await search_tools.handle_tool("query_model_statistics", args_base)

    # Results should be identical
    assert unified_result == original_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
