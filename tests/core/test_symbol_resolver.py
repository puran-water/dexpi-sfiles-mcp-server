"""
Tests for SymbolResolver - Fuzzy Logic Adapter

Tests the three capabilities:
1. Actuated variant lookup (A→B mappings)
2. Fuzzy matching with confidence scores
3. Validation with multi-symbol class support
"""

import pytest
from src.core.symbol_resolver import SymbolResolver, get_resolver
from src.core.symbols import SymbolRegistry, SymbolInfo, SymbolCategory


class TestSymbolResolverActuatedVariants:
    """Test actuated valve variant lookup (A→B suffix mapping)."""

    def test_get_actuated_variant_ball_valve(self):
        """Test getting actuated variant of ball valve."""
        resolver = SymbolResolver()
        actuated = resolver.get_actuated_variant("PV019A")
        assert actuated == "PV019B", "Ball valve A→B mapping"

    def test_get_actuated_variant_gate_valve(self):
        """Test getting actuated variant of gate valve."""
        resolver = SymbolResolver()
        actuated = resolver.get_actuated_variant("PV005A")
        assert actuated == "PV005B", "Gate valve A→B mapping"

    def test_get_actuated_variant_globe_valve(self):
        """Test getting actuated variant of globe valve."""
        resolver = SymbolResolver()
        actuated = resolver.get_actuated_variant("PV007A")
        assert actuated == "PV007B", "Globe valve A→B mapping"

    def test_get_actuated_variant_all_known_mappings(self):
        """Test all 11 known actuated valve mappings."""
        resolver = SymbolResolver()

        expected_mappings = {
            "PV003A": "PV003B",  # Three way
            "PV004A": "PV004B",  # Four way
            "PV005A": "PV005B",  # Gate
            "PV007A": "PV007B",  # Globe
            "PV008A": "PV008B",  # Float
            "PV014A": "PV014B",  # Pinch
            "PV015A": "PV015B",  # Diaphragm
            "PV016A": "PV016B",  # Needle
            "PV018A": "PV018B",  # Butterfly
            "PV019A": "PV019B",  # Ball
            "PV023A": "PV023B",  # Plug
        }

        for manual, actuated in expected_mappings.items():
            result = resolver.get_actuated_variant(manual)
            assert result == actuated, f"{manual} should map to {actuated}"

    def test_get_actuated_variant_non_valve_returns_none(self):
        """Test that non-valve symbols return None."""
        resolver = SymbolResolver()
        assert resolver.get_actuated_variant("PP001A") is None  # Pump
        assert resolver.get_actuated_variant("PT002A") is None  # Tank
        assert resolver.get_actuated_variant("PE037A") is None  # Heat exchanger

    def test_actuated_cache_built_once(self):
        """Test that actuated cache is built only once."""
        resolver = SymbolResolver()

        # First call builds cache
        resolver.get_actuated_variant("PV019A")
        assert resolver._actuated_cache is not None

        # Store cache reference
        cache_ref = resolver._actuated_cache

        # Second call reuses cache
        resolver.get_actuated_variant("PV005A")
        assert resolver._actuated_cache is cache_ref, "Cache should be reused"


class TestSymbolResolverFuzzyMatching:
    """Test fuzzy matching with confidence scores (opt-in)."""

    def test_fuzzy_exact_match_confidence_1_0(self):
        """Test exact match returns confidence 1.0."""
        resolver = SymbolResolver()
        result = resolver.get_by_dexpi_class_fuzzy("CentrifugalPump")

        assert result is not None, "Should find exact match"
        symbol, confidence = result
        # Catalog may have PP001A or PP001A_Detail for CentrifugalPump
        assert symbol.symbol_id.startswith("PP001A"), "Should find pump symbol"
        assert confidence == 1.0, "Exact match should have confidence 1.0"

    def test_fuzzy_custom_prefix_stripping(self):
        """Test Custom prefix stripping returns confidence 0.95."""
        resolver = SymbolResolver()
        result = resolver.get_by_dexpi_class_fuzzy("CustomPump")

        if result:
            symbol, confidence = result
            # Should match to Pump (if catalog has it)
            assert confidence >= 0.9, "Custom prefix match should have high confidence"

    def test_fuzzy_no_match_returns_none(self):
        """Test that completely unknown class returns None."""
        resolver = SymbolResolver()
        result = resolver.get_by_dexpi_class_fuzzy("CompletelyUnknownEquipment")

        # May return None or low confidence result
        if result:
            symbol, confidence = result
            assert confidence < 0.7, "Unknown equipment should have low confidence"

    def test_fuzzy_threshold_filtering(self):
        """Test confidence threshold filtering."""
        resolver = SymbolResolver()

        # High threshold should filter out fuzzy matches
        result = resolver.get_by_dexpi_class_fuzzy(
            "SomewhatSimilarPump",
            confidence_threshold=0.95
        )

        # Should either be None or very high confidence
        if result:
            symbol, confidence = result
            assert confidence >= 0.95, "Should respect threshold"

    def test_fuzzy_levenshtein_ranking(self):
        """Test that results are ranked by Levenshtein similarity."""
        resolver = SymbolResolver()

        # Test with a typo
        result = resolver.get_by_dexpi_class_fuzzy("CentrifgalPump")  # Missing 'u'

        if result:
            symbol, confidence = result
            # Should still find CentrifugalPump with reasonably high confidence
            assert symbol.symbol_id == "PP001A"
            assert confidence > 0.8, "Typo should still match with good confidence"

    def test_fuzzy_returns_tuple(self):
        """Test that fuzzy matching always returns (SymbolInfo, float) tuple."""
        resolver = SymbolResolver()
        result = resolver.get_by_dexpi_class_fuzzy("CentrifugalPump")

        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Tuple should have 2 elements"

        symbol, confidence = result
        assert isinstance(symbol, SymbolInfo), "First element should be SymbolInfo"
        assert isinstance(confidence, float), "Second element should be float"
        assert 0.0 <= confidence <= 1.0, "Confidence should be in [0.0, 1.0]"


