"""Smoke tests for DEXPI MCP tool schemas.

Phase 2.2: Verify that all MCP tool schemas expose the correct number of component types
from the ComponentRegistry (159 equipment, 79 piping, 34 instrumentation, 22 valves).
"""

import pytest
from src.tools.dexpi_tools import DexpiTools
from src.core.components import get_registry, ComponentType, ComponentCategory


class TestToolSchemaCoverage:
    """Verify MCP tool schemas expose all 272 component types."""

    @pytest.fixture
    def dexpi_tools(self):
        """Create DexpiTools instance for testing."""
        return DexpiTools(model_store={}, flowsheet_store={})

    @pytest.fixture
    def tool_schemas(self, dexpi_tools):
        """Get all tool schemas."""
        tools = dexpi_tools.get_tools()
        return {tool.name: tool for tool in tools}

    def test_equipment_tool_schema_coverage(self, tool_schemas):
        """Verify dexpi_add_equipment exposes all equipment types (aliases + class names)."""
        equipment_tool = tool_schemas.get("dexpi_add_equipment")
        assert equipment_tool is not None, "dexpi_add_equipment tool not found"

        # Get enum values from schema
        enum_values = equipment_tool.inputSchema["properties"]["equipment_type"]["enum"]

        # Get expected count from ComponentRegistry (Codex fix: includes both aliases AND class names)
        registry = get_registry()
        equipment_components = registry.get_all_by_type(ComponentType.EQUIPMENT)
        # Each component contributes 1 alias + 1 class name (some may overlap if alias == class name)
        expected_aliases = set(c.sfiles_alias for c in equipment_components)
        expected_classes = set(c.dexpi_class.__name__ for c in equipment_components)
        expected_count = len(expected_aliases | expected_classes)  # Union of sets

        assert len(enum_values) == expected_count, \
            f"Expected {expected_count} equipment types (aliases + class names), got {len(enum_values)}"

        # Verify both aliases and class names are present
        assert 'pump' in enum_values, "SFILES alias 'pump' should be in enum"
        assert 'CentrifugalPump' in enum_values, "DEXPI class name 'CentrifugalPump' should be in enum"

        # Verify description mentions 159 types
        assert "159 types" in equipment_tool.description, \
            "Tool description should mention 159 equipment types"

        # Verify description includes examples
        assert "pump" in equipment_tool.description.lower(), \
            "Description should include 'pump' example"
        assert "boiler" in equipment_tool.description.lower(), \
            "Description should include 'boiler' example"

    def test_valve_tool_schema_coverage(self, tool_schemas):
        """Verify dexpi_add_valve_between_components exposes all valve types (aliases + class names)."""
        valve_tool = tool_schemas.get("dexpi_add_valve_between_components")
        assert valve_tool is not None, "dexpi_add_valve_between_components tool not found"

        # Get enum values from schema
        enum_values = valve_tool.inputSchema["properties"]["valve_type"]["enum"]

        # Get expected count from ComponentRegistry (Codex fix: includes both aliases AND class names)
        registry = get_registry()
        valve_components = registry.get_all_by_category(ComponentCategory.VALVE)
        expected_aliases = set(c.sfiles_alias for c in valve_components)
        expected_classes = set(c.dexpi_class.__name__ for c in valve_components)
        expected_count = len(expected_aliases | expected_classes)

        assert len(enum_values) == expected_count, \
            f"Expected {expected_count} valve types (aliases + class names), got {len(enum_values)}"

        # Verify both aliases and class names are present
        assert 'ball_valve' in enum_values, "SFILES alias 'ball_valve' should be in enum"
        assert 'BallValve' in enum_values, "DEXPI class name 'BallValve' should be in enum"

        # Verify description mentions 22 types
        assert "22 valve types" in valve_tool.description, \
            "Tool description should mention 22 valve types"

        # Verify description includes examples
        assert "ball_valve" in valve_tool.description.lower(), \
            "Description should include 'ball_valve' example"

    def test_piping_tool_schema_coverage(self, tool_schemas):
        """Verify dexpi_add_piping exposes all piping types (aliases + class names)."""
        piping_tool = tool_schemas.get("dexpi_add_piping")
        assert piping_tool is not None, "dexpi_add_piping tool not found"

        # Get enum values from schema
        enum_values = piping_tool.inputSchema["properties"]["piping_type"]["enum"]

        # Get expected count from ComponentRegistry (Codex fix: includes both aliases AND class names)
        registry = get_registry()
        piping_components = registry.get_all_by_type(ComponentType.PIPING)
        expected_aliases = set(c.sfiles_alias for c in piping_components)
        expected_classes = set(c.dexpi_class.__name__ for c in piping_components)
        expected_count = len(expected_aliases | expected_classes)

        assert len(enum_values) == expected_count, \
            f"Expected {expected_count} piping types (aliases + class names), got {len(enum_values)}"

        # Verify both aliases and class names are present
        assert 'pipe' in enum_values, "SFILES alias 'pipe' should be in enum"
        assert 'Pipe' in enum_values, "DEXPI class name 'Pipe' should be in enum"

        # Verify description mentions 79 types
        assert "79 types" in piping_tool.description, \
            "Tool description should mention 79 piping types"

        # Verify description includes examples
        description_lower = piping_tool.description.lower()
        assert "pipe" in description_lower or "flow_meter" in description_lower, \
            "Description should include piping component examples"

    def test_instrumentation_tool_schema_coverage(self, tool_schemas):
        """Verify dexpi_add_instrumentation exposes all instrumentation types (aliases + class names)."""
        instrumentation_tool = tool_schemas.get("dexpi_add_instrumentation")
        assert instrumentation_tool is not None, "dexpi_add_instrumentation tool not found"

        # Get enum values from schema
        enum_values = instrumentation_tool.inputSchema["properties"]["instrument_type"]["enum"]

        # Get expected count from ComponentRegistry (Codex fix: includes both aliases AND class names)
        registry = get_registry()
        instrumentation_components = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
        expected_aliases = set(c.sfiles_alias for c in instrumentation_components)
        expected_classes = set(c.dexpi_class.__name__ for c in instrumentation_components)
        expected_count = len(expected_aliases | expected_classes)

        assert len(enum_values) == expected_count, \
            f"Expected {expected_count} instrumentation types (aliases + class names), got {len(enum_values)}"

        # Verify both aliases and class names are present
        assert 'transmitter' in enum_values, "SFILES alias 'transmitter' should be in enum"
        assert 'Transmitter' in enum_values, "DEXPI class name 'Transmitter' should be in enum"

        # Verify description mentions 34 types
        assert "34 types" in instrumentation_tool.description, \
            "Tool description should mention 34 instrumentation types"

        # Verify description includes examples
        assert "transmitter" in instrumentation_tool.description.lower(), \
            "Description should include 'transmitter' example"

    def test_total_component_coverage(self):
        """Verify total of 272 component types (159 + 79 + 34)."""
        registry = get_registry()

        equipment_count = len(registry.list_all_aliases(ComponentType.EQUIPMENT))
        piping_count = len(registry.list_all_aliases(ComponentType.PIPING))
        instrumentation_count = len(registry.list_all_aliases(ComponentType.INSTRUMENTATION))

        total = equipment_count + piping_count + instrumentation_count

        assert total == 272, \
            f"Expected 272 total components, got {total} " \
            f"({equipment_count} equipment + {piping_count} piping + {instrumentation_count} instrumentation)"

    def test_deprecated_valve_tool_coverage(self, tool_schemas):
        """Verify deprecated dexpi_add_valve has valve types (aliases + class names)."""
        valve_tool = tool_schemas.get("dexpi_add_valve")
        assert valve_tool is not None, "dexpi_add_valve tool not found"

        # Get enum values from schema
        enum_values = valve_tool.inputSchema["properties"]["valve_type"]["enum"]

        # Get expected count from ComponentRegistry (Codex fix: includes both aliases AND class names)
        registry = get_registry()
        valve_components = registry.get_all_by_category(ComponentCategory.VALVE)
        expected_aliases = set(c.sfiles_alias for c in valve_components)
        expected_classes = set(c.dexpi_class.__name__ for c in valve_components)
        expected_count = len(expected_aliases | expected_classes)

        assert len(enum_values) == expected_count, \
            f"Expected {expected_count} valve types (aliases + class names), got {len(enum_values)}"

        # Verify it's marked as deprecated
        assert "DEPRECATED" in valve_tool.description, \
            "Deprecated tool should be marked as DEPRECATED"

    def test_insert_valve_tool_coverage(self, tool_schemas):
        """Verify dexpi_insert_valve_in_segment has valve types (aliases + class names)."""
        valve_tool = tool_schemas.get("dexpi_insert_valve_in_segment")
        assert valve_tool is not None, "dexpi_insert_valve_in_segment tool not found"

        # Get enum values from schema
        enum_values = valve_tool.inputSchema["properties"]["valve_type"]["enum"]

        # Get expected count from ComponentRegistry (Codex fix: includes both aliases AND class names)
        registry = get_registry()
        valve_components = registry.get_all_by_category(ComponentCategory.VALVE)
        expected_aliases = set(c.sfiles_alias for c in valve_components)
        expected_classes = set(c.dexpi_class.__name__ for c in valve_components)
        expected_count = len(expected_aliases | expected_classes)

        assert len(enum_values) == expected_count, \
            f"Expected {expected_count} valve types (aliases + class names), got {len(enum_values)}"

    def test_tool_enums_are_sorted(self, tool_schemas):
        """Verify all tool enums are alphabetically sorted for consistency."""
        tools_with_enums = [
            ("dexpi_add_equipment", "equipment_type"),
            ("dexpi_add_valve", "valve_type"),
            ("dexpi_add_valve_between_components", "valve_type"),
            ("dexpi_insert_valve_in_segment", "valve_type"),
            ("dexpi_add_piping", "piping_type"),
            ("dexpi_add_instrumentation", "instrument_type"),
        ]

        for tool_name, param_name in tools_with_enums:
            tool = tool_schemas.get(tool_name)
            if tool is None:
                continue

            enum_values = tool.inputSchema["properties"][param_name]["enum"]
            sorted_values = sorted(enum_values)

            assert enum_values == sorted_values, \
                f"{tool_name}.{param_name} enum should be sorted alphabetically"

    def test_tool_descriptions_mention_both_alias_types(self, tool_schemas):
        """Verify tool descriptions mention both SFILES aliases and DEXPI class names."""
        tools_to_check = [
            "dexpi_add_equipment",
            "dexpi_add_valve_between_components",
            "dexpi_add_piping",
            "dexpi_add_instrumentation",
        ]

        for tool_name in tools_to_check:
            tool = tool_schemas.get(tool_name)
            if tool is None:
                continue

            description = tool.description.lower()

            # Check for mentions of both alias types
            assert "sfiles alias" in description or "dexpi class name" in description, \
                f"{tool_name} description should mention support for both SFILES aliases and DEXPI class names"


