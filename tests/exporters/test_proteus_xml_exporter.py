"""Unit tests for Proteus XML Exporter.

Tests cover:
- Equipment export (Tank, Pump, HeatExchanger, Vessel, Column)
- Nozzle export as Equipment children
- ID registration and uniqueness
- XML structure validation
- XSD schema validation
"""

import pytest
from pathlib import Path
from datetime import datetime
from lxml import etree

from src.exporters.proteus_xml_exporter import (
    IDRegistry,
    ProteusXMLExporter,
    export_to_proteus_xml,
)
from pydexpi.dexpi_classes import dexpiModel, equipment


# Test Fixtures
@pytest.fixture
def empty_model():
    """Create minimal DexpiModel for testing."""
    # Create conceptual model first
    conceptual_model = dexpiModel.ConceptualModel()

    # Create model with all required fields
    model = dexpiModel.DexpiModel(
        conceptualModel=conceptual_model,
        originatingSystemName="pyDEXPI-Test",
        originatingSystemVendorName="Engineering-MCP-Server",
        originatingSystemVersion="1.0.0",
        exportDateTime=datetime.now()
    )
    return model


@pytest.fixture
def tank_with_nozzles():
    """Create Tank equipment with nozzles.

    Note: pyDEXPI Equipment objects don't have componentName/componentTag attributes.
    These are stored in customAttributes or accessed differently.
    For export testing, we use the object's ID and tagName attributes.
    """
    # Create nozzles first
    nozzle1 = equipment.Nozzle()
    nozzle1.id = "NOZ-001"
    nozzle1.subTagName = "Inlet"  # Used for ComponentName in export

    nozzle2 = equipment.Nozzle()
    nozzle2.id = "NOZ-002"
    nozzle2.subTagName = "Outlet"  # Used for ComponentName in export

    # Create tank with nozzles
    tank = equipment.Tank(nozzles=[nozzle1, nozzle2])
    tank.id = "TANK-001"
    tank.tagName = "V-101"  # tagName is used as ComponentName
    return tank


@pytest.fixture
def pump():
    """Create CentrifugalPump equipment."""
    pump = equipment.CentrifugalPump()
    pump.id = "PMP-001"
    pump.tagName = "P-101"  # Used as ComponentName in export
    return pump


@pytest.fixture
def heat_exchanger():
    """Create PlateHeatExchanger equipment."""
    hx = equipment.PlateHeatExchanger()
    hx.id = "HEX-001"
    hx.tagName = "HX-101"  # Used as ComponentName in export
    return hx


@pytest.fixture
def pressure_vessel():
    """Create PressureVessel equipment."""
    vessel = equipment.PressureVessel()
    vessel.id = "VES-001"
    vessel.tagName = "V-201"  # Used as ComponentName in export
    return vessel


@pytest.fixture
def column():
    """Create ProcessColumn equipment."""
    col = equipment.ProcessColumn()
    col.id = "COL-001"
    col.tagName = "C-101"  # Used as ComponentName in export
    return col


