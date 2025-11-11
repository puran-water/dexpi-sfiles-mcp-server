# Equipment Coverage Analysis

**Date**: November 11, 2025
**Issue**: Critical coverage gap discovered during Week 2 (model_service.py removal)

## Executive Summary

The engineering-mcp-server currently supports **19 out of 159 pyDEXPI equipment classes (12% coverage)**. This prevents users from creating P&IDs with 140 standard equipment types including power generation, material handling, and specialized process equipment.

## Current State

### Registered Equipment (19 classes)

| SFILES Type | DEXPI Class | Category | Symbol |
|-------------|-------------|----------|---------|
| agitator | Agitator | REACTION | PE006A |
| blower | Blower | ROTATING | PA002A |
| centrifuge | Centrifuge | SEPARATION | PE030A |
| compressor | Compressor | ROTATING | PA001A |
| dryer | Dryer | TREATMENT | PD001A |
| fan | Fan | ROTATING | PA003A |
| filter | Filter | SEPARATION | PS014A |
| furnace | Furnace | HEAT_TRANSFER | PE007A |
| heat_exchanger | HeatExchanger | HEAT_TRANSFER | PE037A |
| heater | Heater | HEAT_TRANSFER | PE001A |
| mixer | Mixer | REACTION | PE005A |
| pump | CentrifugalPump | ROTATING | PP001A |
| column | ProcessColumn | SEPARATION | PE004A |
| separator | Separator | SEPARATION | PE012A |
| tank | Tank | STORAGE | PE025A |
| turbine | Turbine | ROTATING | PT011A |
| vessel | Vessel | STORAGE | PT002A |
| custom | CustomEquipment | CUSTOM | - |
| - | Pump | ROTATING | - |

**Total: 19 unique DEXPI classes**

### Missing Equipment (140 classes)

Critical gaps by category:

#### Power Generation (8 missing)
- Boiler
- SteamGenerator
- SteamTurbine
- GasTurbine
- AlternatingCurrentGenerator
- DirectCurrentGenerator
- CombustionEngine
- ElectricGenerator

#### Material Handling (15 missing)
- Conveyor
- Crusher
- Extruder
- Mill
- Grinder
- Screw
- Feeder
- Lift
- ForkliftTruck
- Truck
- Ship
- RailWaggon
- LoadingUnloadingSystem
- PackagingSystem
- TransportableContainer

#### Specialized Processing (20 missing)
- Kneader
- Agglomerator
- Pelletizer
- Briquetting equipment
- Sieve (multiple types)
- Weigher (multiple types)
- CoolingTower (multiple types)
- Column internals (multiple types)
- MixingElementAssembly
- And 10+ more...

#### Heat Transfer Variants (10 missing)
- PlateHeatExchanger
- SpiralHeatExchanger
- TubularHeatExchanger
- CustomHeatExchanger
- ElectricHeater
- CustomHeater
- HeatedSurfaceDryer
- SprayCooler
- ConvectionDryer
- ThinFilmEvaporator

#### Separation Equipment (15 missing)
- GravitationalSeparator
- MechanicalSeparator
- ElectricalSeparator
- ScrubbingSeparator
- FilteringCentrifuge
- SedimentalCentrifuge
- GasFilter
- LiquidFilter
- CustomFilter
- CustomSeparator
- CustomCentrifuge
- FilterUnit
- Displacer
- And more...

#### Pumps & Compressors (12 missing)
- ReciprocatingPump
- RotaryPump
- EjectorPump
- CustomPump
- AxialCompressor
- ReciprocatingCompressor
- RotaryCompressor
- CentrifugalCompressor
- CustomCompressor
- AirEjector
- And more...

#### Other Equipment (60+ missing)
- Various motors (AC, DC, as components)
- Burners and flames
- Waste gas emitters
- Storage types (Silo, Chamber, PressureVessel)
- Nozzles and spray systems
- Gearboxes and rotors
- Transport systems
- And many more...

## Impact Assessment