class TestToolSchemaExamples:
    """Verify tool schema examples are valid component types."""

    @pytest.fixture
    def registry(self):
        """Get ComponentRegistry instance."""
        return get_registry()

    def test_equipment_examples_are_valid(self, registry):
        """Verify equipment tool examples are valid types."""
        examples = ["pump", "boiler", "conveyor", "steam_generator", "crusher"]

        for example in examples:
            component_def = registry.get_by_alias(example)
            assert component_def is not None, \
                f"Equipment example '{example}' should be a valid component type"
            assert component_def.component_type == ComponentType.EQUIPMENT, \
                f"Equipment example '{example}' should be an equipment type"

    def test_valve_examples_are_valid(self, registry):
        """Verify valve tool examples are valid types."""
        examples = ["ball_valve", "butterfly_valve", "check_valve"]

        for example in examples:
            component_def = registry.get_by_alias(example)
            assert component_def is not None, \
                f"Valve example '{example}' should be a valid component type"
            assert component_def.category == ComponentCategory.VALVE, \
                f"Valve example '{example}' should have VALVE category"

    def test_instrumentation_examples_are_valid(self, registry):
        """Verify instrumentation tool examples are valid types."""
        examples = ["transmitter", "positioner"]

        for example in examples:
            component_def = registry.get_by_alias(example)
            assert component_def is not None, \
                f"Instrumentation example '{example}' should be a valid component type"
            assert component_def.component_type == ComponentType.INSTRUMENTATION, \
                f"Instrumentation example '{example}' should be an instrumentation type"
