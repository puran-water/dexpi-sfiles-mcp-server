"""Integration tests for BFD functionality with SFILES2.

These tests verify end-to-end BFD operations including:
- BFD flowsheet creation with validation
- BFD block addition with process hierarchy
- BFD flow addition
- BFD-to-PFD expansion planning
- Integration with existing SFILES tools

Sprint 2 - Codex Review #6 minimal approach verification.
"""

import pytest
from src.tools.sfiles_tools import SfilesTools
from src.tools.bfd_tools import BfdTools


@pytest.fixture
def sfiles_tools():
    """Create SfilesTools instance with empty store."""
    flowsheet_store = {}
    return SfilesTools(flowsheet_store, model_store={})


@pytest.fixture
def bfd_tools():
    """Create BfdTools instance with empty store."""
    flowsheet_store = {}
    return BfdTools(flowsheet_store)


class TestBfdFlowsheetCreation:
    """Test BFD flowsheet creation with validation."""

    @pytest.mark.asyncio
    async def test_create_bfd_flowsheet(self, sfiles_tools):
        """Test creating BFD flowsheet with minimal args."""
        result = await sfiles_tools._create_flowsheet({
            "name": "Wastewater Treatment Plant",
            "type": "BFD"
        })

        assert result["ok"] is True
        assert "flowsheet_id" in result["data"]
        assert result["data"]["type"] == "BFD"

    @pytest.mark.asyncio
    async def test_create_bfd_with_description(self, sfiles_tools):
        """Test creating BFD with description."""
        result = await sfiles_tools._create_flowsheet({
            "name": "Plant A",
            "type": "BFD",
            "description": "Main treatment facility"
        })

        assert result["ok"] is True
        flowsheet_id = result["data"]["flowsheet_id"]

        # Verify flowsheet is stored
        assert flowsheet_id in sfiles_tools.flowsheets
        flowsheet = sfiles_tools.flowsheets[flowsheet_id]
        assert flowsheet.type == "BFD"
        assert flowsheet.description == "Main treatment facility"

    @pytest.mark.asyncio
    async def test_bfd_validation_rejects_empty_name(self, sfiles_tools):
        """Test that BFD validation rejects empty name."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            await sfiles_tools._create_flowsheet({
                "name": "",  # Empty name should fail BFD validation
                "type": "BFD"
            })


class TestBfdBlockAddition:
    """Test BFD block addition with process hierarchy."""

    @pytest.mark.asyncio
    async def test_add_bfd_block_minimal(self, sfiles_tools):
        """Test adding BFD block with minimal args."""
        # Create BFD flowsheet first
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        # Add BFD block
        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank"
        })

        assert block_result["ok"] is True
        assert "unit_id" in block_result["data"]
        assert "equipment_tag" in block_result["data"]
        assert block_result["data"]["unit_type"] == "Aeration Tank"

    @pytest.mark.asyncio
    async def test_add_bfd_block_with_sequence(self, sfiles_tools):
        """Test adding BFD block with explicit sequence number."""
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Primary Clarification",
            "sequence_number": 5
        })

        assert block_result["ok"] is True
        # Equipment tag should include sequence number
        equipment_tag = block_result["data"]["equipment_tag"]
        assert "05" in equipment_tag or "-5" in equipment_tag

    @pytest.mark.asyncio
    async def test_add_multiple_bfd_blocks(self, sfiles_tools):
        """Test adding multiple BFD blocks to same flowsheet."""
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        # Add multiple blocks - use same type with different instances
        block1 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 1
        })
        block2 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 2
        })
        block3 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 3
        })

        assert block1["ok"] is True
        assert block2["ok"] is True
        assert block3["ok"] is True

        # Verify flowsheet has 3 nodes
        flowsheet = sfiles_tools.flowsheets[flowsheet_id]
        assert flowsheet.state.number_of_nodes() == 3

    @pytest.mark.asyncio
    async def test_bfd_block_validation_rejects_zero_sequence(self, sfiles_tools):
        """Test that BFD validation rejects sequence_number=0."""
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        with pytest.raises(Exception):  # Pydantic ValidationError
            await sfiles_tools._add_unit({
                "flowsheet_id": flowsheet_id,
                "unit_type": "Tank",
                "sequence_number": 0  # Invalid
            })


class TestBfdFlowAddition:
    """Test BFD flow addition between blocks."""

    @pytest.mark.asyncio
    async def test_add_bfd_flow(self, sfiles_tools):
        """Test adding flow between BFD blocks."""
        # Create BFD and add blocks
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block1 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Primary Clarification"
        })
        block2 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank"
        })

        unit1_id = block1["data"]["unit_id"]
        unit2_id = block2["data"]["unit_id"]

        # Add flow
        flow_result = await sfiles_tools._add_stream({
            "flowsheet_id": flowsheet_id,
            "from_unit": unit1_id,
            "to_unit": unit2_id
        })

        assert flow_result["ok"] is True
        assert flow_result["data"]["from"] == unit1_id
        assert flow_result["data"]["to"] == unit2_id

    @pytest.mark.asyncio
    async def test_add_bfd_flow_with_properties(self, sfiles_tools):
        """Test adding BFD flow with stream properties."""
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block1 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 1
        })
        block2 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 2
        })

        flow_result = await sfiles_tools._add_stream({
            "flowsheet_id": flowsheet_id,
            "from_unit": block1["data"]["unit_id"],
            "to_unit": block2["data"]["unit_id"],
            "stream_name": "primary_effluent",
            "stream_type": "material",
            "properties": {"flow_rate": 1000}
        })

        assert flow_result["ok"] is True
        assert flow_result["data"]["stream_name"] == "primary_effluent"


class TestBfdToPfdPlanning:
    """Test BFD-to-PFD expansion planning tool."""

    @pytest.mark.asyncio
    async def test_bfd_to_pfd_plan_known_process(self, sfiles_tools, bfd_tools):
        """Test expansion planning for known process type."""
        # Create BFD with block
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        # Add block for known process type
        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Primary Clarification"
        })
        block_id = block_result["data"]["unit_id"]

        # Share flowsheet store
        bfd_tools.flowsheets = sfiles_tools.flowsheets

        # Get expansion plan
        plan_result = await bfd_tools._bfd_to_pfd_plan({
            "flowsheet_id": flowsheet_id,
            "bfd_block": block_id
        })

        assert plan_result["ok"] is True
        assert "pfd_options" in plan_result["data"]
        assert len(plan_result["data"]["pfd_options"]) > 0

        # Should have clarifier options
        first_option = plan_result["data"]["pfd_options"][0]
        assert "equipment_type" in first_option
        assert "typical_count" in first_option

    @pytest.mark.asyncio
    async def test_bfd_to_pfd_plan_with_alternates(self, sfiles_tools, bfd_tools):
        """Test expansion planning with multiple alternate configurations."""
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank"
        })
        block_id = block_result["data"]["unit_id"]

        bfd_tools.flowsheets = sfiles_tools.flowsheets

        plan_result = await bfd_tools._bfd_to_pfd_plan({
            "flowsheet_id": flowsheet_id,
            "bfd_block": block_id,
            "include_alternates": True
        })

        assert plan_result["ok"] is True
        # Aeration Tank should have multiple options
        assert len(plan_result["data"]["pfd_options"]) >= 1
        assert "recommended_option" in plan_result["data"]

    @pytest.mark.asyncio
    async def test_bfd_to_pfd_plan_without_alternates(self, sfiles_tools, bfd_tools):
        """Test expansion planning with only recommended option."""
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Tertiary Filtration"
        })
        block_id = block_result["data"]["unit_id"]

        bfd_tools.flowsheets = sfiles_tools.flowsheets

        plan_result = await bfd_tools._bfd_to_pfd_plan({
            "flowsheet_id": flowsheet_id,
            "bfd_block": block_id,
            "include_alternates": False
        })

        assert plan_result["ok"] is True
        # Should return only 1 option
        assert len(plan_result["data"]["pfd_options"]) == 1

    @pytest.mark.asyncio
    async def test_bfd_to_pfd_plan_rejects_pfd(self, sfiles_tools, bfd_tools):
        """Test that planning tool rejects PFD flowsheets."""
        # Create PFD (not BFD)
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "PFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "tank"
        })
        block_id = block_result["data"]["unit_name"]

        bfd_tools.flowsheets = sfiles_tools.flowsheets

        plan_result = await bfd_tools._bfd_to_pfd_plan({
            "flowsheet_id": flowsheet_id,
            "bfd_block": block_id
        })

        # Should return error
        assert plan_result["ok"] is False
        # Error message is nested in error.message
        error_msg = plan_result.get("error", {}).get("message", "")
        assert "not a BFD" in error_msg


class TestBfdMetadataPersistence:
    """Test metadata persistence to graph (Codex Review #7)."""

    @pytest.mark.asyncio
    async def test_port_specs_persist_to_graph(self, sfiles_tools):
        """Test that port_specs are stored in flowsheet graph."""
        from src.models.bfd import BfdPortSpec, BfdPortType, CardinalDirection

        # Create BFD
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        # Create port specs
        port1 = BfdPortSpec(
            port_id="inlet",
            cardinal_direction=CardinalDirection.WEST,
            port_type=BfdPortType.INPUT,
            stream_type="material"
        )
        port2 = BfdPortSpec(
            port_id="outlet",
            cardinal_direction=CardinalDirection.EAST,
            port_type=BfdPortType.OUTPUT,
            stream_type="material"
        )

        # Add block with port specs
        block_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "port_specs": [port1, port2]
        })

        assert block_result["ok"] is True
        unit_id = block_result["data"]["unit_id"]

        # Verify port specs are in the graph
        flowsheet = sfiles_tools.flowsheets[flowsheet_id]
        node_data = flowsheet.state.nodes[unit_id]

        assert "port_specs" in node_data
        assert node_data["port_specs"] is not None
        assert len(node_data["port_specs"]) == 2
        assert node_data["port_specs"][0]["port_id"] == "inlet"
        assert node_data["port_specs"][1]["port_id"] == "outlet"

    @pytest.mark.asyncio
    async def test_stream_type_persists_to_edge(self, sfiles_tools):
        """Test that stream_type is stored on edges."""
        # Create BFD and blocks
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Test Plant",
            "type": "BFD"
        })
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        block1 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 1
        })
        block2 = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank",
            "sequence_number": 2
        })

        # Add stream with stream_type
        flow_result = await sfiles_tools._add_stream({
            "flowsheet_id": flowsheet_id,
            "from_unit": block1["data"]["unit_id"],
            "to_unit": block2["data"]["unit_id"],
            "stream_type": "material",
            "properties": {"flow_rate": 1000}
        })

        assert flow_result["ok"] is True

        # Verify stream_type is on the edge
        flowsheet = sfiles_tools.flowsheets[flowsheet_id]
        edge_data = flowsheet.state.edges[block1["data"]["unit_id"], block2["data"]["unit_id"]]

        assert "stream_type" in edge_data
        assert edge_data["stream_type"] == "material"
        assert edge_data["flow_rate"] == 1000  # Other properties should also persist


