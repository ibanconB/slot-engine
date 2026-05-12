"""Data models for wallet and ledger"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID


class TransactionType(StrEnum):
    """Kind of a ledger entry. Determines amount adds or substracts from"""

    DEPOSIT = "deposit"
    BET = "bet"
    WIN ="win"

@dataclass(frozen=True, slots=True)
class Wallet:
    """A player's balance

    Immutable: every change produces a new Wallet via the operations module
    """

    player_id: str
    balance: Decimal

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("Wallet requires a non-empty player_id")
        if self.balance < 0:
            raise ValueError(f"Wallet balance cannot be negative, got {self.balance}")

@dataclass(frozen=True, slots=True)
class Transaction:
    """An immutable ledger entry recording one balance change.

    Convention: `amount` is always non-negative. The `type` determines
    wheter it added to (DEPOSIT, WIN) or substracted from (BET) the balance.
    `balance_after` is recorded for audit: scanning the ledger for a player
    you can verify the running balance without recomputing from scratch
    """

    id: UUID
    player_id: str
    type: TransactionType
    amount: Decimal
    balance_after: Decimal
    timestamp: datetime
    metadata: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("Transaction requires a non-empty player_id")
        if self.amount < 0:
            raise ValueError(f"Transaction amount cannot be negative, got {self.amount}")
        if self.balance_after < 0:
            raise ValueError(f"Transaction balance cannot be negative, got {self.balance_after}")


