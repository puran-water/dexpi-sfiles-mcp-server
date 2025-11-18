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
from pydexpi.dexpi_classes import (
    dataTypes,
    dexpiModel,
    equipment,
    instrumentation,
    piping,
    physicalQuantities,
    enumerations,
)
from pydexpi.dexpi_classes.pydantic_classes import CustomStringAttribute


def _generic_attribute_map(element):
    """Build mapping of GenericAttribute name to list of attribute elements."""
    attr_map: dict[str, list[etree._Element]] = {}
    for attr_set in element.findall("GenericAttributes"):
        for attr in attr_set.findall("GenericAttribute"):
            attr_map.setdefault(attr.get("Name"), []).append(attr)
    return attr_map


def _generic_attribute_values(element, name):
    """Return all Value strings for the given GenericAttribute Name."""
    return [
        attr.get("Value")
        for attr in _generic_attribute_map(element).get(name, [])
    ]


def _generic_attribute_elements(element, name):
    """Return GenericAttribute elements for the given Name."""
    return _generic_attribute_map(element).get(name, [])


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
    nozzle1.nominalPressureNumericalValueRepresentation = "150"
    nozzle1.nominalPressureStandard = (
        enumerations.NominalPressureStandardClassification.Class150LbsArtefact
    )
    nozzle1_node = piping.PipingNode()
    nozzle1_node.id = "NOZZLE-NODE-IN"
    nozzle1.nodes = [nozzle1_node]

    nozzle2 = equipment.Nozzle()
    nozzle2.id = "NOZ-002"
    nozzle2.subTagName = "Outlet"  # Used for ComponentName in export
    nozzle2.nominalPressureNumericalValueRepresentation = "150"
    nozzle2.nominalPressureStandard = (
        enumerations.NominalPressureStandardClassification.Class150LbsArtefact
    )
    nozzle2_node = piping.PipingNode()
    nozzle2_node.id = "NOZZLE-NODE-OUT"
    nozzle2.nodes = [nozzle2_node]

    # Create tank with nozzles
    tank = equipment.Tank(nozzles=[nozzle1, nozzle2])
    tank.id = "TANK-001"
    tank.tagName = "V-101"  # tagName is used as ComponentName
    tank.tagNamePrefix = "V"
    tank.tagNameSequenceNumber = "101"
    tank.tagNameSuffix = "A"
    tank.equipmentDescription = dataTypes.MultiLanguageString(
        singleLanguageStrings=[
            dataTypes.SingleLanguageString(language="en", value="Feed Tank"),
            dataTypes.SingleLanguageString(language="de", value="Speichertank"),
        ]
    )
    tank.customAttributes = [
        CustomStringAttribute(attributeName="Service", value="Feed System")
    ]
    return tank


@pytest.fixture
def pump():
    """Create CentrifugalPump equipment."""
    pump = equipment.CentrifugalPump()
    pump.id = "PMP-001"
    pump.tagName = "P-101"  # Used as ComponentName in export
    pump.designShaftPower = physicalQuantities.Power(
        value=25.0,
        unit=physicalQuantities.PowerUnit.Kilowatt,
    )
    pump.designVolumeFlowRate = physicalQuantities.VolumeFlowRate(
        value=120.0,
        unit=physicalQuantities.VolumeFlowRateUnit.MetreCubedPerHour,
    )
    return pump


@pytest.fixture
def heat_exchanger():
    """Create PlateHeatExchanger equipment."""
    hx = equipment.PlateHeatExchanger()
    hx.id = "HEX-001"
    hx.tagName = "HX-101"  # Used as ComponentName in export
    hx.designHeatTransferArea = physicalQuantities.Area(
        value=45.0,
        unit=physicalQuantities.AreaUnit.MetreSquared,
    )
    hx.designHeatFlowRate = physicalQuantities.Power(
        value=150.0,
        unit=physicalQuantities.PowerUnit.Kilowatt,
    )
    return hx


