"""Tests for the wallet domain (models, store, operations)."""
from decimal import Decimal

import pytest

from slot_engine.wallet import (
    InsufficientFundsError,
    TransactionType,
    Wallet,
    WalletStore,
    credit_win,
    deposit,
    place_bet,
)


# --- Wallet model -----------------------------------------------------------

def test_wallet_requires_non_empty_player_id() -> None:
    with pytest.raises(ValueError, match="player_id"):
        Wallet(player_id="", balance=Decimal("0"))


def test_wallet_rejects_negative_balance() -> None:
    with pytest.raises(ValueError, match="negative"):
        Wallet(player_id="alice", balance=Decimal("-1"))


# --- Store ------------------------------------------------------------------

def test_get_or_create_returns_zero_balance_for_new_player() -> None:
    store = WalletStore()
    wallet = store.get_or_create_wallet("alice")
    assert wallet.player_id == "alice"
    assert wallet.balance == Decimal("0")


def test_get_or_create_returns_existing_state_for_known_player() -> None:
    store = WalletStore()
    deposit(store, "alice", Decimal("50"))
    wallet = store.get_or_create_wallet("alice")
    assert wallet.balance == Decimal("50")


# --- deposit ----------------------------------------------------------------

def test_deposit_increases_balance_and_records_transaction() -> None:
    store = WalletStore()
    tx = deposit(store, "alice", Decimal("100"))

    assert store.get_or_create_wallet("alice").balance == Decimal("100")
    assert tx.type == TransactionType.DEPOSIT
    assert tx.amount == Decimal("100")
    assert tx.balance_after == Decimal("100")


def test_deposit_rejects_zero_or_negative() -> None:
    store = WalletStore()
    with pytest.raises(ValueError, match="must be > 0"):
        deposit(store, "alice", Decimal("0"))
    with pytest.raises(ValueError, match="must be > 0"):
        deposit(store, "alice", Decimal("-10"))


# --- place_bet --------------------------------------------------------------

def test_place_bet_decreases_balance_and_records_bet_transaction() -> None:
    store = WalletStore()
    deposit(store, "alice", Decimal("100"))
    tx = place_bet(store, "alice", Decimal("30"))

    assert store.get_or_create_wallet("alice").balance == Decimal("70")
    assert tx.type == TransactionType.BET
    assert tx.amount == Decimal("30")  # always positive
    assert tx.balance_after == Decimal("70")


def test_place_bet_raises_with_helpful_error_when_insufficient() -> None:
    store = WalletStore()
    deposit(store, "alice", Decimal("10"))

    with pytest.raises(InsufficientFundsError) as exc_info:
        place_bet(store, "alice", Decimal("100"))

    assert exc_info.value.player_id == "alice"
    assert exc_info.value.balance == Decimal("10")
    assert exc_info.value.requested == Decimal("100")


def test_failed_bet_does_not_modify_wallet_or_ledger() -> None:
    """Atomic guarantee: a failed bet leaves no trace."""
    store = WalletStore()
    deposit(store, "alice", Decimal("10"))

    with pytest.raises(InsufficientFundsError):
        place_bet(store, "alice", Decimal("100"))

    assert store.get_or_create_wallet("alice").balance == Decimal("10")
    assert len(store.transactions_for("alice")) == 1  # only the deposit


# --- credit_win -------------------------------------------------------------

def test_credit_win_increases_balance_and_records_win_transaction() -> None:
    store = WalletStore()
    deposit(store, "alice", Decimal("100"))
    place_bet(store, "alice", Decimal("30"))
    tx = credit_win(store, "alice", Decimal("50"))

    assert store.get_or_create_wallet("alice").balance == Decimal("120")  # 100 - 30 + 50
    assert tx.type == TransactionType.WIN


# --- Ledger -----------------------------------------------------------------

def test_transactions_accumulate_in_insertion_order() -> None:
    store = WalletStore()
    deposit(store, "alice", Decimal("100"))
    place_bet(store, "alice", Decimal("30"))
    credit_win(store, "alice", Decimal("50"))

    history = store.transactions_for("alice")
    assert len(history) == 3
    assert [t.type for t in history] == [
        TransactionType.DEPOSIT,
        TransactionType.BET,
        TransactionType.WIN,
    ]


def test_ledger_isolates_transactions_per_player() -> None:
    store = WalletStore()
    deposit(store, "alice", Decimal("100"))
    deposit(store, "bob", Decimal("50"))

    assert len(store.transactions_for("alice")) == 1
    assert len(store.transactions_for("bob")) == 1
    assert store.transactions_for("alice")[0].player_id == "alice"


def test_balance_after_chain_is_consistent() -> None:
    """Audit property: replaying balance_after across ledger matches actual balance."""
    store = WalletStore()
    deposit(store, "alice", Decimal("100"))
    place_bet(store, "alice", Decimal("30"))
    credit_win(store, "alice", Decimal("50"))

    history = store.transactions_for("alice")
    assert [t.balance_after for t in history] == [
        Decimal("100"),
        Decimal("70"),
        Decimal("120"),
    ]


# --- metadata ---------------------------------------------------------------

def test_metadata_is_attached_and_immutable() -> None:
    store = WalletStore()
    tx = deposit(store, "alice", Decimal("100"), metadata={"source": "test"})

    assert tx.metadata["source"] == "test"

    # Modifying the metadata is forbidden (MappingProxyType)
    with pytest.raises(TypeError):
        tx.metadata["new"] = "value"  # type: ignore[index]