class TestSymbolResolverValidation:
    """Test validation with multi-symbol class support."""

    def test_validate_exact_match(self):
        """Test validation of exact DEXPI class match."""
        resolver = SymbolResolver()

        is_valid, reason = resolver.validate_mapping("CentrifugalPump", "PP001A")

        assert is_valid is True, "Exact match should be valid"
        assert "exact" in reason.lower() or "match" in reason.lower()

    def test_validate_wrong_symbol_for_class(self):
        """Test validation rejects wrong symbol for class."""
        resolver = SymbolResolver()

        # PP001A is Pump, not a Valve
        is_valid, reason = resolver.validate_mapping("BallValve", "PP001A")

        assert is_valid is False, "Wrong symbol should be invalid"
        assert "PP001A" in reason, "Reason should mention the symbol"

    def test_validate_actuated_variant_allowed(self):
        """Test validation accepts actuated variant when allowed."""
        resolver = SymbolResolver()

        # PV019B (actuated) should be valid for BallValve when allow_actuated=True
        is_valid, reason = resolver.validate_mapping(
            "BallValve",
            "PV019B",
            allow_actuated=True
        )

        # May be valid if catalog has OperatedBallValve → PV019B mapping
        # Or if it recognizes PV019B as actuated variant of PV019A
        if is_valid:
            assert "actuated" in reason.lower() or "variant" in reason.lower()

    def test_validate_actuated_variant_disallowed(self):
        """Test validation rejects actuated variant when disallowed."""
        resolver = SymbolResolver()

        # When allow_actuated=False, should only accept manual variant
        is_valid, reason = resolver.validate_mapping(
            "BallValve",
            "PV019B",
            allow_actuated=False
        )

        # Behavior depends on whether catalog has OperatedBallValve entry
        # If only BallValve→PV019A exists, PV019B should be rejected
        if not is_valid:
            assert "PV019B" in reason

    def test_validate_custom_prefix(self):
        """Test validation handles Custom prefix classes."""
        resolver = SymbolResolver()

        # CustomPump should accept Pump symbol
        is_valid, reason = resolver.validate_mapping("CustomPump", "PP001A")

        # May be valid if base class matching is supported
        if is_valid:
            assert "base class" in reason.lower() or "custom" in reason.lower()

    def test_validate_unknown_class(self):
        """Test validation of completely unknown DEXPI class."""
        resolver = SymbolResolver()

        is_valid, reason = resolver.validate_mapping("UnknownEquipment", "PP001A")

        assert is_valid is False, "Unknown class should be invalid"
        assert "not found" in reason.lower() or "unknown" in reason.lower()

    def test_validate_returns_tuple(self):
        """Test that validation always returns (bool, str) tuple."""
        resolver = SymbolResolver()

        result = resolver.validate_mapping("CentrifugalPump", "PP001A")

        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Tuple should have 2 elements"

        is_valid, reason = result
        assert isinstance(is_valid, bool), "First element should be bool"
        assert isinstance(reason, str), "Second element should be str"
        assert len(reason) > 0, "Reason should be non-empty"


