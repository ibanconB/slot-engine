"""Outcome of evaluating a spin against all the paylines"""

from dataclasses import dataclass
from decimal import Decimal

from slot_engine.domain.line_win import LineWin


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Total result of the evaluation of a SpinResult

    Groups all `LineWin` that a spin triggered. The list can
    be empty (no winning spin). Total calculates from wins.

    Attributes:
        wins: Unmutable tuple of individual prizes; stable order
        by the order of evaluated paylines
    """

    wins: tuple[LineWin, ...]

    @property
    def total_payout(self) -> Decimal:
        """Adds all the individual prizes to the total payout"""
        return sum((win.payout for win in self.wins), start=Decimal("0"))

    @property
    def is_winning(self) -> bool:
        """True if the spin generated at least a prize with positive payout"""
        return self.total_payout > Decimal("0")

    def describe(self) -> str:
        """Describe the spin result"""
        if not self.wins:
            return "No wins"
        lines = [win.describe() for win in self.wins]
        lines.append(f"TOTAL: {self.total_payout}")
        return "\n".join(lines)
