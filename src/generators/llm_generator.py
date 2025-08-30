"""LLM-guided generator function for pyDEXPI synthetic P&ID generation."""

import logging
from typing import Any, Dict, List, Optional

from pydexpi.syndata import (
    GeneratorFunction,
    Pattern,
)
from pydexpi.syndata.generator_step import (
    GeneratorStep,
    InitializationStep,
    AddPatternStep,
    InternalConnectionStep,
)
from pydexpi.syndata.dexpi_pattern import DexpiPattern
from pydexpi.dexpi_classes.dexpiModel import DexpiModel, ConceptualModel
from pydexpi.dexpi_classes.equipment import Tank, Pump, HeatExchanger
from pydexpi.dexpi_classes.piping import PipingNetworkSegment, Pipe

logger = logging.getLogger(__name__)


class LLMGuidedGeneratorFunction(GeneratorFunction):
    """Custom GeneratorFunction for pyDEXPI that accepts LLM instructions."""
    
    def __init__(self, llm_plan: Dict[str, Any]):
        """Initialize with an LLM-generated plan.
        
        Args:
            llm_plan: Dictionary containing the generation plan with structure:
                {
                    "initial_pattern": {...},
                    "steps": [
                        {
                            "type": "add_pattern",
                            "pattern": {...},
                            "connections": {...}
                        },
                        ...
                    ]
                }
        """
        super().__init__()
        self.plan = llm_plan
        self.step_index = 0
        self.pattern_library = self._initialize_pattern_library()
    
    def _initialize_pattern_library(self) -> Dict[str, DexpiPattern]:
        """Initialize library of common equipment patterns."""
        patterns = {}
        
        # Simple tank pattern
        tank_model = DexpiModel()
        if not tank_model.conceptualModel:
            tank_model.conceptualModel = ConceptualModel()
        tank = Tank(tagName="TK-001", volume=100.0)
        tank_model.conceptualModel.taggedPlantItems.append(tank)
        patterns["tank"] = DexpiPattern(tank_model, label="Tank")
        
        # Simple pump pattern
        pump_model = DexpiModel()
        if not pump_model.conceptualModel:
            pump_model.conceptualModel = ConceptualModel()
        pump = Pump(tagName="P-001", flowRate=50.0)
        pump_model.conceptualModel.taggedPlantItems.append(pump)
        patterns["pump"] = DexpiPattern(pump_model, label="Pump")
        
        # Heat exchanger pattern
        hex_model = DexpiModel()
        if not hex_model.conceptualModel:
            hex_model.conceptualModel = ConceptualModel()
        hex_unit = HeatExchanger(tagName="HX-001")
        hex_model.conceptualModel.taggedPlantItems.append(hex_unit)
        patterns["heat_exchanger"] = DexpiPattern(hex_model, label="HeatExchanger")
        
        return patterns
    
    def initialize_pattern(self) -> InitializationStep:
        """Initialize the pattern based on LLM plan.
        
        Returns:
            InitializationStep with the initial pattern
        """
        initial_spec = self.plan.get("initial_pattern", {"type": "tank"})
        pattern_type = initial_spec.get("type", "tank")
        
        # Get pattern from library or create new one
        if pattern_type in self.pattern_library:
            initial_pattern = self.pattern_library[pattern_type].copy_pattern()
        else:
            # Create a generic pattern if not in library
            initial_pattern = self._create_pattern_from_spec(initial_spec)
        
        return InitializationStep(initial_pattern)
    
    def get_next_step(self, current_pattern: Pattern) -> Optional[GeneratorStep]:
        """Return next step from LLM plan.
        
        Args:
            current_pattern: The current pattern being built
            
        Returns:
            Next GeneratorStep or None if plan is complete
        """
        if self.step_index >= len(self.plan.get("steps", [])):
            return None
        
        step_spec = self.plan["steps"][self.step_index]
        self.step_index += 1
        
        return self._create_step_from_spec(step_spec, current_pattern)
    
    def _create_step_from_spec(
        self, 
        step_spec: Dict[str, Any], 
        current_pattern: Pattern
    ) -> GeneratorStep:
        """Create a GeneratorStep from LLM specification.
        
        Args:
            step_spec: Step specification from LLM plan
            current_pattern: Current pattern being built
            
        Returns:
            GeneratorStep to execute
        """
        step_type = step_spec.get("type", "add_pattern")
        
        if step_type == "add_pattern":
            # Add a new pattern to the current one
            pattern_type = step_spec.get("pattern", {}).get("type", "tank")
            
            if pattern_type in self.pattern_library:
                new_pattern = self.pattern_library[pattern_type].copy_pattern()
            else:
                new_pattern = self._create_pattern_from_spec(step_spec.get("pattern", {}))
            
            # Get connection information
            own_connector = step_spec.get("connections", {}).get("from", "Out")
            counterpart_connector = step_spec.get("connections", {}).get("to", "In")
            
            return AddPatternStep(
                pattern_to_add=new_pattern,
                own_connector_label=own_connector,
                counterpart_connector_label=counterpart_connector
            )
        
        elif step_type == "internal_connection":
            # Connect two connectors within the current pattern
            from_connector = step_spec.get("from_connector", "Out1")
            to_connector = step_spec.get("to_connector", "In1")
            
            return InternalConnectionStep(
                connector_label=from_connector,
                counterpart_label=to_connector
            )
        
        else:
            # Default to adding a simple pattern
            return AddPatternStep(
                pattern_to_add=self.pattern_library["tank"].copy_pattern(),
                own_connector_label="Out",
                counterpart_connector_label="In"
            )
    
    def _create_pattern_from_spec(self, spec: Dict[str, Any]) -> DexpiPattern:
        """Create a DEXPI pattern from specification.
        
        Args:
            spec: Pattern specification
            
        Returns:
            DexpiPattern created from specification
        """
        pattern_type = spec.get("type", "tank")
        tag_name = spec.get("tag_name", f"{pattern_type.upper()}-001")
        
        # Create model
        model = DexpiModel()
        if not model.conceptualModel:
            model.conceptualModel = ConceptualModel()
        
        # Add equipment based on type
        if pattern_type == "tank":
            equipment = Tank(
                tagName=tag_name,
                volume=spec.get("volume", 100.0)
            )
        elif pattern_type == "pump":
            equipment = Pump(
                tagName=tag_name,
                flowRate=spec.get("flow_rate", 50.0)
            )
        elif pattern_type == "heat_exchanger":
            equipment = HeatExchanger(
                tagName=tag_name,
                area=spec.get("area", 10.0)
            )
        else:
            # Default to tank for unknown types
            equipment = Tank(tagName=tag_name)
        
        model.conceptualModel.taggedPlantItems.append(equipment)
        
        # Add piping if specified
        if spec.get("add_piping", False):
            segment = PipingNetworkSegment(
                id=f"{tag_name}_piping",
                pipingClassArtefact=spec.get("pipe_class", "CS150")
            )
            pipe = Pipe(
                nominalDiameter=spec.get("pipe_diameter", 50),
                material=spec.get("pipe_material", "Carbon Steel")
            )
            segment.pipingNetworkSegmentItems = [pipe]
            model.conceptualModel.pipingNetworkSystems.append(segment)
        
        return DexpiPattern(model, label=pattern_type.title())


