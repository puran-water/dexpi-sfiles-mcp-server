"""Basic tests for engineering MCP server components."""

import pytest
import json
from unittest.mock import MagicMock

from src.tools.dexpi_tools import DexpiTools
from src.tools.sfiles_tools import SfilesTools
from src.converters.graph_converter import UnifiedGraphConverter
from src.validators.constraints import EngineeringConstraints
# Note: LLM generator module removed - functionality moved to batch tools


class TestDexpiTools:
    """Test DEXPI tools functionality."""
    
    @pytest.fixture
    def dexpi_tools(self):
        """Create DEXPI tools instance."""
        model_store = {}
        return DexpiTools(model_store)
    
    @pytest.mark.asyncio
    async def test_create_pid(self, dexpi_tools):
        """Test P&ID creation."""
        args = {
            "project_name": "Test Project",
            "drawing_number": "PID-001",
            "revision": "A",
            "description": "Test P&ID"
        }
        
        result = await dexpi_tools._create_pid(args)
        
        assert result["status"] == "success"
        assert "model_id" in result
        assert result["project_name"] == "Test Project"
        assert result["drawing_number"] == "PID-001"
    
    @pytest.mark.asyncio
    async def test_add_equipment(self, dexpi_tools):
        """Test adding equipment to P&ID."""
        # First create a P&ID
        create_args = {
            "project_name": "Test",
            "drawing_number": "PID-001"
        }
        create_result = await dexpi_tools._create_pid(create_args)
        model_id = create_result["model_id"]
        
        # Add equipment
        equipment_args = {
            "model_id": model_id,
            "equipment_type": "Tank",
            "tag_name": "TK-101",
            "specifications": {"volume": 100.0}
        }
        
        result = await dexpi_tools._add_equipment(equipment_args)
        
        assert result["status"] == "success"
        assert result["equipment_type"] == "Tank"
        assert result["tag_name"] == "TK-101"


class TestSfilesTools:
    """Test SFILES tools functionality."""
    
    @pytest.fixture
    def sfiles_tools(self):
        """Create SFILES tools instance."""
        flowsheet_store = {}
        return SfilesTools(flowsheet_store)
    
    @pytest.mark.asyncio
    async def test_create_flowsheet(self, sfiles_tools):
        """Test flowsheet creation."""
        args = {
            "name": "Test Flowsheet",
            "type": "PFD",
            "description": "Test PFD"
        }
        
        result = await sfiles_tools._create_flowsheet(args)
        
        assert result["status"] == "success"
        assert "flowsheet_id" in result
        assert result["name"] == "Test Flowsheet"
        assert result["type"] == "PFD"
    
    @pytest.mark.asyncio
    async def test_add_unit(self, sfiles_tools):
        """Test adding unit to flowsheet."""
        # First create a flowsheet
        create_args = {"name": "Test"}
        create_result = await sfiles_tools._create_flowsheet(create_args)
        flowsheet_id = create_result["flowsheet_id"]
        
        # Add unit
        unit_args = {
            "flowsheet_id": flowsheet_id,
            "unit_name": "reactor-1",
            "unit_type": "reactor",
            "parameters": {"volume": 50.0}
        }
        
        result = await sfiles_tools._add_unit(unit_args)
        
        assert result["status"] == "success"
        assert result["unit_name"] == "reactor-1"
        assert result["unit_type"] == "reactor"


