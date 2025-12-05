# Visualization Plan: Federated Rendering Platform

**Created:** 2025-11-09
**Last Updated:** 2025-12-02 (SVG/PDF Export Complete)
**Status:** ✅ SVG/PDF EXPORT COMPLETE (Dec 2, 2025)
**Sprint:** Sprint 5++ (Production Rendering)
**Current Phase:** SVG/PDF Export via GraphicBuilder - Complete

---

## ✅ WEEK 1 COMPLETE - NOVEMBER 10, 2025

### Core Layer Integration - ALL BLOCKERS RESOLVED

The visualization system depends on the core layer (`src/core/`) for model enrichment and symbol resolution. **Phase 1 of core layer stabilization is complete**, and **all blocking bugs have been fixed** (Nov 10, 2025).

**Phase 5 Week 1 Deliverables (Nov 10, 2025):**
- ✅ Bug #1: Already fixed (Oct 2025)
- ✅ Bug #2: Symbol catalog backfill complete (308/805 symbols mapped)
- ✅ Bug #3: Nozzle creation implemented (DEXPI-compliant)
- ✅ Validation script created with regression protection

#### ✅ All Bugs Fixed (UNBLOCKED)

**Bug #1: BFD Expansion Tag Suffix** ✅ **COMPLETE**
- **Location:** `src/core/equipment.py:537-585`
- **Status:** ✅ COMPLETE - Fixed in Phase 1 (Oct 2025)
- **Impact:** BFD tags maintain fidelity through expansion (no suffix corruption)
- **Verification:** Confirmed in Phase 1 completion

**Bug #2: Symbol Catalog Missing DEXPI Mappings** ✅ **COMPLETE (Nov 10, 2025)**
- **Location:** `src/visualization/symbols/assets/merged_catalog.json`
- **Result:** **308 of 805 symbols mapped** (38.3% coverage, 76.7% equipment)
- **Implementation:** `scripts/backfill_symbol_dexpi_classes.py` (162 lines)
  - Base SYMBOL_MAPPINGS (87 unique symbols)
  - Actuated valve variants (11 A→B conversions)
  - Alternative mappings (5 fallback types)
- **Validation:** `scripts/validate_symbol_catalog.py` with percentage thresholds (≥35% total, ≥70% equipment)
- **Impact:** Equipment → Symbol ID resolution now works for 76.7% of equipment
- **Remaining:** 88 unmapped equipment symbols (30 unique base IDs) lack upstream DEXPI classes

**Bug #3: Nozzle Creation Stub** ✅ **COMPLETE (Nov 10, 2025)**
- **Location:** `src/core/equipment.py:519-549`
- **Implementation:** DEXPI-compliant nozzle creation with PipingNode
  - Creates PipingNode with diameter properties (DN50, 50mm)
  - Nozzle has pressure representation (PN16)
  - Sequential naming: N1, N2, N3, etc.
- **Impact:** All equipment now have proper connection points for piping
- **Verification:** Tested with CentrifugalPump (2 nozzles with correct properties)

#### ✅ Duplication Issues - ALL RESOLVED (Dec 2, 2025)

**Status Update:** All duplication identified by Codex has been resolved through refactoring and consolidation.

**Duplicate #1: model_service.py** ✅ **REMOVED**
- **Status:** File removed, functionality migrated to `src/core/analytics/model_metrics.py`
- **Resolution:** Proper refactoring during Phase 1 migration

**Duplicate #2: symbols/mapper.py** ✅ **REMOVED**
- **Status:** File removed, consolidated into core layer
- **Resolution:** Frozen copy preserved at `tests/fixtures/legacy_sfiles_mapper.py` for regression testing only

**Duplicate #3: dexpi_tools.py instrumentation** ✅ **NO DUPLICATION FOUND**
- **Status:** Code properly delegates to `instrumentation_toolkit`
- **Verification:** Uses `it.add_signal_generating_function_to_instrumentation_function()` correctly