class LLMPlanValidator:
    """Validates LLM-generated plans for P&ID generation."""
    
    @staticmethod
    def validate_plan(plan: Dict[str, Any]) -> List[str]:
        """Validate an LLM-generated plan.
        
        Args:
            plan: The plan to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check for required fields
        if "initial_pattern" not in plan:
            issues.append("Missing 'initial_pattern' in plan")
        
        if "steps" not in plan:
            issues.append("Missing 'steps' in plan")
        elif not isinstance(plan["steps"], list):
            issues.append("'steps' must be a list")
        
        # Validate initial pattern
        if "initial_pattern" in plan:
            initial = plan["initial_pattern"]
            if "type" not in initial:
                issues.append("Initial pattern missing 'type'")
        
        # Validate steps
        for i, step in enumerate(plan.get("steps", [])):
            if "type" not in step:
                issues.append(f"Step {i} missing 'type'")
            
            step_type = step.get("type")
            if step_type == "add_pattern":
                if "pattern" not in step:
                    issues.append(f"Step {i}: add_pattern missing 'pattern'")
                if "connections" not in step:
                    issues.append(f"Step {i}: add_pattern missing 'connections'")
            
            elif step_type == "internal_connection":
                if "from_connector" not in step:
                    issues.append(f"Step {i}: internal_connection missing 'from_connector'")
                if "to_connector" not in step:
                    issues.append(f"Step {i}: internal_connection missing 'to_connector'")
        
        return issues


def create_example_llm_plan() -> Dict[str, Any]:
    """Create an example LLM plan for testing.
    
    Returns:
        Example plan dictionary
    """
    return {
        "initial_pattern": {
            "type": "tank",
            "tag_name": "TK-101",
            "volume": 500.0
        },
        "steps": [
            {
                "type": "add_pattern",
                "pattern": {
                    "type": "pump",
                    "tag_name": "P-101",
                    "flow_rate": 100.0
                },
                "connections": {
                    "from": "Out",
                    "to": "In"
                }
            },
            {
                "type": "add_pattern",
                "pattern": {
                    "type": "heat_exchanger",
                    "tag_name": "HX-101",
                    "area": 25.0
                },
                "connections": {
                    "from": "Out",
                    "to": "In"
                }
            },
            {
                "type": "add_pattern",
                "pattern": {
                    "type": "tank",
                    "tag_name": "TK-102",
                    "volume": 300.0
                },
                "connections": {
                    "from": "Out",
                    "to": "In"
                }
            }
        ]
    }
