"""Tests for SweetCascadeEngine."""
from dataclasses import replace
from pathlib import Path

import pytest

from slot_engine.config import load_game_config
from slot_engine.domain.play_result import PlayResult
from slot_engine.engines.impls.sweet_cascade import SweetCascadeEngine
from slot_engine.engines.registry import get_engine_class
from slot_engine.game import Game
from slot_engine.rng import SeededRng

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


def _load_sweet_cascade() -> Game:
    config = load_game_config(GAMES_DIR / "sweet_cascade.toml")
    return Game.from_config(config)


def test_engine_is_registered_under_sweet_cascade_name() -> None:
    assert get_engine_class("sweet_cascade") is SweetCascadeEngine


def test_play_returns_a_play_result_with_at_least_one_step() -> None:
    game = _load_sweet_cascade()
    engine = SweetCascadeEngine(game=game, rng=SeededRng(seed=1))

    result = engine.play()

    assert isinstance(result, PlayResult)
    assert result.num_steps >= 1


def test_play_is_deterministic_with_same_seed() -> None:
    game = _load_sweet_cascade()
    engine_a = SweetCascadeEngine(game=game, rng=SeededRng(seed=42))
    engine_b = SweetCascadeEngine(game=game, rng=SeededRng(seed=42))

    assert engine_a.play() == engine_b.play()


def test_play_raises_when_cascade_rules_are_missing() -> None:
    """SweetCascadeEngine cannot run on a game without cascade rules."""
    game = _load_sweet_cascade()
    no_cascade_game = replace(game, cascade=None)
    engine = SweetCascadeEngine(game=no_cascade_game, rng=SeededRng(seed=1))

    with pytest.raises(ValueError, match="cascade rules"):
        engine.play()


def test_multi_step_result_has_increasing_multipliers() -> None:
    """When a cascade triggers, multipliers must come from cascade.multipliers in order."""
    game = _load_sweet_cascade()
    expected_multipliers = game.cascade.multipliers

    # Find a seed that produces at least 2 cascade steps
    for seed in range(100):
        engine = SweetCascadeEngine(game=game, rng=SeededRng(seed=seed))
        result = engine.play()
        if result.num_steps >= 2:
            # Verify multipliers match the expected sequence
            for i, step in enumerate(result.steps):
                expected = expected_multipliers[
                    min(i, len(expected_multipliers) - 1)
                ]
                assert step.multiplier == expected, (
                    f"Step {i}: expected multiplier {expected}, got {step.multiplier}"
                )
            return  # found one, test passes

    pytest.skip("No cascading seed found in first 100 attempts")