**Duplicate #4: dexpi_tools.py manual lookups** ✅ **RESOLVED**
- **Status:** Uses ComponentRegistry and model_toolkit appropriately

**Duplicate #5: dexpi_introspector.py** ✅ **CONSOLIDATED**
- **Status:** Consolidated into `src/tools/dexpi_introspector.py` (21 KB)
- **Purpose:** Dynamic introspection for pyDEXPI classes, used by schema_tools.py

### Timeline Impact - COMPLETED

**Original Plan:** 1 week of bug fixes → 2 weeks of implementation
**Actual Result:** 8 weeks of systematic enhancement → ALL CORE WORK COMPLETE

**COMPLETED 8-WEEK SCHEDULE:**
- **Week 1 (Nov 10-17):** ✅ COMPLETE - Bugs #2-#3 fixed, validation script created
- **Weeks 2-3:** ✅ COMPLETE - Duplication resolved through proper refactoring
- **Weeks 5-6:** ✅ COMPLETE - MCP visualization tools operational
- **Week 7:** ✅ COMPLETE - ModelStore abstraction, E2E tests
- **Week 8:** ✅ COMPLETE - Geometry data population (805/805 symbols), SVG parser extraction
- **Week 8+:** ✅ COMPLETE - Layout System with ELK integration

**Remaining Work (Future Sprints):**
- ✅ SVG/PDF export (COMPLETE - via GraphicBuilder side-effect discovery)
- ProteusXMLDrawing integration (not started)

### Dependencies Ready (Updated Dec 2, 2025)

✅ **Core Layer Architecture:** Production-ready
✅ **pyDEXPI Integration:** Real classes instantiate correctly
✅ **SFILES Parsing:** Working correctly
✅ **Symbol Registry:** Loading 805 symbols with geometry data
  - Bounding boxes: 805/805 (100%)
  - Anchor points: 805/805 (100%)
  - Port geometry: 422/805 (52.4%)
  - DEXPI class mappings: 94/805 (11.7%)
✅ **Fail-Fast Philosophy:** No fallbacks masking bugs
✅ **Layout System:** ELK integration complete with 8 MCP tools
✅ **ModelStore:** Thread-safe with optimistic concurrency
✅ **All Bugs Fixed:** #1, #2, #3 resolved
✅ **Duplication Cleanup:** All identified duplication resolved

**Status:** Core infrastructure complete - Ready for rendering integration
**Next Action:** SVG export via GraphicBuilder Java API

---

## ✅ WEEKS 5-6 COMPLETE - NOVEMBER 30, 2025

### MCP Visualization Tools - OPERATIONAL

The MCP visualization infrastructure is now **production-ready** with two new tools:

**New MCP Tools:**
1. **`visualize_model`** - Generate visualizations from DEXPI/SFILES models
   - Supports HTML (Plotly interactive), PNG (GraphicBuilder), GraphML export
   - Auto-detects model type
   - Intelligent renderer selection via RendererRouter
   - Quality levels: draft, standard, production
   - Layout algorithms: spring, hierarchical, auto

2. **`visualize_list_renderers`** - List available renderers with capabilities
   - Returns health status for each renderer
   - Shows supported formats and platforms

**Key Implementation Details:**
- File: `src/tools/visualization_tools.py` (469 lines)
- Tests: `tests/tools/test_visualization_tools.py` (24 tests)
- Integrated into `src/server.py` with `visualize_*` prefix routing

**Bug Fixes Applied (Codex Review):**
- ✅ GraphML routing: Now bypasses RendererRouter (direct export)
- ✅ Error handling: Uses `result.get("ok") is False` consistently
- ✅ Zero-score guard: Rejects renderers that can't handle requested format
- ✅ Input validation: User-friendly errors for invalid format/quality

### Symbol Geometry Foundation - COMPLETE

