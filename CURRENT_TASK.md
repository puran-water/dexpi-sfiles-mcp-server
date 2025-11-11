# Current Task: Remove model_service.py Duplication

**Week:** Phase 5 Week 2 (Nov 17-24, 2025)  
**Priority:** CRITICAL  
**Impact:** -537 lines, eliminates redundant conversion pipeline

## Files to Modify

### Remove
- `src/visualization/orchestrator/model_service.py` (537 lines via `wc -l`)
  - Lines 376-402: inline regex SFILES parser duplicates `src/core/conversion.py:110-207`
  - Lines 409-456: BFD expansion + fallback mirrors `src/core/conversion.py:333-399`
  - Lines 459-496: manual equipment instantiation overlaps `src/core/conversion.py:622-628` and `src/core/equipment.py:144-210`
  - Lines 174-360: metadata/validation/statistics helpers must move into the core layer instead of visualization

### Update (Callers)
- `tests/visualization/test_orchestrator_integration.py:15-205`
  - Only runtime import of `ModelService` (`rg` limited to src/tests)
  - All 10 tests call `enrich_sfiles_to_dexpi`, `extract_metadata`, `validate_model`, `get_model_statistics`
  - Replace fixture with shared helpers: `core.conversion.get_engine()` for conversion (see `src/core/conversion.py:333-418`, `707-712`), new core metrics helper for metadata/stats, and validation pulled from `src/tools/validation_tools.py:1-200`

## Replacement Strategy

1. Extract metadata/validation/complexity logic from `model_service.py:174-360` into a reusable module (e.g., `src/core/analytics/model_metrics.py`) so every layer calls the same helpers.
2. Reuse the existing conversion singleton:
   ```python
   from src.core.conversion import get_engine

   engine = get_engine()
   dexpi_model = engine.sfiles_to_dexpi(sfiles_string)
   ```
3. Surface validation by refactoring `src/tools/validation_tools.py` internals into callable helpers (instead of standalone async MCP handlers) so visualization code can synchronously check models.
4. Provide a `summarize(model: DexpiModel)` helper that returns the metadata/validation/complexity dictionary formerly produced by `ModelService.get_model_statistics`.
5. Update the visualization integration test suite to import the new helpers, then delete `model_service.py`.

## Implementation Steps

1. [ ] Create `src/core/analytics/model_metrics.py` with `extract_metadata`, `validate_model`, and `summarize` functions moved verbatim (and improved) from `model_service.py:174-360`.
2. [ ] Refactor `src/tools/validation_tools.py` so its validation routines can be invoked directly by the new metrics helper without MCP scaffolding.
3. [ ] Replace all `ModelService` usage in `tests/visualization/test_orchestrator_integration.py:15-205` with `get_engine()` + the new metrics helper.
4. [ ] Remove `src/visualization/orchestrator/model_service.py` and any stale imports or docs that reference it.
5. [ ] Run visualization + core regression tests and capture results.

## Success Criteria

- [ ] No file imports `visualization.orchestrator.model_service`
- [ ] `src/visualization/orchestrator/model_service.py` deleted from the repository
- [ ] Conversion path uses `core.conversion.get_engine()` exclusively
- [ ] Metadata/validation/statistics helpers live under `src/core` with accompanying tests
- [ ] Visualization integration suite (10 tests) passes using the new adapter

## Testing

Run: `pytest tests/visualization/test_orchestrator_integration.py -v`  
Expected: 10 tests succeed using `core.conversion` + the shared metrics helper
