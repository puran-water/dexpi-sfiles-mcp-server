# Engineering MCP Server - Development Roadmap

**Last Updated:** 2026-01-22

This document tracks completed work and planned development for the Engineering MCP Server.

---

## Completed Work

### Phase 2: Complete pyDEXPI Component Coverage

- All **272 pyDEXPI classes** accessible: 159 equipment, 79 piping, 34 instrumentation
- ComponentRegistry integration with unified registry
- Dual naming support (SFILES aliases and DEXPI class names)
- 46/46 tests passing
- Zero breaking changes

### Phase 3: Symbol Mapping for Visualization

- 185/272 components mapped (68.0% coverage)
- 100% instrumentation (34/34), 85% piping (67/79), 53% equipment (84/159)
- SymbolMapper extended with 168 new mappings
- Analysis tools: `scripts/analyze_symbol_gaps.py`, `scripts/suggest_symbol_mappings.py`

### Phase 4: Tool Consolidation

- 58 legacy tools consolidated into 12 unified tools (79% reduction)
- ACID transaction support via `model_tx_begin`, `model_tx_apply`, `model_tx_commit`
- Unified model lifecycle: `model_create`, `model_load`, `model_save`
- 150/150 tests passing
- Migration guide: `docs/FEATURE_PARITY_MATRIX.md`

### Phase 5: Symbol Registry + Tool Refactor

- Symbol Registry Consolidation in `src/core/symbol_resolver.py`
- Instrumentation routed to `instrumentation_toolkit`
- Component lookup via `model_toolkit`
- 437 tests passed

### GraphicBuilder Integration (Week 4)

- GitLab source pinning with Java 8 compatibility
- PNG rendering validated with DEXPI TrainingTestCases
- 701 NOAKADEXPI symbols mounted
- Router integration with fallback

### Layout System (Week 8+)

- Complete Layout Layer with ELK integration
- Persistent Node.js worker for layout computation
- 8 MCP tools: `layout_compute`, `layout_get`, `layout_update`, `layout_validate`, `layout_list`, `layout_save_to_file`, `layout_load_from_file`, `layout_delete`
- Etag-based optimistic concurrency control
- 39 layout tests, 768 total tests passing

### Codex Deep Review (January 2026)

- SFILES2 native parsing via `Flowsheet.create_from_sfiles()`
- Proper piping connections using `piping_toolkit.connect_piping_network_segment()`
- ConceptualModel field preservation via in-place mutation
- MLGraphLoader validation standardization
- Fixed nozzle connectivity logic (removed non-existent `pipingConnection` checks)
- Fixed silent exception swallowing in conversion
- Fixed operation registry attributes (`segment.id`, `pns.segments`)
- Fixed `resolve_process_type` import path
- Aligned dependency versions
- Companion skills updated with correct MCP tool signatures
- New dexpi-schedules-skill

See `docs/completed-plans/2026-01-22-codex-deep-review.md` for full details.

---

## Active Work

### Core Layer Migration

**Status:** IN PROGRESS
**Document:** `docs/active/CORE_LAYER_MIGRATION_PLAN.md`

- Phase 0: Symbol Format Standardization - COMPLETE
- Phase 1: Core layer stabilization - COMPLETE
- Remaining: `catalog.py` migration

### Visualization Platform

**Status:** SVG/PDF EXPORT COMPLETE
**Document:** `docs/active/VISUALIZATION_PLAN.md`

- Week 1: Core integration, bug fixes - COMPLETE
- Weeks 2-6: MCP visualization tools - COMPLETE
- Week 8+: Layout System - COMPLETE
- Remaining: ProteusXMLDrawing integration

---

## Planned Work

### ProteusXMLDrawing Integration
Fork `src/visualization/proteus-viewer/` backend with text/spline fixups, WebSocket/live update path, expose through MCP visualize tools.

### SFILES2 Visualization
Expose `SFILES2.visualize_flowsheet()` via `src/tools/sfiles_tools.py`, ship stream/unit tables + OntoCape tags in outputs.

### Additional Templates
Library currently has 4 patterns; expansion to 5+ tracked in `docs/templates/template_system.md`.

### Rendering Integration
Wire Layout Layer into visualization pipeline for coordinate-based rendering.

---

## Documentation Structure

| Location | Purpose |
|----------|---------|
| `ROADMAP.md` | This file - development progress and plans |
| `README.md` | User-facing documentation |
| `CLAUDE.md` | Coding agent instructions |
| `SETUP.md` | Installation guide |
| `docs/active/` | Active planning documents |
| `docs/completed-plans/` | Completed work documentation |
| `docs/api/` | API specifications |
| `docs/architecture/` | Architecture documentation |

---

## Version History

| Date | Milestone |
|------|-----------|
| 2026-01-22 | Codex Deep Review - core conversion fixes |
| 2025-12-02 | SVG/PDF Export via GraphicBuilder |
| 2025-12-01 | Layout System v0.8.0 |
| 2025-11-30 | ComponentRegistry migration |
| 2025-11-14 | Proteus XML 4.2 export |
| 2025-11-10 | Visualization Week 1 |
| 2025-01-09 | Bug Surfacing Sprint |
