# Engineering MCP Server
## Structured P&ID and Flowsheet Generation for LLM Agents

The Engineering MCP Server exposes pyDEXPI (DEXPI P&IDs) and SFILES2 (BFD/PFD flowsheets) through Anthropic's Model Context Protocol so language-model agents can create, modify, analyze, and persist process-engineering diagrams entirely in machine-readable formats.

This repository prioritizes data fidelity over drawing aesthetics: the authoritative artifacts are JSON/SFILES models tracked in git, with optional Plotly-based HTML visualizations and GraphML exports generated from the same state.

---

## Current Capabilities

- **Complete pyDEXPI Coverage (Phase 2)** – All **272 pyDEXPI classes** are now accessible: 159 equipment types, 79 piping types, and 34 instrumentation types. Both SFILES aliases (e.g., `pump`, `heat_exchanger`) and DEXPI class names (e.g., `CentrifugalPump`, `PlateHeatExchanger`) are accepted. See [`docs/EQUIPMENT_CATALOG.md`](docs/EQUIPMENT_CATALOG.md) for the complete catalog and [`docs/USER_MIGRATION_GUIDE.md`](docs/USER_MIGRATION_GUIDE.md) for usage guidance.
- **Production-Ready Symbol Mapping (Phase 3)** – 185/272 components mapped (68.0% coverage): 100% instrumentation (34/34), 85% piping (67/79), and 53% equipment (84/159). The remaining 87 unmapped components are specialized/abstract classes validated as acceptable by Codex review.
- **Proteus XML 4.2 Export** – Comprehensive pyDEXPI → Proteus XML exporter with complete attribute coverage. Exports equipment, piping (with CenterLine geometry), instrumentation (with actuating functions and signal connectors), nozzle connection points, and GenericAttributes. Features "fail loudly" validation with clear error messages. See [`docs/proteus_export_gap_analysis.md`](docs/proteus_export_gap_analysis.md) for implementation details. 45/45 tests passing with XSD validation and round-trip fidelity verified.
- **DEXPI P&ID tooling** – 14 MCP tools for creating models, adding equipment/piping/instrumentation, importing/exporting, and inserting inline valves (`src/tools/dexpi_tools.py`).
- **SFILES BFD/PFD tooling** – 12 MCP tools for flowsheet construction, stream management, canonicalization, regex validation, and conversions from/to DEXPI (`src/tools/sfiles_tools.py`).
- **Git-native persistence** – Project tools (`project_init/save/load/list`) wrap `src/persistence/project_persistence.py`, storing JSON/SFILES plus metadata, GraphML, and Plotly HTML in per-model folders with automatic commits.
- **Template deployment** – `template_list`, `template_get_schema`, and `area_deploy` expose four YAML templates (`library/patterns/*.yaml`): pump_basic, pump_station_n_plus_1, tank_farm, and heat_exchanger_with_integration.
- **Validation & analytics** – Schema introspection (`schema_*`), validation (`validate_model`, `validate_round_trip`), graph analytics (`graph_*`), search (`search_*`, `query_model_statistics`), and batch automation (`model_batch_apply`, `rules_apply`, `graph_connect`).
- **Visualization outputs** – Project saves produce Plotly-based interactive HTML files (with SVG/PDF exports via Plotly's toolbar) and GraphML topology exports. GraphicBuilder integration provides production-quality PNG rendering from Proteus/DEXPI XML (validated with official DEXPI TrainingTestCases). There is no standalone dashboard service; visual review happens through the generated HTML files.
- **Phase 4 Tool Consolidation** – 58 legacy atomic tools have been consolidated into 12 unified tools (79% reduction), providing both direct API access and ACID transaction support. See [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md) for the complete migration guide mapping legacy → consolidated tools.

---

## MCP Tool Catalog (as registered in `src/server.py`)

### DEXPI Tools
`dexpi_create_pid`, `dexpi_add_equipment`, `dexpi_add_piping`, `dexpi_add_instrumentation`, `dexpi_add_control_loop`, `dexpi_connect_components`, `dexpi_validate_model`, `dexpi_export_json`, `dexpi_export_graphml`, `dexpi_import_json`, `dexpi_import_proteus_xml`, `dexpi_add_valve`, `dexpi_add_valve_between_components`, `dexpi_insert_valve_in_segment`, `dexpi_convert_from_sfiles`.

### SFILES Tools
`sfiles_create_flowsheet`, `sfiles_add_unit`, `sfiles_add_stream`, `sfiles_to_string`, `sfiles_from_string`, `sfiles_export_networkx`, `sfiles_export_graphml`, `sfiles_add_control`, `sfiles_parse_and_validate`, `sfiles_canonical_form`, `sfiles_pattern_helper`, `sfiles_convert_from_dexpi`.

### Project & Persistence Tools
`project_init`, `project_save`, `project_load`, `project_list`.

### Validation & Schema Tools
`validate_model`, `validate_round_trip`, plus `schema_list_classes`, `schema_describe_class`, `schema_find_class`, `schema_get_hierarchy`.

### Graph, Search, Batch, and Template Tools
- Graph analytics: `graph_analyze_topology`, `graph_find_paths`, `graph_detect_patterns`, `graph_calculate_metrics`, `graph_compare_models`.
- Search & statistics: `search_by_tag`, `search_by_type`, `search_by_attributes`, `search_connected`, `query_model_statistics`, `search_by_stream`.
- Batch/automation: `model_batch_apply`, `rules_apply`, `graph_connect`.
- Templates: `template_list`, `template_get_schema`, `area_deploy`.

### Visualization Tools (Weeks 5-6)
- `visualize_model` - Generate HTML (Plotly), PNG (GraphicBuilder), or GraphML from DEXPI/SFILES models with auto model-type detection and intelligent renderer selection
- `visualize_list_renderers` - List available renderers with capabilities and health status

### Layout Tools (NEW - Week 8+)
- `layout_compute` - Compute automatic layout using ELK algorithm (layered, orthogonal routing)
- `layout_get` - Retrieve stored layout with positions, edges, ports
- `layout_update` - Update layout with etag-based optimistic concurrency control
- `layout_validate` - Validate layout schema and model consistency
- `layout_list` - List layouts, optionally filtered by model
- `layout_save_to_file` / `layout_load_from_file` - Persist layouts to project files
- `layout_delete` - Remove layout from store

> **Phase 4 Update:** The consolidated tools (`model_create`, `model_load`, `model_save`, `model_tx_begin`, `model_tx_apply`, `model_tx_commit`, `schema_query`, `search_execute`, and `graph_modify`) are now **production-ready** and exposed by the MCP server. Legacy atomic tools remain available for backward compatibility. See [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md) for migration guidance.

> **Layout System Update (Dec 2025):** Complete Layout Layer with ELK integration. Persistent Node.js worker for efficient layout computation, etag-based concurrency control, file persistence alongside models. See [`docs/LAYOUT_SYSTEM.md`](docs/LAYOUT_SYSTEM.md) for details.

---

## Architecture Overview

| Component | Purpose |
|-----------|---------|
| `src/server.py` | Registers MCP handlers and routes tool calls to category handlers.
| `src/tools/*` | Tool implementations grouped by domain (DEXPI, SFILES, project, validation, schema, graph, search, batch, templates, visualization).
| `src/tools/visualization_tools.py` | MCP visualization tools with RendererRouter integration (Weeks 5-6).
| `src/tools/layout_tools.py` | MCP layout tools for ELK-based automatic positioning (Week 8+).
| `src/layout/engines/elk.py` | Persistent ELK worker integration for layout computation.
| `src/persistence/project_persistence.py` | Saves/loads models, writes metadata, GraphML, and Plotly HTML artifacts, and performs git commits.
| `src/templates/*.py` + `library/patterns/*.yaml` | Parametric template engine and YAML catalog (4 templates).
| `src/managers/transaction_manager.py` & `src/registry/operation_registry.py` | ACID transaction infrastructure for `model_tx_*` tools (Phase 4 complete, production-ready).
| `tests/` | Pytest suites covering graph export, template tooling, and TransactionManager behavior.

---

## Installation & Quick Start

1. **Clone & set up environment** (see [SETUP.md](SETUP.md) for full instructions):
   ```bash
   git clone https://github.com/yourusername/engineering-mcp-server.git
   cd engineering-mcp-server
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Validate core imports**:
   ```bash
   python -c "from src.tools.dexpi_tools import DexpiTools; from src.tools.sfiles_tools import SfilesTools; print('OK')"
   ```
3. **Run the MCP server**:
   ```bash
   python -m src.server
   ```
4. **Add to an MCP client** (e.g., `.mcp.json` for Claude Code or Codex CLI) pointing to `python -m src.server`.

---

## Example MCP Workflow

1. **Create a DEXPI P&ID** using `dexpi_create_pid`.
2. **Add equipment and piping** via `dexpi_add_equipment`, `dexpi_add_piping`, and `dexpi_connect_components` (or batch via `model_batch_apply`).
3. **Validate** with `validate_model` or `validate_round_trip`.
4. **Save to a git project**:
   - `project_init` to scaffold `pid/`, `pfd/`, `bfd/` directories.
   - `project_save` to persist JSON, metadata, GraphML, and Plotly HTML (commits automatically).
5. **Inspect outputs** by opening the generated `<model>.html` or `<model>.graphml` files in your browser/tooling of choice.

A similar flow applies to SFILES models using the `sfiles_*` tools and conversions between representations.

---

## Visualization & Data Exports

### Visualization Philosophy

This system provides **two complementary visualization approaches** serving different purposes:

#### Plotly HTML (Topology Analysis)
- **Purpose**: Fast topology visualization for connectivity analysis and debugging
- **What it shows**: Network graph with nodes (equipment) and edges (connections)
- **Layout**: Spring/force-directed layout (automatic positioning)
- **Symbols**: No symbols - abstract nodes only
- **Speed**: <1 second generation time
- **Use case**: Development iteration, flow analysis, bottleneck detection
- **Generated**: Automatically during `project_save`

#### GraphicBuilder (Engineering Documentation)
- **Purpose**: Production-quality P&ID rendering for engineering deliverables
- **What it shows**: Proper P&ID with ISA-compliant symbols, spatial layout, annotations
- **Layout**: Proteus XML positioning (requires layout data)
- **Symbols**: Uses all 701 NOAKADEXPI symbols (from Phase 3 mapping work)
- **Speed**: 2-15 seconds depending on complexity
- **Use case**: Final documentation, compliance, client deliverables
- **Generated**: On-demand via GraphicBuilder Docker service
- **Current Status**: PNG rendering validated with DEXPI TrainingTestCases (SVG/PDF pending Java API integration)

**Both approaches are complementary** - Plotly for rapid iteration, GraphicBuilder for final outputs.

### Data Export Formats

| Output | How it's produced | Notes |
|--------|-------------------|-------|
| HTML (Plotly) | Generated during `project_save` for DEXPI and SFILES models | Interactive hover details, Plotly toolbar can export PNG/SVG locally.
| PNG (GraphicBuilder) | GraphicBuilder Docker service (`src/visualization/graphicbuilder/`) renders Proteus/DEXPI XML to production-quality PNG | Validated with official DEXPI TrainingTestCases. Requires Proteus XML export (planned).
| GraphML | `dexpi_export_graphml`, `sfiles_export_graphml`, and automatic exports during `project_save` | Suitable for NetworkX or external graph tooling.
| JSON/SFILES | Primary storage formats; accessible via import/export tools | Git-friendly text files.

**Symbol Library Status**: Phase 3 mapped 185/272 components (68.0% coverage) with 100% instrumentation coverage. These mappings are used by GraphicBuilder and future symbol-based renderers. Plotly visualizations do not use symbols.

---

## Templates

`library/patterns/` currently contains four YAML templates surfaced through `template_*` tools:

- `pump_basic.yaml`
- `pump_station_n_plus_1.yaml`
- `tank_farm.yaml`
- `heat_exchanger_with_integration.yaml`

Each template exposes typed parameters (see `template_get_schema`) and can be instantiated into DEXPI or SFILES models via `area_deploy`.

---

## Roadmap & Completed Work

**Phase 2 (Completed):** Complete pyDEXPI Component Coverage
- ✅ ComponentRegistry integration – Unified registry for all 272 pyDEXPI classes
- ✅ 5.3x equipment expansion – From ~30 to 159 equipment types
- ✅ Dual naming support – Both SFILES aliases and DEXPI class names accepted
- ✅ Complete piping coverage – All 79 piping types now available
- ✅ Complete instrumentation – All 34 instrumentation types create correct pyDEXPI classes
- ✅ 46/46 tests passing (22 registry + 12 schema + 12 other)
- ✅ User documentation: [Equipment Catalog](docs/EQUIPMENT_CATALOG.md), [Migration Guide](docs/USER_MIGRATION_GUIDE.md), [Usage Examples](docs/MCP_TOOL_EXAMPLES.md)
- ✅ Zero breaking changes – 100% backward compatible

**Phase 3 (Completed):** Symbol Mapping for Visualization
- ✅ High-visibility components mapped – 42 targets (valves, rotating equipment, instrumentation)
- ✅ Long-tail coverage completed – 185/272 components mapped (68.0% coverage)
- ✅ 100% instrumentation coverage (34/34), 85% piping (67/79), 53% equipment (84/159)
- ✅ Production-ready per Codex review – Remaining 87 placeholders are specialized/abstract components
- ✅ SymbolMapper extended – 168 new mappings (24 → 192 total in KNOWN_MAPPINGS)
- ✅ Analysis tools created – `scripts/analyze_symbol_gaps.py`, `scripts/suggest_symbol_mappings.py`
- ✅ Documentation: [`docs/PHASE3_PASS1_COMPLETE.md`](docs/PHASE3_PASS1_COMPLETE.md), [`docs/PHASE3_PASS2_COMPLETE.md`](docs/PHASE3_PASS2_COMPLETE.md)
- ✅ All 22 ComponentRegistry tests passing, zero breaking changes

**Phase 4 (Completed):** Tool consolidation and transaction support
- ✅ `model_create`, `model_load`, `model_save` – Unified model lifecycle (replaces 9 legacy tools)
- ✅ `model_tx_begin`, `model_tx_apply`, `model_tx_commit` – ACID transactions for atomic multi-operation changes
- ✅ `schema_query` – Unified schema introspection (replaces 4 legacy tools)
- ✅ `search_execute` – Unified search interface (replaces 6 legacy tools)
- ✅ `graph_modify` – Tactical graph modifications (10 actions available)
- ✅ 150/150 tests passing with full coverage of consolidated tools
- ✅ Live MCP testing validated all 12 consolidated tools
- ✅ Migration guide: [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md)

**Phase 5 Week 3 (Completed):** Symbol Registry + Tool Refactor
- ✅ Symbol Registry Consolidation – Created `src/core/symbol_resolver.py` with 3 capabilities (actuated variants, fuzzy matching, validation)
- ✅ Replaced `src/visualization/symbols/mapper.py` with deprecation wrapper
- ✅ Added 31 comprehensive tests for SymbolResolver (all passing)
- ✅ Routed instrumentation to `instrumentation_toolkit` – Modified `src/tools/dexpi_tools.py` to use pyDEXPI toolkits
- ✅ Replaced component lookup with `model_toolkit` – Removed manual traversal (27 lines → 16 lines)
- ✅ Documented `dexpi_introspector` relationship – ACTIVE, complementary to base_model_utils
- ✅ Full test suite: 437 passed, 3 skipped, zero breaking changes

**Phase 5 Week 4 (Completed):** GraphicBuilder Integration
- ✅ GitLab source pinning – Dockerfile with ARG-based version pinning, Java 8 compatible
- ✅ Service integration – Fixed Flask wrapper to work with GraphicBuilder CLI limitations
- ✅ Validation with DEXPI TrainingTestCases – PNG rendering validated (6000x5276 output)
- ✅ Comprehensive documentation – [`README.md`](src/visualization/graphicbuilder/README.md) (420+ lines) with CLI limitations documented
- ✅ Test coverage – 17 tests (15 passing, 2 skipped pending Proteus export)
- ✅ Router integration – Pre-existing, functional, fallback tested
- ✅ Symbol library – 701 NOAKADEXPI symbols mounted
- **Status:** Functional for PNG rendering, SVG/PDF pending Java API integration

**Week 8+ (Completed):** Layout System with ELK Integration
- ✅ Complete Layout Layer – LayoutMetadata schema, LayoutStore, ELK engine integration
- ✅ Persistent ELK Worker – Node.js worker process with request/response protocol (Codex Consensus #019adb91)
- ✅ 8 MCP Tools – layout_compute, layout_get, layout_update, layout_validate, layout_list, layout_save_to_file, layout_load_from_file, layout_delete
- ✅ Optimistic Concurrency – Etag-based updates with ETAG_MISMATCH error handling
- ✅ File Persistence – Layouts stored alongside models in project structure
- ✅ 39 Layout Tests – Full coverage of schema, store, engine, and MCP tools
- ✅ 768 Total Tests Passing
- **Documentation:** [`docs/LAYOUT_SYSTEM.md`](docs/LAYOUT_SYSTEM.md)

**Planned Work:**
1. **ProteusXMLDrawing Integration** – Fork `src/visualization/proteus-viewer/` backend with text/spline fixups, WebSocket/live update path, expose through MCP visualize tools.
2. **SFILES2 Visualization** – Expose `SFILES2.visualize_flowsheet()` via `src/tools/sfiles_tools.py`, ship stream/unit tables + OntoCape tags in outputs.
3. **Additional templates** – Library currently has 4 patterns; expansion to 5+ and beyond is tracked in `docs/templates/template_system.md`.
4. **Rendering Integration** – Wire Layout Layer into visualization pipeline for coordinate-based rendering.

Refer to [`IMPLEMENTATION_PROGRESS.md`](IMPLEMENTATION_PROGRESS.md) for detailed progress tracking.

---

## License

Released under the GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE) for details.