class TestEngineeringConstraints:
    """Test engineering constraints validation."""
    
    @pytest.fixture
    def constraints(self):
        """Create constraints validator."""
        return EngineeringConstraints()
    
    def test_validate_tag_name(self, constraints):
        """Test tag name validation."""
        # Valid tags
        assert constraints.validate_tag_name("pump", "P-001")
        assert constraints.validate_tag_name("pump", "P-001A")
        assert constraints.validate_tag_name("tank", "TK-001")
        assert constraints.validate_tag_name("valve", "V-123")
        
        # Invalid tags
        assert not constraints.validate_tag_name("pump", "PUMP-001")
        assert not constraints.validate_tag_name("pump", "P001")
        assert not constraints.validate_tag_name("tank", "T-001")
    
    def test_validate_pipe_class(self, constraints):
        """Test pipe class validation."""
        assert constraints.validate_pipe_class("CS150")
        assert constraints.validate_pipe_class("SS300")
        assert not constraints.validate_pipe_class("INVALID")
    
    def test_validate_material(self, constraints):
        """Test material validation."""
        assert constraints.validate_material("Carbon Steel")
        assert constraints.validate_material("Stainless Steel 316")
        assert not constraints.validate_material("Unknown Material")
    
    def test_validate_nominal_diameter(self, constraints):
        """Test nominal diameter validation."""
        assert constraints.validate_nominal_diameter(50)
        assert constraints.validate_nominal_diameter(100)
        assert not constraints.validate_nominal_diameter(75)  # Non-standard
    
    def test_validate_equipment_specs(self, constraints):
        """Test equipment specification validation."""
        # Valid tank specs
        tank_specs = {"volume": 100.0, "pressure": 1.0}
        issues = constraints.validate_equipment_specs("tank", tank_specs)
        assert len(issues) == 0
        
        # Invalid tank specs
        tank_specs_invalid = {"volume": 20000, "pressure": -1}
        issues = constraints.validate_equipment_specs("tank", tank_specs_invalid)
        assert len(issues) == 2
        
        # Valid pump specs
        pump_specs = {"flow_rate": 50.0, "head": 30.0}
        issues = constraints.validate_equipment_specs("pump", pump_specs)
        assert len(issues) == 0
        
        # Invalid pump specs
        pump_specs_invalid = {"flow_rate": -10, "head": 0}
        issues = constraints.validate_equipment_specs("pump", pump_specs_invalid)
        assert len(issues) == 2


class TestGraphConverter:
    """Test graph converter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create graph converter."""
        return UnifiedGraphConverter()
    
    def test_networkx_to_graphml(self, converter):
        """Test NetworkX to GraphML conversion."""
        import networkx as nx
        
        # Create simple graph
        graph = nx.DiGraph()
        graph.add_node("A", type="tank")
        graph.add_node("B", type="pump")
        graph.add_edge("A", "B", type="piping")
        
        # Convert to GraphML
        graphml = converter.networkx_to_graphml(graph)
        
        assert isinstance(graphml, str)
        assert "<graphml" in graphml
        assert "<node" in graphml
        assert "<edge" in graphml
    
    def test_extract_topology_summary(self, converter):
        """Test topology summary extraction."""
        import networkx as nx
        
        # Create graph
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D")])
        
        # Extract summary
        summary = converter.extract_topology_summary(graph)
        
        assert summary["num_nodes"] == 4
        assert summary["num_edges"] == 3
        assert summary["is_directed"] == True
        assert summary["is_acyclic"] == True


class TestLLMPlanValidator:
    """Test LLM plan validation."""
    
    def test_validate_valid_plan(self):
        """Test validation of valid plan."""
        plan = create_example_llm_plan()
        issues = LLMPlanValidator.validate_plan(plan)
        assert len(issues) == 0
    
    def test_validate_invalid_plan(self):
        """Test validation of invalid plan."""
        # Missing initial_pattern
        plan = {"steps": []}
        issues = LLMPlanValidator.validate_plan(plan)
        assert "Missing 'initial_pattern' in plan" in issues
        
        # Missing steps
        plan = {"initial_pattern": {"type": "tank"}}
        issues = LLMPlanValidator.validate_plan(plan)
        assert "Missing 'steps' in plan" in issues
        
        # Invalid step
        plan = {
            "initial_pattern": {"type": "tank"},
            "steps": [{"invalid": "step"}]
        }
        issues = LLMPlanValidator.validate_plan(plan)
        assert any("missing 'type'" in issue for issue in issues)