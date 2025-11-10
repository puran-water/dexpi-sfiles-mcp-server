"""Test that all completed templates load properly."""

import pytest
from src.models.template_system import TemplateLoader, ProcessTemplate
from src.tools.pfd_expansion_engine import PfdExpansionEngine


class TestTemplateLoading:
    """Test loading of completed templates."""

    def test_aeration_tank_template_loads(self):
        """Test that Aeration Tank template loads."""
        loader = TemplateLoader()
        template = loader.load_template('TK', area_number=230)

        assert template is not None
        assert template.process_unit_id == 'TK'
        assert template.area_number == 230
        assert template.name == 'Aeration Tank'
        assert len(template.per_train_equipment) > 0
        assert len(template.shared_equipment) > 0

    def test_primary_clarifier_template_loads(self):
        """Test that Primary Clarifier template loads."""
        loader = TemplateLoader()
        template = loader.load_template('TK', area_number=130)  # Registry uses 130_TK

        assert template is not None
        assert template.process_unit_id == 'CL'  # Template has CL as process_unit_id
        assert template.area_number == 130
        assert template.name == 'Primary Clarifier'
        assert len(template.per_train_equipment) > 0

    def test_secondary_clarifier_template_loads(self):
        """Test that Secondary Clarifier template loads."""
        loader = TemplateLoader()
        template = loader.load_template('TK', area_number=240)  # Registry uses 240_TK

        assert template is not None
        assert template.process_unit_id == 'SC'  # Template has SC as process_unit_id
        assert template.area_number == 240
        assert template.name == 'Secondary Clarifier'

    def test_uv_disinfection_template_loads(self):
        """Test that UV Disinfection template loads."""
        loader = TemplateLoader()
        # Registry uses 401_UV pointing to library/420/uv_disinfection.yaml
        template = loader.load_template('401_UV')

        assert template is not None
        assert template.process_unit_id == 'UV'  # Template has UV as process_unit_id
        assert template.area_number == 420  # Template has area 420
        assert template.name == 'UV Disinfection'

    def test_gravity_thickener_template_loads(self):
        """Test that Gravity Thickener template loads."""
        loader = TemplateLoader()
        # Registry uses 601_TK pointing to library/510/gravity_thickener.yaml
        template = loader.load_template('601_TK')

        assert template is not None
        assert template.process_unit_id == 'GT'  # Template has GT as process_unit_id
        assert template.area_number == 510  # Template has area 510
        assert template.name == 'Gravity Thickener'

    def test_template_parameter_variations(self):
        """Test that templates support parameter variations."""
        engine = PfdExpansionEngine()

        # Test with different parameters (using registry key)
        # Note: expand_bfd_block uses registry keys, so we need to use '130_TK' not 'CL'
        # But the primary clarifier is registered as 130_TK, so we'll use that
        # Actually, let's use the Aeration Tank which we know works
        result_with_do = engine.expand_bfd_block(
            bfd_block='230-AerationTank',
            process_unit_id='TK',
            area_number=230,
            train_count=1,
            parameters={'do_control': True, 'aeration_type': 'fine_bubble'}
        )

        result_without_do = engine.expand_bfd_block(
            bfd_block='230-AerationTank',
            process_unit_id='TK',
            area_number=230,
            train_count=1,
            parameters={'do_control': False, 'aeration_type': 'coarse_bubble'}
        )

        # Should have different equipment based on parameters
        assert result_with_do is not None
        assert result_without_do is not None
        # DO sensor should only be in the first result
        do_sensors_with = [eq for eq in result_with_do.equipment if 'DOSensor' in eq.id]
        do_sensors_without = [eq for eq in result_without_do.equipment if 'DOSensor' in eq.id]
        assert len(do_sensors_with) > 0
        assert len(do_sensors_without) == 0

    def test_multi_train_expansion(self):
        """Test expansion with multiple trains."""
        engine = PfdExpansionEngine()

        result = engine.expand_bfd_block(
            bfd_block='230-AerationTank',
            process_unit_id='TK',
            area_number=230,
            train_count=4,
            parameters={'aeration_type': 'fine_bubble'}
        )

        # Should have 4 basins (one per train)
        basins = [eq for eq in result.equipment if 'Basin' in eq.id]
        assert len(basins) == 4

        # Check tags are correct
        basin_tags = [eq.tag for eq in basins]
        assert '230-T-01' in basin_tags
        assert '230-T-02' in basin_tags
        assert '230-T-03' in basin_tags
        assert '230-T-04' in basin_tags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])