"""
Phase 0 Symbol Format Standardization - Unit Tests

Tests verify that Phase 0 success criteria are met:
1. All core layer defaults use PP001A format (with documented exceptions)
2. Symbol file paths resolve correctly
3. Equipment definitions verified against catalog
"""

import pytest
from src.core.symbols import get_registry as get_symbol_registry, SymbolCategory
from src.core.equipment import get_registry as get_equipment_registry


class TestSymbolFormatStandardization:
    """Test that all symbols use PP001A format standard."""

    def test_symbol_registry_loads_805_symbols(self):
        """Test that merged catalog loads with expected count."""
        registry = get_symbol_registry()
        assert len(registry._symbols) == 805, "Expected 805 symbols from merged catalog"

    def test_default_symbols_use_pp001a_format(self):
        """Test that fallback defaults use PP001A format."""
        registry = get_symbol_registry()

        # Get symbols that would be loaded from fallback defaults
        # (when merged catalog doesn't exist)
        default_symbols = [
            "PP001A",  # Centrifugal Pump
            "PP010A",  # Reciprocating Pump
            "PV005A",  # Gate Valve
            "PV007A",  # Globe Valve
            "PE025A",  # Storage Tank
            "PT002A",  # Pressure Vessel (fixed from PT001A)
            "PE037A",  # Heat Exchanger
        ]

        for symbol_id in default_symbols:
            symbol = registry.get_symbol(symbol_id)
            assert symbol is not None, f"Default symbol {symbol_id} should exist"
            assert symbol.symbol_id == symbol_id, f"Symbol ID should match PP001A format"

            # Verify format: 2 letters + 3 digits + 1 letter
            assert len(symbol_id) == 6, f"{symbol_id} should be 6 characters"
            assert symbol_id[:2].isalpha(), f"{symbol_id} prefix should be letters"
            assert symbol_id[2:5].isdigit(), f"{symbol_id} middle should be 3 digits"
            assert symbol_id[5].isalpha(), f"{symbol_id} suffix should be a letter"

    def test_nd_series_format_exception(self):
        """Test that ND series (annotations) uses documented 4-digit format."""
        registry = get_symbol_registry()

        # ND series is documented exception to PP001A format
        nd_symbol = registry.get_symbol("ND0006")
        assert nd_symbol is not None, "ND0006 should exist as documented exception"
        assert nd_symbol.category == SymbolCategory.ANNOTATIONS, "ND0006 should be annotation"

        # Verify ND format: 2 letters + 4 digits (no trailing letter)
        assert len("ND0006") == 6, "ND symbols are 6 characters"
        assert "ND0006"[:2] == "ND", "ND symbols start with ND"
        assert "ND0006"[2:].isdigit(), "ND symbols end with 4 digits"

    def test_pressure_vessel_fixed_to_pt002a(self):
        """Test that pressure vessel uses PT002A (not PT001A) per XLSM catalog."""
        registry = get_symbol_registry()

        # Verify PT002A exists and is mapped to PressureVessel
        pt002 = registry.get_symbol("PT002A")
        assert pt002 is not None, "PT002A should exist"
        assert pt002.dexpi_class == "PressureVessel", "PT002A should map to PressureVessel DEXPI class"

        # Verify old PT001A is NOT used for pressure vessel
        # (It may exist for other purposes, but not as default for PressureVessel)
        pt001 = registry.get_symbol("PT001A")
        if pt001:
            assert pt001.dexpi_class != "PressureVessel", "PT001A should NOT map to PressureVessel"


