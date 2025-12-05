# 8-Week Enhancement Plan: Implementation Progress

**Started**: 2025-11-17
**Current Phase**: Phase 3 (Symbol Library Integration Complete)
**Last Updated**: 2025-12-05
**Test Count**: 758 passed, 3 skipped

---

## Quick Wins: ✅ COMPLETE (4/4)

All Quick Wins completed before starting main 8-week plan:

### ✅ Quick Win #1: Remove Unused Dependencies
- **Commit**: `bfa81e9` - Remove unused dependencies (numpy, pandas, pathfinding)
- **Impact**: Cleaned pyproject.toml, removed 3 unused dependencies
- **Tests**: 45/45 passing after removal

### ✅ Quick Win #2: Remove Dead Feature Flags
- **Commit**: `41231a9` - Remove dead feature flags module
- **Impact**: Deleted src/config/settings.py (116 lines), removed unused flags
- **Tests**: 45/45 passing after removal

### ✅ Quick Win #3: Wire model_metrics into validation
- **Commit**: `efcebab` - Wire model_metrics into validation_tools
- **Impact**:
  - Enhanced _validate_model() with comprehensive model_summary from model_metrics
  - Improved _compare_dexpi_models() with detailed component-level checks
  - Added metadata, complexity, and validation metrics to validation results
- **Tests**: All tests passing, import verification successful

### ✅ Quick Win #4: Add GenericAttributeExporter Unit Tests
- **Commit**: `3443a95` - test(exporter): Add comprehensive GenericAttributeExporter unit tests
- **Impact**:
  - Created tests/exporters/test_generic_attribute_exporter.py (484 lines, 43 tests)
  - 100% coverage of _serialize_value() method and helper methods
  - Validated all value types: MultiLanguageString, SingleLanguageString, Enum, bool, int, float, str, datetime, physical quantities, lists/tuples, custom attributes
- **Tests**: 43/43 tests passing (100% pass rate)

**Quick Wins Total Effort**: ~2 days
**Quick Wins Total Impact**: Immediate code cleanup, measurement infrastructure operational, comprehensive test coverage for GenericAttributeExporter

---

## Weeks 1-2: Attribute Completeness + Metrics (COMPLETE)

**Theme**: "Unify attribute export with pyDEXPI's native API + add measurement"

**Start Date**: 2025-11-17
**Completed**: 2025-11-17

### Task Checklist

- [x] **Task 1**: Integrate pyDEXPI get_data_attributes() with GenericAttributeExporter
  - [x] Use pydexpi.toolkits.base_model_utils.get_data_attributes() as primary source
  - [x] Keep model_fields metadata for enrichment/override
  - [x] Add feature flag for fallback behavior
  - [x] Files: `src/exporters/proteus_xml_exporter.py` (GenericAttributeExporter class)

- [x] **Task 2**: Extend GenericAttributeExporter type coverage
  - [x] Add dict handling: flatten `{"k": v}` into `Name=f"{attr_name}.{k}"`
  - [x] Add generic "object with value/unit/name" pattern
  - [x] Improve nullable physical quantities handling (zero is meaningful)
  - [x] Files: `src/exporters/proteus_xml_exporter.py` (_serialize_value method)

- [x] **Task 3**: Complete instrumentation attribute export
  - [x] Export all 11+ ProcessInstrumentationFunction data attributes (via get_data_attributes() from Task 1)
  - [x] Wire core/data/instrumentation_registrations.csv for metadata enrichment (already used in ComponentRegistry)
  - [x] Use instrumentation_toolkit for semantic completeness (GenericAttributeExporter handles all data attributes)
  - [x] Files: `src/exporters/proteus_xml_exporter.py` (line 1258: attribute_exporter.export())

- [x] **Task 4**: Add comprehensive GenericAttributeExporter unit tests
  - [x] ✅ **COMPLETED IN QUICK WIN #4**
  - [x] Test fixtures for all value types
  - [x] Assert GenericAttributes appear in correct sets
  - [x] Files: `tests/exporters/test_generic_attribute_exporter.py`

- [x] **Task 5**: Implement fidelity metrics using model_metrics
  - [x] Define metric: `% preserved = len(exported_attrs) / len(get_data_attributes(component))`
  - [x] Call from integration tests to measure improvement
  - [x] Baseline results: 100-200% fidelity (>100% due to multi-language expansion - correct behavior)
  - [x] Files: `src/core/analytics/model_metrics.py`, `src/exporters/attribute_utils.py`, `tests/exporters/test_baseline_fidelity.py`

### Success Criteria

- [x] ✅ 80%+ of get_data_attributes() entries appear in Proteus GenericAttributes (achieved 100-200%)
- [x] ✅ Equipment design conditions (temp, pressure, capacity) exported
- [x] ✅ Piping attributes (heat tracing, insulation) exported
- [x] ✅ Instrumentation metadata (location, panelID) exported
- [x] ✅ Fidelity metrics demonstrate ≥80% preservation (all fixtures: 100-200%)
- [x] ✅ Tests validate all value types: dict, nullable quantities, composite objects

### Progress Notes

