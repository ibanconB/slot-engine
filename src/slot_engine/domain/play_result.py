"""PlayResult: composite result of one play, possibly with multiple cascade steps."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from slot_engine.domain.evaluation import Evaluation
from slot_engine.domain.spin_result import SpinResult


@dataclass(frozen=True, slots=True)
class PlayStep:
    """One (spin, evaluation, multiplier) within a play.

    A non-cascade game produces exactly one PlayStep with multiplier=1.
    A cascade game produces a sequence: (spin0, eval0, m=1), (spin1, eval1, m=2), ...
    """

    spin: SpinResult
    evaluation: Evaluation
    multiplier: int

    def __post_init__(self) -> None:
        if self.multiplier <= 0:
            raise ValueError(f"PlayStep multiplier must be > 0, got {self.multiplier}")


@dataclass(frozen=True, slots=True)
class PlayResult:
    """Result of one full play.

    Always has at least one PlayStep. Non-cascade games have exactly one
    step (multiplier=1). Cascade games append a step each time the cascade
    continues, with the multiplier the engine chose for that step.
    """

    steps: tuple[PlayStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("PlayResult requires at least one PlayStep")

    @property
    def total_payout(self) -> Decimal:
        """Sum of payouts across all steps, each weighted by its multiplier."""
        return sum(
            (step.evaluation.total_payout * step.multiplier for step in self.steps),
            start=Decimal("0"),
        )

    @property
    def is_winning(self) -> bool:
        """True if any step had a winning evaluation."""
        return any(step.evaluation.is_winning for step in self.steps)

    @property
    def num_steps(self) -> int:
        return len(self.steps)