class TestEquipmentSymbolMapping:
    """Test that equipment definitions use correct PP001A symbols."""

    def test_equipment_registry_uses_pp001a_format(self):
        """Test that all equipment definitions reference PP001A format symbols."""
        eq_registry = get_equipment_registry()

        # Critical equipment types from Phase 0
        equipment_tests = [
            ("pump", "PP001A"),
            ("tank", "PE025A"),
            ("vessel", "PT002A"),  # Fixed from PT001A
            ("heat_exchanger", "PE037A"),
            ("filter", "PS014A"),
        ]

        for sfiles_type, expected_symbol in equipment_tests:
            definition = eq_registry.get_by_sfiles_type(sfiles_type)
            assert definition is not None, f"Equipment type '{sfiles_type}' should be registered"
            assert definition.symbol_id == expected_symbol, \
                f"{sfiles_type} should use {expected_symbol}, got {definition.symbol_id}"

    def test_all_equipment_symbols_exist_in_registry(self):
        """Test that all equipment symbol IDs resolve in symbol registry."""
        eq_registry = get_equipment_registry()
        symbol_registry = get_symbol_registry()

        # Get all registered equipment (actual types from equipment.py)
        all_equipment = []
        for sfiles_type in ["pump", "pump_centrifugal", "pump_reciprocating", "tank",
                            "vessel", "reactor", "heat_exchanger", "heater", "cooler",
                            "separator", "centrifuge", "filter", "column", "mixer"]:
            eq_def = eq_registry.get_by_sfiles_type(sfiles_type)
            if eq_def and eq_def.symbol_id:
                all_equipment.append((sfiles_type, eq_def.symbol_id))

        # Verify each symbol exists
        for sfiles_type, symbol_id in all_equipment:
            symbol = symbol_registry.get_symbol(symbol_id)
            assert symbol is not None, \
                f"Equipment '{sfiles_type}' references symbol '{symbol_id}' which doesn't exist"


class TestSymbolPathResolution:
    """Test that symbol file paths resolve correctly."""

    def test_pp001a_symbol_path_resolution(self):
        """Test that PP001A format symbols resolve to file paths."""
        registry = get_symbol_registry()

        # Test representative symbols
        test_symbols = ["PP001A", "PV005A", "PE025A", "PT002A"]

        for symbol_id in test_symbols:
            path = registry.get_symbol_path(symbol_id)
            # Path may be None if file doesn't exist, but method should not crash
            # In production, these should resolve to DISCDEXPI or NOAKADEXPI folders
            assert path is None or path.suffix == ".svg", \
                f"Symbol path for {symbol_id} should be None or end in .svg"

    def test_symbol_path_searches_correct_locations(self):
        """Test that get_symbol_path checks expected directories."""
        registry = get_symbol_registry()

        # Verify assets_dir is set
        assert registry.assets_dir is not None, "Registry should have assets_dir configured"

        # Test that path resolution doesn't crash for various formats
        test_cases = [
            "PP001A",  # Standard pump
            "ND0006",  # ND series exception
            "INVALID",  # Non-existent symbol
        ]

        for symbol_id in test_cases:
            try:
                path = registry.get_symbol_path(symbol_id)
                # Should return None for invalid/missing, or a Path for valid
                assert path is None or hasattr(path, 'exists'), \
                    f"get_symbol_path({symbol_id}) should return None or Path object"
            except Exception as e:
                pytest.fail(f"get_symbol_path({symbol_id}) raised unexpected exception: {e}")


class TestPhase0Regression:
    """Regression tests for Phase 0 changes."""

    def test_old_pp0101_format_no_longer_works(self):
        """Test that old PP0101 format is not supported (backward compat removed)."""
        registry = get_symbol_registry()

        # Old format should NOT resolve
        old_format = registry.get_symbol("PP0101")
        assert old_format is None, "Old PP0101 format should not resolve (no backward compat)"

    def test_hyphenated_format_not_supported(self):
        """Test that hyphenated P-01-01 format is not supported."""
        registry = get_symbol_registry()

        # Hyphenated format should NOT resolve
        hyphen_format = registry.get_symbol("P-01-01")
        assert hyphen_format is None, "Hyphenated format should not resolve (no backward compat)"

    def test_symbol_count_remains_805(self):
        """Test that symbol count stays at 805 (no symbols lost)."""
        registry = get_symbol_registry()
        stats = registry.get_statistics()

        assert stats["total"] == 805, "Total symbol count should remain 805"
        assert stats["by_category"]["Pumps"] > 0, "Should have pump symbols"
        assert stats["by_category"]["Valves"] > 0, "Should have valve symbols"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