Extended `src/core/symbols.py` with geometry support for future rendering:

**New Dataclasses:**
- `Point` - 2D coordinate (x, y)
- `BoundingBox` - Symbol dimensions with `center` property
- `Port` - Connection point with id, position, direction, type, flow_direction

**SymbolInfo Extensions:**
- `bounding_box: Optional[BoundingBox]` - Symbol dimensions
- `anchor_point: Optional[Point]` - Connection anchor
- `ports: List[Port]` - Connection points (default: empty list)
- `scalable: bool = True` - Render hint
- `rotatable: bool = True` - Render hint
- `get_anchor()` method - Returns explicit anchor or derives from bounding box center

**Tests:** `tests/core/test_symbol_geometry.py` (25 tests)

### ComponentRegistry Migration - COMPLETE

Removed deprecated methods from `DexpiIntrospector`:
- `get_available_types()` → Use `ComponentRegistry.get_all_by_type()`
- `get_valves()` → Use `ComponentRegistry.get_all_by_category()`
- `generate_dynamic_enum()` → Use `ComponentRegistry` directly

Updated scripts to use new API:
- `scripts/generate_all_registrations.py`
- `scripts/generate_equipment_registrations.py`

### Test Results
- **Total tests:** 590 passed, 16 skipped, 3 failed (GraphicBuilder Docker)
- **Visualization tests:** 24 passed
- **Geometry tests:** 25 passed

---

## ✅ WEEK 8+: LAYOUT SYSTEM COMPLETE - DECEMBER 2, 2025

### Layout Layer - OPERATIONAL

The Layout System with ELK integration is now **production-ready**:

**Core Components:**
- `src/models/layout_metadata.py` - Layout schema with etag computation
- `src/core/layout_store.py` - Thread-safe storage with optimistic concurrency
- `src/layout/engines/elk.py` - Persistent ELK worker integration
- `src/layout/elk_worker.js` - Node.js worker process

**MCP Tools (8 new):**
- `layout_compute` - Compute automatic layout using ELK
- `layout_get` - Retrieve stored layout
- `layout_update` - Update with etag requirement
- `layout_validate` - Schema and model consistency validation
- `layout_list` - List layouts by model
- `layout_save_to_file` / `layout_load_from_file` - File persistence
- `layout_delete` - Remove from store