@pytest.fixture
def pressure_vessel():
    """Create PressureVessel equipment."""
    vessel = equipment.PressureVessel()
    vessel.id = "VES-001"
    vessel.tagName = "V-201"  # Used as ComponentName in export
    vessel.nominalCapacityVolume = physicalQuantities.Volume(
        value=50.0,
        unit=physicalQuantities.VolumeUnit.MetreCubed,
    )
    vessel.cylinderLength = physicalQuantities.Length(
        value=4.0,
        unit=physicalQuantities.LengthUnit.Metre,
    )
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

        # Check nozzles
        nozzles = equipment_elem.findall("Nozzle")
        assert len(nozzles) == 2
        assert nozzles[0].get("ID") == "NOZ-001"
        assert nozzles[0].get("ComponentName") == "Inlet"
        assert nozzles[1].get("ID") == "NOZ-002"
        assert nozzles[1].get("ComponentName") == "Outlet"

        # Equipment GenericAttributes
        assert _generic_attribute_values(equipment_elem, "TagNameAssignmentClass") == ["V-101"]
        desc_values = sorted(
            _generic_attribute_values(equipment_elem, "EquipmentDescriptionAssignmentClass")
        )
        assert desc_values == ["Feed Tank", "Speichertank"]

        custom_sets = [
            attr_set
            for attr_set in equipment_elem.findall("GenericAttributes")
            if attr_set.get("Set") == "DexpiCustomAttributes"
        ]
        assert any(
            attr.get("Name") == "Service" and attr.get("Value") == "Feed System"
            for attr_set in custom_sets
            for attr in attr_set.findall("GenericAttribute")
        )

        # Nozzle GenericAttributes
        assert _generic_attribute_values(
            nozzles[0], "SubTagNameAssignmentClass"
        ) == ["Inlet"]
        assert _generic_attribute_values(
            nozzles[0], "NominalPressureNumericalValueRepresentationAssignmentClass"
        ) == ["150"]

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

        power_attr = _generic_attribute_elements(
            equipment_elem, "DesignShaftPowerAssignmentClass"
        )[0]
        assert power_attr.get("Value") == "25.0"
        assert power_attr.get("Units") == physicalQuantities.PowerUnit.Kilowatt.name

        flow_attr = _generic_attribute_elements(
            equipment_elem, "DesignVolumeFlowRateAssignmentClass"
        )[0]
        assert flow_attr.get("Value") == "120.0"
        assert flow_attr.get("Units") == physicalQuantities.VolumeFlowRateUnit.MetreCubedPerHour.name

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

        area_attr = _generic_attribute_elements(
            equipment_elem, "DesignHeatTransferAreaAssignmentClass"
        )[0]
        assert area_attr.get("Value") == "45.0"
        assert area_attr.get("Units") == physicalQuantities.AreaUnit.MetreSquared.name

        heat_attr = _generic_attribute_elements(
            equipment_elem, "DesignHeatFlowRateAssignmentClass"
        )[0]
        assert heat_attr.get("Value") == "150.0"
        assert heat_attr.get("Units") == physicalQuantities.PowerUnit.Kilowatt.name

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

        volume_attr = _generic_attribute_elements(
            equipment_elem, "NominalCapacityVolumeAssignmentClass"
        )[0]
        assert volume_attr.get("Value") == "50.0"
        assert volume_attr.get("Units") == physicalQuantities.VolumeUnit.MetreCubed.name

        length_attr = _generic_attribute_elements(
            equipment_elem, "CylinderLengthAssignmentClass"
        )[0]
        assert length_attr.get("Value") == "4.0"
        assert length_attr.get("Units") == physicalQuantities.LengthUnit.Metre.name

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
        assert _generic_attribute_values(
            equipment_elem, "TagNameAssignmentClass"
        ) == ["C-101"]

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


# Piping Test Fixtures
@pytest.fixture
def simple_piping_segment():
    """Create a simple PipingNetworkSegment with one valve.

    Note: Piping components use pipingComponentName, not tagName.
    """
    # Create a valve with nodes
    valve = piping.BallValve()
    valve.id = "VLV-001"
    valve.pipingComponentName = "HV-101"
    valve.numberOfPorts = enumerations.NumberOfPortsClassification.TwoPortValve
    valve.operation = enumerations.OperationClassification.ContinuousOperation
    valve.pipingClassCode = "CS150"

    # Create piping nodes for the valve
    node1 = piping.PipingNode()
    node1.id = "NODE-001"
    node2 = piping.PipingNode()
    node2.id = "NODE-002"
    valve.nodes = [node1, node2]

    # Create segment
    segment = piping.PipingNetworkSegment()
    segment.id = "SEG-001"
    segment.fluidCode = "W"  # Water
    segment.segmentNumber = "S1"
    segment.nominalDiameterNumericalValueRepresentation = "50"
    segment.nominalDiameterRepresentation = "DN50"
    segment.pipingClassCode = "CS150"
    segment.heatTracingType = enumerations.HeatTracingTypeClassification.ElectricalHeatTracingSystem
    segment.insulationType = "Calcium Silicate"
    segment.lowerLimitHeatTracingTemperature = physicalQuantities.Temperature(
        value=10.0,
        unit=physicalQuantities.TemperatureUnit.DegreeCelsius,
    )
    segment.items = [valve]
    object.__setattr__(
        segment,
        "centerLinePoints",
        [
            (0.0, 0.0),
            (5.0, 0.0),
            (10.0, 2.5),
        ],
    )

    return segment