**2025-11-17**:
- Quick Wins completed (4/4)
- Started Weeks 1-2
- Task 1 complete: Integrated get_data_attributes() API (commit 5e81715)
- Task 2 complete: Extended type coverage (dict/objects/nullables) (commit ec5f2ca)
- Task 3 complete: Instrumentation export verified - GenericAttributeExporter already exports all data attributes for ProcessInstrumentationFunction
- Task 4 already complete from Quick Win #4
- Task 5 complete: Fidelity metrics implemented with baseline measurements
  - Created `calculate_export_fidelity()` in model_metrics.py
  - Created shared `attribute_utils.py` to avoid circular imports
  - Codex review: Fixed calculation to filter DexpiAttributes set only, improved dotted-name detection
  - Updated baseline results: Tank (160%), Pump (100%), HX (100%), Piping (138%), Instrumentation (200%)
  - All tests now use `fail_below_threshold=True` for strict validation
  - All fixtures demonstrate complete attribute export (missing_attributes=[])
- All tests passing: 45 Proteus exporter + 43 GenericAttributeExporter + 5 baseline fidelity = 93 tests

**Weeks 1-2 COMPLETE** ✅ - Target was 80% fidelity, achieved 100-200% (no data loss)

---

## Weeks 3-4: Layout & Presentation Integration (COMPLETE)

**Theme**: "Make GraphMetadata/LayoutMetadata operational + inject into Proteus XML"

**Started**: 2025-11-18
**Completed**: 2025-11-18

### Task Checklist

- [x] **Task 0**: Prototype visibility test
  - [x] Created test suite `tests/exporters/test_position_presentation_export.py` (6 tests)
  - [x] Validates Position/Extent/Presentation export structure
  - [x] Tests equipment, piping, Drawing extent, error cases

- [x] **Task 1**: Design metadata transport contract
  - [x] Added `GraphConversionResult` to `src/models/graph_metadata.py`
  - [x] Added `extract_layout_from_graph()` helper function
  - [x] Supports layout extraction and generation from NetworkX graphs

- [x] **Task 2**: Wire GraphMetadata & LayoutMetadata into graph flow
  - [x] Added `dexpi_to_networkx_with_layout()` to `UnifiedGraphConverter`
  - [x] Returns `GraphConversionResult` with layout metadata
  - [x] Supports fallback spring layout generation

- [x] **Task 3**: Inject Position/Extent/Presentation into Proteus XML
  - [x] Added `layout_metadata` parameter to `ProteusXMLExporter.export()`
  - [x] Added `_export_position()` with Location/Axis/Reference
  - [x] Added `_export_extent()` for bounding box
  - [x] Added `_export_component_presentation()` for styling
  - [x] Updated `_export_equipment()` to call helpers
  - [x] Updated `_export_piping_network_segment()` to call helpers
  - [x] Updated `_create_drawing_element()` to add Drawing Extent from layout

- [ ] **Task 4**: Implement Label export (deferred)
- [ ] **Task 5**: Handle nested equipment hierarchies (deferred)
- [x] **Task 6**: Export InstrumentationLoopFunction
  - [x] Added `_export_instrumentation_loop_function()` to ProteusXMLExporter
  - [x] Exports ID, ComponentClass, GenericAttributes (includes loop number)
  - [x] Nests child ProcessInstrumentationFunction elements
  - [x] Added fixtures: `instrumentation_loop_function`, `simple_instrumentation_loop`
  - [x] Added 3 tests: basic export, simple loop, multiple loops
  - [x] Added fidelity test: 100% fidelity achieved
- [x] **Task 7**: Tests and validation
  - [x] 103 exporter tests passing (was 99)
  - [x] 6 baseline fidelity tests (including InstrumentationLoopFunction)

### Progress Notes

**2025-11-18**:
- Started Weeks 3-4 implementation
- Task 0: Created prototype visibility tests (6 tests)
- Task 1: Added GraphConversionResult and extract_layout_from_graph
- Task 2: Added dexpi_to_networkx_with_layout() to converter
- Task 3: Implemented Position/Extent/Presentation export helpers
- Task 6: Implemented InstrumentationLoopFunction export
  - Added `_export_instrumentation_loop_function()` method
  - Created fixtures and 3 unit tests
  - Added fidelity test: 100% fidelity achieved
- Exporter tests: 103 passed (was 99)
- Baseline fidelity tests: 6 passed (added InstrumentationLoopFunction)

**Note on Fidelity >100%**:
Fidelity values exceeding 100% (e.g., Tank 160%, Instrumentation 200%) are expected and correct.
This occurs because MultiLanguageStrings expand to multiple GenericAttributes (e.g., `Name_en`, `Name_de`).
The key metric is `missing_attributes == []` - when this is empty, no data is lost.

### Success Criteria

- [x] ✅ Equipment exports with Position/Extent/Presentation
- [x] ✅ Piping segments export with Position/Extent/Presentation
- [x] ✅ Drawing Extent computed from layout bounding box
- [x] ✅ Metadata transport contract established
- [x] ✅ InstrumentationLoopFunction export with 100% fidelity
- [ ] ⏳ Labels export (deferred to Weeks 5-6)
- [ ] ⏳ Nested equipment (deferred to Weeks 7-8)

**Weeks 3-4 COMPLETE** ✅ - Core structural export complete with 103 exporter tests passing

---

