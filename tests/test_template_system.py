"""Tests for the template system and PFD expansion engine."""

import pytest
import yaml
from pathlib import Path
from src.models.template_system import (
    TemplateLoader, ProcessTemplate, EquipmentSpec, ConnectionSpec,
    validate_template_coverage, ConnectionDSLParser
)
from src.tools.pfd_expansion_engine import (
    PfdExpansionEngine, EquipmentInstance, ConnectionInstance, ExpansionResult
)


class TestTemplateLoader:
    """Test template loading and resolution."""

    def test_load_equipment_library(self):
        """Test that equipment library loads correctly."""
        loader = TemplateLoader()

        # Check that equipment library is loaded
        assert loader.equipment_library is not None
        assert len(loader.equipment_library) > 0

        # Check for key equipment
        assert 'standard_aeration_basin' in loader.equipment_library
        assert 'centrifugal_pump' in loader.equipment_library
        assert 'centrifugal_blower' in loader.equipment_library

    def test_load_components(self):
        """Test that component library loads correctly."""
        loader = TemplateLoader()

        # Check that components are loaded
        assert loader.components is not None

        # Check for key components
        expected_components = ['screening_base', 'mechanical_drive', 'recycle_loop', 'aeration_system']
        for comp in expected_components:
            assert comp in loader.components, f"Component {comp} not found"

    def test_load_registry(self):
        """Test that template registry loads correctly."""
        loader = TemplateLoader()

        # Check that registry is loaded
        assert loader.registry is not None
        assert len(loader.registry) > 0

        # Check for key templates
        assert '230_TK' in loader.registry  # Aeration Tank

    def test_resolve_equipment_ref(self):
        """Test equipment reference resolution."""
        loader = TemplateLoader()

        # Test equipment with $ref
        equipment = {
            '$ref': 'equipment_library.standard_aeration_basin',
            'tag_prefix': 'T'
        }

        resolved = loader._resolve_equipment_ref(equipment)

        # Check that library fields are merged
        assert 'dexpi_class' in resolved
        assert resolved['dexpi_class'] == 'Tank'
        assert 'default_params' in resolved
        assert 'ports' in resolved
        assert resolved['tag_prefix'] == 'T'  # Local override preserved

    def test_parse_connection_dsl(self):
        """Test connection DSL parsing."""
        loader = TemplateLoader()

        dsl = """
        Basin.outlet -> Pump.inlet
        Pump.outlet -> Basin.inlet
        Blower-*.discharge -> AirHeader
        BFD.inlet -> Basin-1.inlet
        """

        connections = loader.parse_connection_dsl(dsl)

        assert len(connections) == 4
        assert connections[0].from_equipment == 'Basin'
        assert connections[0].from_port == 'outlet'
        assert connections[0].to_equipment == 'Pump'
        assert connections[0].to_port == 'inlet'

        # Check wildcard parsing
        assert connections[2].from_equipment == 'Blower-*'
        assert connections[2].to_equipment == 'AirHeader'

    def test_load_aeration_tank_template(self):
        """Test loading the complete Aeration Tank template."""
        loader = TemplateLoader()

        try:
            template = loader.load_template('TK', area_number=230)
        except (ValueError, FileNotFoundError):
            pytest.skip("Aeration Tank template not yet created")

        # Check template structure
        assert template.process_unit_id == 'TK'
        assert template.area_number == 230
        assert template.name == 'Aeration Tank'

        # Check equipment
        assert len(template.per_train_equipment) > 0
        assert len(template.shared_equipment) > 0

        # Check connections parsed from DSL
        assert len(template.connections) > 0


class TestConnectionDSLParser:
    """Test enhanced connection DSL parsing."""

    def test_simple_connections(self):
        """Test parsing simple connections."""
        dsl = "A.out -> B.in"
        connections = ConnectionDSLParser.parse(dsl)

        assert len(connections) == 1
        assert connections[0].from_equipment == 'A'
        assert connections[0].from_port == 'out'
        assert connections[0].to_equipment == 'B'
        assert connections[0].to_port == 'in'

    def test_wildcard_connections(self):
        """Test parsing wildcard connections."""
        dsl = "Pump-* -> Header"
        connections = ConnectionDSLParser.parse(dsl)

        assert len(connections) == 1
        assert connections[0].from_equipment == 'Pump-*'
        assert connections[0].from_port == 'outlet'  # Default port
        assert connections[0].to_equipment == 'Header'

    def test_series_connections(self):
        """Test parsing series connections."""
        dsl = "Tank-*.outlet -> Tank-(*+1).inlet"
        connections = ConnectionDSLParser.parse(dsl)

        assert len(connections) == 1
        assert 'Tank-*' in connections[0].from_equipment
        assert '(*+1)' in connections[0].to_equipment


