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

### Week 2: Remove model_service.py 🚧 IN PROGRESS
- [ ] Delete `src/visualization/orchestrator/model_service.py` (537 lines per `wc -l`)
- [ ] Swap orchestration + callers to `core.conversion.get_engine().sfiles_to_dexpi` (`src/core/conversion.py:333-418`, `707-712`)
- [ ] Update `tests/visualization/test_orchestrator_integration.py:15-205` (10 tests) to drop `ModelService`

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
- Validation script: `python3 scripts/validate_symbol_catalog.py` currently passes
