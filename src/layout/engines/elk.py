"""ELK layout engine via elkjs.

Provides layered layout with orthogonal edge routing for P&ID diagrams.
Uses a persistent Node.js worker for performance.

Architecture Decision (Codex Consensus #019adb91):
    - Persistent Node.js worker (not per-call spawn)
    - stdin/stdout JSON protocol with request IDs
    - Store ELK-native coordinates (top-left origin, mm)
    - Capture sourcePoint/targetPoint for edge fidelity
"""

import asyncio
import atexit
import glob
import json
import logging
import os
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from src.layout.engines.base import LayoutEngine
from src.models.layout_metadata import (
    EdgeRoute,
    EdgeSection,
    LabelPosition,
    LayoutMetadata,
    NodePosition,
    PortLayout,
)

logger = logging.getLogger(__name__)

# P&ID-specific ELK preset (Codex Consensus)
PID_LAYOUT_OPTIONS = {
    # Algorithm
    "elk.algorithm": "layered",
    "elk.direction": "RIGHT",
    # Edge routing
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.mergeEdges": False,
    # Layering strategy
    "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
    "elk.layered.cycleBreaking.strategy": "DEPTH_FIRST",
    "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
    # Port constraints
    "elk.portConstraints": "FIXED_ORDER",
    "elk.portAlignment.default": "CENTER",
    # Spacing (mm)
    "elk.layered.spacing.nodeNodeBetweenLayers": 50,
    "elk.layered.spacing.edgeNodeBetweenLayers": 25,
    "elk.layered.spacing.edgeEdgeBetweenLayers": 25,
    "elk.spacing.portPort": 10,
    "elk.port.borderOffset": 3,
    # Labels
    "elk.edgeLabels.inline": True,
    "elk.layered.spacing.labelLabel": 10,
}


class ELKWorkerManager:
    """Manages a persistent ELK worker process.

    Provides thread-safe access to a long-running Node.js process
    that handles ELK layout requests via stdin/stdout JSON protocol.
    """

    def __init__(
        self,
        node_path: str,
        worker_script: Path,
        timeout: int = 30,
    ):
        """Initialize worker manager.

        Args:
            node_path: Path to Node.js executable
            worker_script: Path to elk_worker.js
            timeout: Timeout in seconds for layout requests
        """
        self._node_path = node_path
        self._worker_script = worker_script
        self._timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._pending: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._started = False

    def _start_worker(self) -> None:
        """Start the worker process if not already running."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return  # Already running

            logger.debug("Starting ELK worker process")
            self._process = subprocess.Popen(
                [self._node_path, str(self._worker_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=Path(__file__).parent.parent.parent.parent,  # Project root
            )
            self._started = True
            logger.info(f"ELK worker started (PID: {self._process.pid})")

    def _ensure_worker(self) -> subprocess.Popen:
        """Ensure worker is running and return it."""
        self._start_worker()
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("ELK worker failed to start")
        return self._process

    async def request(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Send layout request and wait for response.

        Args:
            graph: ELK graph JSON

        Returns:
            ELK layout result

        Raises:
            RuntimeError: If layout fails or times out
        """
        request_id = str(uuid.uuid4())
        request = {"id": request_id, "graph": graph}

        # Send request synchronously (worker uses stdin)
        def send_and_receive():
            process = self._ensure_worker()

            # Send request
            request_line = json.dumps(request) + "\n"
            try:
                process.stdin.write(request_line)
                process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                # Worker died, try to restart
                logger.warning(f"ELK worker pipe broken: {e}, restarting")
                self._process = None
                process = self._ensure_worker()
                process.stdin.write(request_line)
                process.stdin.flush()

            # Read response (blocking)
            response_line = process.stdout.readline()
            if not response_line:
                raise RuntimeError("ELK worker closed unexpectedly")

            return json.loads(response_line)

        # Run in executor to not block event loop
        loop = asyncio.get_event_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(None, send_and_receive),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            logger.error(f"ELK request {request_id} timed out after {self._timeout}s")
            # Kill and restart worker on timeout
            self.shutdown()
            raise RuntimeError(f"ELK layout timed out after {self._timeout}s")

        # Check for error
        if "error" in response:
            raise RuntimeError(f"ELK layout failed: {response['error']}")

        if response.get("id") != request_id:
            logger.warning(f"Response ID mismatch: expected {request_id}, got {response.get('id')}")

        return response.get("result", {})

    def shutdown(self) -> None:
        """Shutdown the worker process."""
        with self._lock:
            if self._process is not None:
                logger.debug("Shutting down ELK worker")
                try:
                    self._process.stdin.close()
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except Exception as e:
                    logger.warning(f"Error shutting down ELK worker: {e}")
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None
                self._started = False

    @property
    def is_running(self) -> bool:
        """Check if worker is currently running."""
        with self._lock:
            return self._process is not None and self._process.poll() is None


