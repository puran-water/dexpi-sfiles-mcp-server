# Feature Parity Matrix: Consolidated Tools (Phase 4)

## Overview

This document maps the 58 legacy atomic tools to the 12 new consolidated tools introduced in Phase 4. The consolidation reduces API surface area while maintaining full functionality through:

- **model_create / model_load / model_save**: Unified model lifecycle (replaces 9 tools)
- **model_tx_begin / model_tx_apply / model_tx_commit**: Transaction-based operations (replaces 45+ tools via operation registry)

## Architecture Notes

- **Operation Names = Tool Names**: The operation registry uses a 1:1 mapping (e.g., `dexpi_add_equipment` tool → `dexpi_add_equipment` operation)
- **No Legacy Aliases**: This is a greenfield project with no existing users, so we made a clean break
- **Two Calling Patterns**:
  - **Direct**: Call atomic tools directly (e.g., `dexpi_add_equipment` as MCP tool)
  - **Transactional**: Use `model_tx_apply` with operation names (provides ACID semantics)

---

## Model Lifecycle Tools

### 1. model_create

**Replaces**: 2 legacy tools

| Legacy Tool | Legacy Parameters | New Parameters | Notes |
|-------------|-------------------|----------------|-------|
| `dexpi_create_pid` | `project_name`, `drawing_number`, `revision`, `description` | `model_type="dexpi"`, `metadata={project_name, drawing_number, revision, description}` | Unified metadata structure |
| `sfiles_create_flowsheet` | `name`, `type`, `description` | `model_type="sfiles"`, `metadata={name, type, description}` | Unified metadata structure |

**Functionality**: ✅ Full parity - creates models with identical structure

---

### 2. model_load

**Replaces**: 3 legacy tools

| Legacy Tool | Legacy Parameters | New Parameters | Notes |
|-------------|-------------------|----------------|-------|
| `dexpi_import_json` | `json_content`, `model_id` | `model_type="dexpi"`, `format="json"`, `content`, `model_id` | Unified format parameter |
| `dexpi_import_proteus_xml` | `directory_path`, `filename`, `model_id` | `model_type="dexpi"`, `format="proteus_xml"`, `directory_path`, `filename`, `model_id` | Proteus XML support preserved |
| `sfiles_from_string` | `sfiles_string`, `flowsheet_id` | `model_type="sfiles"`, `format="sfiles_string"`, `content`, `model_id` | Unified content parameter |

**Functionality**: ✅ Full parity - imports from all supported formats

---

### 3. model_save

**Replaces**: 4 legacy tools

| Legacy Tool | Legacy Parameters | New Parameters | Notes |
|-------------|-------------------|----------------|-------|
| `dexpi_export_json` | `model_id` | `model_id`, `format="json"` | Unified format selection |
| `dexpi_export_graphml` | `model_id`, `include_msr` | `model_id`, `format="graphml"`, `options={include_msr}` | Options structure for format-specific params |
| `sfiles_to_string` | `flowsheet_id`, `canonical`, `version` | `model_id`, `format="sfiles_string"`, `options={canonical, version}` | Unified ID parameter |
| `sfiles_export_graphml` | `flowsheet_id` | `model_id`, `format="graphml"` | Unified format selection |

**New Feature**: `model_type` parameter disambiguates when model exists in both DEXPI and SFILES stores (supports migration scenarios)

**Functionality**: ✅ Full parity + enhanced disambiguation

---

## Transaction Tools

### 4. model_tx_begin

**New Tool**: Start ACID transaction on a model

**Parameters**:
- `model_id`: Model to lock
- `metadata` (optional): Transaction metadata (client, session, purpose)

**Returns**: `transaction_id`, `snapshot_strategy`, `started_at`

**Enables**: Atomic multi-operation changes with rollback capability

---

### 5. model_tx_apply

**Replaces**: 45+ atomic operation tools via operation registry

**Core Functionality**: Executes operations within transaction context

**DEXPI Operations** (9 operations):

