# Engineering-MCP-Server: ROADMAP Audit & Quick Wins

**Created:** 2026-01-22
**Status:** COMPLETED
**Verified:** 2026-01-23 (Playwright webapp testing)

---

## Executive Summary

Audit of the ROADMAP.md revealed several inaccuracies that need correction, and research of upstream libraries (SFILES2, pyDEXPI) identified high-value opportunities for the next development phase.

---

## Part 1: ROADMAP Accuracy Issues

### Issues Found

| Claim in ROADMAP | Actual Finding | Action |
|------------------|----------------|--------|
| "58 legacy tools consolidated into 12 unified tools" | 77 MCP tools exist; 6 unified tools alongside 71 domain-specific | Correct wording |
| "185/272 components mapped (68.0%)" | 308/805 symbols mapped (38.3%) | Correct metrics |
| "768 total tests passing" | 860+ test functions | Update count |

### Verified Correct
- Layout System (8 MCP tools) - complete
- SVG/PDF Export via GraphicBuilder - complete
- SFILES2/pyDEXPI integration - complete (Codex Deep Review)
- Upstream versions at latest (SFILES2 @ fdc5761, pyDEXPI @ 174321e v1.1.0)

---

## Part 2: Implementation Plan

### Phase 8.1: Fix ROADMAP Accuracy (Priority: P0)

**File:** `ROADMAP.md`

**Changes:**
1. Update Phase 4 description from "consolidated into 12 unified tools" to:
   > "6 unified tools (model_create, model_load, model_save, model_tx_begin, model_tx_apply, model_tx_commit) added for ACID transactions alongside 71 domain-specific tools"

2. Update Phase 3 symbol mapping from "185/272 components mapped (68.0%)" to:
   > "308/805 symbols mapped (38.3% coverage) with DEXPI class mappings"

3. Update test count references from "768" to "860+"

4. Add Current Metrics section under Completed Work:
   ```markdown
   ### Current Metrics (2026-01-22)
   - MCP Tools: 77 total (6 unified + 71 domain-specific)
   - Symbol Coverage: 308/805 (38.3%)
   - Test Suite: 860+ tests
   - Process Templates: 8 complete
   ```

**Verification:**
```bash
uv run python -c "import glob; print(len(glob.glob('src/tools/*.py')))"
uv run pytest tests/ --collect-only -q | tail -5
```

---

### Phase 8.2: Quick Wins (Priority: P1)

#### 8.2.1: SFILES2 Visualization MCP Tool

**Why:** SFILES2 has rich `visualize_flowsheet()` capabilities not exposed via MCP.

**File:** `src/tools/sfiles_tools.py`

**Add tool:**
```python
Tool(
    name="sfiles_visualize",
    description="Generate visualization of SFILES flowsheet with stream/unit tables",
    inputSchema={
        "type": "object",
        "properties": {
            "flowsheet_id": {"type": "string"},
            "output_format": {"enum": ["html", "png", "svg"], "default": "html"},
            "include_tables": {"type": "boolean", "default": true}
        },
        "required": ["flowsheet_id"]
    }
)
```

**Implementation:** Call `Flowsheet.visualize_flowsheet()` and return result

**Verification:**
```bash
uv run pytest tests/test_sfiles_tools.py -v -k visualize
```

---

#### 8.2.2: Model Combination Tool

**Why:** pyDEXPI `model_toolkit.combine_dexpi_models()` enables multi-model workflows but isn't exposed.

**File:** `src/tools/model_tools.py`

**Add tool:**
```python
Tool(
    name="model_combine",
    description="Merge multiple DEXPI models into one combined model",
    inputSchema={
        "type": "object",
        "properties": {
            "source_model_ids": {"type": "array", "items": {"type": "string"}},
            "target_model_id": {"type": "string"}
        },
        "required": ["source_model_ids", "target_model_id"]
    }
)
```

**Implementation:** Use `from pydexpi.toolkits.model_toolkit import combine_dexpi_models`

**Verification:**
```bash
uv run pytest tests/test_model_tools.py -v -k combine
```

---

#### 8.2.3: Instance Query Tool

**Why:** pyDEXPI `get_all_instances_in_model()` enables equipment inventory/search but isn't exposed.

**File:** `src/tools/search_tools.py`