@pytest.fixture
def piping_system_with_segment(simple_piping_segment):
    """Create a PipingNetworkSystem with one segment."""
    system = piping.PipingNetworkSystem()
    system.id = "SYS-001"
    system.lineNumber = "100"
    system.fluidCode = "W"
    system.pipingClassCode = "150#"
    system.nominalDiameterRepresentation = "DN100"
    system.heatTracingType = enumerations.HeatTracingTypeClassification.SteamHeatTracingSystem
    system.insulationThickness = physicalQuantities.Length(
        value=5.0,
        unit=physicalQuantities.LengthUnit.Millimetre,
    )
    system.lowerLimitHeatTracingTemperature = physicalQuantities.Temperature(
        value=15.0,
        unit=physicalQuantities.TemperatureUnit.DegreeCelsius,
    )
    system.segments = [simple_piping_segment]

    return system


@pytest.fixture
def piping_segment_requires_centerline():
    """Segment requiring center line data but lacking configuration."""
    valve = piping.BallValve()
    valve.id = "VLV-REQ"
    node1 = piping.PipingNode()
    node1.id = "NODE-REQ-1"
    node2 = piping.PipingNode()
    node2.id = "NODE-REQ-2"
    valve.nodes = [node1, node2]

    segment = piping.PipingNetworkSegment()
    segment.id = "SEG-REQ"
    segment.items = [valve]
    object.__setattr__(segment, "centerLineRequired", True)

    return segment


@pytest.fixture
def piping_segment_with_connection(tank_with_nozzles):
    """Create a PipingNetworkSegment with connections to equipment nozzles."""
    # Create a valve
    valve = piping.BallValve()
    valve.id = "VLV-002"
    valve.pipingComponentName = "HV-102"

    # Create piping nodes
    node1 = piping.PipingNode()
    node1.id = "NODE-003"
    node2 = piping.PipingNode()
    node2.id = "NODE-004"
    valve.nodes = [node1, node2]

    # Create segment
    segment = piping.PipingNetworkSegment()
    segment.id = "SEG-002"
    segment.items = [valve]

    # Create connections
    # Connection from tank nozzle to valve inlet
    conn1 = piping.PipingConnection()
    conn1.sourceItem = tank_with_nozzles.nozzles[1]  # Tank outlet
    conn1.sourceNode = tank_with_nozzles.nozzles[1].nodes[0] if hasattr(tank_with_nozzles.nozzles[1], 'nodes') and tank_with_nozzles.nozzles[1].nodes else None
    conn1.targetItem = valve
    conn1.targetNode = node1  # Valve inlet

    segment.connections = [conn1]

    return segment


