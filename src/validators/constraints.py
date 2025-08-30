"""Engineering constraints and validation for P&IDs and flowsheets."""

import re
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EngineeringConstraints:
    """Validate against engineering rules and ISA standards."""
    
    # ISA-5.1 compliant tag patterns
    VALID_TAG_PATTERNS = {
        "pump": r"^P-\d{3}[A-Z]?$",
        "tank": r"^TK-\d{3}[A-Z]?$",
        "valve": r"^V-\d{3}[A-Z]?$",
        "heat_exchanger": r"^(HX|E)-\d{3}[A-Z]?$",
        "reactor": r"^R-\d{3}[A-Z]?$",
        "compressor": r"^C-\d{3}[A-Z]?$",
        "column": r"^(T|C)-\d{3}[A-Z]?$",
        # Instrumentation
        "flow_controller": r"^FC-\d{3}[A-Z]?$",
        "level_controller": r"^LC-\d{3}[A-Z]?$",
        "pressure_indicator": r"^PI-\d{3}[A-Z]?$",
        "temperature_indicator": r"^TI-\d{3}[A-Z]?$",
        "flow_transmitter": r"^FT-\d{3}[A-Z]?$",
        "level_transmitter": r"^LT-\d{3}[A-Z]?$",
        "pressure_transmitter": r"^PT-\d{3}[A-Z]?$",
        "temperature_transmitter": r"^TT-\d{3}[A-Z]?$",
    }
    
    # Valid pipe classes
    VALID_PIPE_CLASSES = {
        "CS150": "Carbon Steel 150#",
        "CS300": "Carbon Steel 300#",
        "CS600": "Carbon Steel 600#",
        "SS150": "Stainless Steel 150#",
        "SS300": "Stainless Steel 300#",
        "SS600": "Stainless Steel 600#",
        "PVC": "PVC Schedule 40",
        "HDPE": "HDPE DR11",
    }
    
    # Valid pipe materials
    VALID_MATERIALS = {
        "Carbon Steel",
        "Stainless Steel 304",
        "Stainless Steel 316",
        "PVC",
        "HDPE",
        "PTFE",
        "Hastelloy",
        "Inconel",
    }
    
    # Valid nominal diameters (mm)
    VALID_NOMINAL_DIAMETERS = [
        15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 
        250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000
    ]
    
    def validate_tag_name(self, equipment_type: str, tag_name: str) -> bool:
        """Validate equipment tag against ISA-5.1 conventions.
        
        Args:
            equipment_type: Type of equipment
            tag_name: Tag name to validate
            
        Returns:
            True if valid, False otherwise
        """
        pattern = self.VALID_TAG_PATTERNS.get(equipment_type.lower())
        if not pattern:
            logger.warning(f"No validation pattern for equipment type: {equipment_type}")
            return True  # Allow unknown types
        
        return bool(re.match(pattern, tag_name))
    
    def validate_pipe_class(self, pipe_class: str) -> bool:
        """Validate pipe class specification.
        
        Args:
            pipe_class: Pipe class to validate
            
        Returns:
            True if valid, False otherwise
        """
        return pipe_class in self.VALID_PIPE_CLASSES
    
    def validate_material(self, material: str) -> bool:
        """Validate material specification.
        
        Args:
            material: Material to validate
            
        Returns:
            True if valid, False otherwise
        """
        return material in self.VALID_MATERIALS
    
    def validate_nominal_diameter(self, diameter: float) -> bool:
        """Validate nominal pipe diameter.
        
        Args:
            diameter: Diameter in mm
            
        Returns:
            True if valid, False otherwise
        """
        return diameter in self.VALID_NOMINAL_DIAMETERS
    
    def validate_equipment_specs(
        self, 
        equipment_type: str, 
        specs: Dict[str, Any]
    ) -> List[str]:
        """Validate equipment specifications.
        
        Args:
            equipment_type: Type of equipment
            specs: Equipment specifications
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if equipment_type.lower() == "tank":
            # Validate tank specifications
            if "volume" in specs:
                volume = specs["volume"]
                if not (0.1 <= volume <= 10000):
                    issues.append(f"Tank volume {volume} m³ out of typical range (0.1-10000)")
            
            if "pressure" in specs:
                pressure = specs["pressure"]
                if pressure < 0:
                    issues.append("Tank pressure cannot be negative")
        
        elif equipment_type.lower() == "pump":
            # Validate pump specifications
            if "flow_rate" in specs:
                flow_rate = specs["flow_rate"]
                if flow_rate <= 0:
                    issues.append("Pump flow rate must be positive")
            
            if "head" in specs:
                head = specs["head"]
                if head <= 0:
                    issues.append("Pump head must be positive")
        
        elif equipment_type.lower() == "heat_exchanger":
            # Validate heat exchanger specifications
            if "area" in specs:
                area = specs["area"]
                if area <= 0:
                    issues.append("Heat exchanger area must be positive")
            
            if "duty" in specs:
                duty = specs["duty"]
                # Duty can be positive (heating) or negative (cooling)
                if duty == 0:
                    issues.append("Heat exchanger duty cannot be zero")
        
        return issues
    
    def validate_stream_properties(self, properties: Dict[str, Any]) -> List[str]:
        """Validate stream properties.
        
        Args:
            properties: Stream properties
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if "flow_rate" in properties:
            flow = properties["flow_rate"]
            if flow < 0:
                issues.append("Stream flow rate cannot be negative")
        
        if "temperature" in properties:
            temp = properties["temperature"]
            if temp < -273.15:  # Absolute zero in Celsius
                issues.append(f"Temperature {temp}°C below absolute zero")
        
        if "pressure" in properties:
            pressure = properties["pressure"]
            if pressure < 0:
                issues.append("Stream pressure cannot be negative")
        
        if "composition" in properties:
            comp = properties["composition"]
            if isinstance(comp, dict):
                total = sum(comp.values())
                if abs(total - 1.0) > 0.01:  # Allow small tolerance
                    issues.append(f"Composition fractions sum to {total}, should be 1.0")
        
        return issues
    
    def validate_connection_compatibility(
        self,
        from_equipment: Dict[str, Any],
        to_equipment: Dict[str, Any],
        connection_type: str = "piping"
    ) -> List[str]:
        """Validate if two equipment items can be connected.
        
        Args:
            from_equipment: Source equipment info
            to_equipment: Target equipment info
            connection_type: Type of connection
            
        Returns:
            List of validation issues
        """
        issues = []
        
        from_type = from_equipment.get("type", "").lower()
        to_type = to_equipment.get("type", "").lower()
        
        # Check for invalid connections
        if connection_type == "piping":
            # Can't connect tank directly to tank without pump
            if from_type == "tank" and to_type == "tank":
                issues.append("Direct tank-to-tank connection requires a pump")
            
            # Instruments typically don't have piping connections to each other
            instrument_types = ["controller", "transmitter", "indicator"]
            if any(t in from_type for t in instrument_types) and \
               any(t in to_type for t in instrument_types):
                issues.append("Instruments should not have direct piping connections")
        
        elif connection_type == "signal":
            # Signal connections should involve at least one instrument
            instrument_types = ["controller", "transmitter", "indicator", "valve"]
            if not any(t in from_type for t in instrument_types) and \
               not any(t in to_type for t in instrument_types):
                issues.append("Signal connections require at least one instrument")
        
        return issues
    
    def validate_control_loop(
        self,
        measured_variable: str,
        controller_type: str,
        manipulated_element: Optional[str] = None
    ) -> List[str]:
        """Validate control loop configuration.
        
        Args:
            measured_variable: Variable being measured (e.g., "level", "flow")
            controller_type: Type of controller (e.g., "LC", "FC")
            manipulated_element: Element being controlled
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Map controller types to expected variables
        controller_variable_map = {
            "FC": "flow",
            "LC": "level",
            "PC": "pressure",
            "TC": "temperature",
        }
        
        expected_variable = controller_variable_map.get(controller_type)
        if expected_variable and measured_variable.lower() != expected_variable:
            issues.append(
                f"{controller_type} controller expects {expected_variable} measurement, "
                f"got {measured_variable}"
            )
        
        # Validate manipulated element
        if manipulated_element:
            if controller_type == "FC" and "valve" not in manipulated_element.lower():
                issues.append("Flow controller typically manipulates a valve")
            elif controller_type == "LC" and "valve" not in manipulated_element.lower() and \
                 "pump" not in manipulated_element.lower():
                issues.append("Level controller typically manipulates a valve or pump")
        
        return issues


class P_IDValidator:
    """Comprehensive P&ID validation."""
    
    def __init__(self):
        """Initialize validator."""
        self.constraints = EngineeringConstraints()
    
    def validate_pid_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete P&ID model.
        
        Args:
            model_data: P&ID model data
            
        Returns:
            Validation results with issues and statistics
        """
        results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Validate equipment
        equipment_list = model_data.get("equipment", [])
        results["statistics"]["equipment_count"] = len(equipment_list)
        
        tag_names = set()
        for equipment in equipment_list:
            tag_name = equipment.get("tag_name", "")
            equipment_type = equipment.get("type", "")
            
            # Check for duplicate tags
            if tag_name in tag_names:
                results["issues"].append(f"Duplicate tag name: {tag_name}")
                results["valid"] = False
            tag_names.add(tag_name)
            
            # Validate tag format
            if not self.constraints.validate_tag_name(equipment_type, tag_name):
                results["warnings"].append(
                    f"Tag {tag_name} does not follow ISA-5.1 convention for {equipment_type}"
                )
            
            # Validate specifications
            specs_issues = self.constraints.validate_equipment_specs(
                equipment_type,
                equipment.get("specifications", {})
            )
            results["warnings"].extend(specs_issues)
        
        # Validate piping
        piping_list = model_data.get("piping", [])
        results["statistics"]["piping_segments"] = len(piping_list)
        
        for segment in piping_list:
            pipe_class = segment.get("pipe_class", "")
            if not self.constraints.validate_pipe_class(pipe_class):
                results["warnings"].append(f"Unknown pipe class: {pipe_class}")
            
            material = segment.get("material", "")
            if material and not self.constraints.validate_material(material):
                results["warnings"].append(f"Unknown material: {material}")
            
            diameter = segment.get("nominal_diameter")
            if diameter and not self.constraints.validate_nominal_diameter(diameter):
                results["warnings"].append(f"Non-standard nominal diameter: {diameter} mm")
        
        # Validate instrumentation
        instruments = model_data.get("instrumentation", [])
        results["statistics"]["instruments"] = len(instruments)
        
        # Check for control loops
        control_loops = model_data.get("control_loops", [])
        results["statistics"]["control_loops"] = len(control_loops)
        
        for loop in control_loops:
            loop_issues = self.constraints.validate_control_loop(
                loop.get("measured_variable", ""),
                loop.get("controller_type", ""),
                loop.get("manipulated_element")
            )
            results["warnings"].extend(loop_issues)
        
        # Set overall validity
        if results["issues"]:
            results["valid"] = False
        
        return results


