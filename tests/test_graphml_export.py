"""Test GraphML export functionality with sanitization."""

import pytest
import networkx as nx
from xml.etree import ElementTree as ET

from src.converters.graph_sanitizer import GraphMLSanitizer
from src.converters.graph_converter import UnifiedGraphConverter


class TestGraphMLSanitizer:
    """Test GraphML sanitization functionality."""
    
    def test_sanitize_primitive_attributes(self):
        """Test that primitive attributes pass through unchanged."""
        attrs = {
            "string_attr": "test",
            "int_attr": 42,
            "float_attr": 3.14,
            "bool_attr": True
        }
        
        sanitized = GraphMLSanitizer.sanitize_attributes(attrs)
        
        assert sanitized == attrs
    
    def test_sanitize_none_values(self):
        """Test that None values become empty strings."""
        attrs = {
            "none_attr": None,
            "valid_attr": "test"
        }
        
        sanitized = GraphMLSanitizer.sanitize_attributes(attrs)
        
        assert sanitized["none_attr"] == ""
        assert sanitized["valid_attr"] == "test"
    
    def test_sanitize_dict_attributes(self):
        """Test that dicts are flattened following DEXPI2graphML pattern."""
        attrs = {
            "config": {
                "temperature": 100.0,
                "pressure": 2.5,
                "unit": "celsius"
            }
        }
        
        sanitized = GraphMLSanitizer.sanitize_attributes(attrs)
        
        assert "config_temperature" in sanitized
        assert sanitized["config_temperature"] == 100.0
        assert "config_pressure" in sanitized
        assert sanitized["config_pressure"] == 2.5
        assert "config_unit" in sanitized
        assert sanitized["config_unit"] == "celsius"
    
    def test_sanitize_list_attributes(self):
        """Test that lists are handled properly."""
        # Small list of primitives - should expand
        attrs = {
            "tags": ["he", "col", "signal"]
        }
        
        sanitized = GraphMLSanitizer.sanitize_attributes(attrs)
        
        assert sanitized["tags_count"] == 3
        assert sanitized["tags_0"] == "he"
        assert sanitized["tags_1"] == "col"
        assert sanitized["tags_2"] == "signal"
        
        # Large list - should stringify
        attrs = {
            "values": list(range(20))
        }
        
        sanitized = GraphMLSanitizer.sanitize_attributes(attrs)
        
        assert sanitized["values_count"] == 20
        assert "values_items" in sanitized
        assert "[0, 1, 2" in sanitized["values_items"]
    
    def test_sanitize_complex_objects(self):
        """Test that complex objects are converted to strings."""
        class CustomObject:
            def __str__(self):
                return "CustomObject()"
        
        attrs = {
            "custom": CustomObject()
        }
        
        sanitized = GraphMLSanitizer.sanitize_attributes(attrs)
        
        assert sanitized["custom"] == "CustomObject()"
    
    def test_sanitize_graph_for_export(self):
        """Test complete graph sanitization."""
        # Create a graph with complex attributes
        G = nx.DiGraph()
        G.graph["metadata"] = {"version": 1.0, "type": "P&ID"}
        
        # Add nodes with various attribute types
        G.add_node(1, name="Tank", specs={"volume": 100}, tags=["vessel"])
        G.add_node(2, name="Pump", flow_rate=50.0, connected=None)
        
        # Add edge with attributes
        G.add_edge(1, 2, connection_type="piping", properties={"diameter": 50})
        
        # Sanitize the graph
        clean_graph = GraphMLSanitizer.sanitize_graph_for_export(G)
        
        # Check that all node IDs are strings
        assert all(isinstance(node, str) for node in clean_graph.nodes())
        assert "1" in clean_graph.nodes()
        assert "2" in clean_graph.nodes()
        
        # Check node attributes are sanitized
        node1_attrs = clean_graph.nodes["1"]
        assert node1_attrs["name"] == "Tank"
        assert "specs_volume" in node1_attrs
        assert node1_attrs["specs_volume"] == 100
        assert "tags_0" in node1_attrs
        assert node1_attrs["tags_0"] == "vessel"
        
        node2_attrs = clean_graph.nodes["2"]
        assert node2_attrs["connected"] == ""  # None -> empty string
        
        # Check edge attributes are sanitized
        edge_attrs = clean_graph.edges["1", "2"]
        assert edge_attrs["connection_type"] == "piping"
        assert "properties_diameter" in edge_attrs
        assert edge_attrs["properties_diameter"] == 50