### User Impact
Users **cannot** create P&IDs for:
1. **Power plants**: No SteamGenerator, SteamTurbine, Boiler, GasTurbine
2. **Material handling**: No Conveyor, Crusher, Mill, Extruder systems
3. **Wastewater treatment**: Limited clarification/separation options
4. **Bulk solids**: No Silo, PackagingSystem, Weigher systems
5. **Specialized processes**: No Kneader, Agglomerator, Pelletizer
6. **HVAC**: Limited CoolingTower variants

### Symbol Utilization Impact
Current symbol coverage: **308/805 (38%)**

Many unused symbols likely correspond to missing equipment types:
- 497 symbols without equipment = potential coverage if types registered
- Hypothesis: Registering 140 missing equipment types could enable 200-300 additional symbols

### API Completeness
The MCP tool `dexpi_add_equipment` advertises "159 equipment types" but only accepts 24 SFILES shortcuts. This is misleading and violates user expectations of DEXPI standard compliance.

## Root Cause Analysis

### Why Only 12% Coverage?

1. **SFILES-Centric Design**
   - System was designed around SFILES notation (simple shortcuts)
   - Only imported equipment needed for common SFILES diagrams
   - pyDEXPI full catalog was not considered

2. **Import Limitations**
   - `src/core/equipment.py:31-64` imports only 24 classes
   - No mechanism for dynamic imports or on-demand loading
   - Hard-coded import list maintained manually

3. **Registration Overhead**
   - Each equipment type requires:
     - EquipmentDefinition entry (~10 lines)
     - Symbol mapping lookup
     - Nozzle defaults configuration
     - Category assignment
   - Registering 159 types = ~1600 lines of code (seemed prohibitive)

4. **No Fail-Fast Enforcement**
   - No test enforcing "all pyDEXPI classes must be registered"
   - Gap went unnoticed until Week 2 investigation
   - No automated validation of coverage percentage

## Proposed Solution

### Strategy: Phased Registration

**Phase 1: High-Priority Equipment (Target: 50 types, 31% coverage)**
Focus on commonly used industrial equipment:
- Power generation (Boiler, SteamGenerator, SteamTurbine, GasTurbine)
- Material handling (Conveyor, Crusher, Mill, Extruder, Screw, Silo)
- Heat transfer variants (PlateHeatExchanger, TubularHeatExchanger)
- Pump/compressor variants (ReciprocatingPump, RotaryPump)
- Separation equipment (GravitationalSeparator, FilteringCentrifuge)

**Phase 2: Process-Specific Equipment (Target: 80 types, 50% coverage)**
Add specialized process equipment:
- Wastewater treatment (CoolingTower variants, clarifiers)
- Bulk solids (Weigher types, PackagingSystem, Feeder)
- Mixing/agglomeration (Kneader, Agglomerator, Pelletizer)
- Drying equipment (HeatedSurfaceDryer, ConvectionDryer)

**Phase 3: Complete Catalog (Target: 159 types, 100% coverage)**
Fill remaining gaps:
- Motors and drives (AC/DC, as components)
- Nozzles and spray systems
- Transport vehicles (Ship, Truck, RailWaggon)
- Column internals and accessories
- All Custom* variants

### Implementation Approach

**Option A: Manual Registration** (Recommended for Phase 1)
```python
# Import all 159 classes
from pydexpi.dexpi_classes.equipment import *

# Register each with proper metadata
self._register(EquipmentDefinition(
    sfiles_type="steam_generator",
    dexpi_class=SteamGenerator,
    bfd_type="steam_generation",
    category=EquipmentCategory.HEAT_TRANSFER,
    display_name="Steam Generator",
    symbol_id="PE_BOILER_001",  # From NOAKADEXPI
    nozzle_count_default=4
))
```

**Option B: Automated Registration** (For Phases 2-3)
```python
# Use introspection to auto-register all equipment classes
import inspect
from pydexpi.dexpi_classes import equipment

for name, obj in inspect.getmembers(equipment, inspect.isclass):
    if issubclass(obj, Equipment) and obj != Equipment:
        self._auto_register(name, obj)
```

### Symbol Mapping Strategy