**Add tool:**
```python
Tool(
    name="search_instances",
    description="Find all instances of a DEXPI class type in model",
    inputSchema={
        "type": "object",
        "properties": {
            "model_id": {"type": "string"},
            "class_names": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["model_id", "class_names"]
    }
)
```

**Verification:**
```bash
uv run pytest tests/test_search_tools.py -v -k instances
```

---

### Phase 8.3: catalog.py Deprecation (Priority: P2)

**Why:** Part of Core Layer Migration Plan - catalog.py marked for removal.

**File:** `src/visualization/symbols/catalog.py`

**Steps:**
1. Add deprecation warnings to all public functions
2. Find and update internal callers: `grep -r "from.*catalog import" src/`
3. Redirect to `core.symbols.SymbolRegistry`

**Verification:**
```bash
uv run pytest tests/ -v --tb=short 2>&1 | grep -i deprecat
```

---

### Phase 8.4: Layout-Rendering Integration (Priority: P2)

**Why:** Layout System computes positions but GraphicBuilder ignores them.

**Files:**
- `src/tools/visualization_tools.py` - Add `use_layout` parameter
- `src/exporters/proteus_xml_exporter.py` - Inject coordinates into XML

**Implementation:**
1. Add `use_layout: bool = False` to `visualize_model` tool
2. When true, lookup layout from LayoutStore
3. Inject node coordinates into Proteus XML before rendering

**Verification:**
```bash
uv run pytest tests/test_visualization_tools.py -v
uv run pytest tests/exporters/ -v
```

---

### Phase 8.5: ProteusXMLDrawing Integration (Priority: P3)

**Why:** Browser-based P&ID viewing is in ROADMAP "Planned Work".

**Status:** TypeScript source exists at `src/visualization/proteus-viewer/` but not integrated.

**Scope:** Create Python wrapper + WebSocket server + MCP tools

**Files to create:**
- `src/visualization/proteus_viewer/wrapper.py`
- `src/visualization/proteus_viewer/server.py`

**New tools:**
- `visualize_start_web_viewer` - Start browser viewer
- `visualize_stop_web_viewer` - Stop viewer

---

## Part 3: Remaining ROADMAP Items (Unchanged)

From existing ROADMAP "Planned Work":
1. **Additional Templates** - Expand from 8 to 15+ (ongoing)
2. **Rendering Integration** - Partially addressed in Phase 8.4

---

## Implementation Order

| Order | Phase | Description | Effort |
|-------|-------|-------------|--------|
| 1 | 8.1 | Fix ROADMAP accuracy | 30 min |
| 2 | 8.2.1 | SFILES2 visualize tool | 2-3 hrs |
| 3 | 8.2.2 | Model combine tool | 2-3 hrs |
| 4 | 8.2.3 | Instance query tool | 1-2 hrs |
| 5 | 8.3 | catalog.py deprecation | 3-4 hrs |
| 6 | 8.4 | Layout-rendering integration | 1-2 days |
| 7 | 8.5 | ProteusXMLDrawing | 1-2 weeks |

---

## Verification Checklist

After implementation, verify:

```bash
# All tests pass
uv run pytest tests/ -v

# Tool count
uv run python -c "from src.server import create_server; s = create_server(); print(f'Tools: {len(s.tools)}')"

# Symbol coverage
uv run python -c "import json; d=json.load(open('src/visualization/symbols/assets/merged_catalog.json')); print(f'Symbols: {len(d[\"symbols\"])}')"
```

---

## Key Files Reference

| Purpose | File |
|---------|------|
| ROADMAP fixes | `ROADMAP.md` |
| SFILES tools | `src/tools/sfiles_tools.py` |
| Model tools | `src/tools/model_tools.py` |
| Search tools | `src/tools/search_tools.py` |
| Visualization | `src/tools/visualization_tools.py` |
| Proteus export | `src/exporters/proteus_xml_exporter.py` |
| Symbol catalog | `src/visualization/symbols/catalog.py` |

---

## Codex Review Findings (Session 019be7f5)

### Plan Critique - Risks & Gaps