# Global worker manager instance (shared across ELKLayoutEngine instances)
_worker_manager: Optional[ELKWorkerManager] = None
_worker_lock = threading.Lock()


def _cleanup_worker():
    """Cleanup worker on process exit."""
    global _worker_manager
    if _worker_manager is not None:
        _worker_manager.shutdown()


atexit.register(_cleanup_worker)


class ELKLayoutEngine(LayoutEngine):
    """ELK layout engine via elkjs Node.js subprocess.

    Uses stdin/stdout JSON protocol with a persistent worker process.
    The worker is shared across all ELKLayoutEngine instances for efficiency.
    """

    def __init__(
        self,
        node_path: Optional[str] = None,
        worker_script: Optional[Path] = None,
        timeout: int = 30,
    ):
        """Initialize ELK layout engine.

        Args:
            node_path: Path to Node.js executable (auto-detect if None)
            worker_script: Path to elk_worker.js (use bundled if None)
            timeout: Timeout in seconds for layout operations
        """
        self._node_path = node_path or self._find_node()
        self._worker_script = worker_script or self._default_worker_script()
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "elk"

    @property
    def supports_orthogonal_routing(self) -> bool:
        return True

    @property
    def supports_ports(self) -> bool:
        return True

    def _find_node(self) -> str:
        """Find Node.js executable."""
        # Try common paths
        for path in ["node", "/usr/bin/node", "/usr/local/bin/node"]:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return path
            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        # Try nvm path
        nvm_node = os.path.expanduser("~/.nvm/versions/node/*/bin/node")
        nvm_paths = glob.glob(nvm_node)
        if nvm_paths:
            return sorted(nvm_paths)[-1]  # Latest version

        raise RuntimeError("Node.js not found. Install Node.js to use ELK layout.")

    def _default_worker_script(self) -> Path:
        """Get path to bundled elk_worker.js."""
        return Path(__file__).parent.parent / "elk_worker.js"

    def _get_worker(self) -> ELKWorkerManager:
        """Get or create the shared worker manager."""
        global _worker_manager
        with _worker_lock:
            if _worker_manager is None:
                _worker_manager = ELKWorkerManager(
                    self._node_path,
                    self._worker_script,
                    self._timeout,
                )
            return _worker_manager

    async def is_available(self) -> bool:
        """Check if ELK is available."""
        try:
            # Check Node.js
            result = subprocess.run(
                [self._node_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False

            # Check elkjs module
            check_script = "try { require('elkjs'); console.log('ok'); } catch(e) { console.log('missing'); }"
            result = subprocess.run(
                [self._node_path, "-e", check_script],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=Path(__file__).parent.parent.parent.parent,  # Project root
            )
            return result.stdout.strip() == "ok"

        except Exception as e:
            logger.warning(f"ELK availability check failed: {e}")
            return False

    async def layout(
        self,
        graph: nx.DiGraph,
        options: Optional[Dict[str, Any]] = None,
    ) -> LayoutMetadata:
        """Compute layout using ELK.

        Args:
            graph: NetworkX DiGraph with node/edge data
            options: ELK layout options (merged with PID_LAYOUT_OPTIONS)

        Returns:
            LayoutMetadata with positions, edges, ports
        """
        # Merge options with defaults
        layout_options = {**PID_LAYOUT_OPTIONS, **(options or {})}

        # Convert graph to ELK JSON format
        elk_graph = self._graph_to_elk(graph, layout_options)

        # Run ELK layout via persistent worker
        worker = self._get_worker()
        elk_result = await worker.request(elk_graph)

        # Convert ELK result to LayoutMetadata
        return self._elk_to_layout(elk_result, layout_options)

    def _graph_to_elk(
        self, graph: nx.DiGraph, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert NetworkX graph to ELK JSON format.

        Args:
            graph: NetworkX DiGraph
            options: ELK layout options

        Returns:
            ELK JSON graph structure
        """
        elk_nodes = []
        elk_edges = []

        for node_id, attrs in graph.nodes(data=True):
            # Get node dimensions from attributes or defaults
            width = attrs.get("width", 60)
            height = attrs.get("height", 40)

            # Build port list
            ports = []
            node_ports = attrs.get("ports", [])
            for i, port in enumerate(node_ports):
                port_id = port.get("id", f"{node_id}_port_{i}")
                ports.append({
                    "id": port_id,
                    "width": port.get("width", 8),
                    "height": port.get("height", 8),
                    "properties": {
                        "port.side": port.get("side", "EAST"),
                        "port.index": port.get("index", i),
                    },
                })

            elk_nodes.append({
                "id": str(node_id),
                "width": width,
                "height": height,
                "ports": ports,
                "labels": [{"text": attrs.get("label", str(node_id))}],
            })

        for i, (source, target, attrs) in enumerate(graph.edges(data=True)):
            edge_id = attrs.get("id", f"e{i}")
            source_port = attrs.get("source_port")
            target_port = attrs.get("target_port")

            edge = {
                "id": edge_id,
                "sources": [source_port if source_port else str(source)],
                "targets": [target_port if target_port else str(target)],
            }

            # Add label if present
            label = attrs.get("label")
            if label:
                edge["labels"] = [{"text": label}]

            elk_edges.append(edge)

        return {
            "id": "root",
            "layoutOptions": options,
            "children": elk_nodes,
            "edges": elk_edges,
        }

    def _elk_to_layout(
        self, elk_result: Dict[str, Any], options: Dict[str, Any]
    ) -> LayoutMetadata:
        """Convert ELK result to LayoutMetadata.

        Args:
            elk_result: ELK JSON result with positions
            options: Layout options used

        Returns:
            LayoutMetadata instance
        """
        positions: Dict[str, NodePosition] = {}
        port_layouts: Dict[str, PortLayout] = {}
        edges: Dict[str, EdgeRoute] = {}
        labels: Dict[str, LabelPosition] = {}
        rotations: Dict[str, float] = {}

        # Process nodes
        for node in elk_result.get("children", []):
            node_id = node["id"]
            positions[node_id] = NodePosition(
                x=node.get("x", 0),
                y=node.get("y", 0),
            )

            # Process node labels
            for i, label in enumerate(node.get("labels", [])):
                label_id = f"{node_id}_label_{i}"
                labels[label_id] = LabelPosition(
                    x=label.get("x", 0),
                    y=label.get("y", 0),
                    width=label.get("width", 0),
                    height=label.get("height", 0),
                    text=label.get("text", ""),
                    kind="node",
                )

            # Process ports
            for port in node.get("ports", []):
                port_id = port["id"]
                port_layouts[port_id] = PortLayout(
                    id=port_id,
                    x=port.get("x", 0),
                    y=port.get("y", 0),
                    width=port.get("width", 8),
                    height=port.get("height", 8),
                    side=self._elk_side_to_side(
                        port.get("properties", {}).get("port.side", "EAST")
                    ),
                    index=port.get("properties", {}).get("port.index", 0),
                )

        # Process edges with full fidelity (Codex Consensus fix)
        for edge in elk_result.get("edges", []):
            edge_id = edge["id"]
            sections = []

            for section in edge.get("sections", []):
                sections.append(
                    EdgeSection(
                        id=section.get("id"),
                        startPoint=(
                            section["startPoint"]["x"],
                            section["startPoint"]["y"],
                        ),
                        endPoint=(
                            section["endPoint"]["x"],
                            section["endPoint"]["y"],
                        ),
                        bendPoints=[
                            (bp["x"], bp["y"])
                            for bp in section.get("bendPoints", [])
                        ],
                    )
                )

            # Extract source/target ports
            sources = edge.get("sources", [])
            targets = edge.get("targets", [])
            source_port = sources[0] if sources else None
            target_port = targets[0] if targets else None

            # Capture sourcePoint/targetPoint for edge fidelity (Codex Consensus fix)
            source_point = None
            target_point = None
            if "sourcePoint" in edge:
                source_point = (edge["sourcePoint"]["x"], edge["sourcePoint"]["y"])
            if "targetPoint" in edge:
                target_point = (edge["targetPoint"]["x"], edge["targetPoint"]["y"])

            # Edge labels
            edge_labels = []
            for label in edge.get("labels", []):
                edge_labels.append(
                    LabelPosition(
                        x=label.get("x", 0),
                        y=label.get("y", 0),
                        width=label.get("width", 0),
                        height=label.get("height", 0),
                        text=label.get("text", ""),
                        kind="edge",
                    )
                )

            edges[edge_id] = EdgeRoute(
                sections=sections,
                source_port=source_port,
                target_port=target_port,
                sourcePoint=source_point,
                targetPoint=target_point,
                labels=edge_labels,
            )

        return LayoutMetadata(
            algorithm="elk",
            layout_options=options,
            positions=positions,
            port_layouts=port_layouts,
            edges=edges,
            labels=labels,
            rotation=rotations,
        )

    def _elk_side_to_side(self, elk_side: str) -> str:
        """Convert ELK side string to standard side."""
        mapping = {
            "NORTH": "NORTH",
            "SOUTH": "SOUTH",
            "EAST": "EAST",
            "WEST": "WEST",
            "N": "NORTH",
            "S": "SOUTH",
            "E": "EAST",
            "W": "WEST",
        }
        return mapping.get(elk_side.upper(), "EAST")

    def shutdown(self) -> None:
        """Shutdown the ELK worker (for cleanup)."""
        global _worker_manager
        with _worker_lock:
            if _worker_manager is not None:
                _worker_manager.shutdown()
                _worker_manager = None
