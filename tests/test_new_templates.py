"""Test the newly created templates for end-to-end plant modeling."""

import pytest
from src.models.template_system import TemplateLoader
from src.tools.pfd_expansion_engine import PfdExpansionEngine


class TestEndToEndTemplates:
    """Test that we can model a complete wastewater treatment train."""

    def test_screening_template_loads(self):
        """Test Screening template."""
        loader = TemplateLoader()
        template = loader.load_template('BS')  # Coarse screening

        assert template is not None
        assert template.process_unit_id == 'BS'
        assert template.name == 'Screening'
        assert len(template.parameters) == 4  # screen_type, cleaning, config, handling

    def test_grit_removal_template_loads(self):
        """Test Grit Removal template."""
        loader = TemplateLoader()
        template = loader.load_template('GR')

        assert template is not None
        assert template.process_unit_id == 'GR'
        assert template.name == 'Grit Removal'
        assert 'grit_type' in template.parameters

    def test_dual_media_filter_template_loads(self):
        """Test Dual Media Filter template."""
        loader = TemplateLoader()
        template = loader.load_template('DMF')

        assert template is not None
        assert template.process_unit_id == 'DMF'
        assert template.name == 'Dual Media Filter'
        assert 'filter_cells' in template.parameters

    def test_complete_treatment_train_expansion(self):
        """Test that we can expand a complete treatment train."""
        engine = PfdExpansionEngine()

        # Headworks: Screening
        screening_result = engine.expand_bfd_block(
            bfd_block='101-Screening',
            process_unit_id='BS',
            area_number=101,
            train_count=2,
            parameters={'screen_type': 'coarse', 'cleaning_mechanism': 'mechanical_rake'}
        )
        assert screening_result is not None
        assert len([e for e in screening_result.equipment if 'Screen' in e.id]) == 2

        # Headworks: Grit Removal
        grit_result = engine.expand_bfd_block(
            bfd_block='101-GritRemoval',
            process_unit_id='GR',
            area_number=101,
            train_count=2,
            parameters={'grit_type': 'aerated', 'grit_washing': True}
        )
        assert grit_result is not None
        # Should have blowers for aerated type
        blowers = [e for e in grit_result.equipment if 'Blower' in e.id]
        assert len(blowers) > 0

        # Primary Treatment: Already tested (Primary Clarifier)

        # Secondary Treatment: Aeration Tank (already tested)

        # Tertiary Treatment: Filtration
        filter_result = engine.expand_bfd_block(
            bfd_block='310-DualMediaFilter',
            process_unit_id='DMF',
            area_number=310,
            train_count=1,
            parameters={'filter_cells': 4, 'backwash_type': 'air_water'}
        )
        assert filter_result is not None
        # Should have 4 filter cells
        filter_cells = [e for e in filter_result.equipment if 'FilterCell' in e.id]
        assert len(filter_cells) == 4

        # Disinfection: UV (already tested)

        # Solids Handling: Thickening (already tested)

        # Verify we can create a complete plant
        print("\nComplete Wastewater Treatment Train Validated:")
        print(f"  1. Screening: {len(screening_result.equipment)} equipment")
        print(f"  2. Grit Removal: {len(grit_result.equipment)} equipment")
        print(f"  3. Primary Clarifier: (tested separately)")
        print(f"  4. Aeration Tank: (tested separately)")
        print(f"  5. Secondary Clarifier: (tested separately)")
        print(f"  6. Dual Media Filter: {len(filter_result.equipment)} equipment")
        print(f"  7. UV Disinfection: (tested separately)")
        print(f"  8. Gravity Thickener: (tested separately)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])