# Changelog

All notable changes to the Engineering MCP Server are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-30

### Added
- **High-Value Batch Tools for LLM Optimization**:
  - `model_batch_apply`: Execute multiple operations atomically
  - `rules_apply`: Structured validation output for LLMs
  - `graph_connect`: Smart autowiring with automatic valve insertion
- **Response Format Normalization**: 
  - `is_success()` helper for handling mixed response formats
  - Standardized `success_response()` and `error_response()` utilities
- **Dynamic Nozzle Creation**: Automatic creation of equipment nozzles for multiple connections
- **Native pyDEXPI Integration**:
  - Using `piping_toolkit.insert_item_to_segment()` for proper valve insertion
  - Leveraging `piping_toolkit` for segment manipulation

### Fixed
- **Critical Bugs**:
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
- **Class Discovery Tools**:
  - `dexpi_describe_class`: Comprehensive class description with schema
  - `dexpi_list_class_attributes`: Attribute listing organized by category
  - `dexpi_list_available_types`: Discovery of all available types
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
- Web-based visualization dashboard
- MCP server implementation for LLM accessibility