| Legacy Tool | Operation Name | Parameters | Notes |
|-------------|----------------|------------|-------|
| `dexpi_add_equipment` | `dexpi_add_equipment` | `equipment_type`, `tag_name`, `specifications`, `nozzles` | 159 equipment types supported |
| `dexpi_add_piping` | `dexpi_add_piping` | `segment_id`, `material`, `nominal_diameter`, `pipe_class` | Piping segments |
| `dexpi_add_instrumentation` | `dexpi_add_instrumentation` | `instrument_type`, `tag_name`, `connected_equipment` | Process instrumentation |
| `dexpi_add_control_loop` | `dexpi_add_control_loop` | `loop_tag`, `controlled_variable`, `sensor_tag`, `controller_tag`, `control_valve_tag` | Complete control loops |
| `dexpi_connect_components` | `dexpi_connect_components` | `from_component`, `to_component`, `line_number`, `pipe_class` | Piping connections |
| `dexpi_add_valve_between_components` | `dexpi_add_valve_between_components` | `from_component`, `to_component`, `valve_type`, `valve_tag`, `at_position` | Inline valve insertion |
| `dexpi_insert_valve_in_segment` | `dexpi_insert_valve_in_segment` | `segment_id`, `valve_type`, `tag_name`, `at_position` | Split existing segment |
| `dexpi_validate_model` | `dexpi_validate_model` | `model_id`, `validation_level` | Pre-commit validation (can be used outside transactions too) |
| `dexpi_convert_from_sfiles` | `dexpi_convert_from_sfiles` | `flowsheet_id`, `model_id` | Cross-format conversion |

**SFILES Operations** (7 operations):

| Legacy Tool | Operation Name | Parameters | Notes |
|-------------|----------------|------------|-------|
| `sfiles_add_unit` | `sfiles_add_unit` | `unit_type`, `unit_name`, `parameters`, `sequence_number` | Process units |
| `sfiles_add_stream` | `sfiles_add_stream` | `from_unit`, `to_unit`, `stream_name`, `properties`, `tags` | Material/energy streams |
| `sfiles_add_control` | `sfiles_add_control` | `control_type`, `control_name`, `connected_unit`, `signal_to` | Control instrumentation |
| `sfiles_parse_and_validate` | `sfiles_parse_and_validate` | `sfiles_string`, `return_tokens` | Syntax validation |
| `sfiles_canonical_form` | `sfiles_canonical_form` | `sfiles_string`, `version` | Normalization |
| `sfiles_generalize` | `sfiles_generalize` | `flowsheet_id` or `sfiles_string` | Remove unit numbers for templates |
| `sfiles_convert_from_dexpi` | `sfiles_convert_from_dexpi` | `model_id`, `flowsheet_id` | Cross-format conversion |

**Template/Strategic Operations** (10+ templates):

| Legacy Tool | Operation Name | Parameters | Notes |
|-------------|----------------|------------|-------|
| `template_list` | N/A - metadata query | `category` | Lists available templates |
| `template_get_schema` | N/A - metadata query | `template_name` | Returns parameter schema |
| `area_deploy` | `template_instantiate_dexpi` or `template_instantiate_sfiles` | `template_name`, `parameters`, `connection_point` | Deploys full template (pump arrays, tank farms, heat integration, etc.) |

**Graph/Tactical Operations** (10 actions via graph_modify):

| Legacy Tool | Operation Name | Parameters | Notes |
|-------------|----------------|------------|-------|
| `graph_modify` | `graph_modify_{action}` | `action`, `target`, `payload`, `options` | 10 actions: insert/update/remove component, inline insertion, segment ops, rewire, properties, toggle instrumentation |

**Functionality**: ✅ Full parity for all atomic operations + transactional semantics

---

### 6. model_tx_commit

**New Tool**: Commit or rollback transaction

**Parameters**:
- `transaction_id`: Transaction to finalize
- `action`: `"commit"` or `"rollback"` (default: commit)
- `validate`: Run pre-commit validation (default: false)

**Returns (commit)**:
- `diff`: Structural changes (added/modified/removed components)
- `operations_applied`: Count of operations
- `validation`: Validation results (if requested)

**Returns (rollback)**: Confirmation message

**Functionality**: ✅ ACID semantics with diff preview and optional validation

---

## Project/Git Tools

### 7. project_init

**Status**: No consolidation - unique functionality

**Functionality**: Initialize git-tracked project for version-controlled models

---

### 8. project_save

**Status**: No consolidation - unique functionality

**Functionality**: Save model to git project with automatic commits

---

### 9. project_load

**Status**: No consolidation - unique functionality

**Functionality**: Load model from git project by name

---

### 10. project_list