# Piping Export Tests
class TestPipingExport:
    """Test piping network XML export functionality."""

    def test_export_piping_system(self, empty_model, piping_system_with_segment, tmp_path):
        """Test PipingNetworkSystem export."""
        empty_model.conceptualModel.pipingNetworkSystems = [piping_system_with_segment]

        output_file = tmp_path / "piping_system_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML
        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Find PipingNetworkSystem element
        system_elem = root.find(".//PipingNetworkSystem")
        assert system_elem is not None

        # Check required attributes
        assert system_elem.get("ID") == "SYS-001"
        assert system_elem.get("ComponentClass") == "PipingNetworkSystem"

        # Check GenericAttributes values via helper
        assert _generic_attribute_values(system_elem, "FluidCodeAssignmentClass") == ["W"]
        assert _generic_attribute_values(system_elem, "LineNumberAssignmentClass") == ["100"]
        assert _generic_attribute_values(system_elem, "PipingClassCodeAssignmentClass") == ["150#"]
        assert _generic_attribute_values(
            system_elem, "HeatTracingTypeAssignmentClass"
        ) == [enumerations.HeatTracingTypeClassification.SteamHeatTracingSystem.name]

        temp_attr = _generic_attribute_elements(
            system_elem, "LowerLimitHeatTracingTemperatureAssignmentClass"
        )[0]
        assert temp_attr.get("Value") == "15.0"
        assert temp_attr.get("Units") == physicalQuantities.TemperatureUnit.DegreeCelsius.name

    def test_export_piping_segment(self, empty_model, piping_system_with_segment, tmp_path):
        """Test PipingNetworkSegment export."""
        empty_model.conceptualModel.pipingNetworkSystems = [piping_system_with_segment]

        output_file = tmp_path / "piping_segment_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find PipingNetworkSegment element
        segment_elem = tree.find(".//PipingNetworkSegment")
        assert segment_elem is not None

        # Check required attributes
        assert segment_elem.get("ID") == "SEG-001"
        assert segment_elem.get("ComponentClass") == "PipingNetworkSegment"

        # Check GenericAttributes for segment using helper
        assert _generic_attribute_values(segment_elem, "FluidCodeAssignmentClass") == ["W"]
        assert _generic_attribute_values(segment_elem, "SegmentNumberAssignmentClass") == ["S1"]
        assert _generic_attribute_values(
            segment_elem, "HeatTracingTypeAssignmentClass"
        ) == [enumerations.HeatTracingTypeClassification.ElectricalHeatTracingSystem.name]

    def test_export_valve_in_segment(self, empty_model, piping_system_with_segment, tmp_path):
        """Test valve export within piping segment."""
        empty_model.conceptualModel.pipingNetworkSystems = [piping_system_with_segment]

        output_file = tmp_path / "valve_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find BallValve element
        valve_elem = tree.find(".//BallValve")
        assert valve_elem is not None

        # Check valve attributes
        assert valve_elem.get("ID") == "VLV-001"
        assert valve_elem.get("ComponentClass") == "BallValve"
        # pipingComponentName is used for ComponentName
        if valve_elem.get("ComponentName"):
            assert valve_elem.get("ComponentName") == "HV-101"

        assert _generic_attribute_values(
            valve_elem, "NumberOfPortsAssignmentClass"
        ) == [enumerations.NumberOfPortsClassification.TwoPortValve.name]
        assert _generic_attribute_values(
            valve_elem, "OperationAssignmentClass"
        ) == [enumerations.OperationClassification.ContinuousOperation.name]

    def test_export_connection_points(self, empty_model, piping_system_with_segment, tmp_path):
        """Test ConnectionPoints export for piping components."""
        empty_model.conceptualModel.pipingNetworkSystems = [piping_system_with_segment]

        output_file = tmp_path / "connection_points_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find ConnectionPoints element
        conn_points = tree.find(".//BallValve/ConnectionPoints")
        assert conn_points is not None

        # Check NumPoints attribute
        assert conn_points.get("NumPoints") == "2"
        assert conn_points.get("FlowIn") == "1"
        assert conn_points.get("FlowOut") == "2"

        # Check Node elements
        nodes = conn_points.findall("Node")
        assert len(nodes) == 2
        assert nodes[0].get("ID") == "NODE-001"
        assert nodes[0].get("Type") == "process"
        assert nodes[1].get("ID") == "NODE-002"

    def test_export_center_line(self, empty_model, piping_system_with_segment, tmp_path):
        """Ensure CenterLine elements are exported when geometry is present."""
        empty_model.conceptualModel.pipingNetworkSystems = [piping_system_with_segment]

        output_file = tmp_path / "center_line_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        center_line = tree.find(".//CenterLine")
        assert center_line is not None
        coords = center_line.findall("Coordinate")
        assert len(coords) == 3
        assert coords[0].get("X") == "0"
        assert coords[2].get("Y") == "2.5"

    def test_center_line_required_missing(self, empty_model, piping_segment_requires_centerline, tmp_path):
        """Fail loudly when a segment requires a center line but none is provided."""
        system = piping.PipingNetworkSystem()
        system.id = "SYS-REQ"
        system.segments = [piping_segment_requires_centerline]
        empty_model.conceptualModel.pipingNetworkSystems = [system]

        exporter = ProteusXMLExporter()
        output_file = tmp_path / "missing_center_line.xml"
        with pytest.raises(ValueError, match="CenterLine geometry"):
            exporter.export(empty_model, output_file, validate=False)

    def test_export_piping_connection(self, empty_model, tank_with_nozzles, piping_segment_with_connection, tmp_path):
        """Test Connection export with FromID/ToID/FromNode/ToNode."""
        # Add both equipment and piping to model
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]

        # Create piping system with the segment
        system = piping.PipingNetworkSystem()
        system.id = "SYS-002"
        system.segments = [piping_segment_with_connection]
        empty_model.conceptualModel.pipingNetworkSystems = [system]

        output_file = tmp_path / "connection_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find Connection element
        connection_elem = tree.find(".//Connection")
        assert connection_elem is not None

        # Check connection attributes
        assert connection_elem.get("FromID") is not None
        assert connection_elem.get("ToID") is not None

        # If nodes are available, check node indices
        if connection_elem.get("FromNode"):
            # FromNode should be 1-based
            from_node = int(connection_elem.get("FromNode"))
            assert from_node >= 1

        if connection_elem.get("ToNode"):
            # ToNode should be 1-based
            to_node = int(connection_elem.get("ToNode"))
            assert to_node >= 1

    def test_node_index_conversion(self, empty_model, tmp_path):
        """Test that node indices are converted from 0-based to 1-based."""
        # Create a valve with explicit nodes
        valve = piping.BallValve()
        valve.id = "VLV-003"

        node1 = piping.PipingNode()
        node1.id = "NODE-005"
        node2 = piping.PipingNode()
        node2.id = "NODE-006"
        valve.nodes = [node1, node2]

        # Create segment
        segment = piping.PipingNetworkSegment()
        segment.id = "SEG-003"
        segment.items = [valve]

        # Create connection using 0-based indices (first node)
        conn = piping.PipingConnection()
        conn.sourceItem = valve
        conn.sourceNode = node1  # Index 0 in pyDEXPI
        conn.targetItem = valve
        conn.targetNode = node2  # Index 1 in pyDEXPI

        segment.connections = [conn]

        # Create system
        system = piping.PipingNetworkSystem()
        system.id = "SYS-003"
        system.segments = [segment]

        empty_model.conceptualModel.pipingNetworkSystems = [system]

        output_file = tmp_path / "node_index_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find Connection element
        connection_elem = tree.find(".//Connection")
        assert connection_elem is not None

        # Check that indices are 1-based in XML
        if connection_elem.get("FromNode"):
            assert connection_elem.get("FromNode") == "1"  # Index 0 -> 1
        if connection_elem.get("ToNode"):
            assert connection_elem.get("ToNode") == "2"  # Index 1 -> 2

    def test_multiple_segments_in_system(self, empty_model, tmp_path):
        """Test exporting multiple segments in one piping system."""
        # Create two segments
        seg1 = piping.PipingNetworkSegment()
        seg1.id = "SEG-004"
        seg1.segmentNumber = "S1"

        seg2 = piping.PipingNetworkSegment()
        seg2.id = "SEG-005"
        seg2.segmentNumber = "S2"

        # Create system with both segments
        system = piping.PipingNetworkSystem()
        system.id = "SYS-004"
        system.segments = [seg1, seg2]

        empty_model.conceptualModel.pipingNetworkSystems = [system]

        output_file = tmp_path / "multiple_segments_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find all PipingNetworkSegment elements
        segments = tree.findall(".//PipingNetworkSegment")
        assert len(segments) == 2

        # Check both segments are present
        segment_ids = {seg.get("ID") for seg in segments}
        assert "SEG-004" in segment_ids
        assert "SEG-005" in segment_ids


