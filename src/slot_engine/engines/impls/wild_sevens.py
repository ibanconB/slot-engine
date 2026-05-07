"""Wild Sevens engine: line slot with joker wild substitution"""
from __future__ import annotations

from dataclasses import dataclass

from slot_engine.domain.play_result import PlayResult
from slot_engine.domain.symbol import Symbol
from slot_engine.engine import SpinEngine
from slot_engine.engines.registry import register_engine
from slot_engine.evaluator import Evaluator
from slot_engine.game import Game
from slot_engine.rng import RandomNumberGenerator


def _wild_match(candidate: Symbol, reference: Symbol) -> bool:
    """Match function for Wild Sevens: jokers substitute for any reference

        Match rules:
            - Strict equality (candidate == reference) -> match
            - Candidate is wild (substitutes for the reference) -> match

        Limitation: when reference itself is wild (R0 = joker), only other
        jokers will match. The line is "anchored" by the wild, with no substitution
        effect. To enable wilds at R0, line-level resolution
        would be needed (deferred until measured impact justifies it)
    """
    if candidate == reference:
        return True
    return candidate.is_wild


@register_engine("wild_sevens")
@dataclass(frozen=True, slots=True)
class WildSevensEngine:
    """Engine for Wild Sevens game"""

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
            match=_wild_match,
        )
        spin = spin_engine.spin()
        evaluation = evaluator.evaluate(spin)
        return PlayResult(spin=spin, evaluation=evaluation)
