# Layout System Documentation

## Overview

The Layout System provides automatic positioning of engineering diagrams (BFD, PFD, P&ID) using the ELK (Eclipse Layout Kernel) algorithm via elkjs. It separates topology (DEXPI/SFILES models) from coordinates (layout metadata), enabling:

- Deterministic, reproducible layouts
- Orthogonal edge routing suitable for P&ID standards
- Optimistic concurrency control via etags
- File persistence alongside models

**Architecture Decision:** Codex Consensus #019adb91

## Components

### Layout Metadata Schema (`src/models/layout_metadata.py`)

Core data structures for layout information:

```python
from src.models.layout_metadata import (
    LayoutMetadata,      # Complete layout with positions, edges, ports
    NodePosition,        # x, y coordinates for a node
    EdgeRoute,           # Edge routing with sections and bend points
    EdgeSection,         # Single segment of an edge route
    PortLayout,          # Port positions with side constraints
    BoundingBox,         # Layout bounds (auto-computed)
    ModelReference,      # Link to source DEXPI/SFILES model
)
```

### Layout Store (`src/core/layout_store.py`)

Thread-safe storage with optimistic concurrency:

```python
from src.core.layout_store import LayoutStore, OptimisticLockError

store = LayoutStore()

# Save layout
layout_id = store.save(layout, model_ref=ModelReference(type="dexpi", model_id="P-101"))

# Update with concurrency check
new_etag = store.update(layout_id, modified_layout, expected_etag=current.etag)

# File persistence
store.save_to_file(layout_id, "/projects/plant", "reactor_pid", "pid")
loaded_id = store.load_from_file("/projects/plant", "reactor_pid")
```

### ELK Layout Engine (`src/layout/engines/elk.py`)

Persistent Node.js worker process for ELK layout computation:

```python
from src.layout.engines.elk import ELKLayoutEngine, PID_LAYOUT_OPTIONS

engine = ELKLayoutEngine()

# Check availability
if await engine.is_available():
    layout = await engine.layout(graph, options=PID_LAYOUT_OPTIONS)
```

**Key Features:**
- Persistent worker process (not per-call subprocess)
- Request/response protocol with UUID correlation
- Automatic process restart on failure
- Thread-safe with proper cleanup on exit

### ELK Worker (`src/layout/elk_worker.js`)

Node.js persistent worker using elkjs:

```javascript
// Protocol: newline-delimited JSON over stdin/stdout
// Request: {"id": "uuid", "graph": {...}}
// Response: {"id": "uuid", "result": {...}}
```

## MCP Tools

### layout_compute

Compute layout for a model using ELK:

```json
{
  "model_id": "my-pid",
  "model_type": "auto",
  "algorithm": "elk",
  "direction": "RIGHT",
  "spacing": 50,
  "store_result": true
}
```

### layout_get

Retrieve stored layout by ID:

```json
{
  "layout_id": "layout_abc123",
  "include_edges": true,
  "include_ports": true
}
```

### layout_update

Update layout with optimistic concurrency control:

```json
{
  "layout_id": "layout_abc123",
  "etag": "a1b2c3d4...",
  "positions": {
    "P-101": {"x": 150, "y": 150}
  }
}
```

**Returns:** New etag and version on success, `ETAG_MISMATCH` error on concurrent modification.

### layout_validate

Validate layout integrity and model consistency:

```json
{
  "layout_id": "layout_abc123",
  "check_model_consistency": true,
  "recompute_diff": false
}
```

**Checks:**
- Schema compliance and required fields
- Etag integrity (stored vs computed)
- Bounding box consistency
- Model topology match (if enabled)
- Position drift from recomputed layout (if enabled)

### layout_list

List layouts, optionally filtered by model:

```json
{
  "model_id": "my-pid",
  "model_type": "dexpi"
}
```

### layout_save_to_file / layout_load_from_file

Persist layouts to project files:

```json
{
  "layout_id": "layout_abc123",
  "project_path": "/projects/plant",
  "model_name": "reactor_pid",
  "model_type": "pid"
}
```

**File Structure:**
```
project_root/
├── pid/
│   ├── reactor_pid.json         # DEXPI model
│   └── reactor_pid.layout.json  # Layout file
├── pfd/
│   └── process_flow.layout.json
└── bfd/
    └── block_diagram.layout.json
```

### layout_delete

Remove layout from store:

```json
{
  "layout_id": "layout_abc123"
}
```

## ELK Layout Options

Default P&ID options (`PID_LAYOUT_OPTIONS`):

```python
{
    "elk.algorithm": "layered",
    "elk.direction": "RIGHT",
    "elk.layered.spacing.nodeNodeBetweenLayers": 50,
    "elk.layered.spacing.nodeNode": 30,
    "elk.spacing.edgeNode": 20,
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
    "elk.portConstraints": "FIXED_SIDE",
}
```

## Etag-Based Concurrency

The system uses SHA-256 etags for optimistic concurrency control:

1. **Get layout** with current etag
2. **Modify locally**
3. **Update with expected_etag** - fails if layout changed since read
4. **Retry** with new etag if `ETAG_MISMATCH` error

```python
# Safe update pattern
layout = store.get(layout_id)
layout.positions["P-101"] = NodePosition(x=100, y=100)

try:
    new_etag = store.update(layout_id, layout, expected_etag=layout.etag)
except OptimisticLockError:
    # Layout was modified - refresh and retry
    layout = store.get(layout_id)
    # ... merge changes and retry
```

## Edge Routing

ELK provides orthogonal edge routing with:

- **Sections**: Edge segments with start/end points and bend points
- **sourcePoint/targetPoint**: Overall edge endpoints for high-fidelity rendering
- **Port-aware routing**: Edges connect to specific port positions

```python
edge = layout.edges["line-1"]
points = edge.get_all_points()  # All points in order
source = edge.sourcePoint       # Edge start (tuple)
target = edge.targetPoint       # Edge end (tuple)
```

## Testing

Run layout tests:

```bash
pytest tests/test_layout_system.py -v
```

Test categories:
- Schema validation (LayoutMetadata, EdgeRoute, etc.)
- Store operations (CRUD, concurrency)
- File persistence (save/load roundtrip)
- ELK engine (availability, layout computation)
- MCP tool interface (handlers, error cases)

## Dependencies

- **elkjs**: ELK layout engine for Node.js
- **Node.js**: Required for ELK worker process
- **networkx**: Graph representation

Install elkjs:
```bash
npm install elkjs
```