## Weeks 5-6: Visualization Orchestration & Symbol Geometry (COMPLETE)

**Theme**: "Production-ready rendering with MCP integration + Symbol geometry foundation"

**Started**: 2025-11-29
**Completed**: 2025-11-30

### Task Checklist

#### Week 5: MCP Visualization Tools & ComponentRegistry Migration ✅ COMPLETE

- [x] **Task 1**: Create MCP `visualize_model` tool
  - [x] Added `src/tools/visualization_tools.py` (469 lines)
  - [x] Integrated RendererRouter for intelligent renderer selection
  - [x] Supports HTML (Plotly), PNG (GraphicBuilder), GraphML export
  - [x] Auto-detects model type (DEXPI/SFILES)
  - [x] 24 tests passing

- [x] **Task 2**: Create MCP `visualize_list_renderers` tool
  - [x] Lists available renderers with capabilities and health status
  - [x] Returns recommended renderers per format

- [x] **Task 3**: Migrate DexpiIntrospector to ComponentRegistry
  - [x] Removed deprecated methods: `get_available_types()`, `get_valves()`, `generate_dynamic_enum()`
  - [x] Updated docstring to clarify ComponentRegistry relationship
  - [x] Updated scripts to use ComponentRegistry API

- [x] **Task 4**: Fix Codex-identified bugs
  - [x] **GraphML routing bug**: GraphML now routes directly to export, not through RendererRouter
  - [x] **Error handling bug**: Changed `result.get("status") == "error"` to `result.get("ok") is False`
  - [x] **Zero-score guard**: Added filtering to reject zero-score renderers with clear error message
  - [x] **Input validation**: Added upfront validation for format/quality enums with user-friendly errors

#### Week 6: Symbol Geometry Extension ✅ COMPLETE

- [x] **Task 5**: Add geometry dataclasses to `src/core/symbols.py`
  - [x] `Point` - 2D coordinate (x, y)
  - [x] `BoundingBox` - Symbol dimensions with `center` property
  - [x] `Port` - Connection point with id, position, direction, type, flow_direction

- [x] **Task 6**: Extend SymbolInfo with geometry fields
  - [x] `bounding_box: Optional[BoundingBox]` - Symbol dimensions
  - [x] `anchor_point: Optional[Point]` - Connection anchor
  - [x] `ports: List[Port]` - Connection points (default: empty list)
  - [x] `scalable: bool = True` - Render hint
  - [x] `rotatable: bool = True` - Render hint
  - [x] `get_anchor()` method - Returns explicit anchor or derives from bounding box center

- [x] **Task 7**: Add comprehensive geometry tests
  - [x] Created `tests/core/test_symbol_geometry.py` (25 tests)
  - [x] Tests cover Point, BoundingBox, Port, SymbolInfo geometry fields
  - [x] Full integration tests for pump/tank with complete geometry

### Remaining Tasks (Week 6 continued) - ALL COMPLETE

- [x] Add geometry data to merged_catalog.json ✅ COMPLETE (Week 8 - 805/805 symbols)
- [x] Update SymbolRegistry loader to parse geometry from catalog ✅ COMPLETE

### Success Criteria

- [x] ✅ MCP visualization tools operational (visualize_model, visualize_list_renderers)
- [x] ✅ RendererRouter correctly selects renderer based on format/quality
- [x] ✅ GraphML export works correctly (bypasses renderer selection)
- [x] ✅ Input validation provides user-friendly error messages
- [x] ✅ SymbolInfo extended with geometry fields (backward compatible)
- [x] ✅ All geometry tests passing (25 tests)
- [x] ✅ Full test suite passing (590 passed, 3 skipped GraphicBuilder Docker tests)

### Progress Notes

**2025-11-29 (Week 5)**:
- Created visualization_tools.py with visualize_model and visualize_list_renderers MCP tools
- Integrated RendererRouter for intelligent renderer selection
- Fixed Plotly API deprecation (titlefont_size → title=dict())
- Fixed SFILES fixture format (invalid cycle syntax)
- Fixed response format (status → ok)
- 19 initial tests passing

**2025-11-30 (Week 5 continued)**:
- Codex review identified bugs: GraphML routing, error handling, zero-score guard
- Fixed all identified bugs
- Added input validation for format/quality enums
- Updated scripts to use ComponentRegistry instead of deprecated DexpiIntrospector methods
- Updated orchestrator tests to expect RuntimeError for unsupported PDF format
- 24 visualization tests passing, 565 total tests passing

**2025-11-30 (Week 6)**:
- Added Point, BoundingBox, Port dataclasses to symbols.py
- Extended SymbolInfo with geometry fields (backward compatible)
- Added get_anchor() method for lazy anchor derivation
- Created comprehensive geometry test suite (25 tests)
- All 590 tests passing

**Weeks 5-6 COMPLETE** ✅ - MCP visualization tools operational, symbol geometry foundation in place

---

## Weeks 7-8: Integration, ModelStore, and Infrastructure Hardening (COMPLETE)

**Theme**: "Complete visualization foundation + harden core infrastructure"

**Started**: 2025-12-01
**Completed**: 2025-12-02

### Task Checklist

