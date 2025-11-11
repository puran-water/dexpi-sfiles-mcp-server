# Equipment Catalog

Complete listing of all 159 equipment types available in the Engineering MCP Server.

**Phase 2.2**: All equipment types are now accessible via MCP tools. You can use either:
- **SFILES alias** (lowercase, e.g., `pump`, `boiler`)
- **DEXPI class name** (CamelCase, e.g., `CentrifugalPump`, `Boiler`)

Both forms are accepted interchangeably in all MCP tool calls.

---

## Quick Reference

| Category | Count | Examples |
|----------|-------|----------|
| ROTATING | 41 | pump, compressor, fan, turbine, mixer |
| SEPARATION | 30 | centrifuge, filter, sieve, separator |
| TREATMENT | 30 | dryer, heater, cooler, furnace |
| HEAT_TRANSFER | 18 | heat_exchanger, boiler, condenser |
| STORAGE | 14 | tank, silo, vessel, container |
| TRANSPORT | 11 | conveyor, pump, elevator |
| REACTION | 8 | reactor, chamber, vessel |
| CUSTOM | 7 | custom_equipment, generic types |

**Total: 159 equipment types**

---

## Equipment Types by Category

### ROTATING Equipment (41 types)

Equipment with rotating components (pumps, compressors, fans, mixers, etc.)

#### Pumps (6 types)
- `pump` / `CentrifugalPump` - Centrifugal pump (primary)
- `pump_reciprocating` / `ReciprocatingPump` - Reciprocating piston pump
- `pump_rotary` / `RotaryPump` - Rotary pump
- `pump_ejector` / `EjectorPump` - Ejector/vacuum pump
- `custom_pump` / `CustomPump` - Custom pump type
- `pump_generic` / `Pump` - Generic pump class

#### Compressors (4 types)
- `compressor_centrifugal` / `CentrifugalCompressor` - Centrifugal compressor
- `compressor_axial` / `AxialCompressor` - Axial compressor
- `compressor_reciprocating` / `ReciprocatingCompressor` - Reciprocating compressor
- `compressor_rotary` / `RotaryCompressor` - Rotary compressor

#### Fans & Blowers (8 types)
- `fan_radial` / `RadialFan` - Radial/centrifugal fan
- `fan_axial` / `AxialFan` - Axial fan
- `blower` / `Blower` - Generic blower (primary)
- `blower_centrifugal` / `CentrifugalBlower` - Centrifugal blower
- `blower_axial` / `AxialBlower` - Axial blower
- `custom_blower` / `CustomBlower` - Custom blower type
- `custom_fan` / `CustomFan` - Custom fan type
- `air_ejector` / `AirEjector` - Air ejector

#### Mixers & Agitators (7 types)
- `mixer` / `Mixer` - Generic mixer (primary)
- `mixer_rotary` / `RotaryMixer` - Rotary mixer
- `mixer_static` / `StaticMixer` - Static mixer (no moving parts)
- `agitator` / `Agitator` - Agitator assembly
- `agitator_rotor` / `AgitatorRotor` - Agitator rotor component
- `kneader` / `Kneader` - Kneading mixer
- `custom_mixer` / `CustomMixer` - Custom mixer type

#### Turbines (3 types)
- `turbine_gas` / `GasTurbine` - Gas turbine
- `turbine_steam` / `SteamTurbine` - Steam turbine
- `custom_turbine` / `CustomTurbine` - Custom turbine type

#### Motors & Generators (7 types)
- `motor_ac` / `AlternatingCurrentMotor` - AC motor
- `motor_dc` / `DirectCurrentMotor` - DC motor
- `motor_ac_component` / `AlternatingCurrentMotorAsComponent` - AC motor as component
- `motor_dc_component` / `DirectCurrentMotorAsComponent` - DC motor as component
- `generator_ac` / `AlternatingCurrentGenerator` - AC generator
- `generator_dc` / `DirectCurrentGenerator` - DC generator
- `custom_motor` / `CustomMotor` - Custom motor type

#### Other Rotating Equipment (6 types)
- `combustion_engine` / `CombustionEngine` - Combustion engine
- `combustion_engine_component` / `CombustionEngineAsComponent` - Engine as component
- `custom_electric_generator` / `CustomElectricGenerator` - Custom generator
- `gear_box` / `GearBox` - Gear box/transmission
- `displacer` / `Displacer` - Displacement device
- `mixing_element_assembly` / `MixingElementAssembly` - Mixing element assembly

---

### SEPARATION Equipment (30 types)

Equipment for separating materials (centrifuges, filters, sieves, etc.)

