"""Reel - a virtual reel with its symbols"""

from collections.abc import Iterable
from dataclasses import dataclass

from slot_engine.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Reel:
    """Represents a slot reel, defined for its symbol strip
    the strip is circular: when it reaches the end of the reel,
    returns to the beggining of the reel. It models the behaviour
    of a reel.
    """

    strip: tuple[Symbol, ...]

    def __post_init__(self) -> None:
        if not self.strip:
            raise ValueError("Reel strip cannot be empty")

    @classmethod
    def from_symbol(cls, symbols: Iterable[Symbol]) -> Reel:
        """Create Reel from symbol iterables"""
        return cls(tuple(symbols))

    @property
    def length(self) -> int:
        """Length of the reel"""
        return len(self.strip)

    def window_at(self, position: int, size: int) -> tuple[Symbol, ...]:
        """Returns `size` consecutive symbols at the given position starting from `position`
        We treat the strip as circular: if the window exceeds final, it continues from
        the beginning of the reel (wrap-around with module).
        """
        if size <= 0:
            raise ValueError(f"Window size cannot be negative, got {size}")
        return tuple(self.strip[(position + i) % self.length] for i in range(size))
