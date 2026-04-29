"""Definition of a line of payment"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Payline:
    """A payment line above the layout

    A payline associates, for every column of the game, what row is being read
    Example:
        - Horizontal middle line: rows = (1, 1, 1, 1, 1)
        - Vertical middle line: rows = (0, 1, 2, 1, 0)
        -ZigZag:                rows = (0, 1, 0, 1, 0)
    """

    name: str
    rows: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Payline name cannot be empty")
        if not self.rows:
            raise ValueError("Payline must define at least one row index")
        if any(row < 0 for row in self.rows):
            raise ValueError("Row indices must be non-negative")

    @classmethod
    def from_rows(cls, name: str, rows: Sequence[int]) -> Payline:
        """Builds a payline from whatever sequence of lines"""
        return cls(name=name, rows=tuple(rows))

    @property
    def length(self) -> int:
        """Number of columns that covers this payline"""
        return len(self.rows)
