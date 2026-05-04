"""Smoke test: end-to-end regression for the load-and-play pipeline.

If this test breaks, something fundamental in the chain
TOML -> Pydantic -> Game -> create_engine -> PlayResult is broken.
"""
from pathlib import Path

from slot_engine.config import load_game_config
from slot_engine.game import Game
from slot_engine.rng import SeededRng

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


def test_lucky_sevens_seeded_play_is_deterministic() -> None:
    """Two engines with the same seed must produce identical play results."""
    config = load_game_config(GAMES_DIR / "lucky_sevens.toml")
    game = Game.from_config(config)

    engine_a = game.create_engine(rng=SeededRng(seed=42))
    engine_b = game.create_engine(rng=SeededRng(seed=42))

    assert engine_a.play() == engine_b.play(), "Same seed must produce same play"