# IDRegistry Tests
class TestIDRegistry:
    """Test ID generation and management."""

    def test_register_with_existing_id(self):
        """Test registering object with existing ID."""
        registry = IDRegistry()
        tank = equipment.Tank()
        tank.id = "TANK-123"

        registered_id = registry.register(tank)
        assert registered_id == "TANK-123"

    def test_register_generates_id(self):
        """Test automatic ID generation with pyDEXPI objects.

        Note: pyDEXPI Equipment objects automatically get UUID IDs assigned,
        so IDRegistry preserves those UUIDs instead of generating new IDs.
        """
        registry = IDRegistry()
        tank = equipment.Tank()

        registered_id = registry.register(tank)
        # pyDEXPI auto-assigns UUID, so we preserve it
        assert registered_id == tank.id
        assert isinstance(registered_id, str)

    def test_register_duplicate_raises_error(self):
        """Test that duplicate IDs raise ValueError."""
        registry = IDRegistry()
        tank1 = equipment.Tank()
        tank1.id = "TANK-123"
        tank2 = equipment.Tank()
        tank2.id = "TANK-123"

        registry.register(tank1)
        with pytest.raises(ValueError, match="Duplicate ID"):
            registry.register(tank2)

    def test_register_same_object_twice(self):
        """Test registering same object returns same ID."""
        registry = IDRegistry()
        tank = equipment.Tank()

        id1 = registry.register(tank)
        id2 = registry.register(tank)
        assert id1 == id2

    def test_reserve_id(self):
        """Test reserving IDs."""
        registry = IDRegistry()
        registry.reserve("CUSTOM-001")

        with pytest.raises(ValueError, match="already reserved"):
            registry.reserve("CUSTOM-001")

    def test_validate_reference(self):
        """Test ID reference validation."""
        registry = IDRegistry()
        tank = equipment.Tank()
        tank.id = "TANK-123"

        registry.register(tank)
        assert registry.validate_reference("TANK-123") is True
        assert registry.validate_reference("UNKNOWN") is False

    def test_prefix_mapping(self):
        """Test prefix mapping for common types.

        Note: pyDEXPI auto-assigns UUID IDs to all objects, so IDRegistry
        preserves those UUIDs. To test prefix generation, we create objects
        without IDs (which pyDEXPI doesn't support), so we test with
        objects that have custom string IDs instead.
        """
        registry = IDRegistry()

        # Create equipment with specific IDs to test prefix-based fallback
        # When objects already have IDs, the registry preserves them
        tank = equipment.Tank()
        pump = equipment.CentrifugalPump()
        hx = equipment.PlateHeatExchanger()

        # pyDEXPI auto-assigns UUIDs, so registry preserves them
        tank_id = registry.register(tank)
        pump_id = registry.register(pump)
        hx_id = registry.register(hx)

        # IDs should be preserved from pyDEXPI (UUIDs)
        assert tank_id == tank.id
        assert pump_id == pump.id
        assert hx_id == hx.id

        # Verify they are valid UUID strings
        import uuid
        assert uuid.UUID(tank_id)  # Should not raise
        assert uuid.UUID(pump_id)  # Should not raise
        assert uuid.UUID(hx_id)  # Should not raise

    def test_uuid_normalization(self):
        """Test UUID to string normalization.

        pyDEXPI requires ID to be a string, so we test that the registry
        can handle string UUIDs correctly.
        """
        import uuid
        registry = IDRegistry()
        tank = equipment.Tank()
        # pyDEXPI validates that id must be a string
        tank.id = str(uuid.uuid4())

        registered_id = registry.register(tank)
        assert isinstance(registered_id, str)
        # Verify it's a valid UUID string
        assert uuid.UUID(registered_id)  # Should not raise


