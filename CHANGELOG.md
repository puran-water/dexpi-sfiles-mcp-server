# Changelog

All notable changes to the Engineering MCP Server are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
