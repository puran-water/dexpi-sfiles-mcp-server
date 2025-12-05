# Proteus XML Viewer Service

Server-side rendering service for Proteus XML P&ID diagrams using Paper.js with external symbol library integration.

## Overview

This service provides HTTP API for rendering Proteus XML to SVG/PNG format. It's designed to run alongside the main Engineering MCP server as a microservice.

## Features

- **Server-side SVG/PNG rendering** using Paper.js + node-canvas
- **External Symbol Library Integration** - Uses curated `merged_catalog.json` with 805 symbols
- **External-first lookup** - Consistent house-standard symbols with embedded ShapeCatalogue fallback
- **Multi-format output** - SVG, HTML, and PNG formats
- **Proteus XML parsing** with JSDOM
- **RESTful API** for rendering requests
- **Docker support** for containerized deployment

## Symbol Library Integration

The viewer integrates with our curated symbol library (`merged_catalog.json`) for consistent P&ID rendering:

- **805 symbols** with bounding boxes, anchor points, and port geometry
- **94 DEXPI classes** mapped for equipment lookup
- **External-first lookup** - Prefers library symbols for corporate-standard consistency
- **Graceful fallback** - Uses embedded ShapeCatalogue if symbol not found
- **Clone-per-placement** - Safe multi-instance rendering

## API Endpoints

### GET /health
Health check endpoint with symbol library status.

```json
{
  "status": "healthy",
  "service": "proteus-viewer",
  "version": "0.3.0",
  "capabilities": ["svg", "html", "png"],
  "symbolLibrary": {
    "initialized": true,
    "preferExternal": true,
    "embeddedCount": 2,
    "externalCacheCount": 0
  },
  "timestamp": "2025-12-05T12:00:00.000Z"
}
```

### POST /render
Render Proteus XML to SVG, HTML, or PNG.

**Request (JSON):**
```json
{
  "xml": "<PlantModel>...</PlantModel>",
  "width": 1200,
  "height": 800,
  "format": "svg",
  "options": {
    "backgroundColor": "#ffffff",
    "scale": 1.0,
    "useExternalSymbols": true
  }
}
```

**Request (Raw XML):**
```http
POST /render
Content-Type: application/xml

<?xml version="1.0"?>
<PlantModel xmlns="http://www.dexpi.org/schemas/Proteus">
  ...
</PlantModel>
```

**Response (SVG):**
```json
{
  "success": true,
  "format": "svg",
  "content": "<svg>...</svg>",
  "metadata": {
    "width": 1200,
    "height": 800,
    "schemaVersion": "4.0.1"
  }
}
```

**Response (PNG):**
```json
{
  "success": true,
  "format": "png",
  "content": "base64-encoded-png-data",
  "metadata": {
    "width": 1200,
    "height": 800,
    "schemaVersion": "4.0.1"
  }
}
```

## Render Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `format` | string | "svg" | Output format: "svg", "html", or "png" |
| `width` | number | auto | Canvas width (auto-detected from Drawing extent) |
| `height` | number | auto | Canvas height (auto-detected from Drawing extent) |
| `backgroundColor` | string | "#ffffff" | Background color (engineering standard: white) |
| `useExternalSymbols` | boolean | true | Use external symbol library (vs embedded ShapeCatalogue) |

## Development

### Prerequisites
- Node.js 18+
- Canvas build dependencies (see Dockerfile)

### Local Development
```bash
cd src/visualization/proteus-viewer
npm install
npm run dev
```

### Build
```bash
npm run build
npm start
```

### Test Rendering
```bash
# Start server
npm start

# Test with sample XML
curl -X POST http://localhost:8081/render \
  -H "Content-Type: application/xml" \
  --data-binary @path/to/dexpi.xml
```

## Docker

### Build
```bash
docker build -t proteus-viewer .
```

### Run
```bash
docker run -p 8081:8081 proteus-viewer
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| PROTEUS_VIEWER_PORT | 8081    | HTTP server port |

## Architecture

### Symbol Lookup Cascade

When resolving a `componentName` reference:

1. **External Cache** - Check for cached ExternalSymbol instance
2. **DEXPI Class Lookup** - Match against symbol library's 94 DEXPI classes
3. **Identifier Lookup** - Match against 805 symbol identifiers
4. **Partial Search** - Fuzzy match on symbol name
5. **Embedded Fallback** - Use ShapeCatalogue from XML

### Key Modules

| Module | Purpose |
|--------|---------|
| `symbolLibrary/SymbolLibraryLoader.ts` | Loads merged_catalog.json, provides lookup |
| `symbolLibrary/SvgToPaperJs.ts` | Converts SVG to Paper.js objects |
| `symbolLibrary/ExternalSymbol.ts` | Component-compatible wrapper for external symbols |
| `proteusXmlDrawing/shapeCatalogStore.ts` | Symbol lookup with external-first cascade |
| `proteusXmlDrawing/Component.ts` | Parses and draws Proteus XML elements |

## Integration with MCP Server

The main Engineering MCP server checks for this service via the `RendererRouter`.
When available, it will be used for:

- Native Proteus XML visualization with consistent symbols
- SVG/PNG export from Proteus XML
- Interactive web-based P&ID viewing (HTML format)

## Status

**Phase 3 Complete** - Full symbol library integration operational.

### Current Capabilities
- Full Paper.js drawing integration for Lines, Circles, Shapes, Ellipses, Text
- External symbol library with 805 symbols
- SVG, HTML, and PNG output formats
- Engineering-standard color scheme (black lines on white background)

### Known Limitations
- Some complex shapes may not render correctly (BsplineCurve, CompositeCurve)
- Interactive features (pan/zoom/selection) not yet implemented for HTML output