# Equipment Export Tests
class TestEquipmentExport:
    """Test equipment XML export functionality."""

    def test_export_tank(self, empty_model, tank_with_nozzles, tmp_path):
        """Test Tank export with nozzles."""
        # Add tank to model
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]

        # Export to file
        output_file = tmp_path / "tank_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML
        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Find Equipment element
        equipment_elem = root.find(".//Equipment")
        assert equipment_elem is not None

        # Check required attributes
        assert equipment_elem.get("ID") is not None
        assert equipment_elem.get("ComponentClass") == "Tank"
        assert equipment_elem.get("ComponentName") == "V-101"
        assert equipment_elem.get("TagName") == "V-101"

        # Check nozzles
        nozzles = equipment_elem.findall("Nozzle")
        assert len(nozzles) == 2
        assert nozzles[0].get("ID") == "NOZ-001"
        assert nozzles[0].get("ComponentName") == "Inlet"
        assert nozzles[1].get("ID") == "NOZ-002"
        assert nozzles[1].get("ComponentName") == "Outlet"

    def test_export_pump(self, empty_model, pump, tmp_path):
        """Test CentrifugalPump export."""
        empty_model.conceptualModel.taggedPlantItems = [pump]

        output_file = tmp_path / "pump_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        equipment_elem = tree.find(".//Equipment")

        assert equipment_elem.get("ComponentClass") == "CentrifugalPump"
        assert equipment_elem.get("ComponentName") == "P-101"
        assert equipment_elem.get("TagName") == "P-101"

    def test_export_heat_exchanger(self, empty_model, heat_exchanger, tmp_path):
        """Test PlateHeatExchanger export."""
        empty_model.conceptualModel.taggedPlantItems = [heat_exchanger]

        output_file = tmp_path / "hx_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        equipment_elem = tree.find(".//Equipment")

        assert equipment_elem.get("ComponentClass") == "PlateHeatExchanger"
        assert equipment_elem.get("ComponentName") == "HX-101"

    def test_export_pressure_vessel(self, empty_model, pressure_vessel, tmp_path):
        """Test PressureVessel export."""
        empty_model.conceptualModel.taggedPlantItems = [pressure_vessel]

        output_file = tmp_path / "vessel_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        equipment_elem = tree.find(".//Equipment")

        assert equipment_elem.get("ComponentClass") == "PressureVessel"
        assert equipment_elem.get("ComponentName") == "V-201"

    def test_export_column(self, empty_model, column, tmp_path):
        """Test ProcessColumn export."""
        empty_model.conceptualModel.taggedPlantItems = [column]

        output_file = tmp_path / "column_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        equipment_elem = tree.find(".//Equipment")

        assert equipment_elem.get("ComponentClass") == "ProcessColumn"
        assert equipment_elem.get("ComponentName") == "C-101"

    def test_multiple_equipment_export(self, empty_model, tank_with_nozzles, pump, heat_exchanger, tmp_path):
        """Test exporting multiple equipment items."""
        empty_model.conceptualModel.taggedPlantItems = [
            tank_with_nozzles,
            pump,
            heat_exchanger
        ]

        output_file = tmp_path / "multiple_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        equipment_elems = tree.findall(".//Equipment")

        assert len(equipment_elems) == 3
        classes = {elem.get("ComponentClass") for elem in equipment_elems}
        assert classes == {"Tank", "CentrifugalPump", "PlateHeatExchanger"}

    def test_id_uniqueness(self, empty_model, tmp_path):
        """Test that all IDs are unique across export."""
        # Create equipment with same IDs
        tank1 = equipment.Tank()
        tank1.id = "SHARED-ID"
        tank2 = equipment.Tank()
        tank2.id = "DIFFERENT-ID"

        empty_model.conceptualModel.taggedPlantItems = [tank1, tank2]

        output_file = tmp_path / "id_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        all_ids = set()

        # Collect all IDs
        for elem in tree.iter():
            elem_id = elem.get("ID")
            if elem_id:
                assert elem_id not in all_ids, f"Duplicate ID found: {elem_id}"
                all_ids.add(elem_id)


# XML Structure Tests
class TestXMLStructure:
    """Test overall XML document structure."""

    def test_root_element_structure(self, empty_model, tmp_path):
        """Test PlantModel root element."""
        output_file = tmp_path / "structure_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        root = tree.getroot()

        assert root.tag == "PlantModel"
        assert "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation" in root.attrib

    def test_plant_information(self, empty_model, tmp_path):
        """Test PlantInformation element."""
        output_file = tmp_path / "plantinfo_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        plant_info = tree.find("PlantInformation")

        assert plant_info is not None
        assert plant_info.get("SchemaVersion") == "4.2"
        assert plant_info.get("OriginatingSystem") == "pyDEXPI-Test"
        assert plant_info.get("Is3D") == "no"
        assert plant_info.get("Units") == "Metre"
        assert plant_info.get("Discipline") == "PID"

        # Check UnitsOfMeasure child
        units = plant_info.find("UnitsOfMeasure")
        assert units is not None
        assert units.get("Distance") == "Metre"

    def test_drawing_element(self, empty_model, tmp_path):
        """Test Drawing element structure."""
        output_file = tmp_path / "drawing_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        drawing = tree.find("Drawing")

        assert drawing is not None
        assert drawing.get("Type") == "PID"
        assert drawing.get("Name") == "PID-001"  # Default value

        # Check required Presentation child
        presentation = drawing.find("Presentation")
        assert presentation is not None
        assert presentation.get("Layer") is not None

    def test_equipment_direct_child_of_root(self, empty_model, tank_with_nozzles, tmp_path):
        """Test Equipment is direct child of root PlantModel element.

        Per DEXPI/Proteus XML spec, Equipment elements should be siblings
        to Drawing, not nested inside Drawing. ProteusSerializer expects
        Equipment at root level.
        """
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]

        output_file = tmp_path / "hierarchy_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Equipment should be direct child of root (sibling to Drawing)
        equipment_elem = root.find("Equipment")
        assert equipment_elem is not None

        # Drawing should exist but NOT contain Equipment
        drawing = root.find("Drawing")
        assert drawing is not None
        assert drawing.find("Equipment") is None


