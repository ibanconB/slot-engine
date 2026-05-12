"""In-memory store for wallets and transactions

A singleton-ish container instantiated once per process. The HTTP server
will inject one instance into endpoint handlers via FastAPI dependency
injection. To be replaced with a database-backed store in Phase 21
"""
from __future__ import annotations

from decimal import Decimal

from slot_engine.wallet.models import Transaction, Wallet

class WalletStore:
    """Hold wallets per player and an append-only transaction ledger"""

    def __init__(self) -> None:
        self._wallets: dict[str, Wallet] = {}
        self._transactions: list[Transaction] = []

    def get_or_create_wallet(self, player_id: str) -> Wallet:
        """Return the wallet for `player_id`, creating one with balance 0 if needed."""
        if player_id not in self._wallets:
            self._wallets[player_id] = Wallet(player_id=player_id, balance=Decimal("0"))
        return self._wallets[player_id]

    def replace_wallet(self, wallet: Wallet) -> None:
        """Persist a new wallet state (overwrites the previous)"""
        self._wallets[wallet.player_id] = wallet

    def append_transaction(self, transaction: Transaction) -> None:
        """Append a transaction to the ledger"""
        self._transactions.append(transaction)

    def transactions_for(self, player_id: str) -> tuple[Transaction, ...]:
        """Return all transactions for the given player, in insertion order."""
        return tuple(t for t in self._transactions if t.player_id == player_id)

