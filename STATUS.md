# Engineering MCP Server - Status

**Last Updated:** 2025-11-11  
**Current Phase:** Phase 5 Week 2 (Nov 17-24, 2025)

## Completed Phases

- [x] Phase 0: Symbol IDs standardized to PP001A in `src/core/equipment.py:144-210` (commit 8038825)
- [x] Phase 1: Core conversion adopted by dexpi/sfiles/validation tools via `core.conversion.get_engine()` (`ddd4cab`, `95a4df0`, `8ac1252`, `1a9681a`)
- [x] Phase 2: Schema + graph/search toolset merged (commit `b1a3bf8`, exercised by `tests/test_migration_equivalence.py`)
- [x] Phase 3: Unified intelligence tooling + regression suite complete (commit `c4292c4`)
- [x] Phase 4: Visualization architecture aligned with upstream (commit `a80bfd8`, README/ROADMAP updated)

## Phase 5: Upstream Integration (8 weeks)

### Week 1: Visualization Blockers ✅ COMPLETE (Nov 10, 2025)
- [x] Symbol catalog 308/805 mapped via `scripts/validate_symbol_catalog.py` (run 2025-11-11; commit `351abcd`)
- [x] Nozzle defaults DEXPI-compliant in `src/core/equipment.py:477-551`
- [x] Validation script regression guards live in `scripts/validate_symbol_catalog.py`

### Week 2: Remove model_service.py + Coverage Gap Resolution ✅ COMPLETE (Nov 11, 2025)
- [x] Created `src/core/analytics/model_metrics.py` with metadata/validation/complexity functions
- [x] Deleted `src/visualization/orchestrator/model_service.py` (537 lines removed)
- [x] Swapped orchestration to use `core.conversion.get_engine().sfiles_to_dexpi`
- [x] Updated `tests/visualization/test_orchestrator_integration.py` (10/10 tests passing)
- [x] **CRITICAL FINDING**: 89% coverage gap discovered across ALL pyDEXPI categories
- [x] **PHASE 1 COMPLETE**: Auto-generated registrations for ALL 272 pyDEXPI classes (<2 hours total)
  - Equipment: 159/159 classes ✅
  - Piping: 79/79 classes ✅
  - Instrumentation: 34/34 classes ✅
  - 27 families with 1:Many mappings
- [x] **PHASE 2.1 COMPLETE**: Core Layer Integration (Nov 11, 2025)
  - Created `src/core/components.py` with unified ComponentRegistry (519 lines)
  - All 272 classes imported and registered
  - Family mappings operational (27 families, 1:Many support)
  - Category filtering working (25 categories across 3 types)
  - Integrated with EquipmentFactory for backward compatibility
  - All tests passing (10/10 orchestrator tests + integration tests)
- [x] **CODEX REVIEW & FIXES** (Nov 11, 2025)
  - Fixed CSV packaging (moved to src/core/data/, declared as package data)
  - Fixed import path (relative import for get_registry)
  - Added DEXPI class name support in EquipmentFactory
  - Preserved category metadata (ComponentCategory → EquipmentCategory mapping)
  - Made CSV loading fail-fast (RuntimeError if missing)
  - Added 22 unit tests for ComponentRegistry (all passing)
- [x] **PHASE 2.2 COMPLETE**: MCP Tool Schema Updates (Nov 11, 2025)
  - Updated all 4 MCP tool schemas to expose ALL 272 classes
  - Replaced DexpiIntrospector with ComponentRegistry-based enums
  - Enhanced tool descriptions with examples and type counts
  - Updated piping implementation to support all 79 piping types
  - Created 12 smoke tests for schema coverage (all passing)
  - Total test coverage: 46 tests (22 registry + 12 schema + 12 other)
  - **ALL 272 pyDEXPI classes now accessible to Claude AI users** ✅

### Week 3: Symbol Registry + Tool Refactor (Pending)
- [ ] Retire `src/visualization/symbols/mapper.py` (283 lines duplicating `core/symbols.py`)
- [ ] Route `src/tools/dexpi_tools.py:475-640` instrumentation to `instrumentation_toolkit`
- [ ] Replace manual nozzle/lookup helpers in `src/tools/dexpi_tools.py:680-735` with `model_toolkit`/`piping_toolkit`
- [ ] Deprecate `src/tools/dexpi_introspector.py` (467 lines) in favor of `base_model_utils`

### Week 4: GraphicBuilder Integration (Pending)
- [ ] Add `docker/graphicbuilder/Dockerfile` pinned to GitLab source
- [ ] Wire `src/visualization/orchestrator/renderer_router.py` to route GraphicBuilder jobs
- [ ] Import 30-40 NOAKADEXPI symbols + metadata into `src/visualization/symbols/assets/`

### Week 5: ProteusXMLDrawing Integration (Pending)
- [ ] Fork `src/visualization/proteus-viewer/` backend with text/spline fixups
- [ ] Add WebSocket/live update path + regression tests
- [ ] Expose Proteus renderer through MCP visualize tools

### Week 6: SFILES2 Visualization (Pending)
- [ ] Expose `SFILES2.visualize_flowsheet()` via `src/tools/sfiles_tools.py`
- [ ] Ship stream/unit tables + OntoCape tags in outputs
- [ ] Document SFILES2 v1.1.1 + monitor issues #9-#12

### Week 7: Toolkit Adoption (Pending)
- [ ] Enforce `model_toolkit`, `instrumentation_toolkit`, `piping_toolkit` for all MCP tools
- [ ] Remove manual traversal helpers from remaining scripts
- [ ] Add ≥20 toolkit regression tests

### Week 8: No-Fallback Enforcement (Pending)
- [ ] Delete CustomEquipment fallbacks (e.g., `src/tools/pfd_expansion_engine.py:278-303`, `src/visualization/symbols/mapper.py:167`)
- [ ] Add CI tests + docs for the "No registries.py" fail-fast policy

## Key Metrics
- Symbol coverage: 308/805 (38.3%) from `scripts/validate_symbol_catalog.py`
- Equipment coverage: 289/377 (76.7%) from the same validation run
- **DEXPI class coverage: 272/272 (100%) - REGISTRATION DATA READY** ✅
  - **Phase 1 complete**: ALL 272 pyDEXPI classes enumerated and registration data generated
  - **Equipment**: 159/159 classes, 16 families, 8 categories (ROTATING: 41, SEPARATION: 30, etc.)
  - **Piping**: 79/79 classes, 6 valve families, 8 categories (VALVE: 22, FLOW_MEASUREMENT: 10, etc.)
  - **Instrumentation**: 34/34 classes, 5 families, 9 categories (SIGNAL: 13, ACTUATING: 9, etc.)
  - **Total families**: 27 with 1:Many mappings defined
  - **Symbols**: 26 real (equipment), rest placeholders (can be mapped in Phase 2)
  - **Next**: Phase 2 integration into core layer (8-12 hours)
- Validation script: `python3 scripts/validate_symbol_catalog.py` currently passes
