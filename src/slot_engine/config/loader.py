"""Loads and validates the game config"""

import tomllib
from pathlib import Path

from slot_engine.config.models import GameConfig


def load_game_config(path: str | Path) -> GameConfig:
    """Loads and validates a TOML game config file

    Args:
        path: Path to TOML game config file

    Returns:
        Validated GameConfig

    Raises:
        FileNotFoundError: If file does not exist
        ValidationError: If the TOML game config is invalid.
    """

    path = Path(path)
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return GameConfig.model_validate(raw)