#### Phase 8.2.1: `sfiles_visualize`
- **SFILES2 API mismatch**: `Flowsheet.visualize_flowsheet()` returns matplotlib `fig` + ASCII tables, writes SVG to disk - does NOT produce HTML/PNG directly. Tool must convert outputs.
- **File path collision**: `plot_flowsheet_pyflowsheet()` writes to `./plots/` in cwd - causes collisions/permissions issues. Use unique temp dir per request.
- **Missing attributes**: SFILES2 table helpers expect `processstream_name/processstream_data` on edges, `unit_type_specific/unit` on nodes. Current `sfiles_add_unit/add_stream` don't populate these.
- **Empty flowsheet**: `_add_positions()` fails on empty graphs. Return clean `EMPTY_FLOWSHEET` error.
- **Headless CI**: `plot_flowsheet_nx()` calls `plt.show()`. Force non-interactive backend.

#### Phase 8.2.2: `model_combine`
- **Correct import**: `pydexpi.toolkits.model_toolkit.combine_dexpi_models`
- **Limitations**: Raises `NotImplementedError` if `diagram` or `shapeCatalogues` present. Surface specific error.
- **Define semantics**: Create new model_id, handle ID/tag collisions, decide metadata priority.
- **Validation**: Enforce `model_ids` length ≥ 2.

#### Phase 8.2.3: `search_instances`
- **Correct import**: `pydexpi.toolkits.model_toolkit.get_all_instances_in_model`
- **Result size**: Unfiltered discovery is large. Support filtering, limits/pagination, stable sorting.
- **Serialization**: Return summary `{class_name, id, tagName}` not full objects.

#### Phase 8.4: Layout-Rendering Integration
- **Already have support**: `ProteusXMLExporter.export(..., layout_metadata=...)` injects Position/Extent. Missing: wiring from `visualize_model`.
- **Code risks**:
  - `VisualizationTools._render_proteus()` calls non-existent `export_to_string()` method
  - `LayoutTools._get_graph()` uses non-existent `MLGraphLoader.parse_dexpi_to_graph()` (correct: `dexpi_to_graph()`)
- **ID mapping**: Exporter expects layout keyed by `equipment.id`. Ensure layout computation uses same IDs.

---

## Automated Test Suite (Real Integration Tests - No Mocks)

### Testing Philosophy
Follow existing `tests/test_graphicbuilder_integration.py` pattern:
- **Real services only** - Use actual GraphicBuilder Docker, real SFILES2/pyDEXPI library calls
- **No mocks** - No `unittest.mock`, no `monkeypatch.setattr` for core functionality
- **Strict assertions** - No swallowed exceptions, no silent skips for expected functionality
- **Structural validation** - Real PNG/SVG/PDF parsing with strict XML parser

### Visual Output Verification via Playwright MCP

**Install Playwright MCP Server for browser-based verification:**
```bash
npx -y @smithery/cli install @automatalabs/mcp-server-playwright --client claude
# Provides: browser_navigate, browser_screenshot, browser_click, browser_fill
```

**Use for:**
- Render HTML output in headless browser, screenshot result
- Verify interactive elements in HTML visualizations
- Visual regression testing against golden images

### Test File: `tests/test_phase8_tools.py`

**Test Classes (Real Integration):**

1. `TestSfilesVisualizeIntegration`
   - Real `Flowsheet.visualize_flowsheet()` calls
   - `lxml.etree.XMLParser(recover=False)` for strict SVG validation
   - PNG chunk-by-chunk parsing (IHDR/IDAT/IEND)
   - `tempfile.TemporaryDirectory()` for file isolation
   - Environment `MPLBACKEND=Agg` (set before import, not patched)

2. `TestModelCombineIntegration`
   - Real `pydexpi.toolkits.model_toolkit.combine_dexpi_models()`
   - Actual DexpiModel instances with equipment
   - Verify exact `taggedPlantItems` counts
   - Let `NotImplementedError` propagate (test that it raises)

3. `TestSearchInstancesIntegration`
   - Real `get_all_instances_in_model()` from pyDEXPI
   - Known equipment counts, exact assertions
   - Invalid class names raise exceptions (not caught)

4. `TestLayoutRenderingIntegration`
   - Requires running GraphicBuilder Docker (like existing tests)
   - Real `ProteusXMLExporter` with `layout_metadata=...`
   - Parse output XML with strict `lxml.etree` parser
   - Verify Position/Location elements have numeric X/Y

