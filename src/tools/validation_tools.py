"""Unified validation tools for DEXPI and SFILES models."""

import logging
from typing import Any, Dict, List, Optional
import networkx as nx

from mcp import Tool
from pydexpi.loaders.ml_graph_loader import MLGraphLoader
from ..adapters.sfiles_adapter import get_flowsheet_class

# Safe import with helpful error messages
Flowsheet = get_flowsheet_class()

from ..utils.response import validation_response, create_issue, error_response
from ..validators.constraints import EngineeringConstraints
from ..converters.sfiles_dexpi_mapper import SfilesDexpiMapper

logger = logging.getLogger(__name__)


class ValidationTools:
    """Handles unified validation for both DEXPI and SFILES models."""
    
    def __init__(self, dexpi_store: Dict[str, Any], sfiles_store: Dict[str, Any]):
        """Initialize with references to both model stores.
        
        Args:
            dexpi_store: Dictionary storing DEXPI models
            sfiles_store: Dictionary storing SFILES flowsheets
        """
        self.dexpi_models = dexpi_store
        self.flowsheets = sfiles_store
        self.constraints = EngineeringConstraints()
        self.graph_loader = MLGraphLoader()
        self.mapper = SfilesDexpiMapper()
    
    def get_tools(self) -> List[Tool]:
        """Return all validation tools."""
        return [
            Tool(
                name="validate_model",
                description="Run comprehensive validation on a model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to validate"
                        },
                        "scopes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["syntax", "topology", "isa", "connectivity", "all"]
                            },
                            "description": "Validation scopes to run",
                            "default": ["all"]
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Type of model (auto-detect if not specified)",
                            "default": "auto"
                        }
                    },
                    "required": ["model_id"]
                }
            ),
            Tool(
                name="validate_round_trip",
                description="Validate round-trip conversion integrity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "ID of model to test"
                        },
                        "model_type": {
                            "type": "string",
                            "enum": ["dexpi", "sfiles", "auto"],
                            "description": "Type of model (auto-detect if not specified)",
                            "default": "auto"
                        },
                        "compare_attributes": {
                            "type": "boolean",
                            "description": "Whether to compare attributes in addition to topology",
                            "default": False
                        }
                    },
                    "required": ["model_id"]
                }
            )
        ]
    
    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool call to appropriate handler.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Standardized response
        """
        handlers = {
            "validate_model": self._validate_model,
            "validate_round_trip": self._validate_round_trip
        }
        
        handler = handlers.get(name)
        if not handler:
            return error_response(f"Unknown validation tool: {name}", code="UNKNOWN_TOOL")
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return error_response(str(e), code="TOOL_ERROR")
    
    async def _validate_model(self, args: dict) -> dict:
        """Run comprehensive validation on a model."""
        model_id = args["model_id"]
        scopes = args.get("scopes", ["all"])
        model_type = args.get("model_type", "auto")
        
        # Auto-detect model type
        if model_type == "auto":
            if model_id in self.dexpi_models:
                model_type = "dexpi"
            elif model_id in self.flowsheets:
                model_type = "sfiles"
            else:
                return error_response(f"Model {model_id} not found", code="MODEL_NOT_FOUND")
        
        issues = []
        metrics = {}
        
        # Expand "all" scope
        if "all" in scopes:
            scopes = ["syntax", "topology", "isa", "connectivity"]
        
        if model_type == "dexpi":
            model = self.dexpi_models.get(model_id)
            if not model:
                return error_response(f"DEXPI model {model_id} not found", code="MODEL_NOT_FOUND")
            
            # Run DEXPI validations
            if "syntax" in scopes:
                issues.extend(self._validate_dexpi_syntax(model))
            
            if "topology" in scopes or "connectivity" in scopes:
                graph = self.graph_loader.dexpi_to_graph(model)
                
                if "topology" in scopes:
                    issues.extend(self._validate_graph_topology(graph, "dexpi"))
                    metrics.update(self._get_graph_metrics(graph))
                
                if "connectivity" in scopes:
                    issues.extend(self._validate_connectivity(graph))
            
            if "isa" in scopes:
                issues.extend(self._validate_isa_tags(model, "dexpi"))
        
        else:  # sfiles
            flowsheet = self.flowsheets.get(model_id)
            if not flowsheet:
                return error_response(f"SFILES flowsheet {model_id} not found", code="MODEL_NOT_FOUND")
            
            # Run SFILES validations
            if "syntax" in scopes:
                issues.extend(self._validate_sfiles_syntax(flowsheet))
            
            if "topology" in scopes or "connectivity" in scopes:
                graph = flowsheet.state
                
                if "topology" in scopes:
                    issues.extend(self._validate_graph_topology(graph, "sfiles"))
                    metrics.update(self._get_graph_metrics(graph))
                
                if "connectivity" in scopes:
                    issues.extend(self._validate_connectivity(graph))
            
            if "isa" in scopes:
                issues.extend(self._validate_isa_tags(flowsheet, "sfiles"))
        
        # Determine overall status
        error_count = sum(1 for i in issues if i["severity"] == "error")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        
        if error_count > 0:
            status = "error"
        elif warning_count > 0:
            status = "warning"
        else:
            status = "ok"
        
        metrics["issue_counts"] = {
            "errors": error_count,
            "warnings": warning_count,
            "total": len(issues)
        }
        
        return validation_response(status, issues, metrics)
    
    async def _validate_round_trip(self, args: dict) -> dict:
        """Validate round-trip conversion integrity."""
        model_id = args["model_id"]
        model_type = args.get("model_type", "auto")
        compare_attributes = args.get("compare_attributes", False)
        
        # Auto-detect model type
        if model_type == "auto":
            if model_id in self.dexpi_models:
                model_type = "dexpi"
            elif model_id in self.flowsheets:
                model_type = "sfiles"
            else:
                return error_response(f"Model {model_id} not found", code="MODEL_NOT_FOUND")
        
        issues = []
        metrics = {}
        
        try:
            if model_type == "dexpi":
                # DEXPI -> SFILES -> DEXPI
                original_model = self.dexpi_models[model_id]
                
                # Convert to SFILES
                intermediate_flowsheet = self.mapper.dexpi_to_sfiles(original_model)
                
                # Convert back to DEXPI
                roundtrip_model = self.mapper.sfiles_to_dexpi(intermediate_flowsheet)
                
                # Compare models
                issues.extend(self._compare_dexpi_models(
                    original_model, 
                    roundtrip_model,
                    compare_attributes
                ))
                
                # Add metrics
                metrics["original_equipment_count"] = len(
                    original_model.conceptualModel.taggedPlantItems
                ) if original_model.conceptualModel else 0
                metrics["roundtrip_equipment_count"] = len(
                    roundtrip_model.conceptualModel.taggedPlantItems
                ) if roundtrip_model.conceptualModel else 0
                
            else:  # sfiles
                # SFILES -> DEXPI -> SFILES
                original_flowsheet = self.flowsheets[model_id]
                
                # Convert to DEXPI
                intermediate_model = self.mapper.sfiles_to_dexpi(original_flowsheet)
                
                # Convert back to SFILES
                roundtrip_flowsheet = self.mapper.dexpi_to_sfiles(intermediate_model)
                
                # Compare flowsheets
                issues.extend(self._compare_flowsheets(
                    original_flowsheet,
                    roundtrip_flowsheet,
                    compare_attributes
                ))
                
                # Add metrics
                metrics["original_node_count"] = original_flowsheet.state.number_of_nodes()
                metrics["roundtrip_node_count"] = roundtrip_flowsheet.state.number_of_nodes()
                metrics["original_edge_count"] = original_flowsheet.state.number_of_edges()
                metrics["roundtrip_edge_count"] = roundtrip_flowsheet.state.number_of_edges()
            
            # Check for control type preservation
            if model_type == "sfiles":
                issues.extend(self._check_control_preservation(
                    original_flowsheet,
                    roundtrip_flowsheet
                ))
            
        except Exception as e:
            return error_response(f"Round-trip validation failed: {str(e)}", code="ROUNDTRIP_ERROR")
        
        # Determine status
        error_count = sum(1 for i in issues if i["severity"] == "error")
        if error_count > 0:
            status = "error"
        elif len(issues) > 0:
            status = "warning"
        else:
            status = "ok"
            issues.append(create_issue(
                "info",
                "Round-trip conversion successful with full fidelity"
            ))
        
        metrics["round_trip_fidelity"] = error_count == 0
        
        return validation_response(status, issues, metrics)
    
    def _validate_dexpi_syntax(self, model: Any) -> List[Dict]:
        """Validate DEXPI model syntax."""
        issues = []
        
        # Check for required elements
        if not model.conceptualModel:
            issues.append(create_issue(
                "error",
                "Missing conceptualModel",
                code="DEXPI-SYN-001"
            ))
        
        # Check equipment
        if model.conceptualModel and model.conceptualModel.taggedPlantItems:
            for equipment in model.conceptualModel.taggedPlantItems:
                if not hasattr(equipment, 'tagName') or not equipment.tagName:
                    issues.append(create_issue(
                        "error",
                        f"Equipment missing tagName",
                        location=str(equipment),
                        code="DEXPI-SYN-002"
                    ))
        
        return issues
    
    def _validate_sfiles_syntax(self, flowsheet: Flowsheet) -> List[Dict]:
        """Validate SFILES flowsheet syntax."""
        issues = []
        
        # Try to convert to SFILES string
        try:
            flowsheet.convert_to_sfiles(version="v2", canonical=True)
            if not flowsheet.sfiles:
                issues.append(create_issue(
                    "error",
                    "Failed to generate SFILES string",
                    code="SFILES-SYN-001"
                ))
        except Exception as e:
            issues.append(create_issue(
                "error",
                f"SFILES conversion error: {str(e)}",
                code="SFILES-SYN-002"
            ))
        
        return issues
    
    def _validate_graph_topology(self, graph: nx.DiGraph, model_type: str) -> List[Dict]:
        """Validate graph topology."""
        issues = []
        
        # Check for disconnected components
        if not nx.is_weakly_connected(graph):
            num_components = nx.number_weakly_connected_components(graph)
            issues.append(create_issue(
                "warning",
                f"Graph has {num_components} disconnected components",
                code=f"{model_type.upper()}-TOP-001"
            ))
        
        # Check for isolated nodes
        isolated = list(nx.isolates(graph))
        if isolated:
            for node in isolated:
                issues.append(create_issue(
                    "warning",
                    f"Isolated node: {node}",
                    location=node,
                    code=f"{model_type.upper()}-TOP-002"
                ))
        
        # Check for cycles (may be valid for recycles)
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                issues.append(create_issue(
                    "info",
                    f"Graph contains {len(cycles)} cycle(s) (may be valid recycles)",
                    code=f"{model_type.upper()}-TOP-003",
                    details={"cycle_count": len(cycles)}
                ))
        
        return issues
    
    def _validate_connectivity(self, graph: nx.DiGraph) -> List[Dict]:
        """Validate equipment connectivity."""
        issues = []
        
        # Check for dangling streams (nodes with only one connection)
        for node in graph.nodes():
            in_degree = graph.in_degree(node)
            out_degree = graph.out_degree(node)
            total_degree = in_degree + out_degree
            
            if total_degree == 1:
                # Check if it's a valid terminal node
                node_str = str(node).lower()
                if not any(term in node_str for term in ['raw', 'feed', 'prod', 'vent', 'waste']):
                    issues.append(create_issue(
                        "warning",
                        f"Node {node} has only one connection",
                        location=node,
                        code="CONN-001"
                    ))
        
        return issues
    
    def _validate_isa_tags(self, model: Any, model_type: str) -> List[Dict]:
        """Validate ISA-5.1 tag compliance."""
        issues = []
        
        if model_type == "dexpi":
            if model.conceptualModel and model.conceptualModel.taggedPlantItems:
                for equipment in model.conceptualModel.taggedPlantItems:
                    tag = getattr(equipment, 'tagName', '')
                    # Try to determine equipment type from class name
                    equipment_type = equipment.__class__.__name__.lower()
                    if tag and not self.constraints.validate_tag_name(equipment_type, tag):
                        issues.append(create_issue(
                            "warning",
                            f"Tag {tag} does not follow ISA-5.1 convention for {equipment_type}",
                            location=tag,
                            code="ISA-001"
                        ))
        
        return issues
    
    def _get_graph_metrics(self, graph: nx.DiGraph) -> Dict:
        """Get graph topology metrics."""
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "is_connected": nx.is_weakly_connected(graph),
            "has_cycles": not nx.is_directed_acyclic_graph(graph),
            "components": nx.number_weakly_connected_components(graph)
        }
    
    def _compare_dexpi_models(self, original: Any, roundtrip: Any, compare_attributes: bool) -> List[Dict]:
        """Compare two DEXPI models."""
        issues = []
        
        # Compare equipment counts
        orig_count = len(original.conceptualModel.taggedPlantItems) if original.conceptualModel else 0
        rt_count = len(roundtrip.conceptualModel.taggedPlantItems) if roundtrip.conceptualModel else 0
        
        if orig_count != rt_count:
            issues.append(create_issue(
                "error",
                f"Equipment count mismatch: {orig_count} vs {rt_count}",
                code="RT-DEXPI-001"
            ))
        
        # TODO: Add detailed comparison if needed
        
        return issues
    
    def _compare_flowsheets(self, original: Flowsheet, roundtrip: Flowsheet, compare_attributes: bool) -> List[Dict]:
        """Compare two SFILES flowsheets."""
        issues = []
        
        # Compare node counts
        if original.state.number_of_nodes() != roundtrip.state.number_of_nodes():
            issues.append(create_issue(
                "error",
                f"Node count mismatch: {original.state.number_of_nodes()} vs {roundtrip.state.number_of_nodes()}",
                code="RT-SFILES-001"
            ))
        
        # Compare edge counts
        if original.state.number_of_edges() != roundtrip.state.number_of_edges():
            issues.append(create_issue(
                "warning",
                f"Edge count mismatch: {original.state.number_of_edges()} vs {roundtrip.state.number_of_edges()}",
                code="RT-SFILES-002"
            ))
        
        return issues
    
    def _check_control_preservation(self, original: Flowsheet, roundtrip: Flowsheet) -> List[Dict]:
        """Check if control types are preserved in round-trip."""
        issues = []
        
        # Get control nodes from both graphs
        orig_controls = {}
        rt_controls = {}
        
        for node, data in original.state.nodes(data=True):
            if data.get('unit_type') == 'Control' or 'control_type' in data:
                orig_controls[node] = data.get('control_type', 'Unknown')
        
        for node, data in roundtrip.state.nodes(data=True):
            if data.get('unit_type') == 'Control' or 'control_type' in data:
                rt_controls[node] = data.get('control_type', 'Unknown')
        
        # Compare control types
        for node, orig_type in orig_controls.items():
            if node in rt_controls:
                rt_type = rt_controls[node]
                if orig_type != rt_type:
                    issues.append(create_issue(
                        "error",
                        f"Control type changed for {node}: {orig_type} -> {rt_type}",
                        location=node,
                        code="RT-CONTROL-001"
                    ))
            else:
                issues.append(create_issue(
                    "error",
                    f"Control {node} lost in round-trip",
                    location=node,
                    code="RT-CONTROL-002"
                ))
        
        return issues