# Engineering MCP Server
## Structured P&ID and Flowsheet Generation for LLM Agents

The Engineering MCP Server exposes pyDEXPI (DEXPI P&IDs) and SFILES2 (BFD/PFD flowsheets) through Anthropic's Model Context Protocol so language-model agents can create, modify, analyze, and persist process-engineering diagrams entirely in machine-readable formats.

This repository prioritizes data fidelity over drawing aesthetics: the authoritative artifacts are JSON/SFILES models tracked in git, with optional Plotly-based HTML visualizations and GraphML exports generated from the same state.

---

## Current Capabilities

- **Complete pyDEXPI Coverage (Phase 2)** – All **272 pyDEXPI classes** are now accessible: 159 equipment types, 79 piping types, and 34 instrumentation types. Both SFILES aliases (e.g., `pump`, `heat_exchanger`) and DEXPI class names (e.g., `CentrifugalPump`, `PlateHeatExchanger`) are accepted. See [`docs/EQUIPMENT_CATALOG.md`](docs/EQUIPMENT_CATALOG.md) for the complete catalog and [`docs/USER_MIGRATION_GUIDE.md`](docs/USER_MIGRATION_GUIDE.md) for usage guidance.
- **DEXPI P&ID tooling** – 14 MCP tools for creating models, adding equipment/piping/instrumentation, importing/exporting, and inserting inline valves (`src/tools/dexpi_tools.py`).
- **SFILES BFD/PFD tooling** – 12 MCP tools for flowsheet construction, stream management, canonicalization, regex validation, and conversions from/to DEXPI (`src/tools/sfiles_tools.py`).
- **Git-native persistence** – Project tools (`project_init/save/load/list`) wrap `src/persistence/project_persistence.py`, storing JSON/SFILES plus metadata, GraphML, and Plotly HTML in per-model folders with automatic commits.
- **Template deployment** – `template_list`, `template_get_schema`, and `area_deploy` expose four YAML templates (`library/patterns/*.yaml`): pump_basic, pump_station_n_plus_1, tank_farm, and heat_exchanger_with_integration.
- **Validation & analytics** – Schema introspection (`schema_*`), validation (`validate_model`, `validate_round_trip`), graph analytics (`graph_*`), search (`search_*`, `query_model_statistics`), and batch automation (`model_batch_apply`, `rules_apply`, `graph_connect`).
- **Visualization outputs** – Project saves produce Plotly-based interactive HTML files (with SVG/PDF exports via Plotly's toolbar) and GraphML topology exports. There is no standalone dashboard service; visual review happens through the generated HTML files.
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

> **Phase 4 Update:** The consolidated tools (`model_create`, `model_load`, `model_save`, `model_tx_begin`, `model_tx_apply`, `model_tx_commit`, `schema_query`, `search_execute`, and `graph_modify`) are now **production-ready** and exposed by the MCP server. Legacy atomic tools remain available for backward compatibility. See [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md) for migration guidance.

---

## Architecture Overview

| Component | Purpose |
|-----------|---------|
| `src/server.py` | Registers MCP handlers and routes tool calls to category handlers.
| `src/tools/*` | Tool implementations grouped by domain (DEXPI, SFILES, project, validation, schema, graph, search, batch, templates).
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

| Output | How it’s produced | Notes |
|--------|-------------------|-------|
| HTML (Plotly) | Generated during `project_save` for DEXPI and SFILES models | Interactive hover details, Plotly toolbar can export PNG/SVG locally.
| GraphML | `dexpi_export_graphml`, `sfiles_export_graphml`, and automatic exports during `project_save` | Suitable for NetworkX or external graph tooling.
| JSON/SFILES | Primary storage formats; accessible via import/export tools | Git-friendly text files.

No dashboard, Cytoscape.js, pyflowsheet SVG renderer, or 3D visualization engine is included in this repository.

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

**Phase 4 (Completed):** Tool consolidation and transaction support
- ✅ `model_create`, `model_load`, `model_save` – Unified model lifecycle (replaces 9 legacy tools)
- ✅ `model_tx_begin`, `model_tx_apply`, `model_tx_commit` – ACID transactions for atomic multi-operation changes
- ✅ `schema_query` – Unified schema introspection (replaces 4 legacy tools)
- ✅ `search_execute` – Unified search interface (replaces 6 legacy tools)
- ✅ `graph_modify` – Tactical graph modifications (10 actions available)
- ✅ 150/150 tests passing with full coverage of consolidated tools
- ✅ Live MCP testing validated all 12 consolidated tools
- ✅ Migration guide: [`docs/FEATURE_PARITY_MATRIX.md`](docs/FEATURE_PARITY_MATRIX.md)

**Planned Work:**
1. **Enhanced visualization** – Proposed pyflowsheet-based SVG/DXF renderer, ISA symbol support, and potential dashboard UI.
2. **Additional templates** – Library currently has 4 patterns; expansion to 5+ and beyond is tracked in `docs/templates/template_system.md`.
3. **Phase 5** – Advanced template system with composition and inheritance (see [ROADMAP.md](ROADMAP.md)).

Refer to [ROADMAP.md](ROADMAP.md) for detailed phase timelines and design discussions.

---

## License

Released under the GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE) for details.
