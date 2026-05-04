"""Objects bundle of the domain ready for use"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from slot_engine.config import GameConfig
from slot_engine.domain import Payline, Paytable, Reel, Symbol
from slot_engine.rng import RandomNumberGenerator

if TYPE_CHECKING:
    from slot_engine.engines import GameEngine


@dataclass(frozen=True, slots=True)
class Game:
    """Game ready to use.

    Groups all the domain objects that engines need plus metadata
    (name, engine identifier, visible window size).

    Built with `Game.from_config(config)` from a validated GameConfig.
    Use `game.create_engine(rng)` to obtain the engine that knows how
    to play this game.
    """

    name: str
    engine_name: str
    window_size: int
    reels: tuple[Reel, ...]
    paytable: Paytable
    paylines: tuple[Payline, ...]
    symbols: Mapping[str, Symbol]

    @classmethod
    def from_config(cls, config: GameConfig) -> Game:
        """Translate a validated GameConfig into a playable Game."""
        symbols: dict[str, Symbol] = {
            name: Symbol(
                name=name,
                is_wild=spec.is_wild,
                is_scatter=spec.is_scatter,
            )
            for name, spec in config.symbols.items()
        }

        reels = tuple(
            Reel.from_symbols(tuple(symbols[s] for s in reel.strip))
            for reel in config.reels
        )

        paytable = Paytable(
            payouts={
                (symbols[symbol_name], count): payout
                for symbol_name, payouts in config.paytable.items()
                for count, payout in payouts.items()
            }
        )

        paylines = tuple(
            Payline(name=p.name, rows=p.rows) for p in config.paylines
        )

        return cls(
            name=config.game.name,
            engine_name=config.game.engine,
            window_size=config.game.window_size,
            reels=reels,
            paytable=paytable,
            paylines=paylines,
            symbols=MappingProxyType(symbols),
        )

    def create_engine(self, rng: RandomNumberGenerator) -> GameEngine:
        """Build the engine configured for this game.

        Looks up the engine class in the registry by `engine_name` and
        instantiates it with this game and the provided RNG.

        Raises KeyError if no engine is registered under `engine_name`.
        """
        # Local import to break the import cycle:
        # engines.impls.classic_lines imports Game; Game uses the registry.
        from slot_engine.engines import get_engine_class

        engine_class = get_engine_class(self.engine_name)
        return engine_class(game=self, rng=rng)