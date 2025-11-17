"""Unit tests for GenericAttributeExporter._serialize_value() method.

This test suite focuses on isolated unit testing of the _serialize_value() method
which handles dynamic Pydantic field introspection and serialization to GenericAttribute
dictionaries for Proteus XML export.

Coverage:
- Multi-language strings (flatten to multiple SingleLanguageString entries)
- Single-language strings (with/without language attribute)
- Enumerations (using .name property)
- Primitives (bool, int, float, str with FORMAT_MAP)
- datetime (isoformat conversion)
- Physical quantities (value+unit extraction, None value handling)
- Lists/tuples (recursive flattening)
- CustomAttributes (AttributeURI propagation via _apply_extra)
- Fallback stringification for unknown types
- None values (empty list return)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import pytest

from pydexpi.dexpi_classes import dataTypes, physicalQuantities
from src.exporters.proteus_xml_exporter import GenericAttributeExporter


class TestSerializeValue:
    """Test suite for GenericAttributeExporter._serialize_value() method."""

    @pytest.fixture
    def exporter(self) -> GenericAttributeExporter:
        """Create a GenericAttributeExporter instance for testing."""
        return GenericAttributeExporter()

    # Test 1: None values → empty list
    def test_serialize_none_returns_empty_list(self, exporter: GenericAttributeExporter) -> None:
        """Test that None values return an empty list."""
        result = exporter._serialize_value("TestAttr", None)
        assert result == []

    # Test 2: MultiLanguageString → multiple entries
    def test_serialize_multi_language_string(self, exporter: GenericAttributeExporter) -> None:
        """Test that MultiLanguageString flattens to multiple SingleLanguageString entries."""
        multi_lang = dataTypes.MultiLanguageString(
            singleLanguageStrings=[
                dataTypes.SingleLanguageString(value="English text", language="en"),
                dataTypes.SingleLanguageString(value="German text", language="de"),
            ]
        )
        result = exporter._serialize_value("Description", multi_lang)

        assert len(result) == 2
        assert result[0] == {
            "Name": "Description",
            "Format": "string",
            "Value": "English text",
            "Language": "en",
        }
        assert result[1] == {
            "Name": "Description",
            "Format": "string",
            "Value": "German text",
            "Language": "de",
        }

    # Test 3: SingleLanguageString with language
    def test_serialize_single_language_string_with_language(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test SingleLanguageString with language attribute."""
        single_lang = dataTypes.SingleLanguageString(value="Test value", language="en")
        result = exporter._serialize_value("Label", single_lang)

        assert len(result) == 1
        assert result[0] == {
            "Name": "Label",
            "Format": "string",
            "Value": "Test value",
            "Language": "en",
        }

    # Test 4: SingleLanguageString without language
    def test_serialize_single_language_string_without_language(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test SingleLanguageString without language attribute."""
        single_lang = dataTypes.SingleLanguageString(value="Test value", language=None)
        result = exporter._serialize_value("Label", single_lang)

        assert len(result) == 1
        assert result[0] == {
            "Name": "Label",
            "Format": "string",
            "Value": "Test value",
        }
        assert "Language" not in result[0]

    # Test 5: SingleLanguageString with None value → empty list
    def test_serialize_single_language_string_with_none_value(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that SingleLanguageString with None value returns empty list."""
        single_lang = dataTypes.SingleLanguageString(value=None, language="en")
        result = exporter._serialize_value("Label", single_lang)

        assert result == []

    # Test 6: Enum using .name
    def test_serialize_enum(self, exporter: GenericAttributeExporter) -> None:
        """Test that Enum values use the .name property."""

        class TestEnum(Enum):
            OPTION_ONE = "option1"
            OPTION_TWO = "option2"

        result = exporter._serialize_value("Status", TestEnum.OPTION_ONE)

        assert len(result) == 1
        assert result[0] == {
            "Name": "Status",
            "Format": "string",
            "Value": "OPTION_ONE",
        }

    # Test 7: Boolean → lowercase string
    def test_serialize_boolean(self, exporter: GenericAttributeExporter) -> None:
        """Test that boolean values are converted to lowercase strings."""
        result_true = exporter._serialize_value("IsActive", True)
        result_false = exporter._serialize_value("IsActive", False)

        assert len(result_true) == 1
        assert result_true[0] == {
            "Name": "IsActive",
            "Format": "string",
            "Value": "true",
        }

        assert len(result_false) == 1
        assert result_false[0] == {
            "Name": "IsActive",
            "Format": "string",
            "Value": "false",
        }

    # Test 8: Integer using FORMAT_MAP
    def test_serialize_integer(self, exporter: GenericAttributeExporter) -> None:
        """Test that integers use FORMAT_MAP (integer format)."""
        result = exporter._serialize_value("Count", 42)

        assert len(result) == 1
        assert result[0] == {
            "Name": "Count",
            "Format": "integer",
            "Value": "42",
        }

    # Test 9: Float using FORMAT_MAP
    def test_serialize_float(self, exporter: GenericAttributeExporter) -> None:
        """Test that floats use FORMAT_MAP (double format)."""
        result = exporter._serialize_value("Temperature", 98.6)

        assert len(result) == 1
        assert result[0] == {
            "Name": "Temperature",
            "Format": "double",
            "Value": "98.6",
        }

    # Test 10: String using FORMAT_MAP
    def test_serialize_string(self, exporter: GenericAttributeExporter) -> None:
        """Test that strings use FORMAT_MAP (string format)."""
        result = exporter._serialize_value("Name", "Test Equipment")

        assert len(result) == 1
        assert result[0] == {
            "Name": "Name",
            "Format": "string",
            "Value": "Test Equipment",
        }

    # Test 11: datetime → isoformat
    def test_serialize_datetime(self, exporter: GenericAttributeExporter) -> None:
        """Test that datetime values are converted to isoformat."""
        dt = datetime(2024, 11, 16, 14, 30, 45)
        result = exporter._serialize_value("Timestamp", dt)

        assert len(result) == 1
        assert result[0] == {
            "Name": "Timestamp",
            "Format": "string",
            "Value": "2024-11-16T14:30:45",
        }

    # Test 12: Physical quantity with value+unit
    def test_serialize_physical_quantity_with_value_and_unit(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test physical quantity serialization with both value and unit."""
        length = physicalQuantities.Length(value=100.0, unit="mm")
        result = exporter._serialize_value("Diameter", length)

        assert len(result) == 1
        assert result[0]["Name"] == "Diameter"
        assert result[0]["Format"] == "double"
        assert result[0]["Value"] == "100.0"
        # pyDEXPI converts unit to enum name (e.g., "mm" → "Millimetre")
        assert result[0]["Units"] == "Millimetre"

    # Test 13: Physical quantity with value but no unit specified
    def test_serialize_physical_quantity_default_unit(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test physical quantity serialization with default unit."""
        # PressureAbsolute has a default unit, test serialization
        pressure = physicalQuantities.PressureAbsolute(value=101.325, unit="bar")
        result = exporter._serialize_value("Pressure", pressure)

        assert len(result) == 1
        assert result[0]["Name"] == "Pressure"
        assert result[0]["Format"] == "double"
        assert result[0]["Value"] == "101.325"
        assert "Units" in result[0]

    # Test 15: List → flattens items
    def test_serialize_list(self, exporter: GenericAttributeExporter) -> None:
        """Test that lists are flattened with each item serialized separately."""
        items = [10, 20, 30]
        result = exporter._serialize_value("Values", items)

        assert len(result) == 3
        assert result[0] == {"Name": "Values", "Format": "integer", "Value": "10"}
        assert result[1] == {"Name": "Values", "Format": "integer", "Value": "20"}
        assert result[2] == {"Name": "Values", "Format": "integer", "Value": "30"}

    # Test 16: Tuple → flattens items
    def test_serialize_tuple(self, exporter: GenericAttributeExporter) -> None:
        """Test that tuples are flattened with each item serialized separately."""
        items = ("first", "second", "third")
        result = exporter._serialize_value("Tags", items)

        assert len(result) == 3
        assert result[0] == {"Name": "Tags", "Format": "string", "Value": "first"}
        assert result[1] == {"Name": "Tags", "Format": "string", "Value": "second"}
        assert result[2] == {"Name": "Tags", "Format": "string", "Value": "third"}

    # Test 17: Mixed list items
    def test_serialize_mixed_list(self, exporter: GenericAttributeExporter) -> None:
        """Test that lists with mixed types are handled correctly."""
        items = [42, "text", True]
        result = exporter._serialize_value("Mixed", items)

        assert len(result) == 3
        assert result[0] == {"Name": "Mixed", "Format": "integer", "Value": "42"}
        assert result[1] == {"Name": "Mixed", "Format": "string", "Value": "text"}
        assert result[2] == {"Name": "Mixed", "Format": "string", "Value": "true"}

    # Test 18: AttributeURI propagation via _apply_extra
    def test_serialize_with_extra_attribute_uri(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that extra attributes (like AttributeURI) are propagated."""
        extra = {"AttributeURI": "http://example.com/custom"}
        result = exporter._serialize_value("CustomAttr", "test_value", extra)

        assert len(result) == 1
        assert result[0] == {
            "Name": "CustomAttr",
            "Format": "string",
            "Value": "test_value",
            "AttributeURI": "http://example.com/custom",
        }

    # Test 19: Multiple extra attributes
    def test_serialize_with_multiple_extra_attributes(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that multiple extra attributes are propagated."""
        extra = {
            "AttributeURI": "http://example.com/custom",
            "Source": "UserInput",
            "Version": "1.0",
        }
        result = exporter._serialize_value("CustomAttr", 100, extra)

        assert len(result) == 1
        assert result[0] == {
            "Name": "CustomAttr",
            "Format": "integer",
            "Value": "100",
            "AttributeURI": "http://example.com/custom",
            "Source": "UserInput",
            "Version": "1.0",
        }

    # Test 20: Fallback object stringification
    def test_serialize_unknown_object_fallback(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that unknown object types are stringified as fallback."""

        class CustomObject:
            def __str__(self) -> str:
                return "CustomObjectString"

        obj = CustomObject()
        result = exporter._serialize_value("UnknownType", obj)

        assert len(result) == 1
        assert result[0] == {
            "Name": "UnknownType",
            "Format": "string",
            "Value": "CustomObjectString",
        }

    # Test 21: Nested list serialization
    def test_serialize_nested_list_flattens(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that nested lists are flattened recursively."""
        nested = [[1, 2], [3, 4]]
        result = exporter._serialize_value("NestedValues", nested)

        # Each inner list is serialized as separate items
        # First inner list [1, 2] becomes 2 items, second inner list [3, 4] becomes 2 items
        assert len(result) == 4

    # Test 22: Empty list returns empty result
    def test_serialize_empty_list(self, exporter: GenericAttributeExporter) -> None:
        """Test that empty lists return empty results."""
        result = exporter._serialize_value("EmptyList", [])
        assert result == []

    # Test 23: Extra with None values should be filtered
    def test_serialize_extra_with_none_values_filtered(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that extra attributes with None values are filtered out."""
        extra = {
            "AttributeURI": "http://example.com/custom",
            "NullField": None,
            "Source": "Test",
        }
        result = exporter._serialize_value("Attr", "value", extra)

        assert len(result) == 1
        assert "NullField" not in result[0]
        assert result[0]["AttributeURI"] == "http://example.com/custom"
        assert result[0]["Source"] == "Test"


class TestHelperMethods:
    """Test suite for GenericAttributeExporter helper methods."""

    @pytest.fixture
    def exporter(self) -> GenericAttributeExporter:
        """Create a GenericAttributeExporter instance for testing."""
        return GenericAttributeExporter()

    # Test _is_empty_value
    def test_is_empty_value_none(self, exporter: GenericAttributeExporter) -> None:
        """Test that None is considered empty."""
        assert exporter._is_empty_value(None) is True

    def test_is_empty_value_empty_string(self, exporter: GenericAttributeExporter) -> None:
        """Test that empty string is considered empty."""
        assert exporter._is_empty_value("") is True

    def test_is_empty_value_non_empty_string(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that non-empty string is not considered empty."""
        assert exporter._is_empty_value("test") is False

    def test_is_empty_value_empty_list(self, exporter: GenericAttributeExporter) -> None:
        """Test that empty list is considered empty."""
        assert exporter._is_empty_value([]) is True

    def test_is_empty_value_non_empty_list(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that non-empty list is not considered empty."""
        assert exporter._is_empty_value([1, 2, 3]) is False

    def test_is_empty_value_empty_dict(self, exporter: GenericAttributeExporter) -> None:
        """Test that empty dict is considered empty."""
        assert exporter._is_empty_value({}) is True

    def test_is_empty_value_non_empty_dict(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that non-empty dict is not considered empty."""
        assert exporter._is_empty_value({"key": "value"}) is False

    def test_is_empty_value_zero(self, exporter: GenericAttributeExporter) -> None:
        """Test that zero is not considered empty."""
        assert exporter._is_empty_value(0) is False

    def test_is_empty_value_false(self, exporter: GenericAttributeExporter) -> None:
        """Test that False is not considered empty."""
        assert exporter._is_empty_value(False) is False

    # Test _attribute_name
    def test_attribute_name_snake_case(self, exporter: GenericAttributeExporter) -> None:
        """Test snake_case to CamelCase conversion with suffix."""
        result = exporter._attribute_name("tag_name")
        assert result == "TagNameAssignmentClass"

    def test_attribute_name_single_word(self, exporter: GenericAttributeExporter) -> None:
        """Test single word capitalization with suffix."""
        result = exporter._attribute_name("name")
        assert result == "NameAssignmentClass"

    def test_attribute_name_custom_suffix(self, exporter: GenericAttributeExporter) -> None:
        """Test custom suffix."""
        result = exporter._attribute_name("tag_name", suffix="Value")
        assert result == "TagNameValue"

    def test_attribute_name_empty_suffix(self, exporter: GenericAttributeExporter) -> None:
        """Test with empty suffix."""
        result = exporter._attribute_name("tag_name", suffix="")
        assert result == "TagName"

    def test_attribute_name_empty_field(self, exporter: GenericAttributeExporter) -> None:
        """Test with empty field name."""
        result = exporter._attribute_name("", suffix="Test")
        assert result == "Test"

    # Test _apply_extra
    def test_apply_extra_with_values(self, exporter: GenericAttributeExporter) -> None:
        """Test applying extra attributes."""
        entry: Dict[str, str] = {"Name": "Test", "Format": "string"}
        extra: Dict[str, str] = {"AttributeURI": "http://test.com"}
        result = exporter._apply_extra(entry, extra)

        assert result["AttributeURI"] == "http://test.com"
        assert result["Name"] == "Test"

    def test_apply_extra_with_none(self, exporter: GenericAttributeExporter) -> None:
        """Test applying None extra (no-op)."""
        entry: Dict[str, str] = {"Name": "Test", "Format": "string"}
        result = exporter._apply_extra(entry, None)

        assert result == entry

    def test_apply_extra_filters_none_values(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that None values in extra dict are filtered."""
        entry: Dict[str, str] = {"Name": "Test"}
        extra: Dict[str, Any] = {"URI": "http://test.com", "Null": None}
        result = exporter._apply_extra(entry, extra)

        assert "URI" in result
        assert "Null" not in result

    # Test _looks_like_physical_quantity
    def test_looks_like_physical_quantity_length(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that Length is recognized as physical quantity."""
        length = physicalQuantities.Length(value=100.0, unit="mm")
        assert exporter._looks_like_physical_quantity(length) is True

    def test_looks_like_physical_quantity_temperature(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that Temperature is recognized as physical quantity."""
        temp = physicalQuantities.Temperature(value=25.0, unit="°C")
        assert exporter._looks_like_physical_quantity(temp) is True

    def test_looks_like_physical_quantity_string(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that string is not recognized as physical quantity."""
        assert exporter._looks_like_physical_quantity("test") is False

    def test_looks_like_physical_quantity_int(
        self, exporter: GenericAttributeExporter
    ) -> None:
        """Test that int is not recognized as physical quantity."""
        assert exporter._looks_like_physical_quantity(42) is False
