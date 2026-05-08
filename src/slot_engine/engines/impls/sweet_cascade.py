"""Sweets Cascade: line slot with cascade mechanic and step multipliers

Mechanic:
  1. Initial spin.
  2. Evaluate all paylines.
  3. If any payline wins, drop & fill: remove participating positions,
     remaining symbols fall down, empty positions from the top filled
     with new random symbols drawn from each reel's strip.
  4. Re-evaluate. Multiplier increments per game.cascade.multipliers.
  5. Repeat until no win on a step.

"""
from __future__ import annotations

from dataclasses import dataclass

from slot_engine.domain.evaluation import Evaluation
from slot_engine.domain.play_result import PlayResult, PlayStep
from slot_engine.domain.reel import Reel
from slot_engine.domain.spin_result import SpinResult
from slot_engine.domain.symbol import Symbol
from slot_engine.engine import SpinEngine
from slot_engine.engines.registry import register_engine
from slot_engine.evaluator import Evaluator
from slot_engine.game import Game
from slot_engine.rng import RandomNumberGenerator

def _winning_positions(evaluation: Evaluation) -> set[tuple[int, int]]:
    """Return de (column, row) positions in any winning payline"""
    positions:set[tuple[int, int]] = set()
    for win in evaluation.wins:
        for col_idx in range(win.count):
            row_idx = win.payline.rows[col_idx]
            positions.add((col_idx, row_idx))
    return positions

def _drop_and_fill_column(
    column: tuple[Symbol, ...],
    removed_rows: set[int],
    rng: RandomNumberGenerator,
    reel: Reel,
) -> tuple[Symbol, ...]:
    """Remove symbols at the given rows, shift remaining down, fill top with new."""
    if not removed_rows:
        return column

    survivors = tuple(s for i, s in enumerate(column) if i not in removed_rows)

    num_new = len(removed_rows)
    new_symbols = tuple(
        reel.window_at(rng.randrange(reel.length), 1)[0]
        for _ in range(num_new)
    )

    return new_symbols + survivors

@register_engine("sweet_cascade")
@dataclass(frozen=True, slots=True)
class SweetCascadeEngine:
    """Cascade engine for Sweet Cascade.

       Multiplier values per step come from game.cascade.multipliers (TOML).
       Linear or any other shape is just data: this engine reads the list
       and clamps to the last value if the cascade exceeds the list length.
       """

    game: Game
    rng: RandomNumberGenerator

    def play(self) -> PlayResult:
        if self.game.cascade is None:
            raise ValueError(
                f"SweetCascadeEngine requires cascade rules in TOML"
                f"(game '{self.game.name}' has none)"
            )

        multipliers = self.game.cascade.multipliers
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
        steps: list[PlayStep] = []
        step_idx = 0

        while True:
            evaluation = evaluator.evaluate(spin)
            multiplier = multipliers[min(step_idx, len(multipliers) - 1)]
            steps.append(
                PlayStep(spin=spin, evaluation=evaluation, multiplier=multiplier)
            )

            if not evaluation.is_winning:
                break

            removed = _winning_positions(evaluation)
            new_columns = tuple(
                _drop_and_fill_column(
                    column=spin.columns[col_idx],
                    removed_rows = {r for c, r in removed if c == col_idx},
                    rng = self.rng,
                    reel = self.game.reels[col_idx],
                )
                for col_idx in range(len(spin.columns))
            )
            spin = SpinResult(
                columns=new_columns,
                stop_positions=spin.stop_positions,
            )
            step_idx += 1

        return PlayResult(steps=tuple(steps))
