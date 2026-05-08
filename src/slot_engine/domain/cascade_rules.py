"""CascadeRules: cascade behavior parameters for a game."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CascadeRules:
    """Per-game cascade configuration.

    Stored on a Game when it implements cascade mechanics. Engines that
    don't use cascades leave Game.cascade as None.

    multipliers: ordered list of multipliers applied at each cascade step.
    Step k applies multipliers[k]. If the cascade exceeds the list length,
    the engine's overflow policy decides (typically: clamp to the last value).
    """

    multipliers: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.multipliers:
            raise ValueError("CascadeRules requires at least one multiplier")
        if any(m <= 0 for m in self.multipliers):
            raise ValueError("All multipliers must be positive integers")