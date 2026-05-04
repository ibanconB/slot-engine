"""Composite result of a single play: spin outcome plus its evaluation."""
from __future__ import annotations

from dataclasses import dataclass

from slot_engine.domain.evaluation import Evaluation
from slot_engine.domain.spin_result import SpinResult

@dataclass(frozen=True, slots=True)
class PlayResult:
    """Result of one full play through a game engine

    Combines what happened (the spin) with what it paid (the evaluation)
    Engines return this from their `play()` method.
    """

    spin: SpinResult
    evaluation: Evaluation