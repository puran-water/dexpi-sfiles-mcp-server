"""FastAPI dashboard server for engineering MCP."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import networkx as nx
from pydantic import BaseModel

from src.persistence import ProjectPersistence
from src.dashboard.graph_converter import CytoscapeConverter
from pydexpi.loaders import MLGraphLoader

logger = logging.getLogger(__name__)

app = FastAPI(title="Engineering MCP Dashboard")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection is closed, remove it
                self.active_connections.remove(connection)

manager = ConnectionManager()
converter = CytoscapeConverter()
persistence = ProjectPersistence()

# Store for active projects
active_projects: Dict[str, Any] = {}


class ProjectInfo(BaseModel):
    project_path: str
    
class ModelUpdate(BaseModel):
    project_path: str
    model_type: str  # "dexpi" or "sfiles"
    model_name: str


@app.get("/")
async def root():
    """Serve the main dashboard HTML."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    return HTMLResponse(content="<h1>Dashboard not built yet</h1>")


@app.post("/api/projects/open")
async def open_project(info: ProjectInfo):
    """Open a project and load its models."""
    try:
        models = persistence.list_models(info.project_path)
        active_projects[info.project_path] = models
        
        # Broadcast to all clients
        await manager.broadcast({
            "type": "project_opened",
            "project_path": info.project_path,
            "models": models
        })
        
        return {"status": "success", "models": models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_path:path}/models")
async def list_project_models(project_path: str):
    """List all models in a project."""
    try:
        models = persistence.list_models(project_path)
        return models
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/models/dexpi/{project_path:path}/{model_name}")
async def get_dexpi_graph(project_path: str, model_name: str):
    """Get DEXPI model as Cytoscape graph."""
    try:
        # Load DEXPI model
        model = persistence.load_dexpi(project_path, model_name)
        
        # Convert to NetworkX graph
        loader = MLGraphLoader(plant_model=model)
        nx_graph = loader.dexpi_to_graph(model)
        
        # Convert to Cytoscape format
        cytoscape_data = converter.networkx_to_cytoscape(nx_graph)
        
        return cytoscape_data
    except Exception as e:
        logger.error(f"Error loading DEXPI model: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/models/sfiles/{project_path:path}/{model_name}")
async def get_sfiles_graph(project_path: str, model_name: str):
    """Get SFILES flowsheet as Cytoscape graph."""
    try:
        # Load SFILES flowsheet
        flowsheet = persistence.load_sfiles(project_path, model_name)
        
        # Convert to Cytoscape format
        cytoscape_data = converter.networkx_to_cytoscape(flowsheet.state)
        
        return cytoscape_data
    except Exception as e:
        logger.error(f"Error loading SFILES model: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
            elif data["type"] == "subscribe":
                # Client wants to subscribe to project updates
                project_path = data.get("project_path")
                if project_path:
                    # Send current state
                    if project_path in active_projects:
                        await websocket.send_json({
                            "type": "models_update",
                            "project_path": project_path,
                            "models": active_projects[project_path]
                        })
                        
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/notify/model_update")
async def notify_model_update(update: ModelUpdate):
    """Notify dashboard of model updates (called by MCP server)."""
    # Refresh model list
    models = persistence.list_models(update.project_path)
    active_projects[update.project_path] = models
    
    # Broadcast update to all clients
    await manager.broadcast({
        "type": "model_updated",
        "project_path": update.project_path,
        "model_type": update.model_type,
        "model_name": update.model_name,
        "models": models
    })
    
    return {"status": "success"}


# Mount static files (for CSS, JS, etc.)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)