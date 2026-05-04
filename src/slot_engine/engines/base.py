"""Base Protocol that every game engine must implement"""
from __future__ import annotations

from typing import Protocol

from slot_engine.domain.play_result import PlayResult


class GameEngine(Protocol):
    """Contract that every game engine implements

    A game engine knows how to play one round of its specific game.
    What "playing" means depends on the engine:
      - A classic line slot: spin reels and evaluate paylines.
      - A cluster-pays game: spin reels and find clusters.
      - A cascade game: spin, evaluate, tumble, repeat until no wins.

    Engines are stateless across plays. Inter-spin state (free spins,
    bonus mode) will be introduced when the first stateful game arrives,
    not before (see ROADMAP AD-4).
    """

    def play(self) -> PlayResult:
        """Execute one play and return the unified result."""
        ...