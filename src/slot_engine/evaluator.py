"""Prize evaluator of a spin"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from slot_engine.domain import (
    Evaluation,
    LineWin,
    Payline,
    Paytable,
    SpinResult,
    Symbol,
)

MatchFm = Callable[[Symbol, Symbol], bool]


def strict_match(candidate: Symbol, reference: Symbol) -> bool:
    """Strictly coincidence: only same symbols count"""
    return candidate == reference


@dataclass(frozen=True, slots=True)
class Evaluator:
    """Evaluator of prizes for a fixed amount of paylines and paytable

    Goes through each payline from left to right counting coincidences
    with the symbol of column 0. The rule of "counts as a coincidence"
    gets ineyected as a function (`match`),  by default strict match.
    This leaves the door open for wilds or others rules
    """

    paylines: tuple[Payline, ...]
    paytable: Paytable
    match: MatchFm = field(default=strict_match)

    @classmethod
    def create(
        cls,
        paylines: Iterable[Payline],
        paytable: Paytable,
        match: MatchFm = strict_match,
    ) -> Evaluator:
        """Builds an evluator from whatever iterable of paylines"""
        return cls(paylines=tuple(paylines), paytable=paytable, match=match)

    def evaluate(self, spin: SpinResult) -> Evaluation:
        """Evaluate the spin against all paylines and returns the result"""
        wins: list[LineWin] = []
        for payline in self.paylines:
            win = self._evaluate_payline(spin, payline)
            if win is not None:
                wins.append(win)
        return Evaluation(wins=tuple(wins))

    def _evaluate_payline(self, spin: SpinResult, payline: Payline) -> LineWin | None:
        self._validate_payline_fits_spin(spin, payline)

        symbols_on_line = self._read_symbols_along_payline(spin, payline)

        reference = symbols_on_line[0]
        count = 1
        for nex_symbol in symbols_on_line[1:]:
            if not self.match(nex_symbol, reference):
                break
            count += 1

        payout = self.paytable.payout_for(reference, count)
        if payout <= Decimal("0"):
            return None

        return LineWin(
            payline=payline,
            symbol=reference,
            count=count,
            payout=payout,
        )

    @staticmethod
    def _validate_payline_fits_spin(spin: SpinResult, payline: Payline) -> None:
        if payline.length != spin.num_columns:
            raise ValueError(
                f"Payline '{payline.name}' has length {payline.length}, "
                f"but spin has {spin.num_columns} columns"
            )
        for col, row in enumerate(payline.rows):
            if not 0 <= row < spin.num_rows:
                raise ValueError(
                    f"Payline '{payline.name}' references row {row} at "
                    f"column {col}, but spin has only {spin.num_rows} rows"
                )

    @staticmethod
    def _read_symbols_along_payline(spin: SpinResult, payline: Payline) -> tuple[Symbol, ...]:
        return tuple(spin.columns[col][payline.rows[col]] for col in range(payline.length))
