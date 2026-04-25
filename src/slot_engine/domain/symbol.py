"""SYMBOL - symbol that appears on slot reels"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    """Represents a symbol on a slot

    A symbol has a unic name that identifies it. It can
    be a wild (replaces other symbols) or a scatter
    (pays witout being in a concrete line). Can't be both
    """

    name: str
    is_wild: bool = False
    is_scatter: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Symbol name cannot be empty")
        if self.is_wild and self.is_scatter:
            raise ValueError(f"Symbol '{self.name}' cannot be a scatter")