class FlowsheetValidator:
    """Comprehensive flowsheet validation for BFD/PFD."""
    
    def __init__(self):
        """Initialize validator."""
        self.constraints = EngineeringConstraints()
    
    def validate_flowsheet(self, flowsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete flowsheet.
        
        Args:
            flowsheet_data: Flowsheet data
            
        Returns:
            Validation results with issues and statistics
        """
        results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Validate units
        units = flowsheet_data.get("units", [])
        results["statistics"]["unit_count"] = len(units)
        
        unit_names = set()
        for unit in units:
            unit_name = unit.get("name", "")
            
            # Check for duplicate names
            if unit_name in unit_names:
                results["issues"].append(f"Duplicate unit name: {unit_name}")
                results["valid"] = False
            unit_names.add(unit_name)
        
        # Validate streams
        streams = flowsheet_data.get("streams", [])
        results["statistics"]["stream_count"] = len(streams)
        
        for stream in streams:
            # Validate stream properties
            properties = stream.get("properties", {})
            prop_issues = self.constraints.validate_stream_properties(properties)
            results["warnings"].extend(prop_issues)
            
            # Check connectivity
            from_unit = stream.get("from")
            to_unit = stream.get("to")
            
            if from_unit not in unit_names:
                results["issues"].append(f"Stream references unknown unit: {from_unit}")
                results["valid"] = False
            
            if to_unit not in unit_names:
                results["issues"].append(f"Stream references unknown unit: {to_unit}")
                results["valid"] = False
        
        # Check for orphaned units
        connected_units = set()
        for stream in streams:
            connected_units.add(stream.get("from"))
            connected_units.add(stream.get("to"))
        
        orphaned = unit_names - connected_units
        if orphaned:
            results["warnings"].append(f"Orphaned units with no connections: {orphaned}")
        
        # Set overall validity
        if results["issues"]:
            results["valid"] = False
        
        return results