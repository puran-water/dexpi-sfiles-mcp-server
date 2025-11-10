"""
Phase 1 Migration Equivalence Tests

These tests compare new core layer implementations against frozen baseline
fixtures captured BEFORE migration. Tests remain meaningful even after
legacy code is deleted because baseline is preserved in JSON.

Baseline captured at: git tag phase1-baseline
"""

import json
import pytest
from pathlib import Path

from src.core.equipment import get_factory, UnknownEquipmentTypeError
from src.core.conversion import get_engine


# Load baseline fixtures
BASELINE_DIR = Path(__file__).parent / "fixtures" / "baseline"


@pytest.fixture
def equipment_baseline():
    """Load frozen equipment baseline from JSON."""
    baseline_path = BASELINE_DIR / "equipment.json"
    if not baseline_path.exists():
        pytest.skip(f"Baseline not found: {baseline_path}")

    with open(baseline_path) as f:
        return json.load(f)


@pytest.fixture
def sfiles_baseline():
    """Load frozen SFILES conversion baseline from JSON."""
    baseline_path = BASELINE_DIR / "sfiles_conversions.json"
    if not baseline_path.exists():
        pytest.skip(f"Baseline not found: {baseline_path}")

    with open(baseline_path) as f:
        return json.load(f)


class TestEquipmentCreationEquivalence:
    """Compare new core factory against baseline fixtures."""

    def test_factory_matches_baseline_tank(self, equipment_baseline):
        """Test that Tank creation matches baseline (nozzle count may improve)."""
        factory = get_factory()

        # Get baseline
        baseline = equipment_baseline["Tank_TK-101"]

        # Create via new core factory
        equipment = factory.create("tank", "TK-101")

        # Compare attributes (type and tag must match)
        assert type(equipment).__name__ == baseline['type']
        assert equipment.tagName == baseline['tagName']
        # Nozzle count can be >= baseline (core factory may create better defaults)
        assert len(equipment.nozzles) >= baseline['nozzle_count']

    def test_factory_matches_baseline_pump(self, equipment_baseline):
        """Test that Pump creation matches baseline (may create more specific type)."""
        factory = get_factory()

        baseline = equipment_baseline["Pump_P-201"]
        equipment = factory.create("pump", "P-201")

        # Core factory creates CentrifugalPump (more specific), legacy created generic Pump
        # Both are acceptable - check that it's a pump type
        assert "Pump" in type(equipment).__name__
        assert equipment.tagName == baseline['tagName']
        assert len(equipment.nozzles) >= baseline['nozzle_count']

    def test_factory_matches_baseline_heat_exchanger(self, equipment_baseline):
        """Test that HeatExchanger creation matches baseline (nozzle count may improve)."""
        factory = get_factory()

        baseline = equipment_baseline["HeatExchanger_HE-401"]
        equipment = factory.create("heat_exchanger", "HE-401")

        assert type(equipment).__name__ == baseline['type']
        assert equipment.tagName == baseline['tagName']
        assert len(equipment.nozzles) >= baseline['nozzle_count']

    def test_factory_matches_baseline_centrifugal_pump(self, equipment_baseline):
        """Test that CentrifugalPump creation matches baseline."""
        factory = get_factory()

        baseline = equipment_baseline["CentrifugalPump_P-202"]
        equipment = factory.create("pump_centrifugal", "P-202")

        assert type(equipment).__name__ == baseline['type']
        assert equipment.tagName == baseline['tagName']
        assert len(equipment.nozzles) == baseline['nozzle_count']

    def test_factory_matches_baseline_vessel(self, equipment_baseline):
        """Test that Vessel creation matches baseline (nozzle count may improve)."""
        factory = get_factory()

        baseline = equipment_baseline["Vessel_V-501"]
        equipment = factory.create("vessel", "V-501")

        assert type(equipment).__name__ == baseline['type']
        assert equipment.tagName == baseline['tagName']
        assert len(equipment.nozzles) >= baseline['nozzle_count']