- [x] **Task 1**: Populate geometry data in merged_catalog.json ✅ COMPLETE
  - [x] Add bounding_box for ALL 805 symbols (100% coverage)
  - [x] Add port definitions from SVG analysis (422/805 = 52.4% have ports)
  - [x] Update SymbolRegistry loader to parse geometry

- [x] **Task 2**: Introduce ModelStore abstraction ✅ COMPLETE (2025-12-01)
  - [x] Abstract current dict-based stores (dexpi_models, flowsheets) → InMemoryModelStore
  - [x] Add lifecycle hooks (on_created, on_updated, on_deleted, on_accessed)
  - [x] Enable caching strategies via CachingHook
  - [x] Add snapshot/rollback for transaction support
  - [x] Full dict-like backward compatibility (660/660 tests pass)

- [x] **Task 3**: Consolidate instrumentation logic ✅ NOT NEEDED
  - [x] Reviewed: dexpi_tools.py already delegates to instrumentation_toolkit properly
  - [x] No duplication found - code is well-structured

- [x] **Task 4**: Complete catalog.py migration ✅ COMPLETE
  - [x] Extract SVG parsing to core/svg_parser.py (320 lines)
  - [x] Update catalog.py imports with deprecation notices

- [x] **Task 5**: End-to-end integration tests ✅ COMPLETE (2025-12-01)
  - [x] Created tests/integration/test_end_to_end.py (20 scenarios)
  - [x] Format conversion chains tested
  - [x] Full lifecycle with snapshots tested
  - [x] Concurrent write safety validated
  - [x] Template instantiation patterns tested
  - [x] Hook chain validation (CachingHook integration) tested

- [ ] Optional: ProteusXMLDrawing integration (deferred per user decision)

### Week 7 Progress Notes

**2025-12-01 (Week 7 Day 1)**:
- Created `src/core/model_store.py` with full ModelStore implementation:
  - `ModelStore` ABC with CRUD + lifecycle + snapshot interface
  - `InMemoryModelStore` thread-safe implementation with RLock
  - `CachingHook` for graph/stats cache invalidation
  - `ModelMetadata` tracking (created_at, modified_at, access_count)
  - `Snapshot` for transaction rollback support
  - Full dict-like backward compatibility (__getitem__, __setitem__, __delitem__, etc.)
- Created 56 comprehensive unit tests in `tests/core/test_model_store.py`
- Integrated ModelStore with server.py (replaced Dict[str, Any] with InMemoryModelStore)
- All 660 tests passing (was 604, +56 new ModelStore tests)

**2025-12-01 (Week 7 Day 1 continued - Codex Review Recommendations)**:
- Added `get(copy=True)` parameter to ModelStore for opt-in deep copy (safe mutation)
- Added `edit()` context manager for ergonomic in-place mutation with auto-update
- Created 14 additional unit tests for new features (70 total ModelStore tests)
- Created `tests/integration/test_end_to_end.py` with 20 E2E scenarios covering:
  - Format conversion chains (SFILES → DEXPI → store roundtrip)
  - Full lifecycle with snapshots (create → update → snapshot → rollback)
  - Concurrent write safety (thread safety validation)
  - Template instantiation patterns
  - Hook chain validation (CachingHook integration)
  - Model validation pipeline
  - Cross-model search operations
- Wired CachingHook into server.py and graph_tools.py:
  - Shared CachingHook instance added to both DEXPI and SFILES stores
  - GraphTools updated to use cache for expensive graph conversions
  - Cache auto-invalidates when models are updated or deleted
- All 694 tests passing (was 660, +14 ModelStore tests, +20 E2E tests)

---

## Measurable Success Metrics (Overall Plan)

- **Week 2**: ✅ Export fidelity 30% → 100-200% (measured via model_metrics) - ACHIEVED
- **Week 4**: ✅ Layout/presentation in Proteus XML, GraphicBuilder quality unlocked - ACHIEVED
- **Week 6**: ✅ MCP visualization tools operational (`visualize_model`, `visualize_list_renderers`) - ACHIEVED
- **Week 6**: ✅ SymbolInfo geometry foundation (Point, BoundingBox, Port) - ACHIEVED
- **Week 8**: ✅ Code duplication eliminated, ModelStore operational, end-to-end tests passing - ACHIEVED
- **Week 8+**: ✅ Layout System with ELK integration, 8 MCP tools, 768 tests passing - ACHIEVED
- **Week 8++**: ✅ SVG/PDF export via GraphicBuilder, 758 tests passing - ACHIEVED

---

## Recent Commits

```
74634a4 feat(layout): Add Layout Layer with ELK integration and MCP tools
a9d6f4f fix(geometry): Port inference uses absolute coordinates with bbox origin
53a76ce fix(geometry): Port direction normalization + SHA-256 hashing + validation
2f7a14d feat(symbols): Complete geometry coverage + SVG parser consolidation (Week 8)
cb73c95 feat(symbols): Add geometry data loading to SymbolRegistry (Week 8 Task 1)
```

---

## Notes