**Status**: No consolidation - unique functionality

**Functionality**: List all models in a git project

---

## Validation/Schema Tools

### 11. validate_model

**Status**: Can be used standalone OR within transactions

**Functionality**: Comprehensive validation (syntax, topology, ISA, connectivity)

**Usage Patterns**:
- **Standalone**: `validate_model(model_id, model_type, scopes)` - direct validation
- **Transactional**: `model_tx_commit(tx_id, validate=True)` - pre-commit validation

---

### 12. schema_query

**Replaces**: 4 legacy schema introspection tools

| Legacy Tool | New Parameters | Notes |
|-------------|----------------|-------|
| `schema_list_classes` | `operation="list_classes"`, `schema_type`, `category` | Unified query interface |
| `schema_describe_class` | `operation="describe_class"`, `class_name`, `schema_type`, `include_inherited` | Class details |
| `schema_find_class` | `operation="find_class"`, `search_term`, `schema_type` | Pattern search |
| `schema_get_hierarchy` | `operation="get_hierarchy"`, `schema_type`, `root_class`, `max_depth` | Inheritance tree |

**Functionality**: ✅ Full parity with unified query interface

---

## Search/Graph Tools

### 13. search_execute

**Replaces**: 5 legacy search tools

| Legacy Tool | New Parameters | Notes |
|-------------|----------------|-------|
| `search_by_tag` | `query_type="by_tag"`, `tag_pattern`, `fuzzy`, `search_scope` | Tag pattern matching |
| `search_by_type` | `query_type="by_type"`, `component_type`, `include_subtypes` | Type-based search |
| `search_by_attributes` | `query_type="by_attributes"`, `attributes`, `match_type` | Attribute matching |
| `search_connected` | `query_type="connected"`, `node_id`, `direction`, `max_depth` | Topology traversal |
| `query_model_statistics` | `query_type="statistics"`, `group_by` | Model statistics |

**Functionality**: ✅ Full parity with unified query interface

---

### 14. graph_analyze_topology

**Status**: No consolidation - advanced graph analysis

**Functionality**: Paths, cycles, bottlenecks, clustering, centrality analysis

---

### 15. graph_find_paths

**Status**: No consolidation - specialized pathfinding

**Functionality**: Shortest/all-simple/all paths between nodes

---

### 16. graph_detect_patterns

**Status**: No consolidation - pattern recognition

**Functionality**: Heat integration, recycle loops, parallel trains, cascade detection

---

### 17. graph_calculate_metrics

**Status**: No consolidation - graph metrics

**Functionality**: Diameter, density, clustering coefficient, efficiency

---

### 18. graph_compare_models

**Status**: No consolidation - model comparison

**Functionality**: Structural and topological comparison of two models

---

## Batch Tools

### 19. model_batch_apply

**Replaces**: Manual sequencing of multiple operations

**Functionality**: Execute multiple operations in single call with idempotency

**Usage**: Tactical batch operations (not replacing atomic tools, but enabling efficient multi-op workflows)

---

### 20. rules_apply

**Status**: No consolidation - validation rule engine

**Functionality**: Apply validation rules with optional auto-fix

---

### 21. graph_connect

**Status**: No consolidation - smart autowiring

**Functionality**: Pattern-based connection with inline component insertion

---

## Layout Tools (NEW - v0.8.0)

### 22-29. Layout Tools

**Status**: New tools - no legacy equivalents

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `layout_compute` | Compute automatic layout using ELK | `model_id`, `algorithm`, `direction`, `spacing` |
| `layout_get` | Retrieve stored layout | `layout_id`, `include_edges`, `include_ports` |
| `layout_update` | Update with concurrency control | `layout_id`, `etag`, `positions`, `edges` |
| `layout_validate` | Validate schema and consistency | `layout_id`, `check_model_consistency` |
| `layout_list` | List layouts by model | `model_id`, `model_type` |
| `layout_save_to_file` | Persist to project | `layout_id`, `project_path`, `model_name` |
| `layout_load_from_file` | Load from project | `project_path`, `model_name` |
| `layout_delete` | Remove from store | `layout_id` |

**Architecture**: Codex Consensus #019adb91

**Key Features**:
- Persistent ELK worker process for efficient layout computation
- Etag-based optimistic concurrency control
- Orthogonal edge routing suitable for P&ID standards
- File persistence alongside models in project structure

