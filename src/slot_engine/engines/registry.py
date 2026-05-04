"""Registry of game engines, populated at import time via @register_engine"""
from __future__ import annotations

from collections.abc import  Callable

from slot_engine.domain import PlayResult
from slot_engine.engines.base import GameEngine

_REGISTRY: dict[str, type[GameEngine]] = {}

def register_engine(name: str) -> Callable[[type[GameEngine]], type[GameEngine]]:
    """Decorator that registers a game engine class under a name


    Usage:
        @register_engine("classic_lines")
        class ClassicLinesEngine:
            def play(self) -> PlayResult: ...

    Raises ValueError if the name is already registered.
    """

    def decorator(cls: type[GameEngine]) -> type[GameEngine]:
        if name in _REGISTRY:
            raise ValueError(
                f"Engine '{name}' is already registered to "
                f"{_REGISTRY[name].__name__}; cannot also register "
                f"{cls.__name__} under the same name."
            )
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_engine_class(name: str) -> type[GameEngine]:
    """Look up an engine class by its registered names

    Raises KeyError (with a helpful message) if no engine is registered
    """
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(none registered)"
        raise KeyError(
            f"No engine registered as '{name}. Avaliable ones are: {available}'"
        )
    return _REGISTRY[name]

def available_engines() -> tuple[str, ...]:
    """Return the names of all registered engines, alphabetically sorted"""
    return tuple(sorted(_REGISTRY))