- **Codex review session** (ID: 019ad060-45df-7272-a6ce-7e54fd37d4be) used for Week 5-6 bug identification and architecture guidance
- **Codex review session** (ID: 019ada9a-4169-7a62-b8c8-c2a4b04b1ab7) used for Week 7 ModelStore enhancement recommendations
- **Codex consensus session** (ID: 019adb91-b13a-79d1-8772-5823bdec96ff) used for Layout System architecture decisions
- **Total test count**: 768 passed, 5 skipped, 0 failed ✅ (was 727, +39 layout tests, +2 additional)
- DEXPI TrainingTestCases cloned to `/tmp/TrainingTestCases` for GraphicBuilder tests
- Node.js with elkjs required for layout computation (`npm install elkjs`)

### Test Fixes (2025-12-01)

**GraphicBuilder Integration Tests Fixed:**
- Updated response format from `status` → `ok` API format
- Fixed tool name: `sfiles_convert_from_sfiles` → `dexpi_convert_from_sfiles`
- Use `ProteusXMLExporter` directly (no MCP export tool exists yet)
- Added graceful skip for models lacking Position/Extent data
- Updated tests to handle GraphicBuilder CLI limitations (PNG-only output)

**Skipped Tests (5 - all with valid reasons):**
- `TestLLMPlanValidator` (2 tests) - Intentionally skipped, functionality moved
- `test_sfiles_to_dexpi_to_graphicbuilder` - Needs shared SFILES/DEXPI stores
- `test_dexpi_model_to_graphicbuilder` - Models lack graphical Position/Extent data
- `test_validate_coverage` - Hierarchy file not found

---

## Files Modified in Weeks 5-6

### New Files
- `src/tools/visualization_tools.py` - MCP visualization tools (469 lines)
- `tests/tools/test_visualization_tools.py` - Visualization tests (24 tests)
- `tests/core/test_symbol_geometry.py` - Geometry tests (25 tests)

### Modified Files
- `src/core/symbols.py` - Added Point, BoundingBox, Port, extended SymbolInfo
- `src/server.py` - Integrated VisualizationTools
- `src/tools/dexpi_introspector.py` - Removed deprecated methods
- `src/visualization/orchestrator/renderer_router.py` - Zero-score guard
- `scripts/generate_all_registrations.py` - Updated to use ComponentRegistry
- `scripts/generate_equipment_registrations.py` - Updated to use ComponentRegistry
- `tests/visualization/test_orchestrator_integration.py` - Updated for new behavior
- `tests/test_graphicbuilder_integration.py` - Fixed response format, tool names, CLI limitations

---

## Files Modified in Week 7

### New Files
- `src/core/model_store.py` - ModelStore abstraction (650 lines):
  - `ModelStore` ABC with CRUD, lifecycle hooks, snapshots
  - `InMemoryModelStore` thread-safe implementation
  - `CachingHook` for derived data cache management
  - `ModelMetadata`, `Snapshot` dataclasses
- `tests/core/test_model_store.py` - 56 comprehensive unit tests

### Modified Files
- `src/server.py` - Replaced `Dict[str, Any]` with `InMemoryModelStore` for dexpi_models/flowsheets

---

## Week 8: Geometry Data Population

### Task 1: Geometry Data Population (COMPLETE)

**Objective**: Enable SymbolRegistry to load geometry data (bounding_box, ports, anchor_point) from merged_catalog.json

**Problem**: merged_catalog.json (805 symbols) had NO geometry data, but catalog.json had geometry for ~40 symbols. The SymbolInfo class already supported geometry fields (Week 6), but SymbolRegistry._load_merged_catalog() didn't load them.

**Solution**:
1. Added geometry loading helper methods to SymbolRegistry:
   - `_load_bounding_box(data)` - loads BoundingBox from catalog entry
   - `_load_anchor_point(data)` - loads Point from catalog entry
   - `_load_ports(data)` - loads list of Port objects

2. Updated `_load_merged_catalog()` to use new helpers when creating SymbolInfo

3. Created migration script `scripts/migrate_geometry_data.py` to copy geometry from catalog.json to merged_catalog.json

4. Added 10 new tests in `TestSymbolRegistryGeometryLoading` class

**Results**:
- Migrated geometry for 40 symbols (100% of those with geometry in catalog.json)
- Coverage by category:
  - Pumps: 10/17 (58.8%)
  - Tanks: 5/12 (41.7%)
  - Valves: 10/53 (18.9%)
  - Equipment: 8/45 (17.8%)
  - Filters: 5/15 (33.3%)
  - Separators: 2/16 (12.5%)
- All 704 tests passing (up from 694)

### Files Modified in Week 8

#### New Files
- `scripts/migrate_geometry_data.py` - Geometry migration script (~120 lines)
- `scripts/extract_all_geometry.py` - Full geometry extraction from all SVG files (~300 lines)
- `src/core/svg_parser.py` - Consolidated SVG parsing module (~320 lines)
- `tests/core/test_svg_parser.py` - SVG parser unit tests (23 tests)

#### Modified Files
- `src/core/symbols.py` - Added `_load_bounding_box()`, `_load_anchor_point()`, `_load_ports()` helper methods (~55 lines)
- `src/visualization/symbols/assets/merged_catalog.json` - Added geometry data to ALL 805 symbols (100% coverage)
- `src/visualization/symbols/catalog.py` - Added deprecation notices for DEXPI_CLASS_MAPPING and extract_svg_metadata()
- `tests/core/test_symbol_geometry.py` - Added TestSymbolRegistryGeometryLoading class (10 tests)

