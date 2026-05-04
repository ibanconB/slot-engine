"""Tests for the Simulator."""
from decimal import Decimal
from pathlib import Path

import pytest

from slot_engine.config import load_game_config
from slot_engine.game import Game
from slot_engine.rng import SeededRng
from slot_engine.simulation import Simulator

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


def _load_lucky_sevens() -> Game:
    config = load_game_config(GAMES_DIR / "lucky_sevens.toml")
    return Game.from_config(config)


def test_simulator_is_deterministic_with_same_seed() -> None:
    """Same seed must produce identical SimulationResult across runs."""
    game = _load_lucky_sevens()
    sim_a = Simulator(game=game, rng=SeededRng(seed=42))
    sim_b = Simulator(game=game, rng=SeededRng(seed=42))

    assert sim_a.run(num_spins=100) == sim_b.run(num_spins=100)


def test_simulator_raises_on_zero_or_negative_spins() -> None:
    game = _load_lucky_sevens()
    sim = Simulator(game=game, rng=SeededRng(seed=1))

    with pytest.raises(ValueError, match="must be > 0"):
        sim.run(num_spins=0)

    with pytest.raises(ValueError, match="must be > 0"):
        sim.run(num_spins=-5)


def test_simulator_total_bet_equals_spins_times_paylines() -> None:
    """Bet convention: 1 unit per payline per spin."""
    game = _load_lucky_sevens()
    sim = Simulator(game=game, rng=SeededRng(seed=1))

    result = sim.run(num_spins=100)

    # Lucky Sevens has 3 paylines. 100 * 3 * 1 = 300 units.
    assert result.num_paylines == 3
    assert result.total_bet == Decimal("300")


def test_simulator_winning_spins_within_total_spins() -> None:
    """Sanity: number of wins cannot exceed number of spins."""
    game = _load_lucky_sevens()
    sim = Simulator(game=game, rng=SeededRng(seed=1))

    result = sim.run(num_spins=1000)

    assert 0 <= result.num_winning_spins <= result.num_spins