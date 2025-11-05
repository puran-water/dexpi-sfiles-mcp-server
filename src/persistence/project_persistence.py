"""Git-based project persistence for DEXPI and SFILES models."""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging
import subprocess

from pydexpi.loaders import JsonSerializer
from ..adapters.sfiles_adapter import get_flowsheet_class

# Safe import with helpful error messages
Flowsheet = get_flowsheet_class()
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
        (path / "bfd").mkdir(exist_ok=True)   # Block Flow Diagrams
        (path / "pfd").mkdir(exist_ok=True)   # Process Flow Diagrams
        (path / "pid").mkdir(exist_ok=True)   # P&ID (DEXPI)
        
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
- `bfd/` - Block Flow Diagrams (SFILES format, BlackBox visualization)
- `pfd/` - Process Flow Diagrams (SFILES format, GraphML visualization)
- `pid/` - Piping & Instrumentation Diagrams (DEXPI format)
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
        pid_dir = path / "pid"
        pid_dir.mkdir(exist_ok=True)
        
        # Save model as JSON
        json_path = pid_dir / f"{model_name}.json"
        self.json_serializer.save(model, str(pid_dir), model_name)
        
        # Save metadata
        meta_path = pid_dir / f"{model_name}.meta.json"
        metadata = {
            "name": model_name,
            "type": "DEXPI P&ID",
            "created": datetime.now().isoformat(),
            "project_name": model.conceptualModel.metaData.projectName if model.conceptualModel and model.conceptualModel.metaData else None,
            "drawing_number": model.conceptualModel.metaData.drawingNumber if model.conceptualModel and model.conceptualModel.metaData else None
        }
        canonical_json_dump(metadata, meta_path)
        
        # Export GraphML (sanitized) and raster/vector images for human auditing
        graphml_path = None
        png_path = None
        try:
            # Use unified converter for GraphML (handles attribute sanitization)
            from ..converters.graph_converter import UnifiedGraphConverter
            converter = UnifiedGraphConverter()
            graphml_content = converter.dexpi_to_graphml(model, include_msr=True)
            graphml_path = pid_dir / f"{model_name}.graphml"
            with open(graphml_path, "w", encoding="utf-8") as f:
                f.write(graphml_content)
        except Exception as e:
            logger.warning(f"DEXPI GraphML export failed: {e}")

        # Interactive HTML visualization with hover details
        html_path = None
        try:
            from pydexpi.loaders.ml_graph_loader import MLGraphLoader
            loader = MLGraphLoader(plant_model=model)
            # Ensure graph is parsed
            try:
                loader.parse_dexpi_to_graph()
            except Exception:
                # Some MLGraphLoader versions support direct conversion
                _ = loader.dexpi_to_graph(model)
            
            # Enhance node data with specifications for hover
            for node_id in loader.plant_graph.nodes():
                node_data = loader.plant_graph.nodes[node_id]
                # The node already has 'dexpi_class' and other attributes
                # We can enhance the hover information by building a better text
                dexpi_class = node_data.get('dexpi_class', 'Unknown')
                hover_text = f"<b>{node_id}</b><br>Type: {dexpi_class}<br>"
                
                # Add any additional attributes that aren't internal
                for key, value in node_data.items():
                    if key not in ['dexpi_class', 'id', 'pos'] and value is not None:
                        hover_text += f"{key}: {value}<br>"
                
                # Store enhanced hover text
                node_data['hover_text'] = hover_text
            
            # Generate interactive Plotly figure
            fig = loader.draw_process_plotly()
            
            # Update figure to use our enhanced hover text
            for trace in fig.data:
                if hasattr(trace, 'marker') and trace.marker.size == 10:  # Node trace
                    # Build hover text array matching node order
                    hover_texts = []
                    for node in loader.plant_graph.nodes():
                        hover_texts.append(loader.plant_graph.nodes[node].get('hover_text', node))
                    trace.hovertext = hover_texts
                    trace.hoverinfo = 'text'
            
            # Save as self-contained HTML with export capabilities
            html_path = pid_dir / f"{model_name}.html"
            fig.write_html(
                str(html_path),
                include_plotlyjs='inline',  # Fully self-contained
                config={
                    'displayModeBar': True,
                    'toImageButtonOptions': {
                        'format': 'svg',  # Can be png, svg, jpeg
                        'filename': model_name,
                        'height': 800,
                        'width': 1200,
                        'scale': 1
                    }
                }
            )
            logger.info(f"DEXPI HTML visualization saved: {html_path}")
        except Exception as e:
            logger.warning(f"DEXPI HTML export failed: {e}")
        
        # Git commit
        if commit_message is None:
            commit_message = f"Save DEXPI model: {model_name}"
        
        self._git_add_commit(path, [json_path, meta_path, graphml_path, html_path], commit_message)

        return {
            "json": str(json_path),
            "meta": str(meta_path),
            "graphml": str(graphml_path) if graphml_path else None,
            "html": str(html_path) if html_path else None
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
        pid_dir = path / "pid"
        
        # Load model from JSON
        try:
            model = self.json_serializer.load(str(pid_dir), model_name)
        except (KeyError, Exception) as e:
            # Handle missing references - try loading raw JSON and converting
            import json
            json_path = pid_dir / f"{model_name}.json"
            with open(json_path, 'r') as f:
                model_dict = json.load(f)
            # Use dict_to_model as fallback
            model = self.json_serializer.dict_to_model(model_dict)
            logger.warning(f"Loaded model with missing reference workaround: {e}")
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
        
        # Determine target directory based on flowsheet type
        if getattr(flowsheet, 'type', 'PFD') == "BFD":
            target_dir = path / "bfd"
        else:
            target_dir = path / "pfd"
        target_dir.mkdir(exist_ok=True)
        
        # Save flowsheet state as JSON
        state_path = target_dir / f"{flowsheet_name}.json"
        state_data = {
            "type": getattr(flowsheet, 'type', 'PFD'),  # Preserve flowsheet type
            "name": getattr(flowsheet, 'name', flowsheet_name),
            "description": getattr(flowsheet, 'description', ''),
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
            sfiles_path = target_dir / f"{flowsheet_name}.sfiles"
            with open(sfiles_path, "w") as f:
                f.write(sfiles_string)
        
        # Save metadata
        meta_path = target_dir / f"{flowsheet_name}.meta.json"
        metadata = {
            "name": flowsheet_name,
            "type": getattr(flowsheet, 'type', 'PFD'),  # Use actual type instead of "SFILES Flowsheet"
            "diagram_type": "BFD" if getattr(flowsheet, 'type', 'PFD') == "BFD" else "PFD",
            "created": datetime.now().isoformat(),
            "num_nodes": flowsheet.state.number_of_nodes(),
            "num_edges": flowsheet.state.number_of_edges()
        }
        canonical_json_dump(metadata, meta_path)
        
        # Export GraphML for human auditing
        graphml_path = None
        png_path = None
        try:
            from ..converters.graph_converter import UnifiedGraphConverter
            converter = UnifiedGraphConverter()
            graphml_content = converter.sfiles_to_graphml(flowsheet)
            graphml_path = target_dir / f"{flowsheet_name}.graphml"
            with open(graphml_path, "w", encoding="utf-8") as f:
                f.write(graphml_content)
        except Exception as e:
            logger.warning(f"SFILES GraphML export failed: {e}")

        # Interactive HTML visualization with hover details
        html_path = None
        try:
            import plotly.graph_objects as go
            import networkx as nx
            
            # Use hierarchical layout for better flow representation
            pos = nx.spring_layout(flowsheet.state, seed=42, k=2)
            
            # Build edge traces with stream hover data
            edge_traces = []
            for edge in flowsheet.state.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_data = edge[2]
                
                # Create hover text for streams
                hover_text = f"<b>Stream: {edge_data.get('stream_name', 'Unnamed')}</b><br>"
                if 'flow' in edge_data:
                    hover_text += f"Flow: {edge_data['flow']}<br>"
                if 'temperature' in edge_data:
                    hover_text += f"Temperature: {edge_data['temperature']}<br>"
                if 'pressure' in edge_data:
                    hover_text += f"Pressure: {edge_data['pressure']}<br>"
                # Add any other stream properties
                for key, value in edge_data.items():
                    if key not in ['stream_name', 'flow', 'temperature', 'pressure', 'tags_he', 'tags_col'] and value is not None:
                        hover_text += f"{key.replace('_', ' ').title()}: {value}<br>"
                
                edge_traces.append(go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=2, color='#888'),
                    hoverinfo='text',
                    hovertext=hover_text,
                    showlegend=False
                ))
            
            # Build node trace with equipment hover data
            node_x = []
            node_y = []
            node_text = []
            node_hover = []
            node_colors = []
            
            # Define colors for different unit types
            unit_type_colors = {
                'reactor': '#ff7f0e',  # Orange
                'hex': '#2ca02c',       # Green
                'distcol': '#1f77b4',   # Blue
                'pump': '#9467bd',      # Purple
                'compressor': '#8c564b', # Brown
                'vessel': '#e377c2',    # Pink
                'mixer': '#7f7f7f',     # Gray
                'splitter': '#bcbd22',  # Olive
                'default': '#17becf'    # Cyan
            }
            
            for node in flowsheet.state.nodes(data=True):
                x, y = pos[node[0]]
                node_x.append(x)
                node_y.append(y)
                node_text.append(node[0])  # Tag/name
                
                # Create hover text for units
                node_data = node[1]
                hover = f"<b>{node[0]}</b><br>"
                unit_type = node_data.get('unit_type', 'Unknown')
                hover += f"Type: {unit_type}<br>"
                
                # Add all specifications
                for key, value in node_data.items():
                    if key not in ['unit_type', 'pos', 'id'] and value is not None:
                        hover += f"{key.replace('_', ' ').title()}: {value}<br>"
                
                node_hover.append(hover)
                
                # Assign color based on unit type
                node_colors.append(unit_type_colors.get(unit_type, unit_type_colors['default']))
            
            node_trace = go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers+text',
                text=node_text,
                textposition="top center",
                hoverinfo='text',
                hovertext=node_hover,
                marker=dict(
                    size=20,
                    color=node_colors,
                    line=dict(color='darkblue', width=2)
                )
            )
            
            # Create figure
            fig = go.Figure(
                data=edge_traces + [node_trace],
                layout=go.Layout(
                    title=f"Flowsheet: {flowsheet_name}",
                    showlegend=False,
                    hovermode='closest',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    plot_bgcolor='white'
                )
            )
            
            # Save as self-contained HTML
            html_path = target_dir / f"{flowsheet_name}.html"
            fig.write_html(
                str(html_path),
                include_plotlyjs='inline',
                config={
                    'displayModeBar': True,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': flowsheet_name,
                        'height': 600,
                        'width': 800
                    }
                }
            )
            logger.info(f"SFILES HTML visualization saved: {html_path}")
        except Exception as e:
            logger.warning(f"SFILES HTML export failed: {e}")

        # Git commit
        if commit_message is None:
            commit_message = f"Save SFILES flowsheet: {flowsheet_name}"

        self._git_add_commit(path, [state_path, sfiles_path, meta_path, graphml_path, html_path], commit_message)

        return {
            "json": str(state_path),
            "sfiles": str(sfiles_path) if sfiles_path else None,
            "meta": str(meta_path),
            "graphml": str(graphml_path) if graphml_path else None,
            "html": str(html_path) if html_path else None
        }
    
    def load_sfiles(self, project_path: str, flowsheet_name: str, diagram_type: str = None) -> Flowsheet:
        """Load SFILES flowsheet from project.
        
        Args:
            project_path: Path to project root
            flowsheet_name: Name of the flowsheet (without extension)
            diagram_type: Optional type hint ("bfd" or "pfd")
            
        Returns:
            Flowsheet object
        """
        path = Path(project_path)
        
        # Determine which directory to load from
        if diagram_type:
            target_dir = path / diagram_type.lower()
            state_path = target_dir / f"{flowsheet_name}.json"
        else:
            # Try both locations
            for dir_name in ["bfd", "pfd"]:
                state_path = path / dir_name / f"{flowsheet_name}.json"
                if state_path.exists():
                    target_dir = path / dir_name
                    break
            else:
                raise FileNotFoundError(f"Flowsheet {flowsheet_name} not found in bfd/ or pfd/ directories")
        
        # Load flowsheet state from JSON
        with open(state_path, "r") as f:
            state_data = json.load(f)
        
        # Reconstruct flowsheet
        flowsheet = Flowsheet()
        flowsheet.state = nx.DiGraph()
        
        # Restore flowsheet metadata
        flowsheet.type = state_data.get('type', 'PFD')
        flowsheet.name = state_data.get('name', flowsheet_name)
        flowsheet.description = state_data.get('description', '')
        
        # Add nodes
        for node, attrs in state_data["nodes"]:
            flowsheet.state.add_node(node, **attrs)
        
        # Add edges
        for u, v, attrs in state_data["edges"]:
            flowsheet.state.add_edge(u, v, **attrs)
        
        # Try to load SFILES string if available
        sfiles_path = target_dir / f"{flowsheet_name}.sfiles"
        if sfiles_path.exists():
            with open(sfiles_path, "r") as f:
                flowsheet.sfiles = f.read()
        
        return flowsheet
    
    def list_models(self, project_path: str) -> Dict[str, List[str]]:
        """List all models in a project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Dict with 'pid', 'bfd', and 'pfd' model lists
        """
        path = Path(project_path)
        
        models = {
            "pid": [],
            "bfd": [],
            "pfd": []
        }
        
        # List P&ID models
        pid_dir = path / "pid"
        if pid_dir.exists():
            for json_file in pid_dir.glob("*.json"):
                if not json_file.name.endswith(".meta.json"):
                    models["pid"].append(json_file.stem)
        
        # List BFD flowsheets
        bfd_dir = path / "bfd"
        if bfd_dir.exists():
            for json_file in bfd_dir.glob("*.json"):
                if not json_file.name.endswith(".meta.json"):
                    models["bfd"].append(json_file.stem)
        
        # List PFD flowsheets
        pfd_dir = path / "pfd"
        if pfd_dir.exists():
            for json_file in pfd_dir.glob("*.json"):
                if not json_file.name.endswith(".meta.json"):
                    models["pfd"].append(json_file.stem)
        
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