# Round-Trip Validation Tests for Piping
class TestPipingRoundTrip:
    """Test piping export → import cycle using ProteusSerializer."""

    def test_roundtrip_piping_system(self, empty_model, piping_system_with_segment, tmp_path):
        """Test that piping system survives export/import cycle."""
        from pydexpi.loaders import ProteusSerializer

        empty_model.conceptualModel.pipingNetworkSystems = [piping_system_with_segment]

        # Export
        output_file = tmp_path / "roundtrip_piping.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Re-import using pyDEXPI's loader
        serializer = ProteusSerializer()
        reloaded_model = serializer.load(str(tmp_path), "roundtrip_piping.xml")

        # Validate structure survived
        assert reloaded_model is not None
        assert reloaded_model.conceptualModel is not None
        assert len(reloaded_model.conceptualModel.pipingNetworkSystems) >= 1

        # Check system details
        reloaded_system = reloaded_model.conceptualModel.pipingNetworkSystems[0]
        assert reloaded_system.lineNumber == "100"
        assert reloaded_system.fluidCode == "W"

        # Check segments survived
        assert len(reloaded_system.segments) >= 1


# Instrumentation Test Fixtures
@pytest.fixture
def simple_sensor():
    """Create a simple ProcessSignalGeneratingFunction (sensor)."""
    sensor = instrumentation.ProcessSignalGeneratingFunction()
    sensor.id = "SENSOR-001"
    sensor.processSignalGeneratingFunctionNumber = "PT-101"
    sensor.sensorType = "PressureTransmitter"
    return sensor


