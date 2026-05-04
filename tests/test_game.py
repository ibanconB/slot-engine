"""Tests for the Game aggregate, focusing on the engine binding."""
from dataclasses import replace
from pathlib import Path

import pytest

from slot_engine.config import load_game_config
from slot_engine.engines.impls.classic_lines import ClassicLinesEngine
from slot_engine.game import Game
from slot_engine.rng import SeededRng

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


def _load_lucky_sevens() -> Game:
    config = load_game_config(GAMES_DIR / "lucky_sevens.toml")
    return Game.from_config(config)


def test_create_engine_returns_the_engine_declared_in_the_toml() -> None:
    game = _load_lucky_sevens()

    engine = game.create_engine(rng=SeededRng(seed=1))

    assert isinstance(engine, ClassicLinesEngine)


def test_create_engine_raises_when_engine_name_is_not_registered() -> None:
    game = _load_lucky_sevens()
    bogus_game = replace(game, engine_name="nonexistent_engine")

    with pytest.raises(KeyError, match="nonexistent_engine"):
        bogus_game.create_engine(rng=SeededRng(seed=1))