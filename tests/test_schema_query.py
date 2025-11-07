"""Tests for unified schema_query tool."""

import pytest
from src.tools.schema_tools import SchemaTools


@pytest.fixture
def schema_tools():
    """Create SchemaTools instance."""
    return SchemaTools()


@pytest.mark.asyncio
async def test_schema_query_list_classes_dexpi(schema_tools):
    """Test list_classes operation for DEXPI."""
    result = await schema_tools.handle_tool("schema_query", {
        "operation": "list_classes",
        "schema_type": "dexpi",
        "category": "equipment"
    })

    assert result.get('ok') is True
    assert 'dexpi' in result['data']
    assert result['data']['dexpi']['count'] > 0
    assert isinstance(result['data']['dexpi']['classes'], list)


@pytest.mark.asyncio
async def test_schema_query_list_classes_all(schema_tools):
    """Test list_classes operation for all schemas."""
    result = await schema_tools.handle_tool("schema_query", {
        "operation": "list_classes",
        "schema_type": "all"
    })

    assert result.get('ok') is True
    assert 'dexpi' in result['data']
    # sfiles may or may not be present depending on installation
    assert result['data']['dexpi']['count'] > 0


@pytest.mark.asyncio
async def test_schema_query_describe_class_dexpi(schema_tools):
    """Test describe_class operation for DEXPI."""
    result = await schema_tools.handle_tool("schema_query", {
        "operation": "describe_class",
        "schema_type": "dexpi",
        "class_name": "Tank",
        "include_inherited": False
    })

    assert result.get('ok') is True
    assert 'category' in result['data']
    assert result['data']['category'] == 'equipment'
    # Should have attribute information
    assert 'all_attributes' in result['data'] or 'data_attributes' in result['data']


@pytest.mark.asyncio
async def test_schema_query_find_class(schema_tools):
    """Test find_class operation."""
    result = await schema_tools.handle_tool("schema_query", {
        "operation": "find_class",
        "search_term": "pump",
        "schema_type": "dexpi"
    })

    assert result.get('ok') is True
    # Should find pump-related classes


@pytest.mark.asyncio
async def test_schema_query_get_hierarchy(schema_tools):
    """Test get_hierarchy operation."""
    result = await schema_tools.handle_tool("schema_query", {
        "operation": "get_hierarchy",
        "schema_type": "dexpi",
        "max_depth": 3
    })

    assert result.get('ok') is True
    # Should return hierarchy information


@pytest.mark.asyncio
async def test_schema_query_missing_operation(schema_tools):
    """Test error handling when operation is missing."""
    result = await schema_tools.handle_tool("schema_query", {
        "schema_type": "dexpi"
    })

    assert result.get('ok') is False
    assert result['error']['code'] == 'MISSING_OPERATION'


@pytest.mark.asyncio
async def test_schema_query_invalid_operation(schema_tools):
    """Test error handling for invalid operation."""
    result = await schema_tools.handle_tool("schema_query", {
        "operation": "invalid_operation",
        "schema_type": "dexpi"
    })

    assert result.get('ok') is False
    assert result['error']['code'] == 'INVALID_OPERATION'


@pytest.mark.asyncio
async def test_schema_query_feature_parity_list(schema_tools):
    """Test feature parity: schema_query vs schema_list_classes."""
    # Call via unified tool
    unified_result = await schema_tools.handle_tool("schema_query", {
        "operation": "list_classes",
        "schema_type": "dexpi",
        "category": "equipment"
    })

    # Call via original tool
    original_result = await schema_tools.handle_tool("schema_list_classes", {
        "schema_type": "dexpi",
        "category": "equipment"
    })

    # Results should be identical
    assert unified_result == original_result


@pytest.mark.asyncio
async def test_schema_query_feature_parity_describe(schema_tools):
    """Test feature parity: schema_query vs schema_describe_class."""
    args_base = {
        "class_name": "Tank",
        "schema_type": "dexpi",
        "include_inherited": False
    }

    # Call via unified tool
    unified_result = await schema_tools.handle_tool("schema_query", {
        "operation": "describe_class",
        **args_base
    })

    # Call via original tool
    original_result = await schema_tools.handle_tool("schema_describe_class", args_base)

    # Results should be identical
    assert unified_result == original_result


@pytest.mark.asyncio
async def test_schema_query_feature_parity_find(schema_tools):
    """Test feature parity: schema_query vs schema_find_class."""
    args_base = {
        "search_term": "pump",
        "schema_type": "dexpi"
    }

    # Call via unified tool
    unified_result = await schema_tools.handle_tool("schema_query", {
        "operation": "find_class",
        **args_base
    })

    # Call via original tool
    original_result = await schema_tools.handle_tool("schema_find_class", args_base)

    # Results should be identical
    assert unified_result == original_result


@pytest.mark.asyncio
async def test_schema_query_feature_parity_hierarchy(schema_tools):
    """Test feature parity: schema_query vs schema_get_hierarchy."""
    args_base = {
        "schema_type": "dexpi",
        "max_depth": 3
    }

    # Call via unified tool
    unified_result = await schema_tools.handle_tool("schema_query", {
        "operation": "get_hierarchy",
        **args_base
    })

    # Call via original tool
    original_result = await schema_tools.handle_tool("schema_get_hierarchy", args_base)

    # Results should be identical
    assert unified_result == original_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