class TestGraphMLExport:
    """Test GraphML export with real graphs."""
    
    @pytest.fixture
    def converter(self):
        """Create a UnifiedGraphConverter instance."""
        return UnifiedGraphConverter()
    
    def test_export_complex_graph(self, converter):
        """Test exporting a graph with complex attributes."""
        # Create a graph that would normally fail GraphML export
        G = nx.DiGraph()
        
        # Add nodes with complex attributes
        G.add_node(
            "TK-001",
            equipment_type="Tank",
            specifications={
                "volume": 100.0,
                "pressure": 2.5,
                "material": "SS316"
            },
            tags=["vessel", "storage"],
            metadata=None
        )
        
        G.add_node(
            "P-001",
            equipment_type="Pump",
            flow_rate=50.0,
            control_signals=["FC-001", "PI-001"],
            status={"running": True, "hours": 1000}
        )
        
        # Add edge with complex attributes
        G.add_edge(
            "TK-001", "P-001",
            connection={
                "type": "piping",
                "line_number": "100-CS-150",
                "diameter": 50
            }
        )
        
        # Export to GraphML (should not raise exception)
        graphml_string = converter.networkx_to_graphml(G)
        
        # Verify it's valid XML
        root = ET.fromstring(graphml_string)
        assert root.tag.endswith("graphml")
        
        # Verify nodes are present
        nodes = root.findall(".//{http://graphml.graphdrawing.org/xmlns}node")
        assert len(nodes) == 2
        
        # Verify edges are present
        edges = root.findall(".//{http://graphml.graphdrawing.org/xmlns}edge")
        assert len(edges) == 1
    
    def test_round_trip_with_sanitization(self, converter):
        """Test that graphs can round-trip through GraphML."""
        # Create original graph
        G = nx.DiGraph()
        G.add_node("A", value=42, tags=["test"])
        G.add_node("B", value=3.14)
        G.add_edge("A", "B", weight=1.5)
        
        # Export to GraphML
        graphml_string = converter.networkx_to_graphml(G)
        
        # Import back
        G2 = converter.graphml_to_networkx(graphml_string)
        
        # Check structure is preserved
        assert G2.number_of_nodes() == 2
        assert G2.number_of_edges() == 1
        assert "A" in G2.nodes()
        assert "B" in G2.nodes()
        assert G2.has_edge("A", "B")
    
    def test_dexpi_class_attributes(self, converter):
        """Test handling of DEXPI-specific attributes."""
        # Simulate a graph from MLGraphLoader
        G = nx.DiGraph()
        
        # Add nodes with dexpi_class attribute (used for MSR filtering)
        G.add_node(
            "TK-001",
            dexpi_class="equipment.Tank",
            tagName="TK-001"
        )
        
        G.add_node(
            "PI-001",
            dexpi_class="instrumentation.ProcessInstrumentationFunction",
            tagName="PI-001",
            instrumentationType="PressureIndicator"
        )
        
        # Export should handle these attributes
        graphml_string = converter.networkx_to_graphml(G)
        
        assert "equipment.Tank" in graphml_string
        assert "ProcessInstrumentationFunction" in graphml_string
        assert "PressureIndicator" in graphml_string
    
    def test_sfiles_tags_handling(self, converter):
        """Test handling of SFILES-specific tags."""
        # Simulate a graph from SFILES2
        G = nx.DiGraph()
        
        # Add nodes
        G.add_node("reactor-1", unit_type="reactor", volume=100.0)
        G.add_node("hex-1", unit_type="heat_exchanger")
        
        # Add edge with SFILES tags
        G.add_edge(
            "reactor-1", "hex-1",
            tags={"he": ["hot_in"], "col": [], "signal": False},
            stream_name="S-001"
        )
        
        # Export should handle these attributes
        graphml_string = converter.networkx_to_graphml(G)
        
        # Check that tags were sanitized properly
        assert "tags_he_0" in graphml_string or "tags_he" in graphml_string
        assert "stream_name" in graphml_string
        assert "S-001" in graphml_string