1. **Phase 1**: Manual symbol lookup from NOAKADEXPI catalog (308 known symbols)
2. **Phase 2**: Assign placeholder symbols for missing equipment (e.g., "PE_XXX")
3. **Phase 3**: Request/create additional symbols from upstream GraphicBuilder

### Testing Strategy

```python
# tests/core/test_equipment_coverage.py

def test_all_pydexpi_classes_registered():
    """Verify all 159 pyDEXPI equipment classes are registered."""
    from pydexpi.dexpi_classes import equipment
    import inspect

    # Get all equipment classes from pyDEXPI
    pydexpi_classes = [
        obj for name, obj in inspect.getmembers(equipment, inspect.isclass)
        if issubclass(obj, Equipment) and obj != Equipment
    ]

    # Get registered classes
    registry = get_registry()
    registered = set(d.dexpi_class for d in registry._definitions.values())

    # Assert 100% coverage
    missing = set(pydexpi_classes) - registered
    assert len(missing) == 0, f"Missing classes: {[c.__name__ for c in missing]}"

def test_equipment_creation():
    """Test that all registered equipment can be instantiated."""
    factory = get_equipment_factory()

    for equip_type in get_registry().list_all_types():
        equipment = factory.create(equip_type, tag=f"TEST-{equip_type.upper()}")
        assert equipment is not None
        assert equipment.tagName.startswith("TEST-")
```

## Timeline & Effort

### Phase 1: High-Priority Equipment (50 types)
- **Effort**: 6-8 hours
- **Tasks**:
  - Import 50 additional classes
  - Register with proper symbols and defaults
  - Add 20 test cases
  - Update MCP tool enum
- **Outcome**: 31% coverage, major equipment gaps filled

### Phase 2: Process-Specific Equipment (30 types)
- **Effort**: 4-6 hours
- **Tasks**:
  - Import 30 additional classes
  - Register with placeholders where symbols missing
  - Add 15 test cases
- **Outcome**: 50% coverage, most industrial processes supported

### Phase 3: Complete Catalog (79 types)
- **Effort**: 4-6 hours (using automation)
- **Tasks**:
  - Auto-register remaining classes
  - Assign placeholder symbols
  - Comprehensive test suite
- **Outcome**: 100% coverage, full DEXPI compliance

**Total Effort**: 14-20 hours over 3 phases

## Success Criteria

1. **Coverage Metrics**
   - Phase 1: ≥50 equipment types (31%)
   - Phase 2: ≥80 equipment types (50%)
   - Phase 3: 159 equipment types (100%)

2. **Symbol Mapping**
   - Phase 1: ≥80% of registered types have real symbols
   - Phase 2: ≥60% have real symbols (some placeholders)
   - Phase 3: 100% have symbols (placeholders acceptable)

3. **Testing**
   - All registered types can be instantiated
   - MCP tool accepts all registered type names
   - No regression in existing tests

4. **Documentation**
   - Complete equipment catalog with categories
   - Symbol reference guide
   - Migration guide for users

## Recommendation

**Proceed with Phase 1 immediately** (6-8 hours):
1. Register 50 high-priority equipment types
2. Map to available symbols from NOAKADEXPI catalog
3. Update MCP tool to accept new types
4. Add automated coverage test to prevent regression

**Schedule Phases 2-3** for Week 3 or later based on priority.

## Open Questions

1. Should we use DEXPI class names (e.g., "SteamGenerator") or SFILES shortcuts (e.g., "steam_generator") as primary keys?
   - **Recommendation**: Support both - DEXPI name as canonical, SFILES shortcut as alias

2. How to handle equipment without symbols in NOAKADEXPI catalog?
   - **Recommendation**: Assign placeholder "PE_CUSTOM_nnn" and document for future symbol creation

3. Should we auto-generate SFILES shortcuts for all types?
   - **Recommendation**: Yes, using simple snake_case conversion (e.g., "SteamGenerator" → "steam_generator")

4. What about Custom* variant classes (CustomPump, CustomHeater, etc.)?
   - **Recommendation**: Register them but prefer specific types where available