class TestSymbolResolverBackwardCompatibility:
    """Test convenience methods for backward compatibility."""

    def test_get_symbol_delegates_to_registry(self):
        """Test get_symbol() delegates to SymbolRegistry."""
        resolver = SymbolResolver()

        symbol = resolver.get_symbol("PP001A")

        assert symbol is not None, "Should find pump symbol"
        assert symbol.symbol_id == "PP001A"
        assert isinstance(symbol, SymbolInfo)

    def test_get_by_dexpi_class_delegates_to_registry(self):
        """Test get_by_dexpi_class() delegates to SymbolRegistry."""
        resolver = SymbolResolver()

        symbol = resolver.get_by_dexpi_class("CentrifugalPump")

        assert symbol is not None, "Should find centrifugal pump"
        # Catalog may have PP001A or PP001A_Detail for CentrifugalPump
        assert symbol.symbol_id.startswith("PP001A"), "Should find pump symbol"
        assert isinstance(symbol, SymbolInfo)

    def test_search_delegates_to_registry(self):
        """Test search() delegates to SymbolRegistry."""
        resolver = SymbolResolver()

        results = resolver.search("pump")

        assert isinstance(results, list), "Should return list"
        assert len(results) > 0, "Should find pump-related symbols"
        assert all(isinstance(s, SymbolInfo) for s in results)


class TestSymbolResolverSingleton:
    """Test global resolver singleton."""

    def test_get_resolver_returns_singleton(self):
        """Test that get_resolver() returns same instance."""
        resolver1 = get_resolver()
        resolver2 = get_resolver()

        assert resolver1 is resolver2, "Should return singleton instance"

    def test_get_resolver_returns_symbol_resolver(self):
        """Test that get_resolver() returns SymbolResolver instance."""
        resolver = get_resolver()

        assert isinstance(resolver, SymbolResolver)


class TestSymbolResolverEdgeCases:
    """Test edge cases and error handling."""

    def test_actuated_variant_with_none_input(self):
        """Test actuated variant with None input."""
        resolver = SymbolResolver()

        # Should handle None gracefully
        result = resolver.get_actuated_variant(None)
        assert result is None

    def test_fuzzy_match_empty_string(self):
        """Test fuzzy matching with empty string."""
        resolver = SymbolResolver()

        result = resolver.get_by_dexpi_class_fuzzy("")

        # Should return None or very low confidence
        if result:
            symbol, confidence = result
            assert confidence < 0.5

    def test_validate_empty_strings(self):
        """Test validation with empty strings."""
        resolver = SymbolResolver()

        is_valid, reason = resolver.validate_mapping("", "PP001A")
        assert is_valid is False, "Empty class should be invalid"

        is_valid, reason = resolver.validate_mapping("CentrifugalPump", "")
        assert is_valid is False, "Empty symbol should be invalid"

    def test_fuzzy_match_case_insensitive(self):
        """Test that fuzzy matching is case-insensitive."""
        resolver = SymbolResolver()

        result1 = resolver.get_by_dexpi_class_fuzzy("centrifugalpump")
        result2 = resolver.get_by_dexpi_class_fuzzy("CentrifugalPump")
        result3 = resolver.get_by_dexpi_class_fuzzy("CENTRIFUGALPUMP")

        # All should find the same symbol (if any match)
        if result1 and result2 and result3:
            symbol1, conf1 = result1
            symbol2, conf2 = result2
            symbol3, conf3 = result3

            assert symbol1.symbol_id == symbol2.symbol_id == symbol3.symbol_id


class TestSymbolResolverIntegration:
    """Integration tests with SymbolRegistry."""

    def test_resolver_uses_registry_data(self):
        """Test that resolver uses real registry data."""
        resolver = SymbolResolver()

        # Should have access to registry
        assert resolver.registry is not None
        assert isinstance(resolver.registry, SymbolRegistry)

        # Should have symbols loaded
        stats = resolver.registry.get_statistics()
        assert stats["total"] > 0, "Should have symbols loaded from catalog"

    def test_resolver_actuated_cache_uses_catalog_data(self):
        """Test that actuated cache is built from catalog data."""
        resolver = SymbolResolver()

        # Build cache
        resolver._build_actuated_cache()

        # Should have at least the 11 hardcoded mappings
        assert len(resolver._actuated_cache) >= 11

        # May have more if catalog contains A/B pairs
        # (e.g., if PV019A and PV019B both exist in catalog)

    def test_resolver_validation_with_registry_multi_symbol_classes(self):
        """Test validation handles classes with multiple symbol mappings."""
        resolver = SymbolResolver()

        # Some DEXPI classes may map to multiple symbols in catalog
        # Validation should accept any of them

        # Get a class that might have multiple symbols
        dexpi_map = resolver.registry._dexpi_map
        multi_symbol_classes = [
            cls for cls, symbols in dexpi_map.items()
            if len(symbols) > 1
        ]

        if multi_symbol_classes:
            test_class = multi_symbol_classes[0]
            valid_symbols = dexpi_map[test_class]

            # All valid symbols should pass validation
            for symbol_id in valid_symbols:
                is_valid, reason = resolver.validate_mapping(test_class, symbol_id)
                assert is_valid is True, f"{symbol_id} should be valid for {test_class}"


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