#### Centrifuges (5 types)
- `centrifuge` / `Centrifuge` - Generic centrifuge (primary)
- `centrifuge_filtering` / `FilteringCentrifuge` - Filtering centrifuge
- `centrifuge_filtering_drum` / `FilteringCentrifugeDrum` - Filtering centrifuge drum
- `centrifuge_sedimental` / `SedimentalCentrifuge` - Sedimental centrifuge
- `centrifuge_sedimental_drum` / `SedimentalCentrifugeDrum` - Sedimental centrifuge drum

#### Filters (7 types)
- `filter` / `Filter` - Generic filter (primary)
- `filter_gas` / `GasFilter` - Gas filter
- `filter_liquid` / `LiquidFilter` - Liquid filter
- `filter_unit` / `FilterUnit` - Filter unit/cartridge
- `custom_filter` / `CustomFilter` - Custom filter type

#### Sieves (5 types)
- `sieve` / `Sieve` - Generic sieve (primary)
- `sieve_revolving` / `RevolvingSieve` - Revolving/rotary sieve
- `sieve_stationary` / `StationarySieve` - Stationary sieve
- `sieve_vibrating` / `VibratingSieve` - Vibrating sieve
- `sieve_element` / `SieveElement` - Sieve element/screen

#### Separators (6 types)
- `separator` / `Separator` - Generic separator (primary)
- `separator_gravitational` / `GravitationalSeparator` - Gravity separator
- `separator_mechanical` / `MechanicalSeparator` - Mechanical separator
- `separator_electrical` / `ElectricalSeparator` - Electrical separator
- `separator_scrubbing` / `ScrubbingSeparator` - Scrubbing separator
- `custom_separator` / `CustomSeparator` - Custom separator type

#### Crushers & Grinders (4 types)
- `crusher` / `Crusher` - Crusher assembly
- `crusher_element` / `CrusherElement` - Crusher element
- `grinder` / `Grinder` - Grinder
- `grinding_element` / `GrindingElement` - Grinding element

#### Mills (2 types)
- `mill` / `Mill` - Generic mill (primary)
- `custom_mill` / `CustomMill` - Custom mill type

#### Other Separation Equipment (1 type)
- `custom_centrifuge` / `CustomCentrifuge` - Custom centrifuge type

---

### TREATMENT Equipment (30 types)

Equipment for treating materials (dryers, heaters, coolers, etc.)

#### Dryers (7 types)
- `dryer` / `Dryer` - Generic dryer (primary)
- `dryer_convection` / `ConvectionDryer` - Convection dryer
- `dryer_heated_surface` / `HeatedSurfaceDryer` - Heated surface dryer
- `drying_chamber` / `DryingChamber` - Drying chamber
- `custom_dryer` / `CustomDryer` - Custom dryer type

#### Cooling Equipment (4 types)
- `cooling_tower` / `CoolingTower` - Generic cooling tower (primary)
- `cooling_tower_wet` / `WetCoolingTower` - Wet cooling tower
- `cooling_tower_dry` / `DryCoolingTower` - Dry cooling tower
- `cooling_tower_rotor` / `CoolingTowerRotor` - Cooling tower rotor
- `custom_cooling_tower` / `CustomCoolingTower` - Custom cooling tower
- `spray_cooler` / `SprayCooler` - Spray cooler
- `air_cooling_system` / `AirCoolingSystem` - Air cooling system

#### Furnaces & Burners (3 types)
- `furnace` / `Furnace` - Furnace
- `burner` / `Burner` - Burner

#### Agglomerators (6 types)
- `agglomerator` / `Agglomerator` - Generic agglomerator (primary)
- `agglomerator_rotating_pressure` / `RotatingPressureAgglomerator` - Rotating pressure agglomerator
- `agglomerator_reciprocating_pressure` / `ReciprocatingPressureAgglomerator` - Reciprocating pressure agglomerator
- `agglomerator_rotating_growth` / `RotatingGrowthAgglomerator` - Rotating growth agglomerator
- `pelletizer_disc` / `PelletizerDisc` - Disc pelletizer
- `briquetting_roller` / `BriquettingRoller` - Briquetting roller
- `custom_agglomerator` / `CustomAgglomerator` - Custom agglomerator

#### Extruders (4 types)
- `extruder` / `Extruder` - Generic extruder (primary)
- `extruder_reciprocating` / `ReciprocatingExtruder` - Reciprocating extruder
- `extruder_rotating` / `RotatingExtruder` - Rotating extruder
- `custom_extruder` / `CustomExtruder` - Custom extruder type

#### Other Treatment Equipment (6 types)
- `feeder` / `Feeder` - Feeder
- `weigher` / `Weigher` - Generic weigher (primary)
- `weigher_batch` / `BatchWeigher` - Batch weigher
- `weigher_continuous` / `ContinuousWeigher` - Continuous weigher
- `custom_weigher` / `CustomWeigher` - Custom weigher
- `packaging_system` / `PackagingSystem` - Packaging system

---

### HEAT_TRANSFER Equipment (18 types)

