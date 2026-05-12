"""Lucky Bonus engine: classic lines with BONUS scatter trigger

Mechanic:
    1. Spin the reels
    2. Evaluate paylines normally. Bonus doesn't pay on lines
    3. Count BONUS visible anywhere on the grid
    4. If 3+ BONUS visible, trigger 8 free spins

The engine is stateless w.r.t. FS mode: it always counts BONUS and reports
the trigger. The server decides whether the player consumes a free spin or
a paid bet — that's HTTP-layer concern, not engine concern.
"""

from __future__ import annotations

from dataclasses import dataclass

from slot_engine.domain.play_result import PlayResult, PlayStep
from slot_engine.domain.spin_result import SpinResult
from slot_engine.domain.symbol import Symbol
from slot_engine.engine import SpinEngine
from slot_engine.engines.registry import register_engine
from slot_engine.evaluator import Evaluator
from slot_engine.game import Game
from slot_engine.rng import RandomNumberGenerator

_SCATTERS_TO_TRIGGER = 3
_FREE_SPINS_AWARDED = 8

def _find_scatter_symbol(game: Game) -> Symbol:
    """Return the single scatter symbol of the game.
    Lucky Bonus expects exactly one scatter. Raises if zero or multiple.
    """
    scatters = [sym for sym in game.symbols.values() if sym.is_scatter]
    if len(scatters) == 0:
        raise ValueError(
            f"Lucky Bonus engine requires a scatter symbol "
            f"(none found in game '{game.name}')"
        )
    if len(scatters) > 1:
        raise ValueError(
            f"Lucky Bonus engine expects exactly one scatter symbol, "
            f"found {len(scatters)}"
        )
    return scatters[0]

def _count_scatters(spin: SpinResult, scatter: Symbol) -> int:
    """Count occurerences of the scatter symbol in the visible window"""
    return sum(
        1
        for column in spin.columns
        for symbol in column
        if symbol == scatter
    )

@register_engine("lucky_bonus")
@dataclass(frozen=True, slots=True)
class LuckyBonusEngine:
    """Line slot with a single scatter symbol that triggers free spins"""

    game: Game
    rng: RandomNumberGenerator

    def play(self) -> PlayResult:
        scatter = _find_scatter_symbol(self.game)

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
        step = PlayStep(spin=spin, evaluation=evaluation, multiplier=1)

        scatter_count = _count_scatters(spin, scatter)
        free_spins_triggered = (
            _FREE_SPINS_AWARDED if scatter_count >= _SCATTERS_TO_TRIGGER else 0
        )

        return PlayResult(
            steps=(step,),
            free_spins_triggered=free_spins_triggered,
        )


