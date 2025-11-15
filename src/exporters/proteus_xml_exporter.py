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

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from lxml import etree
from pydexpi.dexpi_classes import (
    dataTypes,
    dexpiModel,
    enumerations,
    equipment,
    instrumentation,
    physicalQuantities,
    piping,
)


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


class GenericAttributeExporter:
    """Serializes pyDEXPI data/custom attributes into Proteus GenericAttributes blocks."""

    FORMAT_MAP = {
        str: "string",
        int: "integer",
        float: "double",
    }

    def __init__(self) -> None:
        self._multi_language_cls = dataTypes.MultiLanguageString
        self._single_language_cls = dataTypes.SingleLanguageString
        self._physical_quantity_types = tuple(
            attr
            for attr in vars(physicalQuantities).values()
            if isinstance(attr, type)
            and hasattr(attr, "model_fields")
            and {"value", "unit"}.issubset(attr.model_fields)
        )

    def export(self, parent: etree._Element, component: Any) -> None:
        """Export standard data attributes and custom attributes for a component."""
        standard_entries = self._collect_standard_attributes(component)
        self._write_generic_attributes(parent, standard_entries, "DexpiAttributes")

        custom_entries = self._collect_custom_attributes(component)
        self._write_generic_attributes(parent, custom_entries, "DexpiCustomAttributes")

    def _collect_standard_attributes(self, component: Any) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        model_fields = getattr(component.__class__, "model_fields", {})
        for field_name, field in model_fields.items():
            meta = field.json_schema_extra or {}
            if meta.get("attribute_category") != "data":
                continue
            value = getattr(component, field_name, None)
            if self._is_empty_value(value):
                continue
            attr_name = self._attribute_name(field_name)
            entries.extend(self._serialize_value(attr_name, value))
        return entries

    def _collect_custom_attributes(self, component: Any) -> List[Dict[str, str]]:
        custom_attrs = getattr(component, "customAttributes", None)
        if not custom_attrs:
            return []

        entries: List[Dict[str, str]] = []
        for custom_attr in custom_attrs:
            attr_name = custom_attr.attributeName or "CustomAttribute"
            extra: Dict[str, str] = {}
            if custom_attr.attributeURI:
                extra["AttributeURI"] = str(custom_attr.attributeURI)
            entries.extend(self._serialize_value(attr_name, custom_attr.value, extra))
        return entries

    def _serialize_value(
        self,
        attr_name: str,
        value: Any,
        extra: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, str]]:
        """Convert a python value into GenericAttribute dictionaries."""
        if value is None:
            return []

        # Multi-language strings
        if isinstance(value, self._multi_language_cls):
            entries: List[Dict[str, str]] = []
            for single in value.singleLanguageStrings or []:
                entries.extend(self._serialize_value(attr_name, single, extra))
            return entries

        if isinstance(value, self._single_language_cls):
            if value.value is None:
                return []
            entry = {
                "Name": attr_name,
                "Format": "string",
                "Value": str(value.value),
            }
            if value.language:
                entry["Language"] = str(value.language)
            return [self._apply_extra(entry, extra)]

        # Enumerations
        if isinstance(value, Enum):
            entry = {
                "Name": attr_name,
                "Format": "string",
                "Value": str(value.name),
            }
            return [self._apply_extra(entry, extra)]

        # Physical quantity (NullableLength, Length, etc.)
        if self._looks_like_physical_quantity(value):
            quantity_value = getattr(value, "value", None)
            quantity_unit = getattr(value, "unit", None)
            if quantity_value is None:
                return []
            entry = {
                "Name": attr_name,
                "Format": "double",
                "Value": str(quantity_value),
            }
            if quantity_unit is not None:
                unit_value = getattr(quantity_unit, "name", None) or str(quantity_unit)
                entry["Units"] = str(unit_value)
            return [self._apply_extra(entry, extra)]

        # Primitive types
        if isinstance(value, bool):
            entry = {
                "Name": attr_name,
                "Format": "string",
                "Value": str(value).lower(),
            }
            return [self._apply_extra(entry, extra)]

        if isinstance(value, int):
            entry = {
                "Name": attr_name,
                "Format": self.FORMAT_MAP[int],
                "Value": str(value),
            }
            return [self._apply_extra(entry, extra)]

        if isinstance(value, float):
            entry = {
                "Name": attr_name,
                "Format": self.FORMAT_MAP[float],
                "Value": str(value),
            }
            return [self._apply_extra(entry, extra)]

        if isinstance(value, str):
            entry = {
                "Name": attr_name,
                "Format": self.FORMAT_MAP[str],
                "Value": value,
            }
            return [self._apply_extra(entry, extra)]

        if isinstance(value, datetime):
            entry = {
                "Name": attr_name,
                "Format": "string",
                "Value": value.isoformat(),
            }
            return [self._apply_extra(entry, extra)]

        # Lists/tuples - serialize each entry separately
        if isinstance(value, (list, tuple)):
            entries: List[Dict[str, str]] = []
            for item in value:
                entries.extend(self._serialize_value(attr_name, item, extra))
            return entries

        # Fallback - stringify the value
        entry = {
            "Name": attr_name,
            "Format": "string",
            "Value": str(value),
        }
        return [self._apply_extra(entry, extra)]

    def _write_generic_attributes(
        self,
        parent: etree._Element,
        entries: Sequence[Dict[str, str]],
        set_name: str,
    ) -> None:
        if not entries:
            return

        container = etree.SubElement(parent, "GenericAttributes")
        container.set("Set", set_name)
        container.set("Number", str(len(entries)))

        for entry in entries:
            attr_elem = etree.SubElement(container, "GenericAttribute")
            for key, value in entry.items():
                if value is None:
                    continue
                attr_elem.set(key, str(value))

    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and value == "":
            return True
        if isinstance(value, (list, tuple, set, dict)) and not value:
            return True
        return False

    @staticmethod
    def _attribute_name(field_name: str, suffix: str = "AssignmentClass") -> str:
        if not field_name:
            return suffix or ""
        if "_" in field_name:
            camel = "".join(part.capitalize() for part in field_name.split("_") if part)
        else:
            camel = field_name[0].upper() + field_name[1:]
        return f"{camel}{suffix}" if suffix else camel

    @staticmethod
    def _apply_extra(
        entry: Dict[str, str],
        extra: Optional[Dict[str, str]],
    ) -> Dict[str, str]:
        if extra:
            for key, value in extra.items():
                if value is not None:
                    entry[key] = str(value)
        return entry

    def _looks_like_physical_quantity(self, value: Any) -> bool:
        if not self._physical_quantity_types:
            return False
        return isinstance(value, self._physical_quantity_types)


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
        self.xsd_path = (
            xsd_path
            or Path(__file__).parent.parent.parent
            / "docs"
            / "schemas"
            / "ProteusPIDSchema_4.2.xsd"
        )
        self.id_registry = IDRegistry()
        self.attribute_exporter = GenericAttributeExporter()
        self.include_component_class_uri = True
        if self.xsd_path and self.xsd_path.name.endswith("_min.xsd"):
            # The project-specific minimal schema omits ComponentClassURI from PlantItem
            self.include_component_class_uri = False

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

    def _apply_plant_item_attributes(
        self,
        element: etree._Element,
        component: Any,
    ) -> None:
        """Set optional PlantItem attributes if present on the pyDEXPI component."""
        if (
            self.include_component_class_uri
            and hasattr(component, "uri")
            and component.uri
        ):
            element.set("ComponentClassURI", str(component.uri))

        optional_map = {
            "specification": "Specification",
            "specificationURI": "SpecificationURI",
            "stockNumber": "StockNumber",
            "componentType": "ComponentType",
            "revision": "Revision",
            "revisionURI": "RevisionURI",
            "status": "Status",
            "statusURI": "StatusURI",
        }

        for attr_name, xml_name in optional_map.items():
            value = getattr(component, attr_name, None)
            if value:
                element.set(xml_name, str(value))

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

            # PlantItem optional attributes (ComponentClassURI, Specification, etc.)
            self._apply_plant_item_attributes(equip_elem, equipment)

            # Export all standard/custom attributes via the generic exporter
            self.attribute_exporter.export(equip_elem, equipment)

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

        # Set common PlantItem attributes
        self._apply_plant_item_attributes(nozzle_elem, nozzle)

        # Optional ComponentName attribute
        # Use subTagName if available (standard pyDEXPI attribute for nozzle identifiers)
        if hasattr(nozzle, 'subTagName') and nozzle.subTagName:
            nozzle_elem.set("ComponentName", str(nozzle.subTagName))

        # Export GenericAttributes (DEXPI attributes like subTagName)
        self.attribute_exporter.export(nozzle_elem, nozzle)

        if not hasattr(nozzle, "nodes") or not nozzle.nodes:
            raise ValueError(
                f"Nozzle {nozzle_id} missing connection points (nodes attribute). "
                "Nozzles must have nodes for piping attachment. "
                "Add PipingNode instances to the pyDEXPI model for each nozzle."
            )

        # Export nozzle connection points if available
        self._export_connection_points(nozzle_elem, nozzle)

        # TODO: Add optional child elements when pyDEXPI provides them
        # - NozzleType (e.g., "Inlet", "Outlet", "Drain")
        # - NominalDiameter (numeric with units)
        # - Rating (pressure/temperature rating)

    def _export_piping(self, parent: etree._Element, piping_systems: list) -> None:
        """Export all piping network systems to XML.

        Args:
            parent: Parent Drawing element (NOT PlantDesignItem - that doesn't exist!)
            piping_systems: List of PipingNetworkSystem objects

        Exports PipingNetworkSystem elements with:
            - Required: ID, ComponentClass
            - Optional: ComponentClassURI
            - Children: Label (optional), GenericAttributes, PipingNetworkSegment
        """
        if not piping_systems:
            return

        for piping_system in piping_systems:
            # Register system ID
            system_id = self.id_registry.register(piping_system)

            # Create PipingNetworkSystem element
            system_elem = etree.SubElement(parent, "PipingNetworkSystem")

            # Required attributes
            system_elem.set("ID", system_id)
            system_elem.set("ComponentClass", piping_system.__class__.__name__)

            self._apply_plant_item_attributes(system_elem, piping_system)

            # Export system-level GenericAttributes
            self.attribute_exporter.export(system_elem, piping_system)

            # Export segments
            if hasattr(piping_system, 'segments') and piping_system.segments:
                for segment in piping_system.segments:
                    self._export_piping_network_segment(system_elem, segment)

    def _export_piping_network_segment(
        self, parent: etree._Element, segment: Any
    ) -> None:
        """Export a single PipingNetworkSegment to XML.

        Args:
            parent: Parent PipingNetworkSystem element
            segment: PipingNetworkSegment object to export

        Exports PipingNetworkSegment with:
            - Required: ID, ComponentClass
            - Optional: ComponentClassURI
            - Children: GenericAttributes, items (PipingComponent, etc.), CenterLine, Connection
        """
        # Register segment ID
        segment_id = self.id_registry.register(segment)

        # Create PipingNetworkSegment element
        segment_elem = etree.SubElement(parent, "PipingNetworkSegment")

        # Required attributes
        segment_elem.set("ID", segment_id)
        segment_elem.set("ComponentClass", segment.__class__.__name__)

        self._apply_plant_item_attributes(segment_elem, segment)

        # Export segment-level GenericAttributes
        self.attribute_exporter.export(segment_elem, segment)

        # Export segment items (PipingComponent, PipeOffPageConnector, etc.)
        if hasattr(segment, 'items') and segment.items:
            for item in segment.items:
                self._export_piping_segment_item(segment_elem, item)

        # Export CenterLine geometry if provided
        self._export_center_lines(segment_elem, segment)

        # Export connections (with FromNode/ToNode conversion)
        if hasattr(segment, 'connections') and segment.connections:
            for connection in segment.connections:
                self._export_piping_connection(segment_elem, connection)

    def _export_piping_segment_item(
        self, parent: etree._Element, item: Any
    ) -> None:
        """Export a piping segment item (PipingComponent, valve, etc.).

        Args:
            parent: Parent PipingNetworkSegment element
            item: Piping component item to export

        Exports items like:
            - PipingComponent (pipes, fittings)
            - Valve (all valve types)
            - PipeOffPageConnector
            - PropertyBreak
        """
        # Register item ID
        item_id = self.id_registry.register(item)

        # Get element name from class (e.g., "BallValve", "PipingComponent")
        element_name = item.__class__.__name__

        # Create element
        item_elem = etree.SubElement(parent, element_name)

        # Required attributes
        item_elem.set("ID", item_id)
        item_elem.set("ComponentClass", item.__class__.__name__)

        self._apply_plant_item_attributes(item_elem, item)

        # Optional ComponentName (use pipingComponentName for piping items, tagName for others)
        if hasattr(item, 'pipingComponentName') and item.pipingComponentName:
            item_elem.set("ComponentName", str(item.pipingComponentName))
        elif hasattr(item, 'tagName') and item.tagName:
            item_elem.set("ComponentName", str(item.tagName))

        # Export GenericAttributes for this item
        self.attribute_exporter.export(item_elem, item)

        # Export ConnectionPoints if available (needed for node references)
        if hasattr(item, 'nodes') and item.nodes:
            self._export_connection_points(item_elem, item)

    def _export_connection_points(
        self, parent: etree._Element, component: Any
    ) -> None:
        """Export ConnectionPoints for a piping component.

        Args:
            parent: Parent component element
            component: Component with nodes to export

        Creates structure:
            <ConnectionPoints FlowIn="N" FlowOut="M" NumPoints="K">
                <Node ID="..." Type="process"/>
                ...
            </ConnectionPoints>
        """
        if not hasattr(component, 'nodes') or not component.nodes:
            return

        # Register all nodes first (needed for Connection export)
        for node in component.nodes:
            self.id_registry.register(node)

        # Create ConnectionPoints element
        conn_points = etree.SubElement(parent, "ConnectionPoints")

        node_count = len(component.nodes)

        # Set NumPoints
        conn_points.set("NumPoints", str(node_count))

        if node_count >= 1:
            conn_points.set("FlowIn", "1")
            conn_points.set("FlowOut", str(node_count))

        # TODO: Determine FlowIn/FlowOut from node types or positions
        # For now, assume first node is inlet (FlowIn=0) and last is outlet (FlowOut=len-1)
        # This is a simplified approach - full implementation would analyze node semantics

        # Export each node
        for node in component.nodes:
            node_elem = etree.SubElement(conn_points, "Node")
            node_elem.set("ID", self.id_registry.get_id(node))

            # Optional Type attribute
            if hasattr(node, 'type') and node.type:
                node_elem.set("Type", str(node.type))
            else:
                # Default to "process" for piping nodes
                node_elem.set("Type", "process")

    def _export_center_lines(
        self,
        parent: etree._Element,
        segment: Any
    ) -> None:
        """Export CenterLine geometry sequences if available."""
        center_line_definitions = self._collect_center_line_definitions(segment)
        if not center_line_definitions:
            self._validate_center_line_requirement(segment)
            return

        for definition in center_line_definitions:
            points = self._normalize_center_line_points(definition, segment)
            center_line_elem = etree.SubElement(parent, "CenterLine")
            center_line_elem.set("NumPoints", str(len(points)))

            definition_id = getattr(definition, "id", None)
            if definition_id:
                center_line_elem.set("ID", str(definition_id))

            if hasattr(definition.__class__, "model_fields"):
                self.attribute_exporter.export(center_line_elem, definition)

            for point in points:
                coord_elem = etree.SubElement(center_line_elem, "Coordinate")
                coord_elem.set("X", self._format_coordinate_value(point[0]))
                coord_elem.set("Y", self._format_coordinate_value(point[1]))
                if point[2] is not None:
                    coord_elem.set("Z", self._format_coordinate_value(point[2]))

    def _collect_center_line_definitions(self, segment: Any) -> List[Any]:
        """Collect potential center line definitions from segment attributes."""
        definitions: List[Any] = []
        attr_configs = [
            ("centerLines", True),
            ("centerLine", False),
            ("centerline", False),
            ("centerLinePoints", False),
            ("centerlinePoints", False),
            ("curve", False),
        ]

        for attr_name, iterate in attr_configs:
            value = getattr(segment, attr_name, None)
            if value in (None, []):
                continue
            if iterate and isinstance(value, (list, tuple)):
                for item in value:
                    if item:
                        definitions.append(item)
            else:
                definitions.append(value)
        return [definition for definition in definitions if definition]

    def _normalize_center_line_points(
        self,
        definition: Any,
        segment: Any
    ) -> List[tuple[float, float, Optional[float]]]:
        """Normalize any supported center line representation into coordinate tuples."""
        points_source = None
        if hasattr(definition, "points"):
            points_source = definition.points
        elif hasattr(definition, "coordinates"):
            points_source = definition.coordinates
        elif isinstance(definition, dict):
            points_source = (
                definition.get("points")
                or definition.get("coordinates")
                or definition.get("coords")
            )
        else:
            points_source = definition

        if points_source in (None, []):
            segment_id = getattr(segment, "id", "UNKNOWN")
            raise ValueError(
                f"PipingNetworkSegment {segment_id} has a center line definition "
                "without coordinate data. Provide at least two coordinate points."
            )

        if isinstance(points_source, (list, tuple)):
            points_iterable = points_source
        elif hasattr(points_source, "__iter__"):
            points_iterable = list(points_source)
        else:
            segment_id = getattr(segment, "id", "UNKNOWN")
            raise ValueError(
                f"PipingNetworkSegment {segment_id} specifies unsupported center "
                "line representation. Use lists/tuples of coordinates or objects "
                "with 'points'/'coordinates' attributes."
            )

        normalized_points: List[tuple[float, float, Optional[float]]] = []
        for point in points_iterable:
            normalized_points.append(
                self._normalize_coordinate_point(point, segment)
            )

        if len(normalized_points) < 2:
            segment_id = getattr(segment, "id", "UNKNOWN")
            raise ValueError(
                f"PipingNetworkSegment {segment_id} center line requires at least "
                "two coordinate points."
            )

        return normalized_points

    def _normalize_coordinate_point(
        self,
        point: Any,
        segment: Any
    ) -> tuple[float, float, Optional[float]]:
        """Normalize a coordinate entry into (x, y, z?)."""
        x = y = z = None
        if isinstance(point, dict):
            x = point.get("x") or point.get("X")
            y = point.get("y") or point.get("Y")
            z = point.get("z") or point.get("Z")
        elif isinstance(point, (list, tuple)):
            if len(point) >= 2:
                x, y = point[0], point[1]
                if len(point) >= 3:
                    z = point[2]
        else:
            for attr in ("x", "X"):
                if hasattr(point, attr):
                    x = getattr(point, attr)
                    break
            for attr in ("y", "Y"):
                if hasattr(point, attr):
                    y = getattr(point, attr)
                    break
            for attr in ("z", "Z"):
                if hasattr(point, attr):
                    z = getattr(point, attr)
                    break

        segment_id = getattr(segment, "id", "UNKNOWN")
        if x is None or y is None:
            raise ValueError(
                f"CenterLine point for segment {segment_id} is missing X or Y "
                "coordinate. Provide numeric X/Y values for each point."
            )

        x_value = self._coerce_float(x, segment_id, axis="X")
        y_value = self._coerce_float(y, segment_id, axis="Y")
        z_value = self._coerce_float(z, segment_id, axis="Z") if z is not None else None

        return (x_value, y_value, z_value)

    def _coerce_float(
        self,
        value: Any,
        segment_id: str,
        axis: str
    ) -> float:
        """Convert coordinate entry to float, failing loudly on invalid data."""
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"CenterLine point for segment {segment_id} has non-numeric "
                f"{axis} value ({value!r}). Provide numeric coordinates."
            )

    def _format_coordinate_value(self, value: float) -> str:
        """Format coordinate values consistently for XML output."""
        return f"{value:.15g}"

    def _validate_center_line_requirement(self, segment: Any) -> None:
        """Raise error if segment demands center line geometry but none provided."""
        if not self._center_line_required(segment):
            return
        segment_id = getattr(segment, "id", "UNKNOWN")
        raise ValueError(
            f"PipingNetworkSegment {segment_id} requires CenterLine geometry but no "
            "centerLinePoints/centerLines were provided. Add coordinate data to the "
            "pyDEXPI model or unset the requirement flag."
        )

    def _center_line_required(self, segment: Any) -> bool:
        """Determine whether the segment explicitly demands center line geometry."""
        flags = [
            getattr(segment, "requiresCenterLine", False),
            getattr(segment, "centerLineRequired", False),
            getattr(segment, "visualRepresentationRequired", False),
            getattr(segment, "requires_center_line", False),
        ]
        return any(self._is_truthy_flag(flag) for flag in flags)

    @staticmethod
    def _is_truthy_flag(value: Any) -> bool:
        """Interpret string/boolean flags in a permissive but precise way."""
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "required"}
        return bool(value)

    def _export_piping_connection(
        self, parent: etree._Element, connection: Any
    ) -> None:
        """Export a Connection element with FromID/ToID/FromNode/ToNode.

        Args:
            parent: Parent PipingNetworkSegment element
            connection: PipingConnection object to export

        Exports Connection with:
            - FromID: Source item ID
            - FromNode: Source node index (1-based for XML)
            - ToID: Target item ID
            - ToNode: Target node index (1-based for XML)

        Note:
            pyDEXPI uses 0-based node indices, but Proteus XML uses 1-based.
            This method converts 0-based to 1-based.
        """
        # Create Connection element
        conn_elem = etree.SubElement(parent, "Connection")

        # Export FromID and FromNode
        if hasattr(connection, 'sourceItem') and connection.sourceItem:
            source_id = self.id_registry.get_id(connection.sourceItem)
            if source_id:
                conn_elem.set("FromID", source_id)

                # Get source node index (0-based in pyDEXPI)
                if hasattr(connection, 'sourceNode') and connection.sourceNode:
                    # Find node index in sourceItem's nodes list
                    if hasattr(connection.sourceItem, 'nodes'):
                        try:
                            node_index = connection.sourceItem.nodes.index(connection.sourceNode)
                            # Convert to 1-based for XML
                            conn_elem.set("FromNode", str(node_index + 1))
                        except (ValueError, AttributeError):
                            # Node not found in list, skip FromNode attribute
                            pass

        # Export ToID and ToNode
        if hasattr(connection, 'targetItem') and connection.targetItem:
            target_id = self.id_registry.get_id(connection.targetItem)
            if target_id:
                conn_elem.set("ToID", target_id)

                # Get target node index (0-based in pyDEXPI)
                if hasattr(connection, 'targetNode') and connection.targetNode:
                    # Find node index in targetItem's nodes list
                    if hasattr(connection.targetItem, 'nodes'):
                        try:
                            node_index = connection.targetItem.nodes.index(connection.targetNode)
                            # Convert to 1-based for XML
                            conn_elem.set("ToNode", str(node_index + 1))
                        except (ValueError, AttributeError):
                            # Node not found in list, skip ToNode attribute
                            pass

    def _export_instrumentation(
        self,
        parent: etree._Element,
        model: dexpiModel.DexpiModel
    ) -> None:
        """Export all instrumentation functions to XML.

        Args:
            parent: Parent root PlantModel element
            model: Source DexpiModel (for accessing instrumentation)

        Exports ProcessInstrumentationFunction elements with:
            - ProcessSignalGeneratingFunction (sensors)
            - InformationFlow (MeasuringLineFunction, SignalLineFunction)
            - Association elements (logical start/end, location)
        """
        if not hasattr(model.conceptualModel, 'processInstrumentationFunctions'):
            return

        functions = model.conceptualModel.processInstrumentationFunctions
        if not functions:
            return

        for function in functions:
            self._export_process_instrumentation_function(parent, function)

    def _export_process_instrumentation_function(
        self, parent: etree._Element, function: Any
    ) -> None:
        """Export a ProcessInstrumentationFunction to XML.

        Args:
            parent: Parent PlantModel element
            function: ProcessInstrumentationFunction object

        Exports structure:
            <ProcessInstrumentationFunction ID="..." ComponentClass="...">
                <GenericAttributes>...</GenericAttributes>
                <ConnectionPoints>...</ConnectionPoints>
                <Association Type="is logical end of" ItemID="..."/>
                <InformationFlow>...</InformationFlow>
                <ProcessSignalGeneratingFunction>...</ProcessSignalGeneratingFunction>
            </ProcessInstrumentationFunction>
        """
        # Register function ID
        function_id = self.id_registry.register(function)

        # Create ProcessInstrumentationFunction element
        func_elem = etree.SubElement(parent, "ProcessInstrumentationFunction")

        # Required attributes
        func_elem.set("ID", function_id)
        func_elem.set("ComponentClass", function.__class__.__name__)

        self._apply_plant_item_attributes(func_elem, function)

        # Optional ComponentName
        if hasattr(function, 'componentName') and function.componentName:
            func_elem.set("ComponentName", str(function.componentName))

        # Export GenericAttributes
        self.attribute_exporter.export(func_elem, function)

        # Export ConnectionPoints if available
        if hasattr(function, 'nodes') and function.nodes:
            self._export_instrumentation_connection_points(func_elem, function)

        # Ensure signal conveying function IDs exist for associations
        self._register_signal_functions(function)

        # Export actuating functions (mechanical + electrical)
        if hasattr(function, 'actuatingFunctions') and function.actuatingFunctions:
            for actuating_function in function.actuatingFunctions:
                self._export_actuating_function(func_elem, actuating_function)

        if hasattr(function, 'actuatingElectricalFunctions') and function.actuatingElectricalFunctions:
            for actuating_function in function.actuatingElectricalFunctions:
                self._export_actuating_function(func_elem, actuating_function)

        # Export ProcessSignalGeneratingFunction elements (sensors) FIRST
        # This ensures they're registered before InformationFlow references them
        if hasattr(function, 'processSignalGeneratingFunctions') and function.processSignalGeneratingFunctions:
            for sensor in function.processSignalGeneratingFunctions:
                self._export_process_signal_generating_function(func_elem, sensor)

        # Export InformationFlow elements (MeasuringLineFunction, SignalLineFunction) AFTER sensors
        if hasattr(function, 'signalConveyingFunctions') and function.signalConveyingFunctions:
            for signal_func in function.signalConveyingFunctions:
                self._export_information_flow(func_elem, signal_func, function)

        # Export Signal connectors (off-page references)
        if hasattr(function, 'signalConnectors') and function.signalConnectors:
            for connector in function.signalConnectors:
                self._export_signal_connector(func_elem, connector)

        # Export Associations after flows to ensure referenced IDs exist
        self._export_instrumentation_associations(func_elem, function)

    def _export_actuating_function(
        self,
        parent: etree._Element,
        actuating_function: Any
    ) -> None:
        """Export ActuatingFunction or ActuatingElectricalFunction nodes."""
        func_id = getattr(actuating_function, "id", None)
        if not func_id:
            raise ValueError(
                "ActuatingFunction missing ID attribute. All actuating functions must "
                "provide stable IDs for association references."
            )

        func_id = self.id_registry.register(actuating_function)

        element_name = actuating_function.__class__.__name__
        act_elem = etree.SubElement(parent, element_name)
        act_elem.set("ID", func_id)
        act_elem.set("ComponentClass", actuating_function.__class__.__name__)

        self._apply_plant_item_attributes(act_elem, actuating_function)
        self.attribute_exporter.export(act_elem, actuating_function)

        if hasattr(actuating_function, "nodes") and actuating_function.nodes:
            self._export_instrumentation_connection_points(act_elem, actuating_function)

        self._export_instrumentation_associations(act_elem, actuating_function)

    def _export_process_signal_generating_function(
        self, parent: etree._Element, sensor: Any
    ) -> None:
        """Export a ProcessSignalGeneratingFunction (sensor) to XML.

        Args:
            parent: Parent ProcessInstrumentationFunction element
            sensor: ProcessSignalGeneratingFunction object

        Exports structure:
            <ProcessSignalGeneratingFunction ID="..." ComponentClass="...">
                <GenericAttributes>...</GenericAttributes>
                <Association Type="is logical start of" ItemID="..."/>
                <Association Type="is located in" ItemID="..."/>
            </ProcessSignalGeneratingFunction>
        """
        # Register sensor ID
        sensor_id = self.id_registry.register(sensor)

        # Create ProcessSignalGeneratingFunction element
        sensor_elem = etree.SubElement(parent, "ProcessSignalGeneratingFunction")

        # Required attributes
        sensor_elem.set("ID", sensor_id)
        sensor_elem.set("ComponentClass", sensor.__class__.__name__)

        self._apply_plant_item_attributes(sensor_elem, sensor)

        # Export GenericAttributes
        self.attribute_exporter.export(sensor_elem, sensor)

        # Ensure measuring line IDs exist for association references
        self._register_signal_functions(sensor)

        # Export Associations
        self._export_instrumentation_associations(sensor_elem, sensor)

    def _export_signal_connector(
        self,
        parent: etree._Element,
        connector: Any
    ) -> None:
        """Export SignalOffPageConnector or similar elements."""
        connector_id = getattr(connector, "id", None)
        if not connector_id:
            raise ValueError(
                "Signal connector missing ID attribute. Provide IDs so connectors "
                "can be referenced in information flows."
            )

        connector_id = self.id_registry.register(connector)

        element_name = connector.__class__.__name__
        connector_elem = etree.SubElement(parent, element_name)
        connector_elem.set("ID", connector_id)
        connector_elem.set("ComponentClass", connector.__class__.__name__)

        connector_name = getattr(connector, "connectorName", None)
        if connector_name:
            connector_elem.set("ConnectorName", str(connector_name))

        self._apply_plant_item_attributes(connector_elem, connector)
        self.attribute_exporter.export(connector_elem, connector)

        if hasattr(connector, "nodes") and connector.nodes:
            self._export_instrumentation_connection_points(connector_elem, connector)

        reference = getattr(connector, "connectorReference", None)
        if reference:
            self._export_signal_connector_reference(connector_elem, reference)

    def _export_signal_connector_reference(
        self,
        parent: etree._Element,
        reference: Any
    ) -> None:
        """Export a SignalOffPageConnectorReference child element."""
        ref_id = getattr(reference, "id", None)
        if not ref_id:
            raise ValueError(
                "SignalOffPageConnectorReference missing ID attribute. Provide IDs "
                "for connector references so they can be resolved."
            )

        ref_id = self.id_registry.register(reference)

        ref_name = reference.__class__.__name__
        ref_elem = etree.SubElement(parent, "SignalOffPageConnectorReference")
        ref_elem.set("ID", ref_id)
        ref_elem.set("ComponentClass", ref_name)

        if hasattr(reference.__class__, "model_fields"):
            self.attribute_exporter.export(ref_elem, reference)

        if hasattr(reference, "referencedConnector") and reference.referencedConnector:
            referenced_id = self.id_registry.get_id(reference.referencedConnector)
            if referenced_id:
                assoc_elem = etree.SubElement(ref_elem, "Association")
                assoc_elem.set("Type", "refers to")
                assoc_elem.set("ItemID", referenced_id)

    def _export_information_flow(
        self, parent: etree._Element, signal_func: Any, instrumentation_func: Any
    ) -> None:
        """Export an InformationFlow element (MeasuringLineFunction or SignalLineFunction).

        Args:
            parent: Parent ProcessInstrumentationFunction element
            signal_func: MeasuringLineFunction or SignalLineFunction object
            instrumentation_func: Parent ProcessInstrumentationFunction for associations

        Exports structure:
            <InformationFlow ID="..." ComponentClass="MeasuringLineFunction">
                <Association Type="has logical start" ItemID="..."/>
                <Association Type="has logical end" ItemID="..."/>
            </InformationFlow>
        """
        # Register signal function ID
        signal_id = self.id_registry.register(signal_func)

        # Create InformationFlow element
        flow_elem = etree.SubElement(parent, "InformationFlow")

        # Required attributes
        flow_elem.set("ID", signal_id)
        flow_elem.set("ComponentClass", signal_func.__class__.__name__)

        self._apply_plant_item_attributes(flow_elem, signal_func)

        # Export GenericAttributes for signal metadata
        self.attribute_exporter.export(flow_elem, signal_func)

        # Export Associations for signal flow
        # "has logical start" - points to source (ProcessSignalGeneratingFunction)
        if hasattr(signal_func, 'source') and signal_func.source:
            source_id = self.id_registry.get_id(signal_func.source)
            if source_id:
                assoc_elem = etree.SubElement(flow_elem, "Association")
                assoc_elem.set("Type", "has logical start")
                assoc_elem.set("ItemID", source_id)

        # "has logical end" - points to target (ProcessInstrumentationFunction)
        if hasattr(signal_func, 'target') and signal_func.target:
            target_id = self.id_registry.get_id(signal_func.target)
            if target_id:
                assoc_elem = etree.SubElement(flow_elem, "Association")
                assoc_elem.set("Type", "has logical end")
                assoc_elem.set("ItemID", target_id)

    def _export_instrumentation_connection_points(
        self, parent: etree._Element, component: Any
    ) -> None:
        """Export ConnectionPoints for instrumentation components.

        Args:
            parent: Parent component element
            component: Component with nodes to export

        Similar to piping ConnectionPoints but for signal nodes.
        """
        if not hasattr(component, 'nodes') or not component.nodes:
            return

        # Register all nodes first
        for node in component.nodes:
            self.id_registry.register(node)

        # Create ConnectionPoints element
        conn_points = etree.SubElement(parent, "ConnectionPoints")

        # Set NumPoints
        conn_points.set("NumPoints", str(len(component.nodes)))

        # Export each node
        for node in component.nodes:
            node_elem = etree.SubElement(conn_points, "Node")
            node_elem.set("ID", self.id_registry.get_id(node))

            # Set Type (default to "signal" for instrumentation)
            if hasattr(node, 'type') and node.type:
                node_elem.set("Type", str(node.type))
            else:
                node_elem.set("Type", "signal")

    def _register_signal_functions(self, component: Any) -> None:
        """Ensure all signal conveying functions have registered IDs."""
        if not hasattr(component, "signalConveyingFunctions"):
            return
        signal_functions = component.signalConveyingFunctions
        if not signal_functions:
            return
        for signal_func in signal_functions:
            self.id_registry.register(signal_func)

    def _export_instrumentation_associations(
        self, parent: etree._Element, component: Any
    ) -> None:
        """Export Association elements for instrumentation components.

        Args:
            parent: Parent element
            component: Component with associations

        Association types:
            - "is logical start of" (sensor → measuring line)
            - "is logical end of" (instrumentation → measuring line)
            - "is located in" (sensor → equipment/piping)
        """
        # Handle "is located in" association (sensingLocation)
        if hasattr(component, 'sensingLocation') and component.sensingLocation:
            location_id = self.id_registry.get_id(component.sensingLocation)
            if location_id:
                assoc_elem = etree.SubElement(parent, "Association")
                assoc_elem.set("Type", "is located in")
                assoc_elem.set("ItemID", location_id)

        # Handle signal conveying function associations
        if hasattr(component, 'signalConveyingFunctions') and component.signalConveyingFunctions:
            for signal_func in component.signalConveyingFunctions:
                signal_id = self.id_registry.get_id(signal_func)
                if signal_id:
                    assoc_elem = etree.SubElement(parent, "Association")
                    # Check if this component is source or target
                    if hasattr(signal_func, 'source') and signal_func.source == component:
                        assoc_elem.set("Type", "is logical start of")
                    elif hasattr(signal_func, 'target') and signal_func.target == component:
                        assoc_elem.set("Type", "is logical end of")
                    else:
                        # Default to "is logical end of" for instrumentation functions
                        assoc_elem.set("Type", "is logical end of")
                    assoc_elem.set("ItemID", signal_id)

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
