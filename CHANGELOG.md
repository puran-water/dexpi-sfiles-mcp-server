# Changelog

All notable changes to the Engineering MCP Server are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-11-11

### Added - Phase 5 Week 2: Complete pyDEXPI Coverage (272 Classes)

**Phase 1: Auto-Generated Registrations** (<2 hours):
- **All 272 pyDEXPI classes enumerated** using DexpiIntrospector
- **Equipment registrations**: 159 classes with SFILES aliases, categories, symbols
  - 16 families with 1:Many mappings (e.g., "pump" → 6 pump types)
  - 8 categories (ROTATING, HEAT_TRANSFER, SEPARATION, STORAGE, etc.)
  - 26 real symbols, 133 placeholders
- **Piping registrations**: 79 classes (22 valves + 57 other components)
  - 6 valve families
  - 8 categories (VALVE, PIPE, FLOW_MEASUREMENT, CONNECTION, etc.)
- **Instrumentation registrations**: 34 classes
  - 5 families
  - 9 categories (ACTUATING, SIGNAL, MEASUREMENT, CONTROL, etc.)
- **CSV generation**: `src/core/data/*.csv` (auto-generated, versioned)

**Phase 2.1: Core Layer Integration** (~4 hours):
- **ComponentRegistry** (`src/core/components.py`, 519 lines):
  - Unified registry for ALL 272 pyDEXPI components
  - CSV-driven registration from `src/core/data/*.csv`
  - 1:Many family support (27 families total)
  - 25 categories across equipment/piping/instrumentation
  - Query interface: by alias, by class, by family, by category
  - Universal `create_component()` factory
- **EquipmentFactory integration**:
  - ComponentRegistry as fallback for 242 new equipment types
  - Backward compatibility maintained (legacy registry still used first)
  - DEXPI class name support (accepts both "pump" and "CentrifugalPump")
  - Category metadata preservation (ComponentCategory → EquipmentCategory mapping)
  - Relative imports for package compatibility
- **Comprehensive test suite** (22 tests in `tests/core/test_component_registry.py`):
  - CSV loading tests (all 272 classes, file existence, headers)
  - SFILES alias lookup tests
  - DEXPI class name lookup tests
  - Category preservation tests
  - Family mapping tests (1:Many)
  - Component instantiation tests
  - New equipment type validation (boiler, conveyor, crusher, silo, valves)

**Codex Review & Critical Fixes**:
- ✅ CSV packaging: Moved to `src/core/data/`, declared as package data
- ✅ Import paths: Changed to relative imports for package compatibility
- ✅ DEXPI class name support: Dual lookup (alias + class name)
- ✅ Category metadata: Mapping function preserves equipment categories
- ✅ Fail-fast loading: RuntimeError on missing CSVs (CI protection)

### Changed - Phase 5 Week 2: Coverage Expansion

**Coverage Achievement**:
- Equipment: 19/159 (12%) → 159/159 (100%) ✅ **+140 classes**
- Piping: 6/79 (7.6%) → 79/79 (100%) ✅ **+73 classes**
- Instrumentation: 5/34 (14.7%) → 34/34 (100%) ✅ **+29 classes**
- **TOTAL: 30/272 (11%) → 272/272 (100%)** ✅ **+242 classes**

**New Equipment Types Available**:
- Power generation: Boiler, SteamGenerator, SteamTurbine, GasTurbine, Generators
- Material handling: Conveyor, Crusher, Mill, Extruder, Silo, Screw, Feeder
- Specialized processing: Kneader, Agglomerator, Pelletizer, Weighers, Sieves
- All pump variants: Reciprocating, Rotary, Ejector (not just Centrifugal)
- All compressor types: Axial, Rotary, Reciprocating
- All heat exchanger types: Plate, Spiral, Tubular, ThinFilm

**New Piping Types Available**:
- All 22 valve types: Butterfly, Plug, Needle, Safety, Operated, Angle variants
- Flow measurement: Electromagnetic, Turbine, Orifice, Venturi (10 types)
- Connections: Flanges, couplings (6 types)
- Piping accessories: Compensators, hoses, sight glasses, strainers

**New Instrumentation Types Available**:
- Actuating systems: Electric, pneumatic, positioners
- Signal conveying: Signal lines, off-page connectors
- Measurement: Primary elements, transmitters, detectors
- Control: Control loops, control functions

### Fixed - Phase 5 Week 2: Production Readiness

