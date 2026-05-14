"""Simulator: run N plays of a Game and aggregate the results"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from slot_engine.game import Game
from slot_engine.rng import RandomNumberGenerator
from slot_engine.simulation import result
from slot_engine.simulation.result import SimulationResult

@dataclass(frozen=True, slots=True)
class Simulator:
    """Run N plays of a game and aggregate the metrics

     Bet convention: 1 unit per payline per spin. Total bet for a run
    of N spins on a game with P paylines = N * P units
    """

    game: Game
    rng: RandomNumberGenerator

    def run(self, num_spins: int) -> SimulationResult:
        """Execute `num_spins` paid plays and return aggregated metrics.

        Each "spin" here is one PAID round. Free spins triggered during
        a round are played automatically (no extra bet) and their payouts
        contribute to total_payout. Re-triggers chain naturally.
        Total bet only counts paid spins.
        """
        if num_spins <= 0:
            raise ValueError(f"num_spins must be > 0, got {num_spins}")

        engine = self.game.create_engine(self.rng)
        num_paylines = len(self.game.paylines)

        total_payout = Decimal("0")
        num_winning_spins = 0
        max_win = Decimal("0")

        for _ in range(num_spins):
            round_payout = Decimal("0")
            fs_remaining = 0

            # Initial paid spin
            result = engine.play()
            round_payout += result.total_payout
            fs_remaining += result.free_spins_triggered

            # Play any triggered free spins (no bet); allow re-triggers
            while fs_remaining > 0:
                fs_remaining -= 1
                fs_result = engine.play()
                round_payout += fs_result.total_payout
                fs_remaining += fs_result.free_spins_triggered

            total_payout += round_payout
            if round_payout > 0:
                num_winning_spins += 1
                if round_payout > max_win:
                    max_win = round_payout

        total_bet = Decimal(num_spins) * Decimal(num_paylines)

        return SimulationResult(
            num_spins=num_spins,
            num_paylines=num_paylines,
            total_bet=total_bet,
            total_payout=total_payout,
            num_winning_spins=num_winning_spins,
            max_win=max_win,
        )