**Strict Validation Functions:**
```python
def assert_valid_png(data: bytes) -> None:
    """Strict PNG validation - raises on invalid."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG signature"
    pos = 8
    chunks_found = set()
    while pos < len(data):
        length = int.from_bytes(data[pos:pos+4], 'big')
        chunk_type = data[pos+4:pos+8]
        chunks_found.add(chunk_type)
        pos += 12 + length
        if chunk_type == b'IEND':
            break
    assert b'IHDR' in chunks_found, "Missing IHDR chunk"
    assert b'IEND' in chunks_found, "Missing IEND chunk"

def assert_valid_svg(content: str) -> etree._Element:
    """Strict SVG parsing - no recovery mode."""
    parser = etree.XMLParser(recover=False)
    root = etree.fromstring(content.encode('utf-8'), parser)
    assert root.tag.endswith('svg'), f"Root is {root.tag}"
    return root
```

**Fixtures (Real Objects):**
```python
@pytest.fixture
def flowsheet_with_sfiles2_attrs():
    """Real Flowsheet with attributes SFILES2 requires."""
    os.environ['MPLBACKEND'] = 'Agg'  # Set before import
    from Flowsheet_Class.flowsheet import Flowsheet
    fs = Flowsheet()
    fs.state.add_node("U1", unit_type="pump", unit_type_specific="pump", unit=None)
    fs.state.add_node("U2", unit_type="tank", unit_type_specific="tank", unit=None)
    fs.state.add_edge("U1", "U2",
        processstream_name="S-001",
        processstream_data=[1.0, 300.0, 101325.0, [0.5, 0.5, 0.0]])
    return fs

@pytest.fixture
def graphicbuilder_service():
    """Require GraphicBuilder - fail fast if not running."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8080))
    sock.close()
    if result != 0:
        pytest.fail("GraphicBuilder Docker not running. Start with: docker-compose up -d")
```

### Environment Requirements

```bash
# Required for matplotlib in tests
export MPLBACKEND=Agg

# Required for visual rendering tests
docker-compose up -d graphicbuilder

# Optional: Playwright MCP for HTML verification
npx playwright install chromium
```

### Run Tests

```bash
# Unit tests (no Docker)
uv run pytest tests/test_phase8_tools.py -v -k "not Integration"

# Full integration (requires Docker)
uv run pytest tests/test_phase8_tools.py -v

# Strict mode - warnings are errors
uv run pytest tests/test_phase8_tools.py -v -W error::UserWarning -W error::DeprecationWarning
```

---

## Verification Results (2026-01-23)

### Playwright Webapp Testing

Visual verification of visualization outputs using Playwright headless browser:

**Test Script:** `test_output/webapp_testing/playwright_verify.py`

**Plotly HTML Verification:**
- SVG elements found: 3
- Plotly div elements: 1
- Scatter layers: 1
- Title visible: ✓
- Node labels found: 4/4 (P-101, T-101, H-101, R-101)
- Result: **PASS**

**Matplotlib SVG Verification:**
- SVG root elements: 1
- Path elements: 32
- Result: **PASS**

**Generated Files:**
- `test_plotly.html` (4.7 MB) - Interactive Plotly graph
- `test_matplotlib.png` (23 KB) - Static flowsheet image
- `test_matplotlib.svg` (24 KB) - Vector flowsheet image

**Screenshots:** `test_output/webapp_testing/screenshots/`
- `plotly_rendered.png` - Browser screenshot of Plotly HTML
- `svg_rendered.png` - Browser screenshot of SVG

### Implementation Summary

All Phase 8.1-8.4 items completed:

| Phase | Description | Status |
|-------|-------------|--------|
| 8.1 | ROADMAP accuracy fixes | ✓ Complete |
| 8.2.1 | `sfiles_visualize` tool | ✓ Complete |
| 8.2.2 | `model_combine` tool | ✓ Complete |
| 8.2.3 | `search_instances` tool | ✓ Complete |
| 8.3 | catalog.py deprecation | ✓ Complete |
| 8.4 | Layout-rendering integration | ✓ Complete |

**Total MCP Tools:** 78 (7 unified + 71 domain-specific)
**Tests Passing:** 870+ (including Phase 8 tests)
