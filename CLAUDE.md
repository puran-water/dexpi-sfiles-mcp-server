# CLAUDE.md - Engineering MCP Server Development Guide

> Concise instructions for AI coding agents developing this MCP server.

## Quick Reference

| Item | Path |
|------|------|
| **Active Plan** | `docs/active/` |
| **Completed Plans** | `docs/completed-plans/` |
| **Roadmap** | `ROADMAP.md` |
| **Tests** | `pytest tests/` |

## Development Status

**Last Updated:** 2026-01-22

### Recent: Phase 8 ROADMAP Audit & Quick Wins (Completed)

New MCP tools and improvements:
- `sfiles_visualize` - SFILES2 visualization with HTML/PNG/SVG output, graceful table fallback
- `model_combine` - Merge multiple DEXPI models into one
- `search_instances` - Find instances by DEXPI class with pagination
- Layout-rendering integration via `use_layout`/`layout_id` params in `visualize_model`
- Full deprecation warnings on `catalog.py` (migration to SymbolRegistry)
- API fixes: `dexpi_to_graph()`, `list_by_model()` for LayoutStore

See `docs/completed-plans/2026-01-22-phase8-roadmap-audit.md` for details.

### Previous: Codex Deep Review (Completed)

Core conversion issues fixed:
- SFILES2 native parsing via `Flowsheet.create_from_sfiles(merge_HI_nodes=False)`
- Piping connections via `piping_toolkit.connect_piping_network_segment()` with nozzles
- pyDEXPI attribute names: `segment.id` (not `segmentId`), `pns.segments` (not `pipingNetworkSegments`)
- Nozzle tracking via `_used_nozzles` set (pyDEXPI has no `pipingConnection` attribute)

See `docs/completed-plans/2026-01-22-codex-deep-review.md` for details.

---

## Critical Development Policies

### 1. File Overwriting Policy

**ALWAYS overwrite existing files** when saving models. Git handles versioning.

```python
# Correct - same name overwrites
project_save(model_name="reactor_design", ...)  # Creates file
project_save(model_name="reactor_design", ...)  # Overwrites file

# WRONG - never version filenames
project_save(model_name="reactor_design_v2", ...)  # Don't do this
```

### 2. pyDEXPI API Usage

```python
# Nozzle connectivity - use tracking set, not non-existent attribute
_used_nozzles = set()
if id(nozzle) not in _used_nozzles:
    _used_nozzles.add(id(nozzle))

# Piping connections
from pydexpi.toolkits import piping_toolkit as pt
pt.connect_piping_network_segment(segment, nozzle, as_source=True)

# Segment attributes
segment = PipingNetworkSegment(id=line_number)  # Not segmentId
pns.segments.append(segment)  # Not pipingNetworkSegments
```

### 3. SFILES2 API Usage

```python
# Two-step pattern for merge_HI_nodes control
flowsheet = Flowsheet()
flowsheet.create_from_sfiles(sfiles_string, merge_HI_nodes=False)

# NOT: Flowsheet(sfiles_in=sfiles_string)  # Can't pass merge_HI_nodes

# Output format
flowsheet.convert_to_sfiles(version="v2", canonical=True)
```

---

## Project Structure

```
engineering-mcp-server/
├── src/
│   ├── server.py              # MCP server entry point
│   ├── tools/                 # MCP tool implementations
│   │   ├── dexpi_tools.py     # DEXPI P&ID tools
│   │   ├── sfiles_tools.py    # SFILES BFD/PFD tools
│   │   └── ...
│   ├── core/                  # Core business logic
│   │   ├── conversion.py      # SFILES <-> DEXPI conversion
│   │   └── ...
│   ├── registry/operations/   # Operation handlers
│   └── utils/                 # Utilities
├── tests/                     # Pytest test suite
├── docs/
│   ├── active/                # Active planning docs
│   └── completed-plans/       # Completed work documentation
├── ROADMAP.md                 # Development roadmap
└── README.md                  # User-facing documentation
```

---

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src

# Run specific module
pytest tests/test_core_layer_errors.py -v

# Syntax check modified files
python3 -m py_compile src/path/to/file.py
```

---

## Dependencies

| Library | Version | Notes |
|---------|---------|-------|
| pyDEXPI | `174321e` | v1.1.0 - stable APIs |
| SFILES2 | `fdc5761` | June 2025 - stream params fix |

Pinned in `pyproject.toml`. Keep `requirements.txt` in sync.

---

## Visualization

| Format | Method | Use Case |
|--------|--------|----------|
| HTML (Plotly) | Auto on `project_save` | Topology analysis |
| GraphML | `*_export_graphml` | External tools |
| PNG | GraphicBuilder Docker | Engineering docs |

SVG/DXF export planned but not yet implemented.

---

## File Organization for Projects

```
project_root/
├── .git/           # Git handles versioning
├── metadata.json
├── bfd/            # Block flow diagrams (SFILES)
├── pfd/            # Process flow diagrams (SFILES)
└── pid/            # P&ID diagrams (DEXPI)
```
