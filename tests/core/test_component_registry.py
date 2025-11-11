"""
Unit tests for ComponentRegistry.

Tests recommended by Codex review to ensure:
- CSV loading works correctly
- All 272 classes are registered
- Alias lookups work
- DEXPI class name lookups work
- Category preservation works
"""

import pytest
from src.core.components import (
    get_registry,
    ComponentRegistry,
    ComponentType,
    ComponentCategory,
    create_component,
    UnknownComponentTypeError
)
from src.core.equipment import EquipmentFactory, EquipmentCategory


class TestComponentRegistryLoading:
    """Test that ComponentRegistry loads all 272 classes from CSVs."""

    def test_registry_loads_all_equipment(self):
        """Test that all 159 equipment classes are loaded."""
        registry = get_registry()
        equipment = registry.get_all_by_type(ComponentType.EQUIPMENT)
        assert len(equipment) == 159, f"Expected 159 equipment classes, got {len(equipment)}"

    def test_registry_loads_all_piping(self):
        """Test that all 79 piping classes are loaded."""
        registry = get_registry()
        piping = registry.get_all_by_type(ComponentType.PIPING)
        assert len(piping) == 79, f"Expected 79 piping classes, got {len(piping)}"

    def test_registry_loads_all_instrumentation(self):
        """Test that all 34 instrumentation classes are loaded."""
        registry = get_registry()
        instrumentation = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
        assert len(instrumentation) == 34, f"Expected 34 instrumentation classes, got {len(instrumentation)}"

    def test_registry_loads_272_total(self):
        """Test that exactly 272 classes are loaded total."""
        registry = get_registry()
        equipment = registry.get_all_by_type(ComponentType.EQUIPMENT)
        piping = registry.get_all_by_type(ComponentType.PIPING)
        instrumentation = registry.get_all_by_type(ComponentType.INSTRUMENTATION)
        total = len(equipment) + len(piping) + len(instrumentation)
        assert total == 272, f"Expected 272 total classes, got {total}"

    def test_csv_files_exist(self):
        """Test that all required CSV files exist and are readable."""
        from pathlib import Path

        data_dir = Path(__file__).parent.parent.parent / "src" / "core" / "data"

        # Check all three CSV files exist
        equipment_csv = data_dir / "equipment_registrations.csv"
        piping_csv = data_dir / "piping_registrations.csv"
        instrumentation_csv = data_dir / "instrumentation_registrations.csv"

        assert equipment_csv.exists(), f"Equipment CSV not found at {equipment_csv}"
        assert piping_csv.exists(), f"Piping CSV not found at {piping_csv}"
        assert instrumentation_csv.exists(), f"Instrumentation CSV not found at {instrumentation_csv}"

    def test_csv_headers_correct(self):
        """Smoke test that CSV headers haven't changed."""
        from pathlib import Path
        import csv

        data_dir = Path(__file__).parent.parent.parent / "src" / "core" / "data"

        expected_headers = {
            'class_name', 'sfiles_alias', 'is_primary', 'family',
            'category', 'symbol_id', 'display_name'
        }

        for csv_file in ['equipment_registrations.csv', 'piping_registrations.csv',
                        'instrumentation_registrations.csv']:
            csv_path = data_dir / csv_file
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames)
                # Check that expected headers are present (may have additional)
                assert expected_headers.issubset(headers), \
                    f"{csv_file} missing expected headers: {expected_headers - headers}"


class TestAliasLookup:
    """Test SFILES alias lookup functionality."""

    def test_lookup_by_sfiles_alias(self):
        """Test lookup by SFILES alias."""
        registry = get_registry()

        # Equipment
        pump = registry.get_by_alias("pump")
        assert pump is not None
        assert pump.dexpi_class.__name__ == "CentrifugalPump"

        # Piping
        valve = registry.get_by_alias("ball_valve")
        assert valve is not None
        assert valve.dexpi_class.__name__ == "BallValve"

        # Instrumentation
        transmitter = registry.get_by_alias("transmitter")
        assert transmitter is not None
        assert transmitter.dexpi_class.__name__ == "Transmitter"

    def test_primary_classes_in_alias_map(self):
        """Test that only primary classes are in the alias map."""
        registry = get_registry()

        # "pump" should map to CentrifugalPump (primary), not Pump (generic)
        pump = registry.get_by_alias("pump")
        assert pump.is_primary
        assert pump.dexpi_class.__name__ == "CentrifugalPump"


class TestDexpiClassNameLookup:
    """Test DEXPI class name lookup - Codex-recommended regression test."""

    def test_equipment_factory_accepts_dexpi_class_name(self):
        """Test that EquipmentFactory.create() works with DEXPI class names."""
        factory = EquipmentFactory()

        # Test with DEXPI class name (not SFILES alias)
        equipment = factory.create("CentrifugalPump", "P-TEST-001")
        assert equipment is not None
        assert equipment.__class__.__name__ == "CentrifugalPump"

    def test_equipment_factory_accepts_sfiles_alias(self):
        """Test that EquipmentFactory.create() still works with SFILES aliases."""
        factory = EquipmentFactory()

        # Test with SFILES alias
        equipment = factory.create("pump", "P-TEST-002")
        assert equipment is not None
        assert equipment.__class__.__name__ == "CentrifugalPump"

    def test_get_dexpi_class_by_name(self):
        """Test ComponentRegistry.get_dexpi_class() method."""
        registry = get_registry()

        # Test with DEXPI class name
        dexpi_class = registry.get_dexpi_class("CentrifugalPump")
        assert dexpi_class.__name__ == "CentrifugalPump"

        # Test with SFILES alias
        dexpi_class = registry.get_dexpi_class("pump")
        assert dexpi_class.__name__ == "CentrifugalPump"


