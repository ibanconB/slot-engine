"""Game engines: framework (base, registry) plus concrete implementations."""
from slot_engine.engines.base import GameEngine
from slot_engine.engines.registry import (
    available_engines,
    get_engine_class,
    register_engine,
)

# Import the impls subpackage to trigger engine registration via decorators.
from slot_engine.engines import impls  # noqa: F401

__all__ = [
    "GameEngine",
    "available_engines",
    "get_engine_class",
    "register_engine",
]