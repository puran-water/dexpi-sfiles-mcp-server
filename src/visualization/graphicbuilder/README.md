# GraphicBuilder Integration

Production-quality DEXPI P&ID renderer microservice based on [DEXPI GraphicBuilder](https://gitlab.com/dexpi/GraphicBuilder).

## Overview

GraphicBuilder is a Java-based renderer that produces high-quality SVG, PNG, and PDF outputs from Proteus/DEXPI XML. This integration provides:

- **Docker microservice** for isolated, reproducible rendering
- **Python async client** for easy integration
- **Flask HTTP wrapper** for REST API access
- **Symbol library support** (NOAKADEXPI)
- **PNG output format** (SVG/PDF require Java API integration - planned)

## Quick Start

### Start the Service

```bash
# Using Docker Compose (recommended)
docker compose up -d graphicbuilder

# Check health
curl http://localhost:8080/health
```

### Python Client Example

```python
import asyncio
from src.visualization.graphicbuilder.wrapper import GraphicBuilderRenderer, RenderOptions

async def render_example():
    async with GraphicBuilderRenderer(host="localhost", port=8080) as renderer:
        # Check service health
        healthy = await renderer.health_check()
        print(f"Service healthy: {healthy}")

        # Render Proteus XML to PNG (currently only supported format)
        proteus_xml = open("model.xml").read()
        result = await renderer.render(
            proteus_xml,
            format="PNG",
            options=RenderOptions()
        )

        # Save output
        result.save_to_file("output.png")
        print(f"Rendered {result.format}: {len(result.content)} bytes (base64)")

asyncio.run(render_example())
```

## Version Information

### GraphicBuilder Source

- **Repository**: https://gitlab.com/dexpi/GraphicBuilder
- **Branch**: `master` (used due to Java 17 compatibility issues in tags)
- **Commit**: `5e1e3ed` (as of 2025-11-12)
- **Build**: Java 8 (Eclipse Temurin 8-jdk-jammy)

**Note**: Legacy tags (1.0-1.2) require Java 8 and have JAXB dependency issues. The master branch is used with Java 8 for compatibility.

### Current Limitations

**CLI Format Support**: GraphicBuilder's command-line interface (`StandAloneTester`) only supports PNG output. While the codebase contains `ImageFactory_SVG` and PDF rendering code, the CLI does not expose these formats:

- **Supported**: PNG (native output)
- **Not Available via CLI**: SVG, PDF (require direct Java API usage)
- **Known Bug**: CLI exits with code 1 even on successful rendering (NullPointerException after file creation)

The Flask service wrapper works around these limitations by checking for output file existence rather than exit codes.

### Version Pinning

The Dockerfile uses an ARG to allow flexible version selection at build time:

```bash
# Default build (uses master)
docker build -t engineering-mcp/graphicbuilder:latest .

# Use different ref
docker build --build-arg GB_REF=refs/tags/1.1 -t engineering-mcp/graphicbuilder:1.1 .
```

## License

GraphicBuilder is an open-source project from the DEXPI organization.

**License Status**: No LICENSE file found in the GraphicBuilder repository (as of commit 5e1e3ed).

**Recommendation**: Contact the DEXPI organization at https://dexpi.org/ for clarification on licensing terms before commercial use.

**This Integration**: The wrapper code, Docker configuration, and Python client in this repository are part of the Engineering MCP Server project.

## Architecture

### Components

1. **GraphicBuilder JAR** (`/app/GraphicBuilder/org.dexpi.pid.imaging/target/GraphicBuilder-1.0-jar-with-dependencies.jar`)
   - Java application that performs actual rendering
   - Requires Proteus 4.2 XML format
   - Outputs SVG, PNG, PDF

2. **Flask Service** (`graphicbuilder-service.py`)
   - HTTP wrapper around GraphicBuilder JAR
   - Endpoints: `/health`, `/render`, `/validate`, `/symbols`
   - Handles temp file management
   - Returns base64-encoded binary formats

3. **Python Client** (`wrapper.py`)
   - Async/await HTTP client
   - Type-safe render options
   - Client-side caching
   - Automatic base64 decoding

4. **Symbol Libraries**
   - NOAKADEXPI symbols (701 symbols)
   - Mounted from `src/visualization/symbols/assets`

### Docker Configuration

```yaml
services:
  graphicbuilder:
    build:
      context: ./src/visualization/graphicbuilder
    ports:
      - "8080:8080"
    volumes:
      - ./src/visualization/symbols/assets:/app/symbols:ro
      - ./cache/graphicbuilder:/tmp/graphicbuilder/cache
      - ./logs/graphicbuilder:/app/logs
    environment:
      - JAVA_OPTS=-Xmx2G -Djava.awt.headless=true
      - SYMBOL_PATH=/app/symbols/NOAKADEXPI
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## API Reference

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0",
  "jar_path": "/app/GraphicBuilder/org.dexpi.pid.imaging/target/GraphicBuilder-1.0-jar-with-dependencies.jar",
  "java_version": "1.8.0_..."
}
```

### Render

```http
POST /render
Content-Type: application/json

{
  "xml": "<PlantModel>...</PlantModel>",
  "format": "PNG",
  "options": {}
}
```

**Supported Formats**: `PNG` only (SVG/PDF planned via Java API integration)

**Note**: The service currently only supports PNG output due to GraphicBuilder CLI limitations. Requests for other formats will return PNG with a warning in the metadata.

**Response** (SVG):
```json
{
  "content": "<?xml version=\"1.0\"?><svg>...</svg>",
  "format": "SVG",
  "encoded": false,
  "metadata": {
    "render_time": 1.234,
    "file_size": 12345
  }
}
```

**Response** (PNG/PDF):
```json
{
  "content": "iVBORw0KGgoAAAANSUhEUgAA...",  // base64
  "format": "PNG",
  "encoded": true,
  "metadata": {
    "render_time": 2.456,
    "file_size": 54321,
    "dimensions": {"width": 1024, "height": 768}
  }
}
```

### Validate XML

```http
POST /validate
Content-Type: application/json

{
  "xml": "<PlantModel>...</PlantModel>"
}
```

### List Symbols

```http
GET /symbols
```

## Testing

The project includes comprehensive integration tests:

```bash
# Run all GraphicBuilder tests
pytest tests/test_graphicbuilder_integration.py -v

# Run specific test class
pytest tests/test_graphicbuilder_integration.py::TestGraphicBuilderSmoke -v

# Run with service logs
docker compose logs -f graphicbuilder &
pytest tests/test_graphicbuilder_integration.py -v
```

### Test Coverage

- **Smoke Tests**: Health check, SVG/PNG/PDF rendering, file saving
- **Base64 Regression**: Encoding/decoding roundtrip, padding validation
- **Router Fallback**: Service unavailable handling
- **Render Options**: DPI, scale, imagemap support
- **Caching**: Client-side cache behavior
- **Full Pipeline**: SFILES → pyDEXPI → GraphicBuilder (integration)

**Note**: Rendering tests require valid Proteus 4.2 XML. Simple DEXPI XML may not render successfully.

## Configuration

Configuration is managed through `config.yaml`:

```yaml
# Version Information
version:
  graphicbuilder_branch: "master"
  graphicbuilder_note: "Using master branch as legacy tags require Java 8"
  repository: "https://gitlab.com/dexpi/GraphicBuilder"
  pinned_date: "2025-11-12"

graphicbuilder:
  jar_path: /app/GraphicBuilder/org.dexpi.pid.imaging/target/GraphicBuilder-1.0-jar-with-dependencies.jar
  symbol_path: /app/symbols
  temp_dir: /tmp/graphicbuilder
  java_opts: "-Xmx2G -Djava.awt.headless=true"

server:
  host: 0.0.0.0
  port: 8080
  max_file_size: 52428800  # 50MB
  timeout: 60  # seconds

rendering:
  default_format: SVG
  default_dpi: 300
  supported_formats:
    - SVG
    - PNG
    - PDF
```

## Build Information

### Build Steps

1. **XML Module**: Built first with `mvn clean install`
   - Located in `org.dexpi.pid.xml/`
   - Provides DEXPI XML parsing

2. **Imaging Module**: Built with `mvn clean package`
   - Located in `org.dexpi.pid.imaging/`
   - Depends on XML module
   - Produces `GraphicBuilder-1.0-jar-with-dependencies.jar`

### Build Time

- Clean build: ~85 seconds
- Image size: 1.49GB
- Java heap: 2GB (configurable via JAVA_OPTS)

## Troubleshooting

### Service won't start

```bash
# Check Docker logs
docker compose logs graphicbuilder

# Check health endpoint
curl -v http://localhost:8080/health
```

### Rendering fails with 500 error

**Symptom**: "Output file not generated"

**Cause**: Invalid Proteus XML format

**Solution**: Ensure XML conforms to Proteus 4.2 schema
- Must have proper namespace declarations
- Equipment must have required attributes
- Positions must be specified

### Java heap space errors

**Solution**: Increase heap size in `docker-compose.yml`:

```yaml
environment:
  - JAVA_OPTS=-Xmx4G -Djava.awt.headless=true
```

### Symbol not found errors

**Solution**: Ensure NOAKADEXPI symbols are mounted:

```bash
ls src/visualization/symbols/assets/NOAKADEXPI/
```

## Performance

### Typical Rendering Times

- Small diagrams (<10 equipment): ~1-2 seconds
- Medium diagrams (10-50 equipment): ~2-5 seconds
- Large diagrams (>50 equipment): ~5-15 seconds

### Optimization

- **Client-side caching**: Identical requests return cached results
- **Server-side caching**: Configurable via `cache.ttl` in config.yaml
- **Format selection**: SVG is fastest, PDF is slowest

## Integration with MCP Server

GraphicBuilder integrates with the Engineering MCP Server renderer router:

1. **Router Registration**: Registered in `renderer_router.py` with production quality level
2. **Capabilities**: Supports SVG/PNG/PDF, high quality, imagemaps
3. **Fallback**: Router falls back to ProteusXMLDrawing if GraphicBuilder unavailable
4. **Priority**: Selected for production-quality rendering requests

## Development

### Rebuild Service

```bash
# Rebuild and restart
docker compose up -d --build graphicbuilder

# View build logs
docker compose logs --tail=100 graphicbuilder
```

### Update GraphicBuilder Version

1. Edit `Dockerfile` ARG:
   ```dockerfile
   ARG GB_REF=refs/tags/1.3  # New version
   ```

2. Update `config.yaml` version info

3. Rebuild:
   ```bash
   docker compose build graphicbuilder
   ```

### Add Symbols

1. Place symbols in `src/visualization/symbols/assets/NOAKADEXPI/`
2. Restart service: `docker compose restart graphicbuilder`
3. Verify: `curl http://localhost:8080/symbols`

## Future Improvements

- [ ] **SVG/PDF support**: Integrate GraphicBuilder Java API directly (bypass CLI limitations)
- [ ] Proteus XML export from pyDEXPI models
- [ ] Batch rendering support
- [ ] WebSocket streaming for large renders
- [ ] Symbol library management API
- [ ] Render queue with priority
- [ ] Horizontal scaling support

## References

- **DEXPI GraphicBuilder**: https://gitlab.com/dexpi/GraphicBuilder
- **DEXPI Organization**: https://dexpi.org/
- **Proteus XML Documentation**: https://dexpi.org/specifications/
- **Engineering MCP Server**: ../../../README.md

---

**Last Updated**: November 13, 2025
**Phase**: 5 Week 4
**Status**: Functional - PNG rendering validated with DEXPI TrainingTestCases (SVG/PDF pending)