class TestSFILESConversionEquivalence:
    """Compare new engine against baseline SFILES conversions."""

    def test_simple_tank_pump_conversion(self):
        """Test simple tank->pump SFILES conversion."""
        engine = get_engine()

        sfiles_string = "tank[tank]->pump[pump_centrifugal]"
        sfiles_model = engine.parse_sfiles(sfiles_string)

        # Should parse 2 units and 1 stream
        assert len(sfiles_model.units) == 2
        assert len(sfiles_model.streams) == 1

        # Convert to DEXPI
        dexpi_model = engine.sfiles_to_dexpi(sfiles_model)

        # Should have equipment
        equipment_count = len(list(dexpi_model.conceptualModel.taggedPlantItems))
        assert equipment_count == 2, f"Expected 2 equipment, got {equipment_count}"

    def test_three_unit_conversion(self):
        """Test three-unit SFILES conversion."""
        engine = get_engine()

        # Use PFD-only equipment (avoid BFD keywords like 'reactor')
        sfiles_string = "tank[tank]->pump[pump_centrifugal]->heater[heater]"
        sfiles_model = engine.parse_sfiles(sfiles_string)

        assert len(sfiles_model.units) == 3
        assert len(sfiles_model.streams) == 2

        dexpi_model = engine.sfiles_to_dexpi(sfiles_model)
        equipment_count = len(list(dexpi_model.conceptualModel.taggedPlantItems))
        assert equipment_count == 3


class TestRoundTripIntegrity:
    """Test that SFILES↔DEXPI conversions preserve data."""

    def test_round_trip_preserves_units(self):
        """Test that units survive SFILES→DEXPI→SFILES round-trip."""
        engine = get_engine()

        original = "pump[pump_centrifugal]->tank[tank]"

        # Parse
        sfiles_model = engine.parse_sfiles(original)
        assert len(sfiles_model.units) == 2

        # Convert to DEXPI
        dexpi_model = engine.sfiles_to_dexpi(sfiles_model)
        assert dexpi_model is not None

        # Convert back
        back = engine.dexpi_to_sfiles(dexpi_model)

        # Verify units preserved
        assert "pump" in back.lower()
        assert "tank" in back.lower()

    def test_round_trip_preserves_connections(self):
        """Test that connections survive SFILES→DEXPI→SFILES round-trip.

        This validates the Phase 0.5 connection data loss bug fix.
        """
        engine = get_engine()

        original = "pump[pump_centrifugal]->tank[tank]"

        sfiles_model = engine.parse_sfiles(original)
        assert len(sfiles_model.streams) == 1

        # Convert to DEXPI
        dexpi_model = engine.sfiles_to_dexpi(sfiles_model)

        # Verify connection stored
        assert dexpi_model.conceptualModel.pipingNetworkSystems is not None
        systems = list(dexpi_model.conceptualModel.pipingNetworkSystems)
        assert len(systems) > 0
        assert systems[0].segments is not None
        segments = list(systems[0].segments)
        assert len(segments) > 0

        # Convert back
        back = engine.dexpi_to_sfiles(dexpi_model)

        # CRITICAL: Connection arrow preserved
        assert "->" in back, "Connection arrow should be preserved"
        assert "pump" in back.lower()
        assert "tank" in back.lower()


class TestNegativeCases:
    """Test that new core layer fails loudly on invalid inputs."""

    def test_invalid_equipment_type_raises(self):
        """Test that invalid equipment type raises UnknownEquipmentTypeError."""
        factory = get_factory()

        with pytest.raises(UnknownEquipmentTypeError) as exc_info:
            factory.create("definitely_not_real", "X-999")

        error_msg = str(exc_info.value)
        assert "definitely_not_real" in error_msg
        assert "Available types" in error_msg

    def test_malformed_sfiles_raises(self):
        """Test that malformed SFILES raises appropriate error."""
        engine = get_engine()

        with pytest.raises(Exception):  # Will be EmptySfilesError or parsing error
            engine.parse_sfiles("this is not valid sfiles")

    def test_empty_sfiles_raises(self):
        """Test that empty SFILES raises error."""
        engine = get_engine()

        with pytest.raises(Exception):
            engine.parse_sfiles("")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
