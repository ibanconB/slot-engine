"""SpinEngine - coordinates the reels and the RNG to generate spin results"""

from collections.abc import Iterable
from dataclasses import dataclass

from slot_engine.domain.reel import Reel
from slot_engine.domain.spin_result import SpinResult
from slot_engine.rng import RandomNumberGenerator


@dataclass(frozen=True, slots=True)
class SpinEngine:
    """Engine that produces spin results.

    Receives the reels, size of visible window and a RNG
    via dependencies injection. It is not mutable.
    """

    reels: tuple[Reel, ...]
    window_size: int
    rng: RandomNumberGenerator

    def __post_init__(self) -> None:
        if not self.reels:
            raise ValueError("SpinEngine must have at least one reel")
        if self.window_size <= 0:
            raise ValueError(f"Window size must be > 0, got {self.window_size}")

    @classmethod
    def create(
        cls,
        reels: Iterable[Reel],
        window_size: int,
        rng: RandomNumberGenerator,
    ) -> SpinEngine:
        """Friendly constructor that accepts every reel iterable"""
        return cls(reels=tuple(reels), window_size=window_size, rng=rng)

    def spin(self) -> SpinResult:
        """Executes a spin and returns the layout"""
        stop_positions = tuple(self.rng.randrange(reel.length) for reel in self.reels)
        columns = tuple(
            reel.window_at(pos, self.window_size)
            for reel, pos in zip(self.reels, stop_positions, strict=True)
        )
        return SpinResult(columns=columns, stop_positions=stop_positions)