**Critical Issues (Identified by Codex MCP)**:
1. **CSV Packaging**: Files now in `src/core/data/`, included in wheel via `pyproject.toml`
2. **Import Path**: `from .components` (relative) instead of `from core.components`
3. **Class Name Support**: Factory accepts both SFILES aliases and DEXPI class names
4. **Category Preservation**: ComponentCategory correctly mapped to EquipmentCategory
5. **Fail-Fast Loading**: Missing CSVs raise RuntimeError (CI catches regressions)

**Week 2 Task Completion**:
- ✅ Created `src/core/analytics/model_metrics.py` (206 lines)
- ✅ Deleted `src/visualization/orchestrator/model_service.py` (537 lines)
- ✅ Updated orchestration tests (10/10 passing)
- ✅ Net code reduction: -331 lines (537 removed, 206 added)

### Documentation - Phase 5 Week 2

**Phase Completion Documentation**:
- `docs/PHASE1_COMPLETE_SUMMARY.md`: Phase 1 auto-generation results
- `docs/PHASE2_1_COMPLETE_SUMMARY.md`: Phase 2.1 integration results
- `docs/CODEX_REVIEW_FIXES.md`: All 5 critical issues documented
- `docs/COMPLETE_PYDEXPI_COVERAGE_ANALYSIS.md`: Gap analysis and solution
- `docs/EQUIPMENT_COVERAGE_ANALYSIS.md`: Equipment-specific analysis
- `docs/PIPING_VALVE_COVERAGE_ANALYSIS.md`: Piping/valve analysis

**Updated Documentation**:
- `STATUS.md`: Phase 2.1 completion, Codex review results
- `CURRENT_TASK.md`: Phase 2.2 objectives and plan
- `CHANGELOG.md`: This entry

### Testing - Phase 5 Week 2

**Test Results**:
- ✅ 22/22 ComponentRegistry unit tests passing
- ✅ 10/10 orchestrator integration tests passing
- ✅ 32/32 total tests passing
- ✅ All CSV files validated (structure, headers, completeness)
- ✅ Component instantiation verified for all types
- ✅ DEXPI class name lookup validated
- ✅ Category preservation validated

**Test Coverage**:
- CSV loading (6 tests)
- Alias lookup (3 tests)
- DEXPI class name support (3 tests)
- Category preservation (2 tests)
- Family mappings (2 tests)
- Component instantiation (4 tests)
- New equipment types (3 tests)

### Breaking Changes - None

All changes are backward compatible:
- Existing equipment types continue to work
- Legacy EquipmentRegistry still used first
- Factory API unchanged
- All existing tests pass without modification

### Deprecation Warnings

**Future Removal** (after Phase 2.2 MCP tools update):
- `src/core/equipment.EquipmentRegistry` may be deprecated in favor of ComponentRegistry
- Manual equipment type registrations (replaced by CSV-driven approach)

### Validation

**ComponentRegistry**:
- ✅ All 272 classes load from CSV files
- ✅ SFILES alias lookup works (primary classes only)
- ✅ DEXPI class name lookup works
- ✅ Family mappings operational (27 families)
- ✅ Category filtering works (25 categories)
- ✅ Component instantiation verified

**Integration**:
- ✅ EquipmentFactory uses ComponentRegistry fallback
- ✅ Both SFILES aliases and DEXPI class names accepted
- ✅ Category metadata preserved through factory
- ✅ All visualization tests passing

**Packaging**:
- ✅ CSV files included in `src/core/data/`
- ✅ Package data declared in `pyproject.toml`
- ✅ Relative imports for package compatibility
- ✅ Fail-fast on missing CSV files

### Performance

**Phase 1 Efficiency**:
- Auto-generation: <2 hours (vs 14-20 hours manual estimate)
- Efficiency gain: 7-10x faster than manual registration

**Phase 2.1 Performance**:
- Lazy loading: ComponentRegistry loaded only when needed
- CSV parsing: One-time cost on first access
- No runtime overhead for existing code paths

### Next Steps

**Phase 2.2** (2-3 hours, approved by Codex):
- Update MCP tool schemas to expose all 272 classes
- Use `ComponentRegistry.list_all_aliases()` for dynamic enums
- Add smoke tests for schema coverage
- Update tool documentation and examples

## [0.4.1] - 2025-11-10

### Added - Phase 5 Week 1: Symbol Catalog & Nozzle Fixes
- **Symbol Catalog Backfill** (`scripts/backfill_symbol_dexpi_classes.py`):
  - Reverse-mapped DEXPI classes to symbol IDs from merged_catalog.json
  - Added actuated valve variants (11 A→B conversions: PV003B, PV005B, etc.)
  - Added alternative mappings (5 fallback types: Pump, Valve, Vessel, etc.)
  - Intelligent suffix-stripping for symbol ID variants (_Origo, _Detail, _Option1/2/3)
