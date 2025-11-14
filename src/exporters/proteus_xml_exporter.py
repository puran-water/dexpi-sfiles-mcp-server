"""Proteus XML Exporter for pyDEXPI Models.

This module provides functionality to export pyDEXPI DexpiModel instances to Proteus XML 4.2 format,
enabling rendering via GraphicBuilder and other Proteus-compliant visualization tools.

Architecture:
    - IDRegistry: Manages unique ID generation and validation
    - ProteusXMLExporter: Main export orchestrator
    - Helper methods for each major component type (equipment, piping, instrumentation)

References:
    - XSD Schema: docs/schemas/ProteusPIDSchema_4.2.xsd
    - Format Guide: docs/PROTEUS_XML_FORMAT.md
    - DEXPI Spec: docs/schemas/DEXPI_Specification_1.2.pdf
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from lxml import etree
from pydexpi.dexpi_classes import dexpiModel, equipment, piping, instrumentation


class IDRegistry:
    """Manages ID generation and validation for Proteus XML export.

    Ensures all exported objects have unique IDs and tracks references for
    cross-validation (e.g., fromNode/toNode in piping segments).

    Attributes:
        _ids: Set of all registered IDs for uniqueness checking
        _object_to_id: Mapping from Python objects to their assigned IDs
        _prefix_map: Mapping from class names to unique prefixes (to avoid collisions)
        _prefix_counters: Counter for each prefix to generate sequential IDs
    """

    # Prefix mapping to avoid collisions for common classes
    DEFAULT_PREFIX_MAP = {
        'Equipment': 'EQU',
        'Nozzle': 'NOZ',
        'PipingNetworkSystem': 'PNS',
        'PipingNetworkSegment': 'SEG',
        'ProcessInstrumentationFunction': 'INS',
        'Tank': 'TNK',
        'CentrifugalPump': 'PMP',
        'PlateHeatExchanger': 'HEX',
        'ProcessColumn': 'COL',
        'PressureVessel': 'VES',
        'Valve': 'VLV',
        'ControlValve': 'CVL',
        'FlowTransmitter': 'FIT',
        'PressureTransmitter': 'PIT',
        'TemperatureTransmitter': 'TIT',
        'LevelTransmitter': 'LIT',
    }

    def __init__(self, prefix_map: Optional[Dict[str, str]] = None):
        """Initialize empty ID registry.

        Args:
            prefix_map: Optional custom prefix mapping (merges with defaults)
        """
        self._ids: Set[str] = set()
        # Use id(obj) as key to avoid issues with pyDEXPI's __eq__ based on ID
        self._object_to_id: Dict[int, str] = {}
        self._prefix_map = {**self.DEFAULT_PREFIX_MAP}
        if prefix_map:
            self._prefix_map.update(prefix_map)
        self._prefix_counters: Dict[str, int] = {}

    def register(self, obj: Any, preferred_id: Optional[str] = None) -> str:
        """Register an object and return its unique ID.

        Args:
            obj: The object to register (equipment, nozzle, segment, etc.)
            preferred_id: Optional preferred ID (uses object.id if available)

        Returns:
            The assigned ID (either existing, preferred, or generated)

        Raises:
            ValueError: If preferred_id is already registered to a different object
        """
        # Return existing ID if object already registered (use id(obj) for identity)
        obj_identity = id(obj)
        if obj_identity in self._object_to_id:
            return self._object_to_id[obj_identity]

        # Determine ID to use - normalize to string
        obj_id = preferred_id or getattr(obj, 'id', None)
        if obj_id is not None:
            obj_id = str(obj_id)  # Normalize UUIDs and other types to strings
        else:
            obj_id = self._generate_id(obj)

        # Validate uniqueness
        if obj_id in self._ids:
            raise ValueError(
                f"Duplicate ID '{obj_id}' - already registered. "
                f"Object: {type(obj).__name__}"
            )

        # Register
        self._ids.add(obj_id)
        self._object_to_id[obj_identity] = obj_id
        return obj_id

    def _generate_id(self, obj: Any) -> str:
        """Generate unique ID for object without existing ID.

        Args:
            obj: Object needing ID generation

        Returns:
            Generated ID in format: {CLASS_PREFIX}{COUNTER:04d}
            Example: EQU0001, PMP0042, INS0012
        """
        class_name = obj.__class__.__name__

        # Use mapped prefix if available, otherwise use first 3 letters
        prefix = self._prefix_map.get(class_name, class_name[:3].upper())

        # Get current counter for this prefix
        if prefix not in self._prefix_counters:
            self._prefix_counters[prefix] = 0

        self._prefix_counters[prefix] += 1
        counter = self._prefix_counters[prefix]

        return f"{prefix}{counter:04d}"

    def get_id(self, obj: Any) -> Optional[str]:
        """Get registered ID for an object without registering it.

        Args:
            obj: Object to look up

        Returns:
            Registered ID or None if not registered
        """
        return self._object_to_id.get(id(obj))

    def reserve(self, obj_id: str) -> None:
        """Reserve an ID in the registry without associating it with an object.

        Useful for pre-seeding IDs from imported models or ensuring consistency.

        Args:
            obj_id: ID to reserve

        Raises:
            ValueError: If ID is already registered
        """
        obj_id = str(obj_id)  # Normalize to string
        if obj_id in self._ids:
            raise ValueError(f"ID '{obj_id}' is already reserved")
        self._ids.add(obj_id)

    def validate_reference(self, ref_id: str) -> bool:
        """Validate that a reference ID exists in the registry.

        Args:
            ref_id: ID to validate (e.g., fromNode value)

        Returns:
            True if ID exists in registry, False otherwise
        """
        return ref_id in self._ids


class ProteusXMLExporter:
    """Main exporter class for converting pyDEXPI models to Proteus XML.

    Usage:
        exporter = ProteusXMLExporter()
        exporter.export(model, output_path="model.xml")

    Architecture:
        1. Initialize ID registry
        2. Export PlantInformation metadata
        3. Export equipment with nozzles
        4. Export piping network systems
        5. Export instrumentation
        6. Validate against XSD schema
        7. Write XML file
    """

    def __init__(self, xsd_path: Optional[Path] = None):
        """Initialize exporter.

        Args:
            xsd_path: Optional path to XSD schema for validation
                     Defaults to docs/schemas/ProteusPIDSchema_4.2.xsd
        """
        self.xsd_path = xsd_path or Path(__file__).parent.parent.parent / "docs" / "schemas" / "ProteusPIDSchema_4.2.xsd"
        self.id_registry = IDRegistry()

    def export(
        self,
        model: dexpiModel.DexpiModel,
        output_path: Path,
        validate: bool = True
    ) -> None:
        """Export pyDEXPI model to Proteus XML file.

        Args:
            model: DexpiModel instance to export
            output_path: Path where XML file will be written
            validate: Whether to validate against XSD schema (default: True)

        Raises:
            ValueError: If model validation fails
            FileNotFoundError: If XSD schema not found (when validate=True)
        """
        # Reset ID registry for fresh export
        self.id_registry = IDRegistry()

        # Build XML tree
        root = self._create_root_element()
        plant_info = self._export_plant_information(root, model)
        drawing = self._create_drawing_element(root, model)

        # Export components directly under root (as siblings to Drawing)
        # ProteusSerializer expects Equipment at root level, not nested in Drawing
        self._export_equipment(root, model.conceptualModel.taggedPlantItems)
        self._export_piping(root, model.conceptualModel.pipingNetworkSystems)
        self._export_instrumentation(root, model)

        # Write XML to file
        self._write_xml(root, output_path)

        # Validate if requested
        if validate:
            self._validate_xml(output_path)

    def _create_root_element(self) -> etree._Element:
        """Create root PlantModel element with XML namespace declarations.

        Returns:
            Root Element with proper attributes and namespace declarations

        Note:
            Based on XSD analysis and TrainingTestCases validation:
            - Schema has NO targetNamespace (uses noNamespaceSchemaLocation)
            - No default namespace should be declared
            - Only xsi namespace is required for schema reference
        """
        # Define namespaces - NO default namespace per XSD 4.2
        nsmap = {
            'xsi': "http://www.w3.org/2001/XMLSchema-instance",
        }

        root = etree.Element("PlantModel", nsmap=nsmap)

        # Use noNamespaceSchemaLocation per TrainingTestCases
        root.set(
            "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation",
            "ProteusPIDSchema_4.2.xsd"
        )

        return root

    def _export_plant_information(
        self,
        root: etree._Element,
        model: dexpiModel.DexpiModel
    ) -> etree._Element:
        """Export PlantInformation metadata element.

        Args:
            root: Root PlantModel element
            model: Source DexpiModel

        Returns:
            Created PlantInformation element

        Note:
            Based on TrainingTestCases analysis:
            - SchemaVersion, OriginatingSystem, Date, Time, Units are required
            - Is3D attribute: "yes" | "no" (default: "no" for P&ID)
            - Discipline attribute: "PID", "PFD", etc. (optional)
            - UnitsOfMeasure is a CHILD element, not sibling
        """
        plant_info = etree.SubElement(root, "PlantInformation")

        # Schema version (required per TrainingTestCases)
        plant_info.set("SchemaVersion", "4.2")

        # Originating system information (required)
        plant_info.set(
            "OriginatingSystem",
            model.originatingSystemName or "pyDEXPI"
        )

        # Date and time (required)
        dt = model.exportDateTime or datetime.now()
        plant_info.set("Date", dt.strftime("%Y-%m-%d"))
        # Time format: HH:MM:SS (ProteusSerializer expects simple format without timezone)
        # Note: ProteusSerializer.load() parses time as HH:MM:SS split by ":"
        time_str = dt.strftime("%H:%M:%S")
        plant_info.set("Time", time_str)

        # Is3D attribute (P&ID = "no", 3D = "yes")
        plant_info.set("Is3D", "no")

        # Units attribute (required) - use Metre as default per TrainingTestCases
        plant_info.set("Units", "Metre")

        # Discipline attribute (optional, but common in TrainingTestCases)
        plant_info.set("Discipline", "PID")

        # Optional vendor attributes
        if model.originatingSystemVendorName:
            plant_info.set("OriginatingSystemVendor", model.originatingSystemVendorName)
        if model.originatingSystemVersion:
            plant_info.set("OriginatingSystemVersion", model.originatingSystemVersion)

        # UnitsOfMeasure child element (CRITICAL: child not sibling!)
        units_elem = etree.SubElement(plant_info, "UnitsOfMeasure")
        units_elem.set("Distance", "Metre")

        return plant_info

    def _create_drawing_element(
        self,
        root: etree._Element,
        model: dexpiModel.DexpiModel
    ) -> etree._Element:
        """Create Drawing element with required Presentation child.

        Args:
            root: Root PlantModel element
            model: Source DexpiModel

        Returns:
            Created Drawing element

        Note:
            Based on TrainingTestCases analysis and XSD (lines 1005-1043):
            - Drawing is direct child of PlantModel
            - Presentation child is REQUIRED
            - Extent child is optional
            - Components (Equipment, PipingNetworkSystem, etc.) are direct children
            - NO PlantDesignItem wrapper element exists!
        """
        drawing = etree.SubElement(root, "Drawing")

        # Required attributes from XSD
        drawing.set("Name", getattr(model, 'drawingName', None) or "PID-001")
        drawing.set("Type", "PID")  # Fixed value per XSD

        # Optional attributes
        if hasattr(model, 'drawingTitle') and model.drawingTitle:
            drawing.set("Title", model.drawingTitle)
        if hasattr(model, 'drawingSize') and model.drawingSize:
            drawing.set("Size", model.drawingSize)

        # Required Presentation child (per TrainingTestCases)
        presentation = etree.SubElement(drawing, "Presentation")
        # Default presentation attributes - can be customized later
        presentation.set("Layer", "Default")
        presentation.set("Color", "Black")
        presentation.set("LineType", "Solid")
        presentation.set("LineWeight", "0.00035")
        # RGB values
        presentation.set("R", "0")
        presentation.set("G", "0")
        presentation.set("B", "0")

        # Optional Extent child - add if model has extent information
        # TODO: Implement extent extraction from model when available

        return drawing

    def _export_equipment(self, parent: etree._Element, equipment_list: list) -> None:
        """Export all equipment (TaggedPlantItems) to XML.

        Args:
            parent: Parent Drawing element (NOT PlantDesignItem - that doesn't exist!)
            equipment_list: List of equipment objects from conceptualModel

        Exports Equipment elements with:
            - Required: ID, ComponentClass, ComponentName
            - Optional: TagName, ProcessArea, Purpose
            - Children: Nozzle elements (0..unbounded)
        """
        if not equipment_list:
            return

        for equipment in equipment_list:
            # Register equipment ID first
            equipment_id = self.id_registry.register(equipment)

            # Create Equipment element
            equip_elem = etree.SubElement(parent, "Equipment")

            # Required attributes
            equip_elem.set("ID", equipment_id)
            equip_elem.set("ComponentClass", equipment.__class__.__name__)

            # ComponentName: Use tagName if available, otherwise fall back to ID
            # tagName is the standard pyDEXPI attribute for equipment identifiers
            component_name = getattr(equipment, 'tagName', None) or equipment_id
            equip_elem.set("ComponentName", str(component_name))

            # Optional attributes
            # TagName maps to pyDEXPI's tagName attribute (NOT componentTag)
            if hasattr(equipment, 'tagName') and equipment.tagName:
                equip_elem.set("TagName", str(equipment.tagName))

            if hasattr(equipment, 'processArea') and equipment.processArea:
                equip_elem.set("ProcessArea", str(equipment.processArea))

            if hasattr(equipment, 'purpose') and equipment.purpose:
                equip_elem.set("Purpose", str(equipment.purpose))

            # Export GenericAttributes (DEXPI attributes like tagName)
            self._export_generic_attributes(equip_elem, equipment)

            # Export nozzles as children
            if hasattr(equipment, 'nozzles') and equipment.nozzles:
                for nozzle in equipment.nozzles:
                    self._export_nozzle(equip_elem, nozzle)

    def _export_nozzle(self, parent: etree._Element, nozzle: Any) -> None:
        """Export a single nozzle as child of Equipment element.

        Args:
            parent: Parent Equipment element
            nozzle: Nozzle object to export

        Exports Nozzle element with:
            - Required: ID
            - Optional: ComponentName
            - Children: NozzleType, NominalDiameter, Rating (all optional)
        """
        # Register nozzle ID (critical for piping segment references)
        nozzle_id = self.id_registry.register(nozzle)

        # Create Nozzle element
        nozzle_elem = etree.SubElement(parent, "Nozzle")

        # Required attribute
        nozzle_elem.set("ID", nozzle_id)

        # Optional ComponentName attribute
        # Use subTagName if available (standard pyDEXPI attribute for nozzle identifiers)
        if hasattr(nozzle, 'subTagName') and nozzle.subTagName:
            nozzle_elem.set("ComponentName", str(nozzle.subTagName))

        # Export GenericAttributes (DEXPI attributes like subTagName)
        self._export_generic_attributes(nozzle_elem, nozzle)

        # TODO: Add optional child elements when pyDEXPI provides them
        # - NozzleType (e.g., "Inlet", "Outlet", "Drain")
        # - NominalDiameter (numeric with units)
        # - Rating (pressure/temperature rating)

    def _export_generic_attributes(self, parent: etree._Element, component: Any) -> None:
        """Export GenericAttributes for DEXPI standard attributes.

        ProteusSerializer expects standard DEXPI attributes (like tagName) to be
        exported as GenericAttribute elements within a GenericAttributes container,
        not as XML attributes.

        Args:
            parent: Parent Equipment or Nozzle element
            component: pyDEXPI component object with attributes to export

        Creates structure:
            <GenericAttributes Set="DexpiAttributes" Number="N">
                <GenericAttribute Name="TagNameAssignmentClass" Format="string" Value="V-101"/>
                <GenericAttribute Name="SubTagNameAssignmentClass" Format="string" Value="Inlet"/>
            </GenericAttributes>
        """
        # Collect attributes to export
        attributes = []

        # TagName attributes (for Equipment)
        if hasattr(component, 'tagName') and component.tagName:
            attributes.append(("TagNameAssignmentClass", component.tagName))

        if hasattr(component, 'tagNamePrefix') and component.tagNamePrefix:
            attributes.append(("TagNamePrefixAssignmentClass", component.tagNamePrefix))

        if hasattr(component, 'tagNameSequenceNumber') and component.tagNameSequenceNumber:
            attributes.append(("TagNameSequenceNumberAssignmentClass", str(component.tagNameSequenceNumber)))

        if hasattr(component, 'tagNameSuffix') and component.tagNameSuffix:
            attributes.append(("TagNameSuffixAssignmentClass", component.tagNameSuffix))

        # SubTagName (for Nozzles)
        if hasattr(component, 'subTagName') and component.subTagName:
            attributes.append(("SubTagNameAssignmentClass", component.subTagName))

        # Only create GenericAttributes if we have attributes to export
        if not attributes:
            return

        # Create GenericAttributes container
        generic_attrs = etree.SubElement(parent, "GenericAttributes")
        generic_attrs.set("Set", "DexpiAttributes")
        generic_attrs.set("Number", str(len(attributes)))

        # Add each GenericAttribute
        for name, value in attributes:
            attr_elem = etree.SubElement(generic_attrs, "GenericAttribute")
            attr_elem.set("Name", name)
            attr_elem.set("Format", "string")
            attr_elem.set("Value", str(value))

    def _export_piping(self, parent: etree._Element, piping_systems: list) -> None:
        """Export all piping network systems to XML.

        Args:
            parent: Parent Drawing element (NOT PlantDesignItem - that doesn't exist!)
            piping_systems: List of PipingNetworkSystem objects

        Implementation: Day 5
        """
        # TODO: Implement piping export
        #  - Iterate through piping_systems
        #  - Create <PipingNetworkSystem> for each system
        #  - Export segments with fromNode/toNode references
        #  - Validate node references exist in id_registry
        #  - Handle inline valves
        pass

    def _export_instrumentation(
        self,
        parent: etree._Element,
        model: dexpiModel.DexpiModel
    ) -> None:
        """Export all instrumentation functions to XML.

        Args:
            parent: Parent Drawing element (NOT PlantDesignItem - that doesn't exist!)
            model: Source DexpiModel (for accessing instrumentation)

        Implementation: Days 6-7
        """
        # TODO: Implement instrumentation export
        #  - Export ProcessInstrumentationFunctions
        #  - Export signal lines (measuring/actuating)
        #  - Export control loops (InstrumentationLoopFunctions)
        #  - Use instrumentation_toolkit for pyDEXPI integration
        pass

    def _write_xml(self, root: etree._Element, output_path: Path) -> None:
        """Write XML element to file with proper formatting.

        Args:
            root: Root element to write
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use lxml for pretty printing
        root_str = etree.tostring(
            root,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True
        )

        output_path.write_bytes(root_str)

    def _validate_xml(self, xml_path: Path) -> None:
        """Validate exported XML against Proteus XSD schema.

        Args:
            xml_path: Path to XML file to validate

        Raises:
            FileNotFoundError: If XSD schema not found
            ValueError: If validation fails
        """
        if not self.xsd_path.exists():
            raise FileNotFoundError(
                f"XSD schema not found: {self.xsd_path}. "
                f"Download from ProteusXML/proteusxml repository."
            )

        # Parse schema and document
        schema_doc = etree.parse(str(self.xsd_path))
        schema = etree.XMLSchema(schema_doc)

        xml_doc = etree.parse(str(xml_path))

        # Validate
        if not schema.validate(xml_doc):
            errors = schema.error_log
            raise ValueError(
                f"Proteus XML validation failed:\n"
                f"{errors}"
            )


def export_to_proteus_xml(
    model: dexpiModel.DexpiModel,
    output_path: Path,
    validate: bool = True
) -> None:
    """Convenience function to export pyDEXPI model to Proteus XML.

    Args:
        model: DexpiModel instance to export
        output_path: Path where XML file will be written
        validate: Whether to validate against XSD schema (default: True)

    Example:
        >>> from pydexpi.loaders.proteus_serializer import ProteusSerializer
        >>> from src.exporters.proteus_xml_exporter import export_to_proteus_xml
        >>>
        >>> # Load existing Proteus XML
        >>> serializer = ProteusSerializer()
        >>> model = serializer.load("path/to/model.xml")
        >>>
        >>> # Export to new Proteus XML
        >>> export_to_proteus_xml(model, Path("output/exported_model.xml"))
    """
    exporter = ProteusXMLExporter()
    exporter.export(model, output_path, validate=validate)