### Week 8 Summary

**Task 1: Geometry Data Population** - COMPLETE
- 100% geometry coverage (805/805 symbols)
- All categories: Pumps 17/17, Tanks 12/12, Valves 53/53, Equipment 45/45

**Task 2: Instrumentation Consolidation** - ALREADY WELL-STRUCTURED
- Existing code uses ComponentRegistry and instrumentation_toolkit appropriately
- No significant consolidation needed

**Task 3: SVG Parser Extraction** - COMPLETE
- Created `src/core/svg_parser.py` with unified SVG parsing
- Deprecated DEXPI_CLASS_MAPPING in catalog.py
- 23 new tests for SVG parsing

**Test Results**: 727 passed, 5 skipped (up from 704)

---

## Week 8+: Layout System with ELK Integration (COMPLETE)

**Theme**: "Automatic positioning for engineering diagrams with orthogonal edge routing"

**Completed**: 2025-12-02
**Codex Consensus**: Session #019adb91-b13a-79d1-8772-5823bdec96ff

### Task Checklist

- [x] **Task 1**: Layout Metadata Schema
  - [x] Created `src/models/layout_metadata.py` with comprehensive dataclasses
  - [x] `LayoutMetadata`: Complete layout with positions, edges, ports, labels
  - [x] `NodePosition`: 2D coordinates with optional width/height
  - [x] `EdgeRoute`: Edge routing with sections, bend points, sourcePoint/targetPoint
  - [x] `PortLayout`: Port positions with side constraints
  - [x] `BoundingBox`: Auto-computed layout bounds
  - [x] `ModelReference`: Link to source DEXPI/SFILES model
  - [x] SHA-256 etag computation for optimistic concurrency

- [x] **Task 2**: Layout Store
  - [x] Created `src/core/layout_store.py` with thread-safe storage
  - [x] CRUD operations with etag-based optimistic concurrency
  - [x] `OptimisticLockError` for concurrent modification detection
  - [x] File persistence (save_to_file/load_from_file)
  - [x] List/filter by model reference

