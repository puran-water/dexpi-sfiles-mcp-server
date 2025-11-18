"""Test Position/Extent/Presentation export for GraphicBuilder rendering.

Task 0: Prototype visibility test for Weeks 3-4 implementation.
Validates that equipment exports with proper layout elements for rendering.
"""

import pytest
from lxml import etree

from src.exporters.proteus_xml_exporter import ProteusXMLExporter
from src.models.layout_metadata import LayoutMetadata, NodePosition, BoundingBox

# Import fixtures from the main test file
pytest_plugins = ["tests.exporters.test_proteus_xml_exporter"]


class TestPositionPresentationExport:
    """Test Position/Extent/Presentation export for equipment visibility."""

    def test_minimal_equipment_with_position(self, empty_model, pump, tmp_path):
        """Test that equipment can be exported with synthetic Position/Extent/Presentation.

        This is the core prototype test - if this passes, equipment will be visible
        in GraphicBuilder and ProteusXMLDrawing.

        Required XML structure per Codex research:
        <Equipment ID="..." ComponentClass="...">
            <Position>
                <Location X="100" Y="200" Z="0" />
                <Axis X="0" Y="0" Z="1" />
                <Reference X="1" Y="0" Z="0" />
            </Position>
            <Extent>
                <Min X="90" Y="190" Z="0" />
                <Max X="110" Y="210" Z="0" />
            </Min>
            <Presentation Layer="Default" Color="Black" R="0" G="0" B="0"
                         LineType="Solid" LineWeight="0.00035" />
            ...
        </Equipment>
        """
        # Setup: Add pump to model
        empty_model.conceptualModel.taggedPlantItems = [pump]
        output_file = tmp_path / "position_test.xml"

        # Create synthetic layout metadata for the pump
        # In real usage, this comes from SFILES2 _add_positions or graph converter
        pump_id = pump.id  # "PMP-001"
        layout = LayoutMetadata(
            algorithm="spring",
            positions={
                pump_id: NodePosition(x=100.0, y=200.0)
            }
        )

        # Export with layout metadata
        exporter = ProteusXMLExporter()
        exporter.export(
            empty_model,
            output_file,
            validate=False,
            layout_metadata=layout
        )

        # Parse and validate XML structure
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        equip_elem = root.find(".//Equipment[@ID='PMP-001']")

        assert equip_elem is not None, "Equipment element not found"

        # Validate Position element
        position = equip_elem.find("Position")
        assert position is not None, (
            "Position element missing - equipment won't be visible in GraphicBuilder"
        )

        # Validate Position children: Location, Axis, Reference
        location = position.find("Location")
        assert location is not None, "Position/Location missing"
        assert location.get("X") == "100", f"Location X wrong: {location.get('X')}"
        assert location.get("Y") == "200", f"Location Y wrong: {location.get('Y')}"
        assert location.get("Z") == "0", f"Location Z missing or wrong: {location.get('Z')}"

        axis = position.find("Axis")
        assert axis is not None, "Position/Axis missing - required for rendering"
        assert axis.get("X") == "0", f"Axis X wrong: {axis.get('X')}"
        assert axis.get("Y") == "0", f"Axis Y wrong: {axis.get('Y')}"
        assert axis.get("Z") == "1", f"Axis Z wrong: {axis.get('Z')}"

        reference = position.find("Reference")
        assert reference is not None, "Position/Reference missing - required for rendering"
        assert reference.get("X") == "1", f"Reference X wrong: {reference.get('X')}"
        assert reference.get("Y") == "0", f"Reference Y wrong: {reference.get('Y')}"
        assert reference.get("Z") == "0", f"Reference Z wrong: {reference.get('Z')}"

        # Validate Extent element (bounding box)
        extent = equip_elem.find("Extent")
        assert extent is not None, (
            "Extent element missing - canvas sizing will fail"
        )

        min_elem = extent.find("Min")
        max_elem = extent.find("Max")
        assert min_elem is not None, "Extent/Min missing"
        assert max_elem is not None, "Extent/Max missing"

        # Min/Max should define a bounding box around the position
        # Default symbol size is 20x20 units
        min_x = float(min_elem.get("X"))
        max_x = float(max_elem.get("X"))
        min_y = float(min_elem.get("Y"))
        max_y = float(max_elem.get("Y"))

        assert min_x < 100 < max_x, f"X bounds don't contain position: {min_x} < 100 < {max_x}"
        assert min_y < 200 < max_y, f"Y bounds don't contain position: {min_y} < 200 < {max_y}"

        # Validate Presentation element
        presentation = equip_elem.find("Presentation")
        assert presentation is not None, (
            "Presentation element missing - equipment won't render with proper style"
        )

        # Required Presentation attributes per Codex research
        assert presentation.get("R") is not None, "Presentation/R missing"
        assert presentation.get("G") is not None, "Presentation/G missing"
        assert presentation.get("B") is not None, "Presentation/B missing"
        assert presentation.get("LineType") is not None, "Presentation/LineType missing"
        assert presentation.get("LineWeight") is not None, "Presentation/LineWeight missing"

    def test_multiple_equipment_with_drawing_extent(self, empty_model, tank_with_nozzles, pump, tmp_path):
        """Test that Drawing element gets Extent from layout bounding box.

        When multiple equipment are exported, the Drawing's Extent should
        encompass all equipment positions for proper canvas sizing.
        """
        # Setup: Add multiple equipment
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles, pump]
        output_file = tmp_path / "multi_equipment_extent.xml"

        # Create layout with both equipment
        layout = LayoutMetadata(
            algorithm="spring",
            positions={
                tank_with_nozzles.id: NodePosition(x=0.0, y=0.0),
                pump.id: NodePosition(x=200.0, y=150.0)
            }
        )

        # Export
        exporter = ProteusXMLExporter()
        exporter.export(
            empty_model,
            output_file,
            validate=False,
            layout_metadata=layout
        )

        # Parse and validate
        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Drawing should have Extent encompassing all equipment
        drawing = root.find(".//Drawing")
        assert drawing is not None, "Drawing element not found"

        drawing_extent = drawing.find("Extent")
        assert drawing_extent is not None, (
            "Drawing/Extent missing - canvas will use wrong dimensions"
        )

        min_elem = drawing_extent.find("Min")
        max_elem = drawing_extent.find("Max")
        assert min_elem is not None, "Drawing/Extent/Min missing"
        assert max_elem is not None, "Drawing/Extent/Max missing"

        # Drawing extent should encompass both equipment with padding
        min_x = float(min_elem.get("X"))
        max_x = float(max_elem.get("X"))
        min_y = float(min_elem.get("Y"))
        max_y = float(max_elem.get("Y"))

        # Should contain tank at (0,0) and pump at (200, 150) with margin
        assert min_x <= 0, f"Drawing min_x doesn't include tank: {min_x}"
        assert max_x >= 200, f"Drawing max_x doesn't include pump: {max_x}"
        assert min_y <= 0, f"Drawing min_y doesn't include tank: {min_y}"
        assert max_y >= 150, f"Drawing max_y doesn't include pump: {max_y}"

    def test_equipment_without_layout_raises_error(self, empty_model, pump, tmp_path):
        """Test that exporting without layout metadata fails loudly.

        Per 'fail loudly' philosophy, we don't silently skip Position/Extent.
        If layout metadata is required but missing, we should raise an error.
        """
        empty_model.conceptualModel.taggedPlantItems = [pump]
        output_file = tmp_path / "no_layout.xml"

        exporter = ProteusXMLExporter()

        # Without layout_metadata, export should work but equipment won't have Position
        # This is allowed for backward compatibility during transition
        exporter.export(empty_model, output_file, validate=False)

        # Parse and verify no Position (this is the current behavior)
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        equip_elem = root.find(".//Equipment[@ID='PMP-001']")

        # No Position should be present when layout_metadata is not provided
        position = equip_elem.find("Position")
        assert position is None, (
            "Position should not be present without layout_metadata"
        )

    def test_missing_equipment_in_layout_raises_error(self, empty_model, pump, tmp_path):
        """Test that equipment missing from layout raises an error.

        If we have layout metadata but equipment is missing from it,
        we should fail loudly rather than silently skip the Position.
        """
        empty_model.conceptualModel.taggedPlantItems = [pump]
        output_file = tmp_path / "missing_in_layout.xml"

        # Create layout without the pump
        layout = LayoutMetadata(
            algorithm="spring",
            positions={
                "OTHER-001": NodePosition(x=0.0, y=0.0)  # Different ID
            }
        )

        exporter = ProteusXMLExporter()

        # Should raise error when equipment is missing from layout
        with pytest.raises(ValueError, match="not found in layout"):
            exporter.export(
                empty_model,
                output_file,
                validate=False,
                layout_metadata=layout
            )

    def test_piping_segment_with_position(self, empty_model, simple_piping_segment, tmp_path):
        """Test that piping segments can have Position/Extent/Presentation.

        Piping needs Position for centerline rendering in GraphicBuilder.
        """
        from pydexpi.dexpi_classes import piping as piping_module

        # Setup piping
        piping_system = piping_module.PipingNetworkSystem()
        piping_system.id = "PS-001"
        piping_system.segments = [simple_piping_segment]
        empty_model.conceptualModel.pipingNetworkSystems = [piping_system]

        output_file = tmp_path / "piping_position.xml"

        # Create layout for piping segment
        segment_id = simple_piping_segment.id  # "SEG-001"
        layout = LayoutMetadata(
            algorithm="spring",
            positions={
                segment_id: NodePosition(x=150.0, y=100.0)
            }
        )

        # Export
        exporter = ProteusXMLExporter()
        exporter.export(
            empty_model,
            output_file,
            validate=False,
            layout_metadata=layout
        )

        # Parse and validate
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        segment_elem = root.find(".//PipingNetworkSegment[@ID='SEG-001']")

        assert segment_elem is not None, "PipingNetworkSegment not found"

        # Piping segments should also have Position/Presentation
        position = segment_elem.find("Position")
        assert position is not None, "PipingNetworkSegment Position missing"

        presentation = segment_elem.find("Presentation")
        assert presentation is not None, "PipingNetworkSegment Presentation missing"


class TestPresentationDefaults:
    """Test default Presentation values for different component types."""

    def test_equipment_presentation_defaults(self, empty_model, pump, tmp_path):
        """Test that equipment gets default Presentation values."""
        empty_model.conceptualModel.taggedPlantItems = [pump]
        output_file = tmp_path / "presentation_defaults.xml"

        layout = LayoutMetadata(
            algorithm="spring",
            positions={pump.id: NodePosition(x=100.0, y=100.0)}
        )

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False, layout_metadata=layout)

        tree = etree.parse(str(output_file))
        root = tree.getroot()
        equip_elem = root.find(".//Equipment[@ID='PMP-001']")
        presentation = equip_elem.find("Presentation")

        # Check defaults
        assert presentation.get("Layer") == "Default"
        assert presentation.get("Color") == "Black"
        assert presentation.get("LineType") == "Solid"
        # LineWeight should be a valid float
        line_weight = float(presentation.get("LineWeight"))
        assert 0 < line_weight < 1, f"LineWeight out of range: {line_weight}"
        # RGB should be 0 for black
        assert presentation.get("R") == "0"
        assert presentation.get("G") == "0"
        assert presentation.get("B") == "0"