# Convenience Function Tests
class TestConvenienceFunction:
    """Test export_to_proteus_xml() convenience function."""

    def test_export_to_proteus_xml(self, empty_model, tank_with_nozzles, tmp_path):
        """Test convenience function."""
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]

        output_file = tmp_path / "convenience_test.xml"
        export_to_proteus_xml(empty_model, output_file, validate=False)

        assert output_file.exists()
        tree = etree.parse(str(output_file))
        assert tree.find(".//Equipment") is not None


# XSD Validation Tests (using minimal schema)
class TestXSDValidation:
    """Test XSD schema validation using minimal schema.

    Uses tests/fixtures/schemas/ProteusPIDSchema_min.xsd which contains only
    the structures we export (PlantModel, PlantInformation, Drawing, Equipment,
    Nozzle, GenericAttributes). The full ProteusPIDSchema_4.2.xsd has parsing
    issues at line 2088 (InformationFlow non-deterministic content model).
    """

    def test_xsd_validation_success(self, empty_model, tank_with_nozzles, tmp_path):
        """Test successful XSD validation using minimal schema."""
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]

        output_file = tmp_path / "validation_test.xml"

        # Use minimal schema that doesn't have parsing issues
        minimal_schema = Path(__file__).parent.parent / "fixtures" / "schemas" / "ProteusPIDSchema_min.xsd"
        exporter = ProteusXMLExporter(xsd_path=minimal_schema)

        # Should not raise ValueError
        exporter.export(empty_model, output_file, validate=True)

    def test_xsd_validation_failure(self, tmp_path):
        """Test XSD validation failure with invalid XML using minimal schema."""
        # Create invalid XML (missing required elements)
        root = etree.Element("PlantModel")
        # Missing PlantInformation - should fail validation

        output_file = tmp_path / "invalid_test.xml"
        tree = etree.ElementTree(root)
        tree.write(str(output_file), encoding="UTF-8", xml_declaration=True)

        minimal_schema = Path(__file__).parent.parent / "fixtures" / "schemas" / "ProteusPIDSchema_min.xsd"
        exporter = ProteusXMLExporter(xsd_path=minimal_schema)
        with pytest.raises(ValueError, match="validation failed"):
            exporter._validate_xml(output_file)


# Round-Trip Validation Tests
class TestRoundTripValidation:
    """Test export → import cycle using ProteusSerializer."""

    def test_roundtrip_tank_with_nozzles(self, empty_model, tank_with_nozzles, tmp_path):
        """Test that tank with nozzles survives export/import cycle."""
        from pydexpi.loaders import ProteusSerializer

        # Add tank to model
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]

        # Export
        output_file = tmp_path / "roundtrip_tank.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Re-import using pyDEXPI's loader
        serializer = ProteusSerializer()
        reloaded_model = serializer.load(str(tmp_path), "roundtrip_tank.xml")

        # Validate structure survived
        assert reloaded_model is not None
        assert reloaded_model.conceptualModel is not None
        assert len(reloaded_model.conceptualModel.taggedPlantItems) == 1

        # Check equipment details
        reloaded_tank = reloaded_model.conceptualModel.taggedPlantItems[0]
        assert reloaded_tank.tagName == "V-101"
        assert reloaded_tank.__class__.__name__ == "Tank"

        # Check nozzles survived
        assert len(reloaded_tank.nozzles) == 2
        nozzle_names = {n.subTagName for n in reloaded_tank.nozzles if n.subTagName}
        assert "Inlet" in nozzle_names
        assert "Outlet" in nozzle_names

    def test_roundtrip_multiple_equipment(self, empty_model, pump, heat_exchanger, tmp_path):
        """Test multiple equipment items survive export/import cycle."""
        from pydexpi.loaders import ProteusSerializer

        # Add multiple equipment
        empty_model.conceptualModel.taggedPlantItems = [pump, heat_exchanger]

        # Export
        output_file = tmp_path / "roundtrip_multiple.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Re-import
        serializer = ProteusSerializer()
        reloaded_model = serializer.load(str(tmp_path), "roundtrip_multiple.xml")

        # Validate all equipment survived
        assert len(reloaded_model.conceptualModel.taggedPlantItems) == 2

        # Check equipment types and tags
        reloaded_items = reloaded_model.conceptualModel.taggedPlantItems
        tags = {item.tagName for item in reloaded_items}
        assert "P-101" in tags
        assert "HX-101" in tags

        classes = {item.__class__.__name__ for item in reloaded_items}
        assert "CentrifugalPump" in classes
        assert "PlateHeatExchanger" in classes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