Equipment for heat exchange and generation

#### Heat Exchangers (7 types)
- `heat_exchanger` / `HeatExchanger` - Generic heat exchanger (primary)
- `heat_exchanger_plate` / `PlateHeatExchanger` - Plate heat exchanger
- `heat_exchanger_tubular` / `TubularHeatExchanger` - Shell & tube heat exchanger
- `heat_exchanger_spiral` / `SpiralHeatExchanger` - Spiral heat exchanger
- `tube_bundle` / `TubeBundle` - Heat exchanger tube bundle
- `heat_exchanger_rotor` / `HeatExchangerRotor` - Rotating heat exchanger component
- `custom_heat_exchanger` / `CustomHeatExchanger` - Custom heat exchanger

#### Heaters (3 types)
- `heater` / `Heater` - Generic heater (primary)
- `heater_electric` / `ElectricHeater` - Electric heater
- `custom_heater` / `CustomHeater` - Custom heater type

#### Boilers & Steam Generators (3 types)
- `boiler` / `Boiler` - Boiler
- `steam_generator` / `SteamGenerator` - Steam generator

#### Evaporators (1 type)
- `evaporator_thin_film` / `ThinFilmEvaporator` - Thin film evaporator

#### Spray Equipment (2 types)
- `spray_nozzle` / `SprayNozzle` - Spray nozzle

#### Chimneys & Flares (2 types)
- `chimney` / `Chimney` - Chimney/stack
- `flare` / `Flare` - Flare stack

---

### STORAGE Equipment (14 types)

Equipment for storing materials

#### Tanks (2 types)
- `tank` / `Tank` - Generic tank (primary)

#### Silos (1 type)
- `silo` / `Silo` - Silo

#### Vessels (4 types)
- `vessel` / `Vessel` - Generic vessel (primary)
- `vessel_pressure` / `PressureVessel` - Pressure vessel
- `custom_vessel` / `CustomVessel` - Custom vessel type

#### Columns (6 types)
- `column_process` / `ProcessColumn` - Process/distillation column
- `column_section` / `ColumnSection` - Column section
- `column_section_tagged` / `TaggedColumnSection` - Tagged column section
- `column_section_subtagged` / `SubTaggedColumnSection` - Sub-tagged column section
- `column_internals` / `ColumnInternalsArrangement` - Column internals arrangement
- `column_trays` / `ColumnTraysArrangement` - Column trays arrangement
- `column_packings` / `ColumnPackingsArrangement` - Column packings arrangement

#### Containers (1 type)
- `container_transportable` / `TransportableContainer` - Transportable container

---

### TRANSPORT Equipment (11 types)

Equipment for transporting materials

#### Conveyors (2 types)
- `conveyor` / `Conveyor` - Conveyor system
- `screw` / `Screw` - Screw conveyor

#### Vehicles (5 types)
- `truck` / `Truck` - Truck
- `rail_waggon` / `RailWaggon` - Rail car/wagon
- `ship` / `Ship` - Ship/vessel
- `forklift` / `ForkliftTruck` - Forklift truck

#### Lifts & Systems (4 types)
- `lift` / `Lift` - Lift/elevator
- `loading_unloading_system` / `LoadingUnloadingSystem` - Loading/unloading system
- `mobile_transport_system` / `MobileTransportSystem` - Generic mobile transport
- `custom_mobile_transport_system` / `CustomMobileTransportSystem` - Custom mobile transport
- `stationary_transport_system` / `StationaryTransportSystem` - Generic stationary transport
- `custom_stationary_transport_system` / `CustomStationaryTransportSystem` - Custom stationary transport

---

### REACTION Equipment (8 types)

Equipment for chemical reactions

#### Chambers (2 types)
- `chamber` / `Chamber` - Generic chamber (primary)
- `chamber_owner` / `ChamberOwner` - Chamber owner/container

#### Nozzles (2 types)
- `nozzle` / `Nozzle` - Generic nozzle (primary)
- `nozzle_owner` / `NozzleOwner` - Nozzle owner/container

#### Impellers (1 type)
- `impeller` / `Impeller` - Impeller

#### Waste Gas (2 types)
- `waste_gas_emitter` / `WasteGasEmitter` - Generic waste gas emitter (primary)
- `custom_waste_gas_emitter` / `CustomWasteGasEmitter` - Custom waste gas emitter

#### Other (1 type)
- `tagged_plant_item` / `TaggedPlantItem` - Generic tagged plant item

---

### CUSTOM Equipment (7 types)

Generic/custom equipment types

- `equipment` / `Equipment` - Generic equipment base class
- `custom_equipment` / `CustomEquipment` - Custom equipment type

---

## Usage Examples

### Using SFILES Aliases

