"""Tests for the free spins domain (store + operations)."""
import pytest

from slot_engine.free_spins import (
    FreeSpinsStore,
    NoFreeSpinsAvailableError,
    grant,
    peek,
    use_one,
)


# --- Store ------------------------------------------------------------------

def test_store_returns_zero_for_unknown_player_and_game() -> None:
    store = FreeSpinsStore()
    assert store.get("alice", "lucky_bonus") == 0


def test_store_rejects_negative_counts() -> None:
    store = FreeSpinsStore()
    with pytest.raises(ValueError, match="cannot be negative"):
        store.set("alice", "lucky_bonus", -1)


def test_store_setting_to_zero_removes_entry() -> None:
    store = FreeSpinsStore()
    store.set("alice", "lucky_bonus", 5)
    store.set("alice", "lucky_bonus", 0)
    assert store.get("alice", "lucky_bonus") == 0
    assert ("alice", "lucky_bonus") not in store._counters  # internal check


# --- grant ------------------------------------------------------------------

def test_grant_adds_free_spins() -> None:
    store = FreeSpinsStore()
    new_total = grant(store, "alice", "lucky_bonus", 8)
    assert new_total == 8
    assert peek(store, "alice", "lucky_bonus") == 8


def test_grant_multiple_times_accumulates() -> None:
    store = FreeSpinsStore()
    grant(store, "alice", "lucky_bonus", 8)
    grant(store, "alice", "lucky_bonus", 5)
    assert peek(store, "alice", "lucky_bonus") == 13


def test_grant_rejects_zero_or_negative() -> None:
    store = FreeSpinsStore()
    with pytest.raises(ValueError, match="must be > 0"):
        grant(store, "alice", "lucky_bonus", 0)
    with pytest.raises(ValueError, match="must be > 0"):
        grant(store, "alice", "lucky_bonus", -3)


# --- use_one ----------------------------------------------------------------

def test_use_one_decrements_counter_and_returns_remaining() -> None:
    store = FreeSpinsStore()
    grant(store, "alice", "lucky_bonus", 3)
    remaining = use_one(store, "alice", "lucky_bonus")
    assert remaining == 2
    assert peek(store, "alice", "lucky_bonus") == 2


def test_use_one_raises_when_no_spins_available() -> None:
    store = FreeSpinsStore()
    with pytest.raises(NoFreeSpinsAvailableError) as exc_info:
        use_one(store, "alice", "lucky_bonus")
    assert exc_info.value.player_id == "alice"
    assert exc_info.value.game_name == "lucky_bonus"


def test_use_one_clears_entry_when_reaches_zero() -> None:
    store = FreeSpinsStore()
    grant(store, "alice", "lucky_bonus", 1)
    use_one(store, "alice", "lucky_bonus")
    assert peek(store, "alice", "lucky_bonus") == 0
    # And another use raises
    with pytest.raises(NoFreeSpinsAvailableError):
        use_one(store, "alice", "lucky_bonus")


# --- Isolation between players and games -----------------------------------

def test_counters_are_isolated_per_player() -> None:
    store = FreeSpinsStore()
    grant(store, "alice", "lucky_bonus", 5)
    grant(store, "bob", "lucky_bonus", 3)

    assert peek(store, "alice", "lucky_bonus") == 5
    assert peek(store, "bob", "lucky_bonus") == 3


def test_counters_are_isolated_per_game() -> None:
    store = FreeSpinsStore()
    grant(store, "alice", "lucky_bonus", 5)
    grant(store, "alice", "sweet_cascade", 10)

    assert peek(store, "alice", "lucky_bonus") == 5
    assert peek(store, "alice", "sweet_cascade") == 10


def test_using_in_one_game_doesnt_affect_other_game() -> None:
    store = FreeSpinsStore()
    grant(store, "alice", "lucky_bonus", 3)
    grant(store, "alice", "sweet_cascade", 7)

    use_one(store, "alice", "lucky_bonus")

    assert peek(store, "alice", "lucky_bonus") == 2
    assert peek(store, "alice", "sweet_cascade") == 7   # unchanged