**Architecture Decisions (Codex Consensus #019adb91):**
- Persistent Node.js worker (not per-call subprocess)
- Etag-based optimistic concurrency control
- sourcePoint/targetPoint capture for high-fidelity edge routing

**Test Coverage:** 39 layout tests, 768 total tests passing

**Documentation:** [`docs/LAYOUT_SYSTEM.md`](../LAYOUT_SYSTEM.md)

**Next Phase:** Wire Layout Layer into visualization pipeline for coordinate-based rendering.

---

## ✅ WEEK 8++: SVG/PDF EXPORT COMPLETE - DECEMBER 2, 2025

### Key Discovery (Codex Analysis)

**GraphicBuilder already creates SVG as a side-effect!**

When `StandAloneTester` runs:
1. It uses `ImageFactory_SVG` internally
2. `gFac.writeToDestination()` writes `input.svg`
3. Then transcodes SVG DOM → PNG via Batik `PNGTranscoder`
4. Result: BOTH `input.svg` AND `input.png` exist after execution

**The Flask service was only reading `.png` and ignoring `.svg`**

This discovery made SVG support a **zero-Java-change feature**.

### Implementation Summary

**Phase 1: SVG Support (Zero Java Changes)**
- Updated `graphicbuilder-service.py` to read `.svg` files
- SVG returned as text (not base64 encoded)
- Added `allow_fallback` option for graceful degradation

**Phase 2: PDF Support (Small Java Helper)**
- Created `PDFConverter.java` (~55 lines) using Batik `PDFTranscoder`
- Updated Dockerfile to compile PDFConverter
- PDF returned as base64-encoded binary

**Phase 3: Router Update**
- GraphicBuilder now supports `SVG`, `PNG`, `PDF` formats
- Router correctly selects GraphicBuilder for production SVG/PDF

### Files Modified

| File | Changes |
|------|---------|
| `src/visualization/graphicbuilder/graphicbuilder-service.py` | Read .svg for SVG, add PDF conversion |
| `src/visualization/graphicbuilder/PDFConverter.java` | NEW - Batik PDF transcoder |
| `src/visualization/graphicbuilder/Dockerfile` | Compile PDFConverter.java |
| `src/visualization/orchestrator/renderer_router.py` | Enable SVG/PDF formats |

### Test Coverage

- 758 tests passing (753 + 5 new router tests)
- Updated existing tests for new SVG/PDF behavior
- Added `TestFormatSelectionRouting` test class

---

## Executive Summary

After extensive analysis with Codex, we're adopting a **federated rendering platform** architecture that leverages existing best-in-class tools rather than building from scratch. This approach delivers production-quality visualization immediately while allowing incremental improvements over time.

### Key Decision

> **"Why re-implement what already works?"** - Use GraphicBuilder (Java) for production rendering, ProteusXMLDrawing (TypeScript) for web visualization, and Python for orchestration.

**Current Reality:** Architecture approved, but implementation blocked pending core layer bug fixes.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              pyDEXPI (Canonical Model)          │
│         Single source of truth for all data     │
└────────────┬────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────┐
│      Python Orchestration Service (MCP)         │
│   • Model enrichment (SFILES→pyDEXPI)          │
│   • Renderer selection & routing                │
│   • Proteus XML serialization                   │
│   • Job scheduling & caching                    │
└──────┬──────────────┬──────────────┬───────────┘
       │              │              │
┌──────▼──────┐ ┌────▼──────┐ ┌────▼──────────┐
│GraphicBuilder│ │ProteusXML │ │Future Python  │
│   (Java)     │ │Drawing(TS)│ │Renderer       │
│Print Quality │ │Interactive│ │(Eventually)   │
└─────────────┘ └───────────┘ └───────────────┘
       │              │              │
┌──────▼──────────────▼──────────────▼───────────┐
│           NOAKADEXPI Symbol Library            │
│        291 MIT-licensed production SVGs        │
└─────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Python Orchestration Service

**Location:** `src/visualization/orchestrator/`

**Components:**
```python
orchestrator/
├── model_service.py         # SFILES→pyDEXPI enrichment
├── renderer_router.py       # Select best renderer per task
├── proteus_serializer.py    # Generate Proteus XML from pyDEXPI
├── job_scheduler.py         # Async job management
├── cache_manager.py         # Intelligent result caching
└── presentation_service.py  # Shared presentation metadata
```

**Responsibilities:**
- Single entry point for all visualization requests
- Model format normalization (SFILES → pyDEXPI → Proteus XML)
- Renderer selection based on requirements (quality, speed, features)
- Result caching to avoid redundant rendering
- Job queuing for batch operations

**Implementation Notes:**
```python
class RendererRouter:
    def select_renderer(self, requirements: RenderRequirements) -> Renderer:
        if requirements.quality == "production" and requirements.format in ["PDF", "PNG"]:
            return self.graphicbuilder_renderer
        elif requirements.interactive and requirements.platform == "web":
            return self.proteus_xml_drawing_renderer
        elif requirements.speed == "fast" and requirements.quality == "draft":
            return self.simple_svg_renderer  # Future Python renderer
        else:
            return self.graphicbuilder_renderer  # Default to highest quality
```

---

### 2. GraphicBuilder Microservice

**Location:** `src/visualization/graphicbuilder/`

**Docker Configuration:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  graphicbuilder:
    build:
      context: ./graphicbuilder
      dockerfile: Dockerfile
    image: engineering-mcp/graphicbuilder:latest
    ports:
      - "8080:8080"
    volumes:
      - ./symbols:/app/symbols
      - ./cache:/app/cache
    environment:
      - JAVA_OPTS=-Xmx2G
      - SYMBOL_PATH=/app/symbols/NOAKADEXPI
```

**Dockerfile:**
```dockerfile
FROM openjdk:17-slim
RUN apt-get update && apt-get install -y maven git
WORKDIR /app

# Clone and build GraphicBuilder
RUN git clone https://gitlab.com/dexpi/GraphicBuilder.git
WORKDIR /app/GraphicBuilder
RUN mvn clean package

# Set up service wrapper
COPY graphicbuilder-service.py /app/
EXPOSE 8080
CMD ["python3", "/app/graphicbuilder-service.py"]
```

**Python Wrapper:**
```python
# src/visualization/graphicbuilder/wrapper.py
class GraphicBuilderRenderer:
    def __init__(self, host="localhost", port=8080):
        self.base_url = f"http://{host}:{port}"

    async def render(self, proteus_xml: str, format: str = "SVG") -> bytes:
        # Send Proteus XML to GraphicBuilder service
        response = await httpx.post(
            f"{self.base_url}/render",
            json={"xml": proteus_xml, "format": format}
        )
        return response.content

    def parse_imagemap(self, svg_content: bytes) -> Dict:
        # Extract imagemap data for interactive features
        pass
```

**Why GraphicBuilder:**
- 10+ years of refinement and edge case handling
- Full DEXPI presentation compliance
- Production-proven in industrial settings
- Handles complex P&ID layouts correctly
- Generates high-quality SVG/PNG/PDF with imagemaps

---

### 3. ProteusXMLDrawing Web Client

**Location:** `src/web-client/proteus-viewer/`

**Fork & Enhancement Plan:**
```typescript
// Based on github.com/vegarringdal/ProteusXMLDrawing
// GPL-3 compatible with our copyleft license

src/web-client/proteus-viewer/
├── renderer/
│   ├── paper-renderer.ts    # Existing Paper.js renderer
│   ├── fixes/
│   │   ├── text-alignment.ts    # Fix text positioning
│   │   ├── spline-curves.ts     # Add spline support
│   │   ├── hatch-fills.ts       # Complete hatch patterns
│   │   └── rotation-handler.ts  # Fix rotation issues
│   └── enhancements/
│       ├── layer-manager.ts     # P&ID layer visibility
│       ├── selection.ts         # Interactive selection
│       └── properties.ts        # Property panel
├── ui/
│   ├── components/
│   │   ├── Toolbar.tsx          # Modern toolbar
│   │   ├── LayerPanel.tsx       # Layer management
│   │   ├── PropertyPanel.tsx    # Equipment properties
│   │   └── DiagramViewer.tsx    # Main viewer
│   └── styles/
│       └── modern-theme.css     # Professional UI theme
└── realtime/
    ├── websocket-client.ts       # Live updates
    └── collaboration.ts          # Multi-user features
```

**Enhancement Roadmap:**

**Phase 1 (Week 1-2):** Critical Fixes
- Fix text alignment issues
- Add spline/curve support
- Complete hatch pattern rendering
- Fix rotation handling

**Phase 2 (Week 3-4):** Core Features
- Layer management (show/hide P&ID layers)
- Selection and highlighting
- Property panel for equipment
- Zoom/pan improvements

**Phase 3 (Week 5-6):** Advanced Features
- WebSocket integration for live updates
- Collaboration cursors
- Annotation system
- Export functionality

**Why ProteusXMLDrawing:**
- Already understands Proteus/DEXPI XML
- Browser-based (no server round-trips)
- TypeScript/modern web stack
- GPL-3 compatible with our license
- Active development (last update June 2024)

---

### 4. NOAKADEXPI Symbol Catalog

**Location:** `src/visualization/symbols/`

**Structure:**
```python
symbols/
├── catalog.py               # Symbol registry and metadata
├── importer.py              # NOAKADEXPI import scripts
├── metadata_extractor.py    # Extract ports, anchors from SVG
├── mapper.py                # DEXPI class → symbol mapping
├── converter.py             # SVG format conversions
└── assets/
    ├── NOAKADEXPI/         # 291 original SVG files
    │   ├── Equipment/
    │   │   ├── P-01-01.svg  # Centrifugal Pump
    │   │   ├── TK-01-01.svg # Tank
    │   │   └── ...
    │   ├── Valves/
    │   │   ├── V-01-01.svg  # Gate Valve
    │   │   ├── V-02-01.svg  # Ball Valve
    │   │   └── ...
    │   └── Instrumentation/
    │       ├── FIT-01.svg   # Flow Transmitter
    │       ├── LIT-01.svg   # Level Transmitter
    │       └── ...
    ├── processed/           # Optimized versions
    └── custom/              # User-added symbols
```

**Symbol Metadata Schema:**
```python
@dataclass
class SymbolMetadata:
    id: str                    # e.g., "P-01-01"
    name: str                  # e.g., "Centrifugal Pump"
    dexpi_class: str          # e.g., "CentrifugalPump"
    category: str             # e.g., "Equipment"
    svg_path: Path            # Path to SVG file

    # Extracted metadata
    bounding_box: BoundingBox
    ports: List[PortSpec]     # Connection points
    anchor_point: Point       # Rotation center

    # Rendering hints
    default_size: Size
    scalable: bool
    rotatable: bool

    # Variants
    variants: List[str]       # e.g., ["vertical", "horizontal"]
```

**Priority Symbols (Phase 1):**
Focus on 30-40 symbols needed for our 8 templates:
1. Tanks (TK-01-01 through TK-01-05)
2. Pumps (P-01-01 through P-01-10)
3. Valves (V-01-01 through V-01-10)
4. Mixers (MX-01-01 through MX-01-03)
5. Filters (F-01-01 through F-01-05)
6. Blowers (BL-01-01 through BL-01-03)
7. Clarifiers (CL-01-01 through CL-01-02)
8. Heat Exchangers (HX-01-01 through HX-01-03)

---

## Implementation Strategy

### Phase 1: Foundation (Weeks 1-2)

**Week 1 Tasks:**
1. **Day 1-2:** Set up Docker environment for GraphicBuilder
   - Create Dockerfile and docker-compose.yml
   - Build and test GraphicBuilder container
   - Verify SVG/PNG generation works

2. **Day 3-4:** Import priority NOAKADEXPI symbols
   - Script to import 30-40 symbols
   - Extract metadata (ports, bounding boxes)
   - Create symbol catalog database

3. **Day 5:** Build orchestration service foundation
   - Create model_service.py
   - Create renderer_router.py
   - Basic Proteus XML serialization

**Week 2 Tasks:**
1. **Day 6-7:** GraphicBuilder wrapper completion
   - Python client for Docker service
   - Parse SVG output and imagemaps
   - Caching layer

2. **Day 8-9:** Fork and setup ProteusXMLDrawing
   - Fork repository
   - Fix critical issues (text, splines)
   - Set up development environment

3. **Day 10:** MCP tool integration
   - Add visualize_bfd/visualize_pfd tools
   - Wire through orchestrator
   - Test with all 8 templates

### Phase 2: Enhancement (Weeks 3-6)

**Week 3-4:** ProteusXMLDrawing improvements
- Complete all presentation fixes
- Add layer management
- Implement selection/properties
- Modern UI with React

**Week 5-6:** Full symbol catalog & optimization
- Import all 291 NOAKADEXPI symbols
- Performance optimization
- Advanced caching
- Load balancing

---

## Technical Decisions

### 1. Why Not Port GraphicBuilder to Python?

**Time:** 6-9 months for faithful port
**Risk:** High - many edge cases and DEXPI nuances
**Alternative:** Use as microservice (2 weeks)
**Decision:** Use GraphicBuilder as-is via Docker

### 2. Why Fork ProteusXMLDrawing?

**Pros:**
- Already handles Proteus XML
- Browser-based (no server calls)
- GPL-3 compatible
- TypeScript/modern stack

**Cons:**
- Missing features (needs fixes)
- Limited documentation
- Small community

**Decision:** Fork and enhance rather than build from scratch

### 3. Why NOAKADEXPI Symbols?

**Pros:**
- 291 production-quality symbols
- MIT licensed (free to use)
- DEXPI compliant
- Industrial standard

**Cons:**
- Need metadata extraction
- Some symbols may need tweaks

**Decision:** Use NOAKADEXPI as primary symbol library

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| GraphicBuilder Docker complexity | Start simple, add features incrementally |
| ProteusXMLDrawing limitations | Keep GraphicBuilder as fallback |
| Symbol metadata extraction issues | Manual fallback for problem symbols |
| Performance with large diagrams | Aggressive caching, pagination |

### Schedule Risks

| Risk | Mitigation |
|------|------------|
| Docker setup delays | Pre-built images available |
| Symbol import takes longer | Start with priority 30-40 |
| ProteusXMLDrawing fixes complex | Focus on critical issues first |
| Integration issues | Test early and often |

---

## Success Metrics

### Phase 1 Exit Criteria (Week 2)
✅ GraphicBuilder containerized and running
✅ 30-40 NOAKADEXPI symbols imported
✅ Orchestrator routing working
✅ Basic ProteusXMLDrawing fork functional
✅ MCP tools integrated
✅ 3+ templates rendering correctly

### Phase 2 Exit Criteria (Week 6)
✅ All 8 templates rendering perfectly
✅ 100+ symbols in catalog
✅ ProteusXMLDrawing feature-complete
✅ Performance <2s for typical diagrams
✅ Caching reducing repeat renders by 90%
✅ Production deployment ready

---

## Comparison with Alternatives

| Approach | Time | Quality | Risk | Flexibility |
|----------|------|---------|------|-------------|
| **Federated Platform** | 2-6 weeks | Excellent | Low | High |
| Port GraphicBuilder | 6-9 months | Excellent | High | Medium |
| Build from scratch | 12+ months | Unknown | Very High | High |
| Use pyflowsheet | 2 weeks | Poor | Medium | Low |

---

## Long-term Vision

### Year 1: Production Platform
- Federated platform fully operational
- 500+ symbols in catalog
- 50+ templates available
- Used in production by multiple clients

### Year 2: Advanced Features
- Native Python renderer for specific use cases
- AI-assisted diagram generation
- Real-time collaboration features
- Process simulation integration

### Year 3: Industry Standard
- Contribute improvements back to upstream
- Establish as reference implementation
- Community-driven symbol libraries
- Plugin ecosystem

---

## Implementation Checklist - STATUS UPDATE (Dec 2, 2025)

### ✅ COMPLETED WORK

**Week 1: Visualization Blockers** ✅ COMPLETE
- [x] Bug #1: BFD tag suffix - Fixed (Oct 2025)
- [x] Bug #2: Symbol catalog backfill - Complete (308/805 symbols mapped)
- [x] Bug #3: Nozzle defaults - Implemented

**Weeks 2-3: Duplication Cleanup** ✅ COMPLETE
- [x] model_service.py - Removed, migrated to core layer
- [x] symbols/mapper.py - Removed, consolidated
- [x] dexpi_tools.py - Already properly structured (no duplication found)
- [x] dexpi_introspector.py - Consolidated

**Weeks 5-6: MCP Visualization** ✅ COMPLETE
- [x] `visualize_model` MCP tool operational
- [x] `visualize_list_renderers` MCP tool operational
- [x] Symbol geometry foundation (Point, BoundingBox, Port)
- [x] 590 tests passing

**Week 7: Infrastructure** ✅ COMPLETE
- [x] ModelStore abstraction with lifecycle hooks
- [x] CachingHook for derived data
- [x] E2E integration tests (20 scenarios)

**Week 8: Geometry & Layout** ✅ COMPLETE
- [x] Geometry data for ALL 805 symbols (100% bbox/anchor)
- [x] SVG parser extraction to core/svg_parser.py
- [x] Layout System with ELK integration
- [x] 8 MCP layout tools
- [x] 768 tests passing

### 🔄 REMAINING WORK (Future Sprints)

**SVG/PDF Export** ✅ **COMPLETE** (Dec 2, 2025)
- [x] GraphicBuilder side-effect discovery: SVG already created alongside PNG
- [x] Updated Flask service to read `.svg` files
- [x] Added `PDFConverter.java` for PDF transcoding
- [x] Router updated to support SVG/PNG/PDF formats

**ProteusXMLDrawing** - NOT STARTED
- [ ] Fork external TypeScript repo
- [ ] Fix critical issues (text, splines, rotation)
- [ ] WebSocket integration

**Symbol Catalog Gaps**
- [ ] Port geometry: 383/805 symbols missing ports
- [ ] DEXPI mappings: 711/805 symbols have null mappings

**Minor TODOs** (9 items in codebase)
- proteus_xml_exporter.py: FlowIn/FlowOut detection
- pfd_expansion_engine.py: Port population, BFD metadata

### Current Status (December 2, 2025)
**Core Infrastructure:** ✅ COMPLETE
**SVG/PDF Export:** ✅ COMPLETE
**Test Coverage:** 758 tests passing
**Next Priority:** ProteusXMLDrawing integration (browser-based viewing)

---

## Appendix A: GraphicBuilder API

### Render Endpoint
```
POST /render
Content-Type: application/json

{
  "xml": "<Proteus XML content>",
  "format": "SVG|PNG|PDF",
  "options": {
    "dpi": 300,
    "include_imagemap": true,
    "layers": ["process", "instrumentation"]
  }
}

Response:
{
  "content": "<base64 encoded output>",
  "imagemap": "<HTML imagemap>",
  "metadata": {
    "width": 1920,
    "height": 1080,
    "components": 42
  }
}
```

---

## Appendix B: Symbol Mapping

### DEXPI Class to NOAKADEXPI Symbol

| DEXPI Class | NOAKADEXPI Symbol | Variants |
|-------------|-------------------|----------|
| CentrifugalPump | P-01-01 | Horizontal, Vertical |
| Tank | TK-01-01 | Atmospheric, Pressurized |
| GateValve | V-01-01 | Manual, Actuated |
| BallValve | V-02-01 | 2-way, 3-way |
| Mixer | MX-01-01 | Top-mounted, Side-mounted |
| Filter | F-01-01 | Cartridge, Bag, Sand |
| HeatExchanger | HX-01-01 | Shell-tube, Plate |
| Clarifier | CL-01-01 | Primary, Secondary |

---

## Appendix C: Codex Validation Quotes

> "The ideal long-term vision is a federated rendering platform where multiple engines consume the same canonical model and symbol assets, and the orchestrator chooses the right one per task."

> "Keep pyDEXPI as the canonical model for both SFILES and DEXPI; everything consumes a single graph/presentation schema."

> "GraphicBuilder already gives us full fidelity, and ProteusXMLDrawing covers the web experience."

> "We leverage proven tooling instead of re-writing renderers from scratch."

---

**END OF VISUALIZATION PLAN**

**Document Version:** 3.1 (SVG/PDF Export Complete)
**Last Updated:** 2025-12-02
**Status:** SVG/PDF export operational via GraphicBuilder, ready for ProteusXMLDrawing integration