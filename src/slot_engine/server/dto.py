"""Response DTOs for the HTTP API.

Translates domain objects (frozen dataclasses with tuples of Symbol etc.)
into JSON-friendly Pydantic models.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Game / spin response DTOs ----------------------------------------------

class SpinDTO(StrictDTO):
    """The visible window after a spin, expressed as rows of symbol names."""
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


# --- Wallet DTOs ------------------------------------------------------------

class DepositRequestDTO(StrictDTO):
    """Body for POST /players/{id}/wallet/deposit."""
    amount: Decimal


class TransactionDTO(StrictDTO):
    id: str           # UUID as string for JSON safety
    type: str         # TransactionType value
    amount: Decimal
    balance_after: Decimal
    timestamp: str    # ISO 8601 UTC
    metadata: Mapping[str, str]


class WalletDTO(StrictDTO):
    player_id: str
    balance: Decimal
    transactions: tuple[TransactionDTO, ...]


# --- Free spins DTOs --------------------------------------------------------

class PlayerFreeSpinsDTO(StrictDTO):
    """Response for GET /players/{id}/free-spins."""
    player_id: str
    free_spins: dict[str, int]   # game_name -> count


class GrantFreeSpinsRequestDTO(StrictDTO):
    """Body for POST /players/{id}/free-spins/grant."""
    game: str
    amount: int


# --- Spin request/response DTOs (with wallet + FS) --------------------------

class SpinRequestDTO(StrictDTO):
    """Body for POST /games/{name}/spin.

    bet_per_line is optional. If the player has free spins for the game,
    they're auto-played (no bet). Otherwise bet_per_line must be > 0.
    """
    player_id: str
    bet_per_line: Decimal | None = None


class RoundDTO(StrictDTO):
    """One play within a spin round.

    kind: "paid" if the player paid for this play, "free" if it was a free spin.
    steps: one or many (cascade games can have multiple steps per play).
    free_spins_triggered: how many FS this specific play awarded (re-trigger info).
    """
    kind: str
    steps: tuple[StepDTO, ...]
    total_payout: Decimal
    is_winning: bool
    free_spins_triggered: int

class SpinResponseDTO(StrictDTO):
    """Response for POST /games/{name}/spin: full round (initial + all FS)."""
    game: str
    engine: str
    rounds: tuple[RoundDTO, ...]
    bet: Decimal                  # what the player paid (0 if started in FS mode)
    total_payout: Decimal         # sum across all rounds
    balance_after: Decimal
    free_spins_remaining: int     # always 0 after auto-drain (kept for clarity)