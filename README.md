# Engineering MCP Server

> **⚠️ DEVELOPMENT STATUS: This project is under active development and is not yet production-ready. APIs, interfaces, and functionality may change without notice. Use at your own risk for evaluation and testing purposes only. Not recommended for production deployments.**

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

> **Phase 4 Update:** The consolidated tools (`model_create`, `model_load`, `model_save`, `model_tx_begin`, `model_tx_apply`, `model_tx_commit`, `schema_query`, `search_execute`, and `graph_modify`) are now **implemented** and exposed by the MCP server. Legacy atomic tools remain available for backward compatibility. See [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md) for migration guidance.

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
| `src/managers/transaction_manager.py` & `src/registry/operation_registry.py` | ACID transaction infrastructure for `model_tx_*` tools (Phase 4 complete).
| `tests/` | Pytest suites covering graph export, template tooling, and TransactionManager behavior.

---

## Dependencies

### Core Libraries (Pinned Versions)

This project depends on two research libraries from the Process Intelligence Research group:

| Library | Version | Commit SHA | Notes |
|---------|---------|------------|-------|
| **pyDEXPI** | v1.1.0 (Sept 2025) | `174321e3575f1488e0fc533d5f61b27a822bd549` | DEXPI P&ID model library - stable equipment/piping APIs |
| **SFILES2** | June 2025 | `fdc57617be9bcee319af5bb0249667189161dc87` | Flowsheet notation library - includes stream params on edges fix |

These versions are pinned in `pyproject.toml` to ensure reproducible builds. If you need to upgrade:
1. Test with the new commit locally
2. Update the SHA in `pyproject.toml`
3. Update this table
4. Run full test suite (`pytest tests/`)

**Known Upstream Issues:**
- SFILES2 #12: `merge_HI_nodes`/`split_HI_nodes` bugs affect heat integration scenarios (workaround: guards in conversion code)
- SFILES2 #10: MultiDiGraph support incomplete (affects parallel edges)
- pyDEXPI: `ProteusSerializer.save()` is NotImplementedError (affects nozzle metadata export)

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

## Development Status

For the complete development roadmap including completed phases and planned work, see **[ROADMAP.md](ROADMAP.md)**.

### Recent Highlights

- **Codex Deep Review (January 2026):** Core conversion fixes including SFILES2 native parsing, proper piping connections, and pyDEXPI API corrections. See [`docs/completed-plans/2026-01-22-codex-deep-review.md`](docs/completed-plans/2026-01-22-codex-deep-review.md).

- **Layout System (December 2025):** Complete ELK-based automatic layout with 8 MCP tools, optimistic concurrency, and file persistence. See [`docs/LAYOUT_SYSTEM.md`](docs/LAYOUT_SYSTEM.md).

- **Tool Consolidation (Phase 4):** 58 legacy tools consolidated into 12 unified tools with ACID transaction support. See [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md).

### Key Documentation

| Document | Purpose |
|----------|---------|
| [ROADMAP.md](ROADMAP.md) | Development progress and plans |
| [SETUP.md](SETUP.md) | Installation guide |
| [docs/EQUIPMENT_CATALOG.md](docs/EQUIPMENT_CATALOG.md) | Complete equipment catalog |
| [docs/USER_MIGRATION_GUIDE.md](docs/USER_MIGRATION_GUIDE.md) | Migration from legacy tools |
| [docs/MCP_TOOL_EXAMPLES.md](docs/MCP_TOOL_EXAMPLES.md) | Usage examples |

---

## License

Released under the GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE) for details.
