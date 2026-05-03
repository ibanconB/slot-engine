"""Smoke test: end-to-end regression for the loading and spinning pipeline.

If this test breaks, something fundamental in the chain
TOML -> Pydantic -> Game -> SpinEngine -> SpinResult is broken.
"""
from pathlib import Path

from slot_engine.config import load_game_config
from slot_engine.engine import SpinEngine
from slot_engine.evaluator import Evaluator
from slot_engine.game import Game
from slot_engine.rng import SeededRng

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


def test_lucky_sevens_seeded_spin_is_deterministic() -> None:
    """Two engines with the same seed must produce identical results."""
    config = load_game_config(GAMES_DIR / "lucky_sevens.toml")
    game = Game.from_config(config)
    evaluator = Evaluator(paylines=game.paylines, paytable=game.paytable)

    engine_a = SpinEngine(
        reels=game.reels,
        window_size=game.window_size,
        rng=SeededRng(seed=42),
    )
    engine_b = SpinEngine(
        reels=game.reels,
        window_size=game.window_size,
        rng=SeededRng(seed=42),
    )

    result_a = engine_a.spin()
    result_b = engine_b.spin()

    assert result_a == result_b, "Same seed must produce same spin"

    eval_a = evaluator.evaluate(result_a)
    eval_b = evaluator.evaluate(result_b)
    assert eval_a == eval_b, "Same spin must produce same evaluation"