- [x] **Task 3**: ELK Layout Engine (Codex Consensus Fix #1)
  - [x] Created `src/layout/engines/elk.py` with `ELKLayoutEngine`
  - [x] **Persistent Node.js worker** (not per-call subprocess)
  - [x] `ELKWorkerManager` class with request/response protocol
  - [x] UUID-based request correlation
  - [x] Thread-safe with proper atexit cleanup
  - [x] P&ID-specific layout options (orthogonal routing, layered algorithm)

- [x] **Task 4**: ELK Worker (Codex Consensus Fix #1)
  - [x] Created `src/layout/elk_worker.js` persistent worker
  - [x] stdin/stdout JSON protocol with newline delimiting
  - [x] Request format: `{"id": "uuid", "graph": {...}}`
  - [x] Response format: `{"id": "uuid", "result": {...}}`
  - [x] Proper error handling with stderr logging

- [x] **Task 5**: MCP Layout Tools
  - [x] Created `src/tools/layout_tools.py` with 8 MCP tools
  - [x] `layout_compute`: Compute layout using ELK algorithm
  - [x] `layout_get`: Retrieve stored layout
  - [x] `layout_update`: Update with etag requirement (Codex Consensus Fix #2)
  - [x] `layout_validate`: Schema and model consistency validation (Codex Consensus Fix #4)
  - [x] `layout_list`: List layouts filtered by model
  - [x] `layout_save_to_file` / `layout_load_from_file`: File persistence
  - [x] `layout_delete`: Remove layout from store

- [x] **Task 6**: sourcePoint/targetPoint Capture (Codex Consensus Fix #3)
  - [x] Updated `_elk_to_layout()` to capture edge endpoints
  - [x] High-fidelity edge routing for rendering

- [x] **Task 7**: Server Integration
  - [x] Integrated `LayoutTools` into `src/server.py`
  - [x] Added `layout_*` prefix routing

- [x] **Task 8**: Tests
  - [x] Created `tests/test_layout_system.py` (39 tests)
  - [x] Schema validation tests (8 tests)
  - [x] Store operations tests (6 tests)
  - [x] ELK engine tests (5 tests)
  - [x] Integration tests (2 tests)
  - [x] Layout Update tests (3 tests)
  - [x] Layout Validate tests (3 tests)
  - [x] MCP interface tests (6 tests)
  - [x] PID layout options tests (2 tests)
  - [x] Edge route tests (2 tests)
  - [x] File persistence tests (2 tests)

### Codex Consensus Fixes Applied

Per Codex review session #019adb91:

1. **Fix #1: Persistent ELK Worker** ✅
   - Replaced per-call subprocess with persistent worker process
   - Added ELKWorkerManager for process lifecycle management
   - Request/response protocol with UUID correlation

2. **Fix #2: layout_update with etag** ✅
   - Added `layout_update` MCP tool requiring `etag` parameter
   - Returns new etag and version on success
   - Returns `ETAG_MISMATCH` error on concurrent modification

3. **Fix #3: sourcePoint/targetPoint** ✅
   - Capture overall edge endpoints from ELK output
   - Stored in EdgeRoute for high-fidelity rendering

4. **Fix #4: layout_validate** ✅
   - Basic validation: schema, required fields, etag integrity
   - Model consistency: layout nodes match model topology
   - Recompute diff: re-run ELK and report position changes

5. **Deferred: model_revision hash**
   - Topology hash for stale detection deferred to next sprint

### Success Criteria

- [x] ✅ ELK integration operational with persistent worker
- [x] ✅ Layout metadata schema complete with etag computation
- [x] ✅ Thread-safe store with optimistic concurrency
- [x] ✅ 8 MCP tools fully functional
- [x] ✅ File persistence alongside models
- [x] ✅ 39 layout tests passing
- [x] ✅ 768 total tests passing

### Files Created

- `src/models/layout_metadata.py` - Extended with full layout schema
- `src/core/layout_store.py` - Thread-safe storage with etag concurrency
- `src/layout/__init__.py` - Package initialization
- `src/layout/engines/__init__.py` - Engines package
- `src/layout/engines/base.py` - Abstract base class for layout engines
- `src/layout/engines/elk.py` - ELK integration with persistent worker
- `src/layout/elk_worker.js` - Node.js persistent worker process
- `src/tools/layout_tools.py` - 8 MCP layout tools
- `tests/test_layout_system.py` - 39 comprehensive tests
- `docs/LAYOUT_SYSTEM.md` - Complete documentation
- `package.json` / `package-lock.json` - elkjs dependency

### Files Modified

- `src/server.py` - Integrated LayoutTools with layout_* routing
- `src/core/__init__.py` - Export layout store

**Week 8+ COMPLETE** ✅ - Layout System fully operational with 768 tests passing

---

## Week 8++: SVG/PDF Export via GraphicBuilder (COMPLETE)

**Theme**: "Enable production-quality SVG and PDF output from GraphicBuilder"

**Completed**: 2025-12-02
**Codex Consensus**: Multi-turn session vetted the implementation approach

### Key Discovery (Codex Analysis)

**GraphicBuilder already creates SVG as a side-effect!**

When `StandAloneTester` runs:
1. It uses `ImageFactory_SVG` internally
2. `gFac.writeToDestination()` writes `input.svg`
3. Then transcodes SVG DOM → PNG via Batik `PNGTranscoder`
4. Result: BOTH `input.svg` AND `input.png` exist after execution

**The Flask service was only reading `.png` and ignoring `.svg`**

This discovery made SVG support a zero-Java-change feature.

### Task Checklist

- [x] **Phase 1**: SVG Support (Zero Java Changes)
  - [x] Updated `graphicbuilder-service.py` to read `.svg` files
  - [x] SVG returned as text (not base64 encoded)
  - [x] `wrapper.py` already handled text vs binary responses correctly
  - [x] Added `allow_fallback` option for graceful degradation

- [x] **Phase 2**: PDF Support (Small Java Helper)
  - [x] Created `PDFConverter.java` (~55 lines) using Batik `PDFTranscoder`
  - [x] Updated Dockerfile to compile PDFConverter
  - [x] PDF returned as base64-encoded binary
  - [x] Cleanup handles all artifact files (.xml, .svg, .png, .pdf)

- [x] **Phase 3**: Update Renderer Router
  - [x] GraphicBuilder now supports `SVG`, `PNG`, `PDF` formats
  - [x] Removed `"png_only"` limitation flag
  - [x] Added `"svg_export"` and `"pdf_export"` features

- [x] **Phase 4**: Update Tests
  - [x] Updated `test_graphicbuilder_integration.py` for new SVG/PDF behavior
  - [x] Added `TestFormatSelectionRouting` test class
  - [x] Updated `test_orchestrator_integration.py` (PDF now supported)

### Files Modified

| File | Changes |
|------|---------|
| `src/visualization/graphicbuilder/graphicbuilder-service.py` | Read .svg for SVG, add PDF conversion |
| `src/visualization/graphicbuilder/PDFConverter.java` | NEW - Batik PDF transcoder (~55 lines) |
| `src/visualization/graphicbuilder/Dockerfile` | Compile PDFConverter.java |
| `src/visualization/orchestrator/renderer_router.py` | Enable SVG/PDF formats |
| `tests/test_graphicbuilder_integration.py` | Updated for SVG/PDF support |
| `tests/visualization/test_orchestrator_integration.py` | PDF now succeeds (was expected to fail) |

### Success Criteria

- [x] ✅ SVG output returns text content (not base64)
- [x] ✅ PNG output returns base64-encoded binary
- [x] ✅ PDF output returns base64-encoded binary via PDFConverter
- [x] ✅ Router selects GraphicBuilder for production SVG/PDF
- [x] ✅ All 758 tests passing (753 + 5 new router tests)

### Error Handling (Codex Recommendation)

- **Default**: Hard error if requested format not created (catch regressions early)
- **Optional**: `allow_fallback=True` in options returns PNG with warning in metadata
- **Cleanup**: Delete all artifacts after reading, skip cleanup on failure for debugging

**Week 8++ COMPLETE** ✅ - SVG/PDF export operational via GraphicBuilder

---

## Phase 3: Symbol Library Integration with Proteus-Viewer (COMPLETE)

**Theme**: "Integrate curated symbol library with proteus-viewer for consistent P&ID rendering"

**Started**: 2025-12-05
**Completed**: 2025-12-05
**Codex Review**: Validated plan with external-first lookup strategy

### Overview

Integrated our curated symbol library (`merged_catalog.json`) with the proteus-viewer to provide consistent, house-standard P&ID symbols with rich metadata (ports, bounding boxes, DEXPI mappings).

**Previous State**: Proteus-viewer only rendered symbols from embedded `<ShapeCatalogue>` in DEXPI XML.
**Current State**: Proteus-viewer uses our symbol library when available (external-first), with embedded shapes as fallback.

### Task Checklist

- [x] **Task 1**: Create Symbol Library Loader (TypeScript)
  - [x] Created `src/symbolLibrary/SymbolLibraryLoader.ts`
  - [x] Loads `merged_catalog.json` with 805 symbols
  - [x] Indexed by: DEXPI class (94 classes), identifier (805 symbols), partial search
  - [x] Lazy-loads SVG content from file paths

- [x] **Task 2**: Create SVG-to-PaperJS Converter
  - [x] Created `src/symbolLibrary/SvgToPaperJs.ts`
  - [x] Paper.js `importSVG()` with server-side compatibility
  - [x] `cloneForPlacement()` for safe multi-instance rendering
  - [x] `applyTransforms()` for position/scale/rotation
  - [x] `normalizeColors()` for engineering-standard black lines on white background

- [x] **Task 3**: Create Symbol Adapter (Component-compatible)
  - [x] Created `src/symbolLibrary/ExternalSymbol.ts`
  - [x] Type discriminator: `isExternalSymbol: boolean = true`
  - [x] Component-compatible `draw()` interface
  - [x] Clone-per-placement pattern (never mutate template)
  - [x] Anchor alignment and transform order matching XML shapes

- [x] **Task 4**: Extend shapeCatalogStore.ts
  - [x] Added external symbol lookup with multi-strategy cascade:
    1. External cache (cached ExternalSymbol instances)
    2. DEXPI class lookup from symbol library
    3. Identifier lookup for non-DEXPI names
    4. Partial name search (fallback)
    5. Embedded ShapeCatalogue (final fallback)
  - [x] Added `preferExternalSymbols` toggle (default: true)
  - [x] Added `clearExternalSymbolCache()` for memory management
  - [x] Union type: `ShapeCatalogItem = Component | ExternalSymbol`

- [x] **Task 5**: Initialize Symbol Library in Server
  - [x] Updated `src/server.ts` to initialize symbol library on startup
  - [x] Loads from `../../symbols/assets/merged_catalog.json`
  - [x] Health endpoint shows symbol library stats:
    - `symbolLibrary.initialized: true`
    - `symbolLibrary.preferExternal: true`
    - `symbolLibrary.embeddedCount: N`
    - `symbolLibrary.externalCacheCount: N`

- [x] **Task 6**: Add Configuration Option
  - [x] Added `useExternalSymbols` render option
  - [x] Per-request toggle for symbol source preference

### Architecture Decision

**Integration Point**: `getFromShapeCatalogStore()` in `shapeCatalogStore.ts`

This function is the single lookup bottleneck where all `componentName` references are resolved. Extended to:
1. **First** check our symbol library by DEXPI class (for corporate-standard consistency)
2. **Fall back** to embedded ShapeCatalogue if not found

**Key Design Choices**:
- External-first by default for consistent house-standard symbols
- Clone-per-placement to avoid cross-instance mutations
- Anchor alignment so connection points align with XML Position
- Transform order: translate → scale → rotate/flip (matching XML shapes)

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/symbolLibrary/SymbolLibraryLoader.ts` | ~250 | Load merged_catalog.json and SVG files |
| `src/symbolLibrary/SvgToPaperJs.ts` | ~200 | Convert SVG to Paper.js objects |
| `src/symbolLibrary/ExternalSymbol.ts` | ~150 | Component-compatible wrapper |
| `src/symbolLibrary/index.ts` | ~40 | Export all symbol library modules |

### Files Modified

| File | Changes |
|------|---------|
| `src/proteusXmlDrawing/shapeCatalogStore.ts` | Added external symbol lookup cascade |
| `src/proteusXmlDrawing/Component.ts` | Added ShapeCatalogItem union type |
| `src/server.ts` | Initialize symbol library, add health stats, add render option |

### Success Criteria

- [x] ✅ TypeScript builds without errors
- [x] ✅ Server starts with symbol library initialized
- [x] ✅ Health endpoint shows `symbolLibrary.initialized: true`
- [x] ✅ External-first lookup operational (`preferExternal: true`)
- [x] ✅ Graceful fallback to embedded ShapeCatalogue
- [x] ✅ Clone-per-placement prevents cross-instance mutations
- [x] ✅ Per-request toggle via `useExternalSymbols` option

### Health Endpoint Example

```json
{
  "status": "healthy",
  "service": "proteus-viewer",
  "version": "0.3.0",
  "capabilities": ["svg", "html", "png"],
  "symbolLibrary": {
    "initialized": true,
    "preferExternal": true,
    "embeddedCount": 2,
    "externalCacheCount": 0
  }
}
```

**Phase 3 COMPLETE** ✅ - Symbol library integration operational with external-first lookup
