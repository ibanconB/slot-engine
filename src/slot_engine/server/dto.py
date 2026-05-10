"""Response DTOs for the HTTP API

Translates domain objects (frozen dataclasses with tuples of Symbol)
into JSON-friendly Pydantic models
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SpinDTO(StrictDTO):
    """The visible window after a spin, expressed as rows of symbol names"""

    grid: tuple[tuple[str, ...], ...]

class LineWinDTO(StrictDTO):
    payline: str
    symbol: str
    count: int
    payout: Decimal


class EvaluationDTO(StrictDTO):
    wins: tuple[LineWinDTO, ...]
    total_payout: Decimal
    is_winning: bool


class StepDTO(StrictDTO):
    spin: SpinDTO
    evaluation: EvaluationDTO
    multiplier: int


class PlayResponseDTO(StrictDTO):
    game: str
    engine: str
    steps: tuple[StepDTO, ...]
    total_payout: Decimal
    is_winning: bool


