# Visualization & Extension Guide

This guide explains the *current* visualization outputs shipped with the Engineering MCP Server and outlines the **planned** pyflowsheet/ISA symbol architecture that has a detailed design but is not yet implemented.

---

## 1. Current Visualization Outputs (Implemented)

### Plotly HTML Reports
- Generated automatically by `ProjectPersistence.save_dexpi` and `save_sfiles` when you call `project_save`.
- Each HTML file contains an interactive Plotly graph with enhanced hover text populated from the underlying model.
- Use the Plotly toolbar to export PNG/SVG snapshots locally if needed; no extra renderer code is required.

### GraphML Exports
- Produced by `UnifiedGraphConverter` through `dexpi_export_graphml`, `sfiles_export_graphml`, and project saves.
- Provide a topology-only view suitable for NetworkX or downstream analytics pipelines.

### How To Extend What Already Exists
- Customize `src/persistence/project_persistence.py` to add additional traces or annotations to the Plotly figure before writing HTML.
- Add post-processing steps after GraphML export if you need domain-specific metadata.

---

## 2. Planned pyflowsheet/ISA Visualization Architecture (Design Spec – Not Yet Implemented)

> **Status:** Design approved, implementation pending. None of the modules described below exist in `src/visualization/` yet.

### Goals
1. Support ISA S5.1 instrumentation bubbles and control attachments in SFILES-derived diagrams.
2. Generate SVG/DXF outputs using `pyflowsheet` and related drawing libraries.
3. Maintain attachment metadata in NetworkX graphs without mutating process topology.

### Proposed Components
- **Instrument Symbol Classes** – `InstrumentBubble`, `ControllerBubble`, etc., inheriting from `pyflowsheet.UnitOperation` to render ISA tags.
- **Enhanced Visualization Wrapper** – A helper such as `visualize_flowsheet_with_instruments()` that:
  1. Builds a pyflowsheet object from the flowsheet graph.
  2. Adds units and instrumentation based on `control_type` metadata.
  3. Connects process streams (excluding control edges) and writes SVG files via `SvgContext`.
- **Control Attachment Semantics** – Metadata describing whether a control attaches to a stream or a unit:
  ```python
  attachment_target = {"type": "stream", "ref": "S-001"}
  attachment_target = {"type": "unit", "ref": "Tank-1"}
  ```
- **Positioning Helpers** – Planned utilities for valve/bubble placement (e.g., offset above stream midpoint).

### Compatibility Targets
- `pyflowsheet == 0.2.2`
- `pathfinding == 1.0.1`

### Future Enhancements (Post-Implementation)
1. Render signal/tap lines.
2. Load ISA symbol definitions from JSON/YAML for customization.
3. Animate flows (e.g., blinking arrows) for instructional material.
4. Explore WebGL/Three.js viewers only after the SVG foundation is complete.

---

## 3. Recommended Next Steps for Contributors

1. **Work within the current Plotly/GraphML outputs** to deliver incremental value (e.g., better hover text, filtering).
2. **Prototype the pyflowsheet renderer** in a separate module or notebook before landing it in the repo.
3. **Add tests** covering any new visualization exporters so they integrate with the existing project persistence pipeline.
4. **Document planned modules clearly** (as done above) so MCP clients understand which capabilities are available now vs. future.

---

*Questions about extending the visualization stack? Open an issue describing the feature, expected outputs, and how it maps to the current model stores.*
