# Visualization Plan: Federated Rendering Platform

**Created:** 2025-11-09
**Last Updated:** 2025-01-09
**Status:** BLOCKED - Core Layer Bugs Must Be Fixed First
**Sprint:** Sprint 4 (Visualization Infrastructure)
**Current Phase:** Core Layer Stabilization Complete - Bug Fixes Pending

---

## ⚠️ CURRENT STATUS - JANUARY 9, 2025

### Core Layer Integration Blockers

The visualization system depends on the core layer (`src/core/`) for model enrichment and symbol resolution. **Phase 1 of core layer stabilization is complete**, but **5 bugs must be fixed** before visualization implementation can proceed:

#### 🔴 Critical Bugs (BLOCKING)

**Bug #1: BFD Expansion Tag Suffix** (HIGH Priority - 2 hours)
- **Location:** `src/core/equipment.py:533-537`
- **Impact:** BFD expansion adds `-{area_code}` suffix to equipment tags
- **Example:** `FEED` becomes `FEED-100` (breaks symbol lookups)
- **Fix Required:** Remove suffix from tag generation
- **Blocks:** BFD workflow integration with visualization

**Bug #2: Symbol Catalog Missing DEXPI Mappings** (HIGH Priority - 1 day)
- **Location:** `src/visualization/symbols/assets/merged_catalog.json`
- **Impact:** All 805 symbols have `dexpi_class: null`
- **Result:** `SymbolRegistry.get_by_dexpi_class()` always returns `None`
- **Fix Required:** Populate dexpi_class field from mapper.py
- **Blocks:** Equipment → Symbol ID resolution for rendering

**Bug #3: Nozzle Creation Stub** (MEDIUM Priority - 4 hours)
- **Location:** `src/core/equipment.py:497-509`
- **Impact:** All equipment have 0 nozzles (should have 2-6)
- **Result:** No connection points for piping
- **Fix Required:** Implement proper Nozzle instantiation
- **Blocks:** Connection rendering in diagrams

#### 🟡 Medium Priority Bugs (NOT BLOCKING PHASE 1)

**Bug #4: Piping Connections Missing Toolkit**
- Connections don't use `piping_toolkit.connect_piping_network_segment()`
- Can proceed with Phase 1, fix in Phase 2

**Bug #5: Missing Instrumentation Support**
- Conversion engine lacks control loop support
- Can proceed with Phase 1, fix in Phase 2

### Timeline Impact

**Original Plan:** Start implementation immediately
**Updated Plan:** Fix bugs #1-#3 first (1 week), then proceed

**Revised Schedule:**
- **Week of Jan 13:** Fix bugs #1, #2, #3
- **Week of Jan 20:** Begin Phase 1 implementation (originally Week 1)
- **Week of Jan 27:** Continue Phase 1 (originally Week 2)
- **Feb 3 onwards:** Phase 2 enhancements

### Dependencies Ready

✅ **Core Layer Architecture:** Production-ready for basic operations
✅ **pyDEXPI Integration:** Real classes instantiate correctly
✅ **SFILES Parsing:** Working correctly
✅ **Symbol Registry:** Loading 805 symbols (needs dexpi_class mapping)
✅ **Fail-Fast Philosophy:** No fallbacks masking bugs

**Next Action:** Fix Bug #1 (BFD tag suffix) to unblock BFD workflow

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

## Implementation Checklist

### Phase 0: Core Layer Bug Fixes (Week of Jan 13) - **IN PROGRESS**
- [ ] **Bug #1 Fixed:** BFD tag suffix removed (src/core/equipment.py:533-537)
- [ ] **Bug #3 Fixed:** Nozzle creation implemented (src/core/equipment.py:497-509)
- [ ] **Bug #2 Fixed:** Symbol catalog dexpi_class populated (merged_catalog.json)
- [ ] **Regression tests:** Verify fixes don't break existing functionality
- [ ] **Integration tests:** Test BFD expansion with real pyDEXPI classes

### Week 1 Deliverables (Week of Jan 20) - **BLOCKED**
- [ ] GraphicBuilder Docker container running
- [ ] 30-40 NOAKADEXPI symbols imported with metadata
- [ ] Basic orchestration service functional
- [ ] Proteus XML serialization working
- [ ] Initial test suite passing

**Blockers:** Requires Bug #2 fixed (symbol mappings)

### Week 2 Deliverables (Week of Jan 27) - **BLOCKED**
- [ ] GraphicBuilder wrapper complete with caching
- [ ] ProteusXMLDrawing fork with critical fixes
- [ ] MCP visualization tools integrated
- [ ] All 8 templates rendering
- [ ] Documentation updated

**Blockers:** Requires Week 1 complete

### Phase 1 Complete (Early February) - **BLOCKED**
- [ ] Production visualization operational
- [ ] Quality benchmarks established
- [ ] Performance targets met
- [ ] Integration tests passing
- [ ] Ready for Phase 2 enhancements

**Blockers:** Requires Week 1-2 complete

### Current Focus (January 9, 2025)
**Active Task:** Fixing Bug #1 (BFD tag suffix)
**Next:** Fix Bug #3 (nozzle creation)
**Then:** Fix Bug #2 (symbol mappings)

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

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Next Review:** End of Week 1 (progress check)