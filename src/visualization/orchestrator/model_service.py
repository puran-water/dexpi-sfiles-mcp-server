"""
Model Service - SFILES to pydexpi enrichment
Handles model format normalization and conversion
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass

# Import pyDEXPI classes
from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.dexpi_classes.metaData import MetaData
from pydexpi.dexpi_classes.equipment import (
    CentrifugalPump, Tank, Mixer, CustomEquipment
)
from pydexpi.dexpi_classes.piping import (
    BallValve, PipingNetworkSegment, PipingNetworkSystem, PipingNode
)

try:
    from src.tools.pfd_expansion_engine import PfdExpansionEngine, ExpansionResult
except ImportError as e:
    raise ImportError(
        "Failed to import PfdExpansionEngine from src.tools. "
        "Install engineering-mcp-server in editable mode so package imports resolve. "
        f"Original error: {e}"
    ) from e

logger = logging.getLogger(__name__)


@dataclass
class ModelContext:
    """Context for model processing."""
    model_id: str
    model_type: str  # 'sfiles', 'dexpi'
    source_format: str
    target_format: str
    metadata: Dict[str, Any]


class ModelService:
    """
    Service for model enrichment and format conversion.
    Ensures all models are normalized to pydexpi format.
    """

    def __init__(self):
        """Initialize model service."""
        self.models_cache = {}
        self.expansion_engine = PfdExpansionEngine()

    def enrich_sfiles_to_dexpi(self, sfiles_model: str) -> DexpiModel:
        """
        Convert SFILES model to enriched pydexpi model.

        Args:
            sfiles_model: SFILES string or model ID

        Returns:
            Enriched pydexpi PlantModel
        """
        try:
            # Parse SFILES string to extract units and connections
            units, connections = self._parse_sfiles(sfiles_model)

            # Create DexpiModel with proper metadata
            # Create metadata
            metadata = MetaData()
            # Note: MetaData fields would be GenericAttributes in full implementation
            # For now, we'll store as a simple object

            # Create conceptual model with metadata
            conceptual_model = ConceptualModel()
            conceptual_model.metaData = metadata

            # Create DexpiModel
            dexpi_model = DexpiModel(
                conceptualModel=conceptual_model,
                originatingSystemName="SFILES Import",
                originatingSystemVendorName="Engineering MCP",
                originatingSystemVersion="PFD-001"
            )

            # For BFD units, use expansion engine to create PFD equipment
            if self._is_bfd_model(units):
                # Expand BFD blocks to PFD equipment using templates
                for unit in units:
                    if unit.get('type') in ['reactor', 'clarifier', 'tank']:
                        # Use template expansion for known BFD types
                        expansion_result = self._expand_bfd_block(unit)
                        # Add expanded equipment to plant model
                        for equipment in expansion_result.equipment:
                            self._add_equipment_to_model(dexpi_model, equipment)
            else:
                # Direct PFD units - create equipment directly
                for unit in units:
                    equipment = self._create_equipment_from_unit(unit)
                    self._add_equipment_to_model(dexpi_model, equipment)

            # Add connections
            for connection in connections:
                self._add_connection_to_model(dexpi_model, connection)

            logger.info(f"Enriched SFILES to pydexpi model")
            return dexpi_model

        except Exception as e:
            logger.error(f"Failed to enrich SFILES model: {e}")
            raise

    def load_dexpi_model(self, model_path: Union[str, Path]) -> DexpiModel:
        """
        Load existing DEXPI model from file.

        Args:
            model_path: Path to DEXPI XML file

        Returns:
            pydexpi PlantModel
        """
        try:
            model_path = Path(model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")

            # Load using pydexpi
            dexpi_model = DexpiModel.load(str(model_path))

            logger.info(f"Loaded DEXPI model from {model_path}")
            return dexpi_model

        except Exception as e:
            logger.error(f"Failed to load DEXPI model: {e}")
            raise

    def normalize_model(
        self,
        model: Union[str, Path, Dict],
        model_type: str
    ) -> DexpiModel:
        """
        Normalize any model format to pydexpi.

        Args:
            model: Model data (various formats)
            model_type: Type of model ('sfiles', 'dexpi', 'json')

        Returns:
            Normalized pydexpi PlantModel
        """
        try:
            if model_type == 'sfiles':
                return self.enrich_sfiles_to_dexpi(model)
            elif model_type == 'dexpi':
                if isinstance(model, (str, Path)):
                    return self.load_dexpi_model(model)
                else:
                    # Already a PlantModel
                    return model
            elif model_type == 'json':
                # Convert JSON to DEXPI
                # TODO: Implement JSON to DEXPI conversion
                dexpi_model = DexpiModel()
                return dexpi_model
            else:
                raise ValueError(f"Unsupported model type: {model_type}")

        except Exception as e:
            logger.error(f"Failed to normalize model: {e}")
            raise

    def extract_metadata(self, dexpi_model: DexpiModel) -> Dict[str, Any]:
        """
        Extract metadata from pydexpi model.

        Args:
            dexpi_model: pydexpi PlantModel

        Returns:
            Metadata dictionary
        """
        metadata = {
            "project": None,
            "drawing_number": None,
            "revision": None,
            "equipment_count": 0,
            "piping_segments": 0,
            "instrumentation_count": 0,
            "valves_count": 0
        }

        try:
            conceptual = getattr(dexpi_model, 'conceptualModel', None)

            if hasattr(dexpi_model, 'originatingSystemName'):
                metadata["project"] = dexpi_model.originatingSystemName
            if hasattr(dexpi_model, 'originatingSystemVersion'):
                metadata["drawing_number"] = dexpi_model.originatingSystemVersion

            equipment = []
            if conceptual and getattr(conceptual, 'taggedPlantItems', None):
                equipment = conceptual.taggedPlantItems
                metadata["equipment_count"] = len(equipment)

            if conceptual and getattr(conceptual, 'pipingNetworkSystems', None):
                segment_total = 0
                for system in conceptual.pipingNetworkSystems:
                    segment_total += len(getattr(system, 'segments', []) or [])
                metadata["piping_segments"] = segment_total

            instrumentation = [
                item for item in equipment
                if "Instrumentation" in type(item).__name__ or "Signal" in type(item).__name__
            ]
            metadata["instrumentation_count"] = len(instrumentation)

            valves = [
                item for item in equipment
                if "Valve" in type(item).__name__
            ]
            metadata["valves_count"] = len(valves)

        except Exception as e:
            logger.warning(f"Failed to extract some metadata: {e}")

        return metadata

    def validate_model(self, dexpi_model: DexpiModel) -> Dict[str, Any]:
        """
        Validate pydexpi model for completeness.

        Args:
            dexpi_model: pydexpi PlantModel

        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "warnings": [],
            "errors": []
        }

        try:
            conceptual = getattr(dexpi_model, 'conceptualModel', None)

            if not getattr(dexpi_model, 'PlantInformation', None):
                results["warnings"].append("Missing PlantInformation")

            equipment = getattr(conceptual, 'taggedPlantItems', []) or []
            if not equipment:
                results["warnings"].append("No equipment defined")

            piping_systems = getattr(conceptual, 'pipingNetworkSystems', []) or []
            unconnected = []
            for system in piping_systems:
                for segment in getattr(system, 'segments', []) or []:
                    if not getattr(segment, 'sourceNode', None) or not getattr(segment, 'targetNode', None):
                        unconnected.append(getattr(segment, 'id', 'unknown'))

            if unconnected:
                results["warnings"].append(
                    f"Unconnected piping segments: {unconnected[:5]}"
                )

            has_presentation = any(
                getattr(equip, 'Presentation', None) is not None for equip in equipment
            )
            if not has_presentation:
                results["warnings"].append(
                    "No presentation data found (coordinates, symbols)"
                )

        except Exception as e:
            results["errors"].append(f"Validation error: {str(e)}")
            results["valid"] = False

        # Set overall validity
        if results["errors"]:
            results["valid"] = False

        return results

    def add_presentation_data(
        self,
        dexpi_model: DexpiModel,
        auto_layout: bool = True
    ) -> DexpiModel:
        """
        Add or enhance presentation data for visualization.

        Args:
            dexpi_model: pydexpi PlantModel
            auto_layout: Automatically layout if no positions

        Returns:
            Enhanced PlantModel with presentation data
        """
        try:
            # TODO: Implement presentation data enrichment
            # - Add coordinates if missing
            # - Add symbol references
            # - Add color/style attributes

            if auto_layout:
                # Simple grid layout if no positions
                x, y = 100, 100
                spacing = 150

                conceptual = getattr(dexpi_model, 'conceptualModel', None)
                equipment = getattr(conceptual, 'taggedPlantItems', []) if conceptual else []
                for i, equip in enumerate(equipment):
                    if not hasattr(equip, 'Presentation'):
                        # Add basic presentation placeholder
                        # TODO: Replace with actual presentation classes
                        pass

                    x += spacing
                    if x > 1000:
                        x = 100
                        y += spacing

            logger.info("Added presentation data to model")
            return dexpi_model

        except Exception as e:
            logger.error(f"Failed to add presentation data: {e}")
            return dexpi_model

    def get_model_statistics(self, dexpi_model: DexpiModel) -> Dict[str, Any]:
        """
        Get detailed statistics about model.

        Args:
            dexpi_model: pydexpi PlantModel

        Returns:
            Statistics dictionary
        """
        stats = {
            "metadata": self.extract_metadata(dexpi_model),
            "validation": self.validate_model(dexpi_model),
            "complexity": {
                "total_elements": 0,
                "connection_density": 0.0,
                "has_presentation": False,
                "has_instrumentation": False
            }
        }

        try:
            conceptual = getattr(dexpi_model, 'conceptualModel', None)
            equipment = getattr(conceptual, 'taggedPlantItems', []) or []
            piping_systems = getattr(conceptual, 'pipingNetworkSystems', []) or []
            connection_count = sum(len(getattr(system, 'segments', []) or []) for system in piping_systems)

            stats["complexity"]["total_elements"] = len(equipment) + connection_count
            stats["complexity"]["connection_density"] = (
                connection_count / len(equipment) if equipment else 0.0
            )
            stats["complexity"]["has_instrumentation"] = any(
                "Instrumentation" in type(item).__name__ or "Signal" in type(item).__name__
                for item in equipment
            )
            stats["complexity"]["has_presentation"] = any(
                getattr(item, 'Presentation', None) is not None for item in equipment
            )

        except Exception as e:
            logger.warning(f"Failed to calculate some statistics: {e}")

        return stats

    def _parse_sfiles(self, sfiles_string: str) -> tuple[List[Dict], List[Dict]]:
        """Parse SFILES string to extract units and connections."""
        import re

        units = []
        connections = []

        # Simple SFILES parser for format: unit1[type1]->unit2[type2]
        # Example: "feed[tank]->reactor[CSTR]->separator[centrifuge]"

        # Extract units
        unit_pattern = r'(\w+)\[(\w+)\]'
        for match in re.finditer(unit_pattern, sfiles_string):
            units.append({
                'name': match.group(1),
                'type': match.group(2)
            })

        # Extract connections
        connection_pattern = r'(\w+)\[[\w]+\]\s*->\s*(\w+)'
        for match in re.finditer(connection_pattern, sfiles_string):
            connections.append({
                'from': match.group(1),
                'to': match.group(2)
            })

        return units, connections

    def _is_bfd_model(self, units: List[Dict]) -> bool:
        """Check if units represent BFD blocks needing expansion."""
        bfd_types = ['reactor', 'clarifier', 'separator', 'treatment']
        return any(unit.get('type', '').lower() in bfd_types for unit in units)

    def _expand_bfd_block(self, unit: Dict) -> ExpansionResult:
        """Expand BFD block using template engine."""
        template_map: Dict[str, Tuple[str, int]] = {
            'reactor': ('230_TK', 230),
            'clarifier': ('240_TK', 240)
        }

        unit_type = unit.get('type', '').lower()
        mapping = template_map.get(unit_type)
        if mapping:
            process_unit_id, area_number = mapping
            return self.expansion_engine.expand_bfd_block(
                bfd_block=unit.get('name', unit_type).upper(),
                process_unit_id=process_unit_id,
                area_number=area_number,
                train_count=unit.get('train_count', 1),
                parameters=unit.get('parameters', {})
            )

        # Fallback to simple equipment when no template exists
        logger.warning(
            "No template mapping available for BFD unit type '%s'. Using simple expansion.",
            unit_type or "unknown"
        )
        return self._create_simple_expansion(unit)

    def _create_simple_expansion(self, unit: Dict) -> ExpansionResult:
        """Create simple expansion for unknown BFD types."""
        from src.tools.pfd_expansion_engine import EquipmentInstance

        equipment = EquipmentInstance(
            id=f"{unit['name']}_01",
            tag=unit['name'].upper(),
            dexpi_class="CustomEquipment",
            dexpi_object=CustomEquipment(
                typeName=unit.get('type', 'CustomEquipment').upper(),
                nozzles=[],
                tagName=unit['name'].upper()
            ),
            parameters={}
        )

        return ExpansionResult(
            pfd_flowsheet_id="PFD-001",
            source_bfd_block=unit['name'],
            equipment=[equipment],
            connections=[],
            expansion_metadata={}
        )

    def _create_equipment_from_unit(self, unit: Dict) -> Any:
        """Create DEXPI equipment from PFD unit."""
        # Map unit types to DEXPI classes
        type_map = {
            'pump': CentrifugalPump,
            'tank': Tank,
            'valve': BallValve,
            'mixer': Mixer
        }

        equipment_class = type_map.get(unit.get('type', '').lower(), CustomEquipment)
        tag_name = unit.get('name', 'UNKNOWN').upper()
        unit_type = unit.get('type', 'Custom').upper()

        if equipment_class is CustomEquipment:
            equipment = equipment_class(
                typeName=unit_type,
                tagName=tag_name,
                nozzles=[]
            )
        else:
            equipment = equipment_class()
            if hasattr(equipment, 'tagName'):
                equipment.tagName = tag_name

        for attr, value in unit.get('parameters', {}).items():
            if hasattr(equipment, attr):
                try:
                    setattr(equipment, attr, value)
                except Exception as exc:
                    logger.debug(
                        "Failed to set attribute '%s' on %s: %s",
                        attr,
                        equipment_class.__name__,
                        exc
                    )

        return equipment

    def _add_equipment_to_model(self, model: DexpiModel, equipment: Any):
        """Add equipment to DEXPI model."""
        dexpi_obj = getattr(equipment, 'dexpi_object', equipment)
        tag_name = getattr(equipment, 'tag', None)

        if tag_name and hasattr(dexpi_obj, 'tagName') and not getattr(dexpi_obj, 'tagName', None):
            dexpi_obj.tagName = tag_name

        if not hasattr(model.conceptualModel, 'taggedPlantItems') or \
           model.conceptualModel.taggedPlantItems is None:
            model.conceptualModel.taggedPlantItems = []

        model.conceptualModel.taggedPlantItems.append(dexpi_obj)

    def _add_connection_to_model(self, model: DexpiModel, connection: Dict):
        """Add piping connection to DEXPI model."""

        def _build_node(label: str) -> PipingNode:
            node = PipingNode()
            node.id = f"PN_{label}"
            return node

        segment = PipingNetworkSegment()
        segment.id = f"SEG_{connection.get('from')}_{connection.get('to')}"
        segment.sourceNode = _build_node(connection.get('from', 'UNKNOWN'))
        segment.targetNode = _build_node(connection.get('to', 'UNKNOWN'))

        if not hasattr(model.conceptualModel, 'pipingNetworkSystems') or \
           model.conceptualModel.pipingNetworkSystems is None:
            model.conceptualModel.pipingNetworkSystems = []

        if not model.conceptualModel.pipingNetworkSystems:
            system = PipingNetworkSystem()
            system.segments = []
            model.conceptualModel.pipingNetworkSystems.append(system)

        system = model.conceptualModel.pipingNetworkSystems[0]
        if not hasattr(system, 'segments') or system.segments is None:
            system.segments = []
        system.segments.append(segment)