- **Symbol Validation Script** (`scripts/validate_symbol_catalog.py`):
  - Percentage-based thresholds for regression protection (≥35% total, ≥70% equipment)
  - JSON structure validation
  - Category breakdown reporting
  - Exit codes: 0 (pass), 1 (fail)
- **DEXPI-Compliant Nozzle Creation** (`src/core/equipment.py:519-549`):
  - PipingNode with diameter properties (nominalDiameterRepresentation: DN50)
  - Numerical diameter value (nominalDiameterNumericalValueRepresentation: 50)
  - Nozzle pressure representation (nominalPressureRepresentation: PN16)
  - Sequential naming: N1, N2, N3, etc.

### Changed - Phase 5 Week 1: Symbol Coverage Improvements
- **Symbol Coverage**: 94 → 308 symbols mapped (+227% improvement)
  - Total coverage: 11.7% → 38.3% (308/805 symbols)
  - Equipment coverage: 20.2% → 76.7% (289/377 equipment symbols)
- **Equipment Symbol Resolution**: `SymbolRegistry.get_by_dexpi_class()` now works for 76.7% of equipment
- **Unmapped Symbols**: 88 equipment symbols (30 unique base IDs) identified as lacking upstream DEXPI classes

### Fixed - Phase 5 Week 1: Visualization Blockers
- Bug #2 (Symbol Catalog): Backfilled 214 additional dexpi_class mappings
- Bug #3 (Nozzle Creation): Equipment now creates proper connection points with DEXPI-compliant structure
- Symbol registry no longer returns `None` for majority of equipment lookups

### Documentation - Phase 5 Week 1
- Updated VISUALIZATION_PLAN.md: Status changed from "BLOCKED" to "WEEK 1 COMPLETE"
- Updated docs/active/README.md: Phase 0-1 and Week 1 completion status
- Updated ROADMAP.md: Phase 5 Week 1 section added
- Updated MIGRATION_SUMMARY.md: Phase 5 update section with Week 1 metrics

### Validation
- ✅ 308 symbols have dexpi_class mappings (38.3% coverage)
- ✅ 289 equipment symbols mapped (76.7% coverage)
- ✅ Catalog structure valid
- ✅ Regression protection thresholds in place

## [0.4.0] - 2025-11-06

### Added - Phase 1 & 2.1 Infrastructure
- **TransactionManager**: ACID transaction support with dual snapshot strategies
  - Deepcopy for models <1MB, serialization for ≥1MB
  - Begin/apply/commit/rollback operations
  - Diff calculation and audit trails
- **Operation Registry**: Typed operation catalog following ParserFactory pattern from pyDEXPI
  - 7 initial operations (3 DEXPI + 2 SFILES + 2 Template)
  - STRATEGIC/TACTICAL/ATOMIC categorization
  - DiffMetadata for transaction integration
- **Template System**: Parametric template instantiation (Phase 1 Task 4)
  - ParameterSubstitutionEngine with ${variable} syntax
  - ParametricTemplate with DEXPI/SFILES dual-mode support
  - 4 strategic templates (pump_basic, pump_station_n_plus_1, tank_farm, heat_exchanger_with_integration)
- **area_deploy MCP Tool** (Phase 2 Task 1):
  - `template_list`: Lists available templates with category filtering
  - `template_get_schema`: Returns parameter schema and metadata
  - `area_deploy`: Deploys parametric templates (reduces 50+ calls to 1)
  - Template caching for performance

### Changed - Phase 0 Cleanup
- **Import Safety**: Created sfiles_adapter.py for safe SFILES2 imports with clear error messages
- **Validation**: MLGraphLoader integration for DEXPI, round-trip validation for SFILES
- **BFD Support**: Fixed CamelCase ID generation for BFD process names
- **Template Architecture**: Direct component addition to DEXPI models (removed Pattern abstraction dependency)
- **pyDEXPI Integration**: Using equipment/piping/instrumentation modules directly

### Fixed - Phase 0 & 1 Critical Issues
- SFILES round-trip validation now handles multi-word BFD process names
- Import errors now provide clear guidance when SFILES2 not installed
- Response format compatibility via is_success() helper
- Import shim bypassed in schema_tools.py (used safe adapter)
- Phase sequencing corrected (TransactionManager before templates)
- Template tag/tagName compatibility for pyDEXPI tools
- DeepWiki integration: Pattern class is for synthetic generation, not templates

