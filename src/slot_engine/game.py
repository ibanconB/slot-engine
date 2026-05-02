"""Objects bundle of the domain ready for use"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from slot_engine.config import GameConfig
from slot_engine.domain import Payline, Paytable, Reel, Symbol


@dataclass(frozen=True, slots=True)
class Game:
    """Game ready to use

    Groups all the domain objets that SpinEngine and Evaluator need
    plus metadata like name and visible window size

    It is build with `Game.from_config(config)` from a validated GameConfig
    """

    name: str
    window_size: int
    reels: tuple[Reel, ...]
    paytable: Paytable
    paylines: tuple[Payline, ...]
    symbols: Mapping[str, Symbol]

    @classmethod
    def from_config(cls, config: GameConfig):
        """Translates validated GameConfig into a playable Game"""
        symbols: dict[str, Symbol] = {
            name: Symbol(
                name=name,
                is_wild=spec.is_wild,
                is_scatter=spec.is_scatter,
            )
            for name, spec in config.symbols.items()
        }

        reels = tuple(
            Reel.from_symbols(tuple(symbols[s] for s in reel.strip)) for reel in config.reels
        )

        paytable = Paytable(
            payouts={
                (symbols[symbol_name], count): payout
                for symbol_name, payouts in config.paytable.items()
                for count, payout in payouts.items()
            }
        )

        paylines = tuple(Payline(name=p.name, rows=p.rows) for p in config.paylines)

        return cls(
            name=config.game.name,
            window_size=config.game.window_size,
            reels=reels,
            paytable=paytable,
            paylines=paylines,
            symbols=MappingProxyType(symbols),
        )
