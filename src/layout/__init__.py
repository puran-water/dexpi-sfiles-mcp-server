"""Layout module for automatic graph positioning.

This module provides:
- Layout engine abstraction (LayoutEngine protocol)
- ELK integration via elkjs (orthogonal routing, port-aware)
- P&ID-specific layout presets

Architecture Decision (Codex Consensus #019adb91):
    - Separate layout layer from topology
    - Store ELK-native coordinates (top-left origin, mm)
    - Use persistent Node.js worker for ELK
"""

from src.layout.engines.base import LayoutEngine
from src.layout.engines.elk import ELKLayoutEngine, PID_LAYOUT_OPTIONS

__all__ = [
    "LayoutEngine",
    "ELKLayoutEngine",
    "PID_LAYOUT_OPTIONS",
]
