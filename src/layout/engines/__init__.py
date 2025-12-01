"""Layout engines registry.

Available engines:
- elk: ELK via elkjs (layered, orthogonal routing)
- spring: NetworkX spring layout (fallback)
"""

from src.layout.engines.base import LayoutEngine
from src.layout.engines.elk import ELKLayoutEngine, PID_LAYOUT_OPTIONS

# Engine registry
ENGINES = {
    "elk": ELKLayoutEngine,
}


def get_engine(name: str) -> type:
    """Get layout engine class by name.

    Args:
        name: Engine name ('elk', 'spring')

    Returns:
        Layout engine class

    Raises:
        ValueError: If engine not found
    """
    if name not in ENGINES:
        raise ValueError(f"Unknown layout engine: {name}. Available: {list(ENGINES.keys())}")
    return ENGINES[name]


__all__ = [
    "LayoutEngine",
    "ELKLayoutEngine",
    "PID_LAYOUT_OPTIONS",
    "ENGINES",
    "get_engine",
]