class TestPfdExpansionEngine:
    """Test PFD expansion engine."""

    def test_engine_initialization(self):
        """Test that expansion engine initializes correctly."""
        engine = PfdExpansionEngine()

        assert engine.loader is not None
        assert engine.dexpi_class_map is not None
        assert 'Tank' in engine.dexpi_class_map
        assert 'CentrifugalPump' in engine.dexpi_class_map

    def test_instantiate_equipment_single(self):
        """Test instantiating a single equipment."""
        engine = PfdExpansionEngine()

        spec = EquipmentSpec(
            id='Basin',
            dexpi_class='Tank',
            tag_prefix='T',
            count=1,
            shared=False,
            default_params={'volume': 1000}
        )

        instances = engine._instantiate_equipment(spec, area_number=230, train_number=1)

        assert len(instances) == 1
        assert instances[0].tag == '230-T-01'
        assert instances[0].dexpi_class == 'Tank'
        assert instances[0].train_number == 1

    def test_instantiate_equipment_multiple(self):
        """Test instantiating multiple equipment."""
        engine = PfdExpansionEngine()

        spec = EquipmentSpec(
            id='Pump',
            dexpi_class='CentrifugalPump',
            tag_prefix='P',
            count=2,
            shared=True,
            default_params={'flow_rate': 100}
        )

        instances = engine._instantiate_equipment(spec, area_number=230)

        assert len(instances) == 2
        assert instances[0].tag == '230-P-01'
        assert instances[1].tag == '230-P-02'
        assert instances[0].train_number is None  # Shared equipment

    def test_expand_equipment_pattern(self):
        """Test equipment pattern expansion."""
        engine = PfdExpansionEngine()

        # Test wildcard expansion
        patterns = engine._expand_equipment_pattern('Basin-*', train_count=3, equipment_map={})
        assert patterns == ['Basin-1', 'Basin-2', 'Basin-3']

        # Test series connection pattern
        patterns = engine._expand_equipment_pattern('Basin-(*+1)', train_count=3, equipment_map={})
        assert patterns == ['Basin-2', 'Basin-3']

        # Test BFD pattern
        patterns = engine._expand_equipment_pattern('BFD.inlet', train_count=3, equipment_map={})
        assert patterns == ['BFD.inlet']

    def test_expand_bfd_block_simple(self):
        """Test simple BFD block expansion."""
        engine = PfdExpansionEngine()

        # Mock simple template by modifying loader
        # For now, just test the structure
        try:
            result = engine.expand_bfd_block(
                bfd_block='230-AerationTank',
                process_unit_id='TK',
                area_number=230,
                train_count=2
            )
        except (ValueError, FileNotFoundError):
            pytest.skip("Template not yet available")

        assert isinstance(result, ExpansionResult)
        assert result.source_bfd_block == '230-AerationTank'
        assert result.expansion_metadata['train_count'] == 2


class TestTemplateCoverage:
    """Test template coverage validation."""

    def test_validate_coverage(self):
        """Test that coverage validation works."""
        # This will fail initially since we don't have all templates
        # Just test that the function runs
        try:
            coverage = validate_template_coverage()

            assert 'total_units' in coverage
            assert 'covered' in coverage
            assert 'missing' in coverage
            assert 'coverage_percentage' in coverage

            # We should have at least the registry entries
            assert coverage['total_units'] > 0
        except FileNotFoundError:
            pytest.skip("Hierarchy file not found")


class TestIntegration:
    """Integration tests for template system."""

    @pytest.mark.asyncio
    async def test_aeration_tank_expansion(self):
        """Test complete Aeration Tank expansion."""
        engine = PfdExpansionEngine()

        try:
            # Expand Aeration Tank with 4 trains
            result = engine.expand_bfd_block(
                bfd_block='230-AerationTank',
                process_unit_id='TK',
                area_number=230,
                train_count=4,
                parameters={'aeration_type': 'fine_bubble'}
            )

            # Check equipment created
            assert len(result.equipment) > 0

            # Should have 4 basins (one per train)
            basins = [eq for eq in result.equipment if 'Basin' in eq.id]
            assert len(basins) == 4

            # Should have shared blowers
            blowers = [eq for eq in result.equipment if 'Blower' in eq.id]
            assert len(blowers) > 0

            # Check connections
            assert len(result.connections) > 0

            # Check metadata
            assert result.expansion_metadata['train_count'] == 4
            assert result.expansion_metadata['area_number'] == 230

        except (ValueError, FileNotFoundError):
            pytest.skip("Aeration Tank template not fully configured")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])