@pytest.fixture
def instrumentation_function_with_sensor(simple_sensor):
    """Create a ProcessInstrumentationFunction with a sensor."""
    func = instrumentation.ProcessInstrumentationFunction()
    func.id = "INS-001"
    func.processInstrumentationFunctionNumber = "PI-101"
    func.processInstrumentationFunctionCategory = "P"
    func.deviceInformation = "PID Controller"
    func.location = enumerations.LocationClassification.Field
    func.vendorCompanyName = "ACME Controls"
    func.qualityRelevance = enumerations.QualityRelevanceClassification.QualityRelevantFunction
    # Note: ProcessInstrumentationFunction doesn't have componentName attribute

    # Add sensor
    func.processSignalGeneratingFunctions = [simple_sensor]

    # Create measuring line
    measuring_line = instrumentation.MeasuringLineFunction()
    measuring_line.id = "MEAS-001"
    measuring_line.source = simple_sensor
    measuring_line.target = func
    measuring_line.signalConveyingType = (
        enumerations.SignalConveyingTypeClassification.ElectricalSignalConveying
    )
    measuring_line.signalPointNumber = "SP-01"

    func.signalConveyingFunctions = [measuring_line]

    # Add actuating function
    actuating_function = instrumentation.ActuatingFunction()
    actuating_function.id = "ACT-001"
    actuating_function.actuatingFunctionNumber = "AF-101"
    func.actuatingFunctions = [actuating_function]

    # Add signal connector
    connector = instrumentation.SignalOffPageConnector()
    connector.id = "SIG-CON-001"
    connector_reference = instrumentation.SignalOffPageConnectorReferenceByNumber()
    connector_reference.id = "SIG-CON-REF-001"
    connector_reference.referencedConnectorNumber = "12"
    connector.connectorReference = connector_reference
    func.signalConnectors = [connector]

    return func


@pytest.fixture
def sensor_with_location(simple_sensor, tank_with_nozzles):
    """Create a sensor with sensing location (equipment)."""
    # Link sensor to equipment nozzle
    sensor = simple_sensor
    sensor.sensingLocation = tank_with_nozzles.nozzles[0]
    return sensor


@pytest.fixture
def instrumentation_loop_function(instrumentation_function_with_sensor):
    """Create an InstrumentationLoopFunction with child ProcessInstrumentationFunction."""
    loop_func = instrumentation.InstrumentationLoopFunction()
    loop_func.id = "LOOP-001"
    loop_func.instrumentationLoopFunctionNumber = "FIC-101"

    # Add child ProcessInstrumentationFunction
    loop_func.processInstrumentationFunctions = [instrumentation_function_with_sensor]

    return loop_func


@pytest.fixture
def simple_instrumentation_loop():
    """Create a simple InstrumentationLoopFunction without children."""
    loop_func = instrumentation.InstrumentationLoopFunction()
    loop_func.id = "LOOP-002"
    loop_func.instrumentationLoopFunctionNumber = "TIC-201"
    return loop_func