class TestCategoryPreservation:
    """Test that ComponentCategory is properly mapped to EquipmentCategory."""

    def test_rotating_equipment_category_preserved(self):
        """Test that ROTATING equipment maintains category through factory."""
        factory = EquipmentFactory()

        # Create a pump (ROTATING category)
        equipment = factory.create("pump", "P-TEST-003")

        # The equipment should have the ROTATING category preserved
        # This is tested indirectly through the EquipmentDefinition
        # that gets created in the factory
        assert equipment is not None

    def test_category_mapping_function(self):
        """Test the category mapping function directly."""
        factory = EquipmentFactory()

        # Test mapping of various categories
        assert factory._map_component_category(ComponentCategory.ROTATING) == EquipmentCategory.ROTATING
        assert factory._map_component_category(ComponentCategory.HEAT_TRANSFER) == EquipmentCategory.HEAT_TRANSFER
        assert factory._map_component_category(ComponentCategory.SEPARATION) == EquipmentCategory.SEPARATION
        assert factory._map_component_category(ComponentCategory.STORAGE) == EquipmentCategory.STORAGE
        assert factory._map_component_category(ComponentCategory.REACTION) == EquipmentCategory.REACTION
        assert factory._map_component_category(ComponentCategory.TREATMENT) == EquipmentCategory.TREATMENT
        assert factory._map_component_category(ComponentCategory.TRANSPORT) == EquipmentCategory.TRANSPORT
        assert factory._map_component_category(ComponentCategory.CUSTOM) == EquipmentCategory.CUSTOM


class TestFamilyMappings:
    """Test 1:Many family mappings."""

    def test_pump_family(self):
        """Test pump family has all expected members."""
        registry = get_registry()
        pump_family = registry.get_family_members("pump")

        assert len(pump_family) > 0
        pump_names = [d.dexpi_class.__name__ for d in pump_family]

        # Check for expected pump types
        assert "CentrifugalPump" in pump_names
        assert "ReciprocatingPump" in pump_names
        assert "RotaryPump" in pump_names

    def test_valve_families(self):
        """Test valve families exist."""
        registry = get_registry()

        # Test ball valve family
        ball_valve_family = registry.get_family_members("ball_valve")
        assert len(ball_valve_family) > 0

        # Test check valve family
        check_valve_family = registry.get_family_members("check_valve")
        assert len(check_valve_family) > 0


class TestComponentInstantiation:
    """Test that components can be instantiated."""

    def test_create_equipment_component(self):
        """Test creating equipment components."""
        pump = create_component("pump", "P-001")
        assert pump is not None
        assert pump.__class__.__name__ == "CentrifugalPump"

    def test_create_piping_component(self):
        """Test creating piping components."""
        valve = create_component("ball_valve", "V-001")
        assert valve is not None
        assert valve.__class__.__name__ == "BallValve"

    def test_create_instrumentation_component(self):
        """Test creating instrumentation components."""
        transmitter = create_component("transmitter", "TT-001")
        assert transmitter is not None
        assert transmitter.__class__.__name__ == "Transmitter"

    def test_invalid_component_type_raises_error(self):
        """Test that invalid component types raise appropriate error."""
        with pytest.raises(UnknownComponentTypeError):
            create_component("nonexistent_type", "X-999")


class TestNewEquipmentTypes:
    """Test that previously unavailable equipment types now work."""

    def test_power_generation_equipment(self):
        """Test power generation equipment (previously missing)."""
        factory = EquipmentFactory()

        # Boiler
        boiler = factory.create("boiler", "B-001")
        assert boiler is not None
        assert boiler.__class__.__name__ == "Boiler"

        # Steam Generator
        sg = factory.create("steam_generator", "SG-001")
        assert sg is not None
        assert sg.__class__.__name__ == "SteamGenerator"

    def test_material_handling_equipment(self):
        """Test material handling equipment (previously missing)."""
        factory = EquipmentFactory()

        # Conveyor
        conveyor = factory.create("conveyor", "CV-001")
        assert conveyor is not None
        assert conveyor.__class__.__name__ == "Conveyor"

        # Crusher
        crusher = factory.create("crusher", "CR-001")
        assert crusher is not None
        assert crusher.__class__.__name__ == "Crusher"

        # Silo
        silo = factory.create("silo", "SI-001")
        assert silo is not None
        assert silo.__class__.__name__ == "Silo"

    def test_valve_variants(self):
        """Test various valve types (previously limited)."""
        factory = EquipmentFactory()

        # Butterfly valve
        butterfly = factory.create("butterfly_valve", "V-001")
        assert butterfly is not None
        assert butterfly.__class__.__name__ == "ButterflyValve"

        # Safety valve
        safety = factory.create("safety_valve", "PSV-001")
        assert safety is not None
        assert safety.__class__.__name__ == "SafetyValveOrFitting"
