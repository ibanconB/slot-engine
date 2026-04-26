"""Paytable - slot prize table"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from slot_engine.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class Paytable:
    """Slot prize table
    for each combination defines the multiplier of the bet
    that pays. Multiplier can't be neagative. Paytable can't
    be negative
    """

    payouts: Mapping[tuple[Symbol, int], Decimal]

    def __post_init__(self) -> None:
        if not self.payouts:
            raise ValueError("Paytable is empty")
        for (symbol, count), multiplier in self.payouts.items():
            if count < 1:
                raise ValueError(f"Count must be greater than zero, got {count}")
            if multiplier < 0:
                raise ValueError(
                    f"Multiplier cannot be negative, got {multiplier}for ({symbol}, {count})"
                )

        object.__setattr__(self, "payouts", MappingProxyType(dict(self.payouts)))

    def payout_for(self, symbol: Symbol, count: int) -> Decimal:
        """Returns multiplier for `count` symbol coincidences
        If there is no prize defined for that combination, returns Decimal(0)
        """
        return self.payouts.get((symbol, count), Decimal(0))

    def has_payout(self, symbol: Symbol, count: int) -> bool:
        """If there is a prize defined for `count` symbol, returns True"""
        return (symbol, count) in self.payouts