**Documentation**: [`docs/LAYOUT_SYSTEM.md`](LAYOUT_SYSTEM.md)

---

## Summary Statistics

| Category | Legacy Tools | Consolidated Tools | Reduction |
|----------|-------------|-------------------|-----------|
| **Model Lifecycle** | 9 | 3 | 67% |
| **Transaction/Operations** | 45+ | 3 | 93% |
| **Schema/Search** | 9 | 2 | 78% |
| **Project (Git)** | 4 | 4 | 0% (unique) |
| **Graph Analysis** | 6 | 6 | 0% (unique) |
| **Batch/Rules** | 3 | 3 | 0% (unique) |
| **Layout** | 0 | 8 | New capability |
| **TOTAL** | **76** | **29** | **62%** |

**Core Consolidation**: 58 tools → 12 tools (79% reduction for commonly-used operations)

**New Capabilities**: 8 layout tools added in v0.8.0

---

## Migration Examples

### Example 1: Creating and Exporting a Model

**Legacy Approach** (2 separate tools):
```json
// Step 1: Create
{"tool": "dexpi_create_pid", "params": {"project_name": "Plant A", "drawing_number": "PID-001"}}

// Step 2: Export
{"tool": "dexpi_export_json", "params": {"model_id": "abc123"}}
```

**Consolidated Approach** (same tools, unified interface):
```json
// Step 1: Create
{"tool": "model_create", "params": {
  "model_type": "dexpi",
  "metadata": {"project_name": "Plant A", "drawing_number": "PID-001"}
}}

// Step 2: Export
{"tool": "model_save", "params": {
  "model_id": "abc123",
  "format": "json"
}}
```

---

### Example 2: Adding Equipment (Direct vs Transactional)

**Direct Approach** (no transaction):
```json
{"tool": "dexpi_add_equipment", "params": {
  "model_id": "abc123",
  "tag_name": "TK-101",
  "equipment_type": "Tank"
}}
```

**Transactional Approach** (with ACID semantics):
```json
// Step 1: Begin transaction
{"tool": "model_tx_begin", "params": {"model_id": "abc123"}}

// Step 2: Apply operations
{"tool": "model_tx_apply", "params": {
  "transaction_id": "tx-456",
  "operations": [
    {"operation": "dexpi_add_equipment", "params": {"tag_name": "TK-101", "equipment_type": "Tank"}},
    {"operation": "dexpi_add_equipment", "params": {"tag_name": "P-101", "equipment_type": "Pump"}},
    {"operation": "dexpi_connect_components", "params": {"from_component": "TK-101", "to_component": "P-101"}}
  ]
}}

// Step 3: Commit (with diff preview and validation)
{"tool": "model_tx_commit", "params": {
  "transaction_id": "tx-456",
  "action": "commit",
  "validate": true
}}
```

**Benefits of Transactional Approach**:
- Atomic: All operations succeed or all rollback
- Diff preview: See exactly what changed before committing
- Validation: Ensure model remains valid
- Rollback: Can discard changes if issues detected

---

## Deprecation Strategy

### Phase 1: Dual API (Current)
- ✅ Both atomic and consolidated tools available
- ✅ Consolidated tools production-ready
- ✅ Full test coverage (150 tests passing)
- ⏳ Add deprecation notices to atomic tools
- ⏳ Document migration paths

### Phase 2: Deprecation Notices
- Mark atomic tools with `[Consolidated into model_* / model_tx_*]` in descriptions
- Point to this parity matrix in deprecation messages
- Ship migration guide with examples

### Phase 3: Optional Removal (Future)
- After one release cycle with deprecation notices
- Decide: Keep both APIs or remove atomics
- Recommendation: Keep atomics for quick scripts, consolidated for robust workflows

---

## Conclusion

The Phase 4 consolidation achieves:

✅ **79% reduction** in commonly-used tools (58 → 12)
✅ **Full functionality preservation** - every legacy tool has a clear consolidated equivalent
✅ **Enhanced capabilities** - ACID transactions, diff preview, validation integration
✅ **Clean architecture** - 1:1 operation→tool mapping, no legacy baggage
✅ **Comprehensive testing** - 150 tests passing, full coverage of SFILES/GraphML/ambiguous paths

**Status**: Production-ready for live MCP testing and deprecation notices.
