"""SimulationResult: aggregated metrics from a mass-spin run"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Aggregated metrics from a simulation of N spins

    Convetion: bet is `1 unit per payline per spin`. So a game
    with P paylines run for N spins has total_bet = N * P units.

    RTP is total_payout / total_bet, a ratio (0.94 means 94%)
    Hit rate is num_winning_spins / num_spins, a ratio
    """

    num_spins: int
    num_paylines: int
    total_bet: Decimal
    total_payout: Decimal
    num_winning_spins: int
    max_win: Decimal

    @property
    def rtp(self) -> Decimal:
        """Return-to-player ratio, 0.96 means 96%"""
        if self.total_bet == 0:
            return Decimal("0")
        return self.total_payout / self.total_bet

    @property
    def hit_rate(self) -> Decimal:
        """Fraction of spins that won something. 0.30 means 30%"""
        if self.num_spins == 0:
            return Decimal("0")
        return Decimal(self.num_winning_spins) / Decimal(self.num_spins)