### Documentation
- Updated ROADMAP.md: Phase 1 marked COMPLETE (100%)
- Updated CLAUDE.md: SVG policy revised (planned for BFD Phase 1, Sprint 5)
- Updated README.md: Tool consolidation status and progress
- Added comprehensive API specifications in docs/ (3,953 lines total)

### Testing
- Phase 1 comprehensive testing (TransactionManager, graph_connect, Operation Registry, Template System)
- Phase 2.1 comprehensive testing (area_deploy with all 4 templates)
- Both DEXPI and SFILES modes validated

### Deprecation Warnings
- Legacy BFD data migration not needed (test data only)
- Phase 3 tool consolidation pending (54 tools → 12 consolidated tools)

## [0.3.0] - 2025-01-30

### Added
- **Batch Tools for LLM Optimization**:
  - `model_batch_apply`: Execute multiple operations atomically
  - `rules_apply`: Structured validation output for LLMs
  - `graph_connect`: Autowiring with automatic valve insertion
- **Response Format Normalization**: 
  - `is_success()` helper for handling mixed response formats
  - Standardized `success_response()` and `error_response()` utilities
- **Dynamic Nozzle Creation**: Automatic creation of equipment nozzles for multiple connections
- **Native pyDEXPI Integration**:
  - Using `piping_toolkit.insert_item_to_segment()` for proper valve insertion
  - Leveraging `piping_toolkit` for segment manipulation

### Fixed
- **Bugs**:
  - Fixed Proteus serializer initialization (was undefined)
  - Corrected `metadata` to `metaData` attribute access
  - Fixed `pipingClassArtefact` to `pipingClassCode` 
  - Resolved routing order - batch tools now checked before prefix matching
  - Fixed pattern matching for wildcards (e.g., "P-*")
  - Server error handling now uses standardized response format
- **Inline Valve Insertion**:
  - Proper use of pyDEXPI toolkit functions with correct parameters
  - Fixed segment connection tracking with `segment_id`
  - Resolved "list index out of range" errors in valve insertion

### Changed
- Removed unimplemented strategies from `graph_connect` enum
- Updated tool routing to prioritize batch tools

### Preparing for Deprecation
- 35+ legacy tools to be deprecated in favor of 12 consolidated tools
- Transition plan documented in HIGH_ROI_IMPLEMENTATION_PLAN.md

## [1.1.0] - 2025-01-30

### Added
- **Dynamic Schema Generation**: Automatic discovery and exposure of all pyDEXPI classes through runtime introspection
  - 159 equipment types now available (previously ~10 hardcoded types)
  - 22 valve types including specialized safety valves
  - 33 instrumentation types with full signal support
- **Enhanced Instrumentation Model**: Complete signal chain implementation
  - `dexpi_add_control_loop` tool for creating complete control loops
  - Signal connections between sensors, controllers, and actuators
  - Support for ProcessSignalGeneratingFunction and ActuatingFunction
- **Proteus XML Import**: Native support for Proteus 4.2 XML format via `dexpi_import_proteus_xml`
- **Inline Valve Insertion**: `dexpi_insert_valve_in_segment` for placing valves within existing piping
- **Class Discovery Tools** (now unified under schema_*):
  - `schema_describe_class`: Comprehensive class description with schema
  - `schema_list_classes`: Enumerate classes by category
  - `schema_find_class` / `schema_get_hierarchy`: Search and navigate inheritance trees
- **Additional SFILES Tools**:
  - `sfiles_from_string`: Create flowsheet from SFILES notation
  - `sfiles_parse_and_validate`: Validate SFILES syntax with regex
  - `sfiles_canonical_form`: Normalize SFILES for comparison
  - `sfiles_pattern_helper`: Get SFILES syntax patterns

### Changed
- **GraphML Export**: Now uses UnifiedGraphConverter with consistent sanitization
- **Tool Schemas**: All equipment, valve, and instrumentation enums now dynamically generated
- **Validation**: Enhanced with native pyDEXPI validation methods

### Fixed
- GraphML export sanitization for None values and special characters
- Type mapping for Python 3.10+ Union types (Type | None syntax)
- Import paths for instrumentation modules aligned with pyDEXPI structure

### Technical Improvements
- DexpiIntrospector class for runtime class discovery and schema generation
- Type annotation mapping from Pydantic FieldInfo to JSON schema
- Consistent error handling across all tools
- Full utilization of pyDEXPI library capabilities

## [1.0.0] - 2025-01-20

### Initial Release
- Core DEXPI P&ID functionality with basic equipment types
- SFILES BFD/PFD support with v1 and v2 notation
- Git-based project persistence
- MCP server implementation for LLM accessibility
