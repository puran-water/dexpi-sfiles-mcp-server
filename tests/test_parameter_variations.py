"""Test parameter variations in template expansion."""

import pytest
from src.tools.pfd_expansion_engine import PfdExpansionEngine
from src.models.template_system import TemplateLoader


class TestParameterVariations:
    """Test that template parameters work correctly."""

    def test_conditional_equipment_inclusion(self):
        """Test that conditional equipment is included/excluded based on parameters."""
        engine = PfdExpansionEngine()

        # Test the condition evaluation directly
        assert engine._evaluate_condition('${do_control|false}', {'do_control': True}) == True
        assert engine._evaluate_condition('${do_control|false}', {'do_control': False}) == False
        assert engine._evaluate_condition('${do_control|false}', {}) == False  # Uses default

        # Test string boolean values
        assert engine._evaluate_condition('${do_control|true}', {'do_control': 'yes'}) == True
        assert engine._evaluate_condition('${do_control|true}', {'do_control': 'no'}) == False

    def test_parameter_substitution_in_equipment(self):
        """Test that parameters are substituted in equipment default_params."""
        engine = PfdExpansionEngine()

        from src.models.template_system import ProcessTemplate, EquipmentSpec

        # Create template with parameter references
        eq_spec = EquipmentSpec(
            id='Basin',
            dexpi_class='Tank',
            tag_prefix='T',
            default_params={
                'volume': '${basin_volume|1000}',
                'material': 'Concrete'
            }
        )

        template = ProcessTemplate(
            process_unit_id='TK',
            area_number=230,
            name='Test',
            per_train_equipment=[eq_spec]
        )

        # Apply parameters
        modified = engine._apply_template_parameters(
            template,
            {'basin_volume': 2000}
        )

        # Check substitution
        assert modified.per_train_equipment[0].default_params['volume'] == '2000'

    def test_parameter_substitution_in_connections(self):
        """Test that parameters are substituted in connection DSL."""
        engine = PfdExpansionEngine()

        from src.models.template_system import ProcessTemplate, ConnectionSpec

        # Create template with parameter references in connections
        conn_spec = ConnectionSpec(
            from_equipment='${source_unit|Tank}-1',
            from_port='outlet',
            to_equipment='Pump-1',
            to_port='inlet'
        )

        template = ProcessTemplate(
            process_unit_id='TEST',
            area_number=100,
            name='Test',
            connections=[conn_spec]
        )

        # Apply parameters
        modified = engine._apply_template_parameters(
            template,
            {'source_unit': 'Reactor'}
        )

        # Check substitution
        assert modified.connections[0].from_equipment == 'Reactor-1'

    def test_equipment_map_with_multiple_instances(self):
        """Test that equipment map handles multiple instances per train correctly."""
        engine = PfdExpansionEngine()

        from src.models.template_system import EquipmentSpec

        # Create spec with count > 1
        spec = EquipmentSpec(
            id='Mixer',
            dexpi_class='Mixer',
            tag_prefix='MX',
            count=2  # Two mixers per train
        )

        # Instantiate for train 1
        instances = engine._instantiate_equipment(spec, 230, train_number=1)

        # Should create 2 instances with proper tags
        assert len(instances) == 2
        assert instances[0].tag == '230-MX-01.01'  # First mixer in train 1
        assert instances[1].tag == '230-MX-01.02'  # Second mixer in train 1

        # Check IDs for equipment map
        assert instances[0].id == 'Mixer-1-1'
        assert instances[1].id == 'Mixer-1-2'

    def test_comparison_condition_evaluation(self):
        """Test evaluation of comparison conditions."""
        engine = PfdExpansionEngine()

        # Test equality conditions
        assert engine._evaluate_condition(
            "aeration_type == 'fine_bubble'",
            {'aeration_type': 'fine_bubble'}
        ) == True

        assert engine._evaluate_condition(
            "aeration_type == 'fine_bubble'",
            {'aeration_type': 'coarse_bubble'}
        ) == False

        # Test inequality conditions
        assert engine._evaluate_condition(
            "train_count != 1",
            {'train_count': 4}
        ) == True

    def test_component_parameter_substitution(self):
        """Test that component parameters are properly substituted."""
        loader = TemplateLoader()

        # Test the _apply_parameters_to_string method
        text = "Connect ${basin_ref}-* to AirHeader"
        result = loader._apply_parameters_to_string(
            text,
            {'basin_ref': 'Basin'}
        )
        assert result == "Connect Basin-* to AirHeader"

        # Test with default value
        text = "Connect ${basin_ref|Tank}-* to Header"
        result = loader._apply_parameters_to_string(text, {})
        assert result == "Connect Tank-* to Header"

    def test_wildcard_expansion_with_parameters(self):
        """Test that wildcard patterns expand correctly with substituted parameters."""
        engine = PfdExpansionEngine()

        # Test expansion with substituted base name
        patterns = engine._expand_equipment_pattern('Basin-*', train_count=3, equipment_map={})
        assert patterns == ['Basin-1', 'Basin-2', 'Basin-3']

        # Test series connection pattern
        patterns = engine._expand_equipment_pattern('Basin-(*+1)', train_count=3, equipment_map={})
        assert patterns == ['Basin-2', 'Basin-3']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])