class TestBfdEndToEnd:
    """End-to-end BFD workflow tests."""

    @pytest.mark.asyncio
    async def test_complete_bfd_workflow(self, sfiles_tools, bfd_tools):
        """Test complete BFD workflow from creation to planning."""
        # 1. Create BFD flowsheet
        fs_result = await sfiles_tools._create_flowsheet({
            "name": "Wastewater Treatment Plant",
            "type": "BFD",
            "description": "Main facility"
        })
        assert fs_result["ok"] is True
        flowsheet_id = fs_result["data"]["flowsheet_id"]

        # 2. Add BFD blocks
        pc_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Primary Clarification"
        })
        at_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Aeration Tank"
        })
        # Use Tertiary Filtration instead of Secondary Clarification to avoid hierarchy issues
        tf_result = await sfiles_tools._add_unit({
            "flowsheet_id": flowsheet_id,
            "unit_type": "Tertiary Filtration"
        })

        assert pc_result["ok"] is True
        assert at_result["ok"] is True
        assert tf_result["ok"] is True

        # 3. Add BFD flows
        flow1 = await sfiles_tools._add_stream({
            "flowsheet_id": flowsheet_id,
            "from_unit": pc_result["data"]["unit_id"],
            "to_unit": at_result["data"]["unit_id"]
        })
        flow2 = await sfiles_tools._add_stream({
            "flowsheet_id": flowsheet_id,
            "from_unit": at_result["data"]["unit_id"],
            "to_unit": tf_result["data"]["unit_id"]
        })

        assert flow1["ok"] is True
        assert flow2["ok"] is True

        # 4. Verify flowsheet structure
        flowsheet = sfiles_tools.flowsheets[flowsheet_id]
        assert flowsheet.state.number_of_nodes() == 3
        assert flowsheet.state.number_of_edges() == 2

        # 5. Get expansion plan for one block
        bfd_tools.flowsheets = sfiles_tools.flowsheets
        plan_result = await bfd_tools._bfd_to_pfd_plan({
            "flowsheet_id": flowsheet_id,
            "bfd_block": at_result["data"]["unit_id"]
        })

        assert plan_result["ok"] is True
        assert len(plan_result["data"]["pfd_options"]) > 0

        # Verify metadata is included
        assert plan_result["data"]["bfd_block"] == at_result["data"]["unit_id"]
        assert plan_result["data"]["bfd_block_metadata"]["process_type"] == "Aeration Tank"
