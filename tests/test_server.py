"""Tests for the FastAPI HTTP server (spin + wallet endpoints)."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from slot_engine.server.app import app, get_wallet_store
from slot_engine.wallet import WalletStore, deposit


@pytest.fixture
def client():
    """Fresh WalletStore + funded test player + TestClient.

    Override the dependency so each test starts from a clean state.
    """
    store = WalletStore()
    deposit(store, "funded", Decimal("10000"))

    app.dependency_overrides[get_wallet_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Spin endpoint: happy path ---------------------------------------------

def test_spin_lucky_sevens_returns_200(client) -> None:
    response = client.post(
        "/games/lucky_sevens/spin",
        json={"player_id": "funded", "bet_per_line": "1.00"},
    )
    assert response.status_code == 200


def test_spin_response_has_required_top_level_fields(client) -> None:
    response = client.post(
        "/games/sweet_cascade/spin",
        json={"player_id": "funded", "bet_per_line": "1.00"},
    )
    body = response.json()

    assert body["game"] == "Sweet Cascade"
    assert body["engine"] == "sweet_cascade"
    assert "steps" in body
    assert "total_payout" in body
    assert "is_winning" in body
    assert "bet" in body
    assert "balance_after" in body


def test_spin_response_has_at_least_one_step_with_required_fields(client) -> None:
    response = client.post(
        "/games/lucky_sevens/spin",
        json={"player_id": "funded", "bet_per_line": "1.00"},
    )
    body = response.json()

    assert len(body["steps"]) >= 1
    first_step = body["steps"][0]
    assert "spin" in first_step
    assert "evaluation" in first_step
    assert "multiplier" in first_step
    assert first_step["multiplier"] >= 1


def test_spin_response_grid_shape_matches_game_layout(client) -> None:
    """Sweet Cascade is 3 reels × 3 rows."""
    response = client.post(
        "/games/sweet_cascade/spin",
        json={"player_id": "funded", "bet_per_line": "1.00"},
    )
    body = response.json()

    grid = body["steps"][0]["spin"]["grid"]
    assert len(grid) == 3
    for row in grid:
        assert len(row) == 3


def test_spin_total_payout_serialized_as_string(client) -> None:
    """Decimal serialized as JSON string to preserve precision."""
    response = client.post(
        "/games/sweet_cascade/spin",
        json={"player_id": "funded", "bet_per_line": "1.00"},
    )
    body = response.json()
    assert isinstance(body["total_payout"], str)


def test_spin_bet_equals_bet_per_line_times_paylines(client) -> None:
    """Sweet Cascade has 5 paylines."""
    response = client.post(
        "/games/sweet_cascade/spin",
        json={"player_id": "funded", "bet_per_line": "2.00"},
    )
    body = response.json()
    assert body["bet"] == "10.00"  # 2 × 5 paylines


# --- Spin endpoint: error cases --------------------------------------------

def test_spin_unknown_game_returns_404(client) -> None:
    response = client.post(
        "/games/nonexistent_game/spin",
        json={"player_id": "funded", "bet_per_line": "1.00"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_spin_with_insufficient_funds_returns_402(client) -> None:
    response = client.post(
        "/games/sweet_cascade/spin",
        json={"player_id": "broke_player", "bet_per_line": "1.00"},
    )
    assert response.status_code == 402
    assert "insufficient" in response.json()["detail"].lower()


def test_spin_with_zero_bet_returns_400(client) -> None:
    response = client.post(
        "/games/sweet_cascade/spin",
        json={"player_id": "funded", "bet_per_line": "0"},
    )
    assert response.status_code == 400


def test_spin_without_body_returns_422(client) -> None:
    """FastAPI validates the body schema before the handler runs."""
    response = client.post("/games/sweet_cascade/spin")
    assert response.status_code == 422


# --- Wallet endpoints ------------------------------------------------------

def test_get_wallet_returns_zero_for_new_player(client) -> None:
    response = client.get("/players/newcomer/wallet")
    assert response.status_code == 200
    body = response.json()
    assert body["player_id"] == "newcomer"
    assert body["balance"] == "0"
    assert body["transactions"] == []


def test_get_wallet_returns_funded_balance_and_history(client) -> None:
    response = client.get("/players/funded/wallet")
    body = response.json()
    assert body["balance"] == "10000"
    assert len(body["transactions"]) == 1
    assert body["transactions"][0]["type"] == "deposit"


def test_deposit_increases_balance_and_records_transaction(client) -> None:
    response = client.post(
        "/players/funded/wallet/deposit",
        json={"amount": "50.00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == "10050.00"
    assert len(body["transactions"]) == 2  # original + new


def test_deposit_zero_amount_returns_400(client) -> None:
    response = client.post(
        "/players/funded/wallet/deposit",
        json={"amount": "0"},
    )
    assert response.status_code == 400


# --- Spin + wallet integration ---------------------------------------------

def test_spin_decreases_balance_by_bet_when_no_win(client) -> None:
    """Tricky test: a single spin might or might not win. Use a tight loop
    until we observe a non-winning spin, then verify the balance dropped
    by exactly the bet."""
    bet_per_line = Decimal("1.00")
    bet_total = bet_per_line * Decimal("5")  # Sweet Cascade has 5 paylines

    for _ in range(50):
        before = client.get("/players/funded/wallet").json()
        balance_before = Decimal(before["balance"])

        response = client.post(
            "/games/sweet_cascade/spin",
            json={"player_id": "funded", "bet_per_line": str(bet_per_line)},
        )
        body = response.json()

        if not body["is_winning"]:
            balance_after = Decimal(body["balance_after"])
            assert balance_after == balance_before - bet_total
            return  # found one, test passes

    pytest.skip("No non-winning spin in 50 attempts (extremely unlikely)")


def test_winning_spin_credits_total_payout(client) -> None:
    """Find a winning spin; verify balance = before - bet + total_payout."""
    bet_per_line = Decimal("1.00")
    bet_total = bet_per_line * Decimal("5")

    for _ in range(50):
        before = client.get("/players/funded/wallet").json()
        balance_before = Decimal(before["balance"])

        response = client.post(
            "/games/sweet_cascade/spin",
            json={"player_id": "funded", "bet_per_line": str(bet_per_line)},
        )
        body = response.json()

        if body["is_winning"]:
            balance_after = Decimal(body["balance_after"])
            total_payout = Decimal(body["total_payout"])
            assert balance_after == balance_before - bet_total + total_payout
            return

    pytest.skip("No winning spin in 50 attempts (very unlikely)")