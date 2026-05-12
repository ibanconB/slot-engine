"""Wallet operations: deposit, place_bet, credit_win
These are the public API of the wallet module. They encapsulate the
"read wallet → compute new balance → create transaction → persist both"
sequence in atomic-feeling functions.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from uuid import uuid4

from slot_engine.wallet.models import Transaction, TransactionType, Wallet
from slot_engine.wallet.store import WalletStore

class InsufficientFundsError(Exception):
    """Raised when a bet exceeds the available wallet balance"""

    def __init__(self, player_id: str, balance: Decimal, requested: Decimal) -> None:
        super().__init__(
            f"Player '{player_id}' has balance {balance}, "
            f"cannot place bet of {requested}"
        )
        self.player_id = player_id
        self.balance = balance
        self.requested = requested

def _now_utc() -> datetime:
     return datetime.now(timezone.utc)

def _frozen(metadata: Mapping[str, str] | None) -> Mapping[str, str]:
    return MappingProxyType(dict(metadata)) if metadata else MappingProxyType({})


def deposit(
    store: WalletStore,
    player_id: str,
    amount: Decimal,
    *,
    metadata: Mapping[str, str] | None = None,
) -> Transaction:
    """Add funds to a player's wallet."""
    if amount <= 0:
        raise ValueError(f"Deposit amount must be > 0, got {amount}")

    wallet = store.get_or_create_wallet(player_id)
    new_balance = wallet.balance + amount

    tx = Transaction(
        id=uuid4(),
        player_id=player_id,
        type=TransactionType.DEPOSIT,
        amount=amount,
        balance_after=new_balance,
        timestamp=_now_utc(),
        metadata=_frozen(metadata),
    )

    store.replace_wallet(Wallet(player_id=player_id, balance=new_balance))
    store.append_transaction(tx)
    return tx


def place_bet(
    store: WalletStore,
    player_id: str,
    amount: Decimal,
    *,
    metadata: Mapping[str, str] | None = None,
) -> Transaction:
    """Subtract a bet from the player's wallet.

    Raises InsufficientFundsError if the player's balance is below the bet.
    """
    if amount <= 0:
        raise ValueError(f"Bet amount must be > 0, got {amount}")

    wallet = store.get_or_create_wallet(player_id)
    if wallet.balance < amount:
        raise InsufficientFundsError(player_id, wallet.balance, amount)

    new_balance = wallet.balance - amount

    tx = Transaction(
        id=uuid4(),
        player_id=player_id,
        type=TransactionType.BET,
        amount=amount,
        balance_after=new_balance,
        timestamp=_now_utc(),
        metadata=_frozen(metadata),
    )

    store.replace_wallet(Wallet(player_id=player_id, balance=new_balance))
    store.append_transaction(tx)
    return tx


def credit_win(
    store: WalletStore,
    player_id: str,
    amount: Decimal,
    *,
    metadata: Mapping[str, str] | None = None,
) -> Transaction:
    """Credit winnings to the player's wallet.

    A no-op should NOT call this. If amount is 0 we'd create a meaningless
    transaction; if you have no win, just skip the call.
    """
    if amount <= 0:
        raise ValueError(f"Win credit amount must be > 0, got {amount}")

    wallet = store.get_or_create_wallet(player_id)
    new_balance = wallet.balance + amount

    tx = Transaction(
        id=uuid4(),
        player_id=player_id,
        type=TransactionType.WIN,
        amount=amount,
        balance_after=new_balance,
        timestamp=_now_utc(),
        metadata=_frozen(metadata),
    )

    store.replace_wallet(Wallet(player_id=player_id, balance=new_balance))
    store.append_transaction(tx)
    return tx