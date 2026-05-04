"""Tests for ClassicLinesEngine."""
from pathlib import Path

from slot_engine.config import load_game_config
from slot_engine.domain.play_result import PlayResult
from slot_engine.engines.impls.classic_lines import ClassicLinesEngine
from slot_engine.engines.registry import get_engine_class
from slot_engine.game import Game
from slot_engine.rng import SeededRng

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


def _load_lucky_sevens() -> Game:
    config = load_game_config(GAMES_DIR / "lucky_sevens.toml")
    return Game.from_config(config)


def test_engine_is_registered_under_classic_lines_name() -> None:
    assert get_engine_class("classic_lines") is ClassicLinesEngine


def test_play_returns_a_play_result() -> None:
    game = _load_lucky_sevens()
    engine = ClassicLinesEngine(game=game, rng=SeededRng(seed=1))

    result = engine.play()

    assert isinstance(result, PlayResult)


def test_play_is_deterministic_with_same_seed() -> None:
    game = _load_lucky_sevens()
    engine_a = ClassicLinesEngine(game=game, rng=SeededRng(seed=42))
    engine_b = ClassicLinesEngine(game=game, rng=SeededRng(seed=42))

    assert engine_a.play() == engine_b.play()


def test_play_produces_different_results_with_different_seeds() -> None:
    game = _load_lucky_sevens()
    engine_a = ClassicLinesEngine(game=game, rng=SeededRng(seed=1))
    engine_b = ClassicLinesEngine(game=game, rng=SeededRng(seed=999))

    assert engine_a.play() != engine_b.play()