```python
# Add equipment using lowercase SFILES aliases
dexpi_add_equipment(
    model_id="model_123",
    equipment_type="pump",  # SFILES alias
    tag_name="P-001"
)

dexpi_add_equipment(
    model_id="model_123",
    equipment_type="heat_exchanger",  # SFILES alias
    tag_name="E-101"
)
```

### Using DEXPI Class Names

```python
# Add equipment using CamelCase DEXPI class names
dexpi_add_equipment(
    model_id="model_123",
    equipment_type="CentrifugalPump",  # DEXPI class name
    tag_name="P-001"
)

dexpi_add_equipment(
    model_id="model_123",
    equipment_type="PlateHeatExchanger",  # DEXPI class name
    tag_name="E-101"
)
```

### Both Forms Are Equivalent

```python
# These two calls create the exact same equipment
dexpi_add_equipment(model_id="m1", equipment_type="pump", tag_name="P-001")
dexpi_add_equipment(model_id="m1", equipment_type="CentrifugalPump", tag_name="P-001")

# These two calls create the exact same equipment
dexpi_add_equipment(model_id="m1", equipment_type="boiler", tag_name="B-001")
dexpi_add_equipment(model_id="m1", equipment_type="Boiler", tag_name="B-001")
```

---

## Family Mappings

Some equipment types belong to families that can be specified using a single alias:

### Pump Family (6 members)
- Alias: `pump` → Primary: `CentrifugalPump`
- Family members: CentrifugalPump, ReciprocatingPump, RotaryPump, EjectorPump, CustomPump, Pump

### Compressor Family (4 members)
- Family members: CentrifugalCompressor, AxialCompressor, ReciprocatingCompressor, RotaryCompressor

### Fan Family (3 members)
- Family members: RadialFan, AxialFan, Fan

### Mixer Family (3 members)
- Alias: `mixer` → Primary: `Mixer`
- Family members: Mixer, RotaryMixer, StaticMixer

---

## Complete Alphabetical Index

All 159 equipment types in alphabetical order by SFILES alias:

```
agglomerator, agglomerator_reciprocating_pressure, agglomerator_rotating_growth,
agglomerator_rotating_pressure, agitator, agitator_rotor, air_cooling_system,
air_ejector, blower, blower_axial, blower_centrifugal, boiler,
briquetting_roller, burner, centrifuge, centrifuge_filtering,
centrifuge_filtering_drum, centrifuge_sedimental, centrifuge_sedimental_drum,
chamber, chamber_owner, chimney, column_internals, column_packings,
column_process, column_section, column_section_subtagged, column_section_tagged,
column_trays, combustion_engine, combustion_engine_component, compressor_axial,
compressor_centrifugal, compressor_reciprocating, compressor_rotary,
container_transportable, conveyor, cooling_tower, cooling_tower_dry,
cooling_tower_rotor, cooling_tower_wet, crusher, crusher_element,
custom_agglomerator, custom_blower, custom_centrifuge, custom_cooling_tower,
custom_dryer, custom_electric_generator, custom_equipment, custom_extruder,
custom_fan, custom_filter, custom_heat_exchanger, custom_heater,
custom_mill, custom_mixer, custom_mobile_transport_system, custom_motor,
custom_pump, custom_separator, custom_stationary_transport_system,
custom_turbine, custom_vessel, custom_waste_gas_emitter, custom_weigher,
displacer, dryer, dryer_convection, dryer_heated_surface, drying_chamber,
equipment, evaporator_thin_film, extruder, extruder_reciprocating,
extruder_rotating, fan_axial, fan_radial, feeder, filter, filter_gas,
filter_liquid, filter_unit, flare, forklift, furnace, gear_box,
generator_ac, generator_dc, grinder, grinding_element, heat_exchanger,
heat_exchanger_plate, heat_exchanger_rotor, heat_exchanger_spiral,
heat_exchanger_tubular, heater, heater_electric, impeller, kneader,
lift, loading_unloading_system, mill, mixer, mixer_rotary, mixer_static,
mixing_element_assembly, mobile_transport_system, motor_ac, motor_ac_component,
motor_dc, motor_dc_component, nozzle, nozzle_owner, packaging_system,
pelletizer_disc, pump, pump_ejector, pump_generic, pump_reciprocating,
pump_rotary, rail_waggon, screw, separator, separator_electrical,
separator_gravitational, separator_mechanical, separator_scrubbing, ship,
sieve, sieve_element, sieve_revolving, sieve_stationary, sieve_vibrating,
silo, spray_cooler, spray_nozzle, stationary_transport_system,
steam_generator, tagged_plant_item, tank, truck, tube_bundle,
turbine_gas, turbine_steam, vessel, vessel_pressure, waste_gas_emitter,
weigher, weigher_batch, weigher_continuous
```

---

**Last Updated**: November 11, 2025
**Phase**: 2.2 Complete - All 159 equipment types accessible
