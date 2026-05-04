"""Classic line slot engine: spin reels, evaluate paylines left-to-right"""
from __future__ import annotations

from dataclasses import dataclass

from slot_engine.domain.play_result import PlayResult
from slot_engine.engine import SpinEngine
from slot_engine.engines.registry import register_engine
from slot_engine.evaluator import Evaluator
from slot_engine.game import Game
from slot_engine.rng import RandomNumberGenerator


@register_engine("classic_lines")
@dataclass(frozen=True, slots=True)
class ClassicLinesEngine:
    """Engine for traditional line-pay slot games

    Spins the reels, then evaluate each payline left-to-right counting
    consecutive matching symbols against the paytable. This is the
    foundational mechanic of most classic slots: Lucky Sevens, Hot 7s,
    Diamond Bars, etc
    """

    game: Game
    rng: RandomNumberGenerator

    def play(self) -> PlayResult:
        spin_engine = SpinEngine(
            reels=self.game.reels,
            window_size=self.game.window_size,
            rng=self.rng,
        )
        evaluator = Evaluator(
            paylines=self.game.paylines,
            paytable=self.game.paytable,
        )
        spin = spin_engine.spin()
        evaluation = evaluator.evaluate(spin)
        return PlayResult(spin=spin, evaluation=evaluation)