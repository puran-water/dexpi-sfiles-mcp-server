"""Git-based project persistence for DEXPI and SFILES models."""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging
import subprocess

from pydexpi.loaders import JsonSerializer
from Flowsheet_Class.flowsheet import Flowsheet
import networkx as nx

logger = logging.getLogger(__name__)


def canonical_json_dump(data: Any, file_path: Path, **kwargs) -> None:
    """Write JSON with sorted keys for deterministic output.
    
    Args:
        data: Data to serialize
        file_path: Path to write to
        **kwargs: Additional arguments passed to json.dump
    """
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, **kwargs)


class ProjectPersistence:
    """Manages git-based persistence for engineering projects."""
    
    def __init__(self):
        """Initialize the persistence manager."""
        self.json_serializer = JsonSerializer()
    
    def init_project(self, project_path: str, project_name: str, description: str = "") -> Dict[str, Any]:
        """Initialize a new git project with standard structure.
        
        Args:
            project_path: Path where project should be created
            project_name: Name of the project
            description: Optional project description
            
        Returns:
            Project metadata dict
        """
        path = Path(project_path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Create standard directories
        (path / "dexpi").mkdir(exist_ok=True)
        (path / "sfiles").mkdir(exist_ok=True)
        
        # Create project metadata
        metadata = {
            "name": project_name,
            "description": description,
            "created": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        canonical_json_dump(metadata, path / "project.json")
        
        # Create README
        readme_content = f"""# {project_name}

{description}

## Structure
- `dexpi/` - P&ID models in DEXPI format
- `sfiles/` - BFD/PFD models in SFILES format
- `project.json` - Project metadata

Created: {metadata['created']}
"""
        with open(path / "README.md", "w") as f:
            f.write(readme_content)
        
        # Initialize git repo
        try:
            subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Initialize project: {project_name}"],
                cwd=path, check=True, capture_output=True
            )
            logger.info(f"Initialized git repository at {path}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git initialization failed: {e}")
        
        return metadata
    
    def save_dexpi(
        self,
        model: Any,
        project_path: str,
        model_name: str,
        commit_message: Optional[str] = None
    ) -> Dict[str, str]:
        """Save DEXPI model to project.
        
        Args:
            model: DEXPI model object
            project_path: Path to project root
            model_name: Name for the model (without extension)
            commit_message: Optional git commit message
            
        Returns:
            Dict with paths to saved files
        """
        path = Path(project_path)
        dexpi_dir = path / "dexpi"
        dexpi_dir.mkdir(exist_ok=True)
        
        # Save model as JSON
        json_path = dexpi_dir / f"{model_name}.json"
        self.json_serializer.save(model, str(dexpi_dir), model_name)
        
        # Save metadata
        meta_path = dexpi_dir / f"{model_name}.meta.json"
        metadata = {
            "name": model_name,
            "type": "DEXPI P&ID",
            "created": datetime.now().isoformat(),
            "project_name": model.metadata.projectData.projectName if hasattr(model, 'metadata') and model.metadata else None,
            "drawing_number": model.metadata.drawingData.drawingNumber if hasattr(model, 'metadata') and model.metadata else None
        }
        canonical_json_dump(metadata, meta_path)
        
        # Export GraphML for visualization
        try:
            from pydexpi.loaders import MLGraphLoader
            loader = MLGraphLoader(plant_model=model)
            graph = loader.dexpi_to_graph(model)
            
            # Clean None values for GraphML export
            for node, attrs in graph.nodes(data=True):
                for key, value in list(attrs.items()):
                    if value is None:
                        attrs[key] = ""
            
            for u, v, attrs in graph.edges(data=True):
                for key, value in list(attrs.items()):
                    if value is None:
                        attrs[key] = ""
            
            graphml_path = dexpi_dir / f"{model_name}.graphml"
            nx.write_graphml(graph, str(graphml_path))
        except Exception as e:
            logger.warning(f"GraphML export failed: {e}")
            graphml_path = None
        
        # Git commit
        if commit_message is None:
            commit_message = f"Save DEXPI model: {model_name}"
        
        self._git_add_commit(path, [json_path, meta_path, graphml_path], commit_message)
        
        return {
            "json": str(json_path),
            "meta": str(meta_path),
            "graphml": str(graphml_path) if graphml_path else None
        }
    
    def load_dexpi(self, project_path: str, model_name: str) -> Any:
        """Load DEXPI model from project.
        
        Args:
            project_path: Path to project root
            model_name: Name of the model (without extension)
            
        Returns:
            DEXPI model object
        """
        path = Path(project_path)
        dexpi_dir = path / "dexpi"
        
        # Load model from JSON
        model = self.json_serializer.load(str(dexpi_dir), model_name)
        return model
    
    def save_sfiles(
        self,
        flowsheet: Flowsheet,
        project_path: str,
        flowsheet_name: str,
        commit_message: Optional[str] = None
    ) -> Dict[str, str]:
        """Save SFILES flowsheet to project.
        
        Args:
            flowsheet: Flowsheet object
            project_path: Path to project root
            flowsheet_name: Name for the flowsheet (without extension)
            commit_message: Optional git commit message
            
        Returns:
            Dict with paths to saved files
        """
        path = Path(project_path)
        sfiles_dir = path / "sfiles"
        sfiles_dir.mkdir(exist_ok=True)
        
        # Save flowsheet state as JSON
        state_path = sfiles_dir / f"{flowsheet_name}.json"
        state_data = {
            "nodes": list(flowsheet.state.nodes(data=True)),
            "edges": list(flowsheet.state.edges(data=True))
        }
        canonical_json_dump(state_data, state_path)
        
        # Generate and save SFILES string
        try:
            flowsheet.convert_to_sfiles(version="v2", canonical=True)
            sfiles_string = flowsheet.sfiles
        except Exception as e:
            logger.warning(f"SFILES conversion failed: {e}")
            sfiles_string = None
        
        sfiles_path = None
        if sfiles_string:
            sfiles_path = sfiles_dir / f"{flowsheet_name}.sfiles"
            with open(sfiles_path, "w") as f:
                f.write(sfiles_string)
        
        # Save metadata
        meta_path = sfiles_dir / f"{flowsheet_name}.meta.json"
        metadata = {
            "name": flowsheet_name,
            "type": "SFILES Flowsheet",
            "created": datetime.now().isoformat(),
            "num_nodes": flowsheet.state.number_of_nodes(),
            "num_edges": flowsheet.state.number_of_edges()
        }
        canonical_json_dump(metadata, meta_path)
        
        # Git commit
        if commit_message is None:
            commit_message = f"Save SFILES flowsheet: {flowsheet_name}"
        
        self._git_add_commit(path, [state_path, sfiles_path, meta_path], commit_message)
        
        return {
            "json": str(state_path),
            "sfiles": str(sfiles_path) if sfiles_path else None,
            "meta": str(meta_path)
        }
    
    def load_sfiles(self, project_path: str, flowsheet_name: str) -> Flowsheet:
        """Load SFILES flowsheet from project.
        
        Args:
            project_path: Path to project root
            flowsheet_name: Name of the flowsheet (without extension)
            
        Returns:
            Flowsheet object
        """
        path = Path(project_path)
        sfiles_dir = path / "sfiles"
        
        # Load flowsheet state from JSON
        state_path = sfiles_dir / f"{flowsheet_name}.json"
        with open(state_path, "r") as f:
            state_data = json.load(f)
        
        # Reconstruct flowsheet
        flowsheet = Flowsheet()
        flowsheet.state = nx.DiGraph()
        
        # Add nodes
        for node, attrs in state_data["nodes"]:
            flowsheet.state.add_node(node, **attrs)
        
        # Add edges
        for u, v, attrs in state_data["edges"]:
            flowsheet.state.add_edge(u, v, **attrs)
        
        # Try to load SFILES string if available
        sfiles_path = sfiles_dir / f"{flowsheet_name}.sfiles"
        if sfiles_path.exists():
            with open(sfiles_path, "r") as f:
                flowsheet.sfiles = f.read()
        
        return flowsheet
    
    def list_models(self, project_path: str) -> Dict[str, List[str]]:
        """List all models in a project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Dict with 'dexpi' and 'sfiles' model lists
        """
        path = Path(project_path)
        
        models = {
            "dexpi": [],
            "sfiles": []
        }
        
        # List DEXPI models
        dexpi_dir = path / "dexpi"
        if dexpi_dir.exists():
            for json_file in dexpi_dir.glob("*.json"):
                if not json_file.name.endswith(".meta.json"):
                    models["dexpi"].append(json_file.stem)
        
        # List SFILES flowsheets
        sfiles_dir = path / "sfiles"
        if sfiles_dir.exists():
            for json_file in sfiles_dir.glob("*.json"):
                if not json_file.name.endswith(".meta.json"):
                    models["sfiles"].append(json_file.stem)
        
        return models
    
    def _git_add_commit(self, project_path: Path, files: List[Path], message: str):
        """Add files and commit to git.
        
        Args:
            project_path: Project root path
            files: List of file paths to add
            message: Commit message
        """
        try:
            # Filter out None values
            files = [f for f in files if f is not None]
            
            # Make paths relative to project root
            rel_files = [str(Path(f).relative_to(project_path)) for f in files]
            
            # Git add
            subprocess.run(
                ["git", "add"] + rel_files,
                cwd=project_path,
                check=True,
                capture_output=True
            )
            
            # Git commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=project_path,
                check=True,
                capture_output=True
            )
            
            logger.info(f"Committed to git: {message}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e}")
        except Exception as e:
            logger.warning(f"Git operation failed: {e}")