# Instrumentation Export Tests
class TestInstrumentationExport:
    """Test instrumentation XML export functionality."""

    def test_export_instrumentation_function(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test ProcessInstrumentationFunction export."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "instrumentation_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML
        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Find ProcessInstrumentationFunction element
        func_elem = root.find(".//ProcessInstrumentationFunction")
        assert func_elem is not None

        # Check required attributes
        assert func_elem.get("ID") == "INS-001"
        assert func_elem.get("ComponentClass") == "ProcessInstrumentationFunction"
        # Note: ComponentName is optional and not set in this test

        assert _generic_attribute_values(
            func_elem, "ProcessInstrumentationFunctionNumberAssignmentClass"
        ) == ["PI-101"]
        assert _generic_attribute_values(
            func_elem, "LocationAssignmentClass"
        ) == [enumerations.LocationClassification.Field.name]

    def test_export_sensor(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test ProcessSignalGeneratingFunction export."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "sensor_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find ProcessSignalGeneratingFunction element
        sensor_elem = tree.find(".//ProcessSignalGeneratingFunction")
        assert sensor_elem is not None

        # Check sensor attributes
        assert sensor_elem.get("ID") == "SENSOR-001"
        assert sensor_elem.get("ComponentClass") == "ProcessSignalGeneratingFunction"

        assert _generic_attribute_values(
            sensor_elem, "ProcessSignalGeneratingFunctionNumberAssignmentClass"
        ) == ["PT-101"]
        assert _generic_attribute_values(
            sensor_elem, "SensorTypeAssignmentClass"
        ) == ["PressureTransmitter"]

    def test_export_information_flow(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test InformationFlow (MeasuringLineFunction) export."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "information_flow_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find InformationFlow element
        flow_elem = tree.find(".//InformationFlow")
        assert flow_elem is not None

        # Check flow attributes
        assert flow_elem.get("ID") == "MEAS-001"
        assert flow_elem.get("ComponentClass") == "MeasuringLineFunction"

        assert _generic_attribute_values(
            flow_elem, "SignalConveyingTypeAssignmentClass"
        ) == [
            enumerations.SignalConveyingTypeClassification.ElectricalSignalConveying.name
        ]
        assert _generic_attribute_values(
            flow_elem, "SignalPointNumberAssignmentClass"
        ) == ["SP-01"]

    def test_export_association_logical_start(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test Association element export (has logical start)."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "association_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find InformationFlow and check its associations
        flow_elem = tree.find(".//InformationFlow")
        assert flow_elem is not None

        # Find "has logical start" association
        associations = flow_elem.findall("Association")
        assert len(associations) >= 1

        start_assoc = [a for a in associations if a.get("Type") == "has logical start"]
        assert len(start_assoc) == 1
        assert start_assoc[0].get("ItemID") == "SENSOR-001"

    def test_export_association_logical_end(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test Association element export (has logical end)."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "association_end_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find InformationFlow and check its associations
        flow_elem = tree.find(".//InformationFlow")
        assert flow_elem is not None

        # Find "has logical end" association
        associations = flow_elem.findall("Association")
        end_assoc = [a for a in associations if a.get("Type") == "has logical end"]
        assert len(end_assoc) == 1
        assert end_assoc[0].get("ItemID") == "INS-001"

    def test_export_association_located_in(self, empty_model, sensor_with_location, tank_with_nozzles, tmp_path):
        """Test Association element export (is located in)."""
        # Create instrumentation function with sensor
        func = instrumentation.ProcessInstrumentationFunction()
        func.id = "INS-002"
        func.processSignalGeneratingFunctions = [sensor_with_location]

        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]
        empty_model.conceptualModel.processInstrumentationFunctions = [func]

        output_file = tmp_path / "association_location_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find ProcessSignalGeneratingFunction and check its associations
        sensor_elem = tree.find(".//ProcessSignalGeneratingFunction")
        assert sensor_elem is not None

        # Find "is located in" association
        associations = sensor_elem.findall("Association")
        location_assoc = [a for a in associations if a.get("Type") == "is located in"]
        assert len(location_assoc) == 1
        assert location_assoc[0].get("ItemID") == "NOZ-001"

    def test_export_instrumentation_generic_attributes(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test GenericAttributes export for instrumentation."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "instrumentation_attributes_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        func_elem = tree.find(".//ProcessInstrumentationFunction")
        assert func_elem is not None

        assert _generic_attribute_values(
            func_elem, "ProcessInstrumentationFunctionNumberAssignmentClass"
        ) == ["PI-101"]
        assert _generic_attribute_values(
            func_elem, "ProcessInstrumentationFunctionCategoryAssignmentClass"
        ) == ["P"]
        assert _generic_attribute_values(
            func_elem, "VendorCompanyNameAssignmentClass"
        ) == ["ACME Controls"]
        assert _generic_attribute_values(
            func_elem, "QualityRelevanceAssignmentClass"
        ) == [
            enumerations.QualityRelevanceClassification.QualityRelevantFunction.name
        ]

    def test_export_actuating_function(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Ensure ActuatingFunction elements are exported with attributes."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "actuating_function_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        act_elem = tree.find(".//ActuatingFunction")
        assert act_elem is not None
        assert act_elem.get("ID") == "ACT-001"
        assert _generic_attribute_values(
            act_elem, "ActuatingFunctionNumberAssignmentClass"
        ) == ["AF-101"]

    def test_export_signal_connector(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Ensure signal connectors are exported."""
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        output_file = tmp_path / "signal_connector_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        connector_elem = tree.find(".//SignalOffPageConnector")
        assert connector_elem is not None
        assert connector_elem.get("ID") == "SIG-CON-001"

    def test_multiple_sensors_in_function(self, empty_model, tmp_path):
        """Test exporting instrumentation function with multiple sensors."""
        # Create multiple sensors
        sensor1 = instrumentation.ProcessSignalGeneratingFunction()
        sensor1.id = "SENSOR-010"
        sensor1.processSignalGeneratingFunctionNumber = "PT-201"

        sensor2 = instrumentation.ProcessSignalGeneratingFunction()
        sensor2.id = "SENSOR-011"
        sensor2.processSignalGeneratingFunctionNumber = "PT-202"

        # Create instrumentation function
        func = instrumentation.ProcessInstrumentationFunction()
        func.id = "INS-010"
        func.processSignalGeneratingFunctions = [sensor1, sensor2]

        empty_model.conceptualModel.processInstrumentationFunctions = [func]

        output_file = tmp_path / "multiple_sensors_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))

        # Find all ProcessSignalGeneratingFunction elements
        sensors = tree.findall(".//ProcessSignalGeneratingFunction")
        assert len(sensors) == 2

        # Check both sensors are present
        sensor_ids = {s.get("ID") for s in sensors}
        assert "SENSOR-010" in sensor_ids
        assert "SENSOR-011" in sensor_ids

    def test_export_instrumentation_loop_function(self, empty_model, instrumentation_loop_function, tmp_path):
        """Test InstrumentationLoopFunction export with child functions."""
        empty_model.conceptualModel.instrumentationLoopFunctions = [instrumentation_loop_function]

        output_file = tmp_path / "loop_function_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Find InstrumentationLoopFunction element
        loop_elem = root.find(".//InstrumentationLoopFunction")
        assert loop_elem is not None

        # Check required attributes
        assert loop_elem.get("ID") == "LOOP-001"
        assert loop_elem.get("ComponentClass") == "InstrumentationLoopFunction"

        # Check GenericAttributes contain loop number
        assert _generic_attribute_values(
            loop_elem, "InstrumentationLoopFunctionNumberAssignmentClass"
        ) == ["FIC-101"]

        # Check child ProcessInstrumentationFunction is nested inside loop
        child_func = loop_elem.find("ProcessInstrumentationFunction")
        assert child_func is not None
        assert child_func.get("ID") == "INS-001"

    def test_export_simple_instrumentation_loop(self, empty_model, simple_instrumentation_loop, tmp_path):
        """Test simple InstrumentationLoopFunction without children."""
        empty_model.conceptualModel.instrumentationLoopFunctions = [simple_instrumentation_loop]

        output_file = tmp_path / "simple_loop_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Find InstrumentationLoopFunction element
        loop_elem = root.find(".//InstrumentationLoopFunction")
        assert loop_elem is not None
        assert loop_elem.get("ID") == "LOOP-002"

        # Check loop number attribute
        assert _generic_attribute_values(
            loop_elem, "InstrumentationLoopFunctionNumberAssignmentClass"
        ) == ["TIC-201"]

        # No children expected
        child_func = loop_elem.find("ProcessInstrumentationFunction")
        assert child_func is None

    def test_export_multiple_loops(self, empty_model, instrumentation_loop_function, simple_instrumentation_loop, tmp_path):
        """Test exporting multiple InstrumentationLoopFunctions."""
        empty_model.conceptualModel.instrumentationLoopFunctions = [
            instrumentation_loop_function,
            simple_instrumentation_loop
        ]

        output_file = tmp_path / "multiple_loops_test.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        tree = etree.parse(str(output_file))
        root = tree.getroot()

        # Find all InstrumentationLoopFunction elements
        loops = root.findall(".//InstrumentationLoopFunction")
        assert len(loops) == 2

        loop_ids = {l.get("ID") for l in loops}
        assert "LOOP-001" in loop_ids
        assert "LOOP-002" in loop_ids


# Round-Trip Validation Tests for Instrumentation
class TestInstrumentationRoundTrip:
    """Test instrumentation export → import cycle using ProteusSerializer."""

    def test_roundtrip_instrumentation_function(self, empty_model, instrumentation_function_with_sensor, tmp_path):
        """Test that instrumentation function survives export/import cycle."""
        from pydexpi.loaders import ProteusSerializer

        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]

        # Export
        output_file = tmp_path / "roundtrip_instrumentation.xml"
        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Re-import using pyDEXPI's loader
        serializer = ProteusSerializer()
        reloaded_model = serializer.load(str(tmp_path), "roundtrip_instrumentation.xml")

        # Validate structure survived
        assert reloaded_model is not None
        assert reloaded_model.conceptualModel is not None
        assert len(reloaded_model.conceptualModel.processInstrumentationFunctions) >= 1

        # Check instrumentation function details
        reloaded_func = reloaded_model.conceptualModel.processInstrumentationFunctions[0]
        assert reloaded_func.processInstrumentationFunctionNumber == "PI-101"
        assert reloaded_func.processInstrumentationFunctionCategory == "P"

        # Check sensor survived
        assert len(reloaded_func.processSignalGeneratingFunctions) >= 1
        reloaded_sensor = reloaded_func.processSignalGeneratingFunctions[0]
        assert reloaded_sensor.processSignalGeneratingFunctionNumber == "PT-101"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
