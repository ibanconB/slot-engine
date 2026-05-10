"""Tests for the FastAPI HTTP server."""
from fastapi.testclient import TestClient

from slot_engine.server import app

client = TestClient(app)


def test_spin_lucky_sevens_returns_200() -> None:
    response = client.post("/games/lucky_sevens/spin")
    assert response.status_code == 200


def test_spin_response_has_required_top_level_fields() -> None:
    response = client.post("/games/sweet_cascade/spin")
    body = response.json()

    assert body["game"] == "Sweet Cascade"
    assert body["engine"] == "sweet_cascade"
    assert "steps" in body
    assert "total_payout" in body
    assert "is_winning" in body


def test_spin_response_has_at_least_one_step_with_required_fields() -> None:
    response = client.post("/games/lucky_sevens/spin")
    body = response.json()

    assert len(body["steps"]) >= 1

    first_step = body["steps"][0]
    assert "spin" in first_step
    assert "evaluation" in first_step
    assert "multiplier" in first_step
    assert first_step["multiplier"] >= 1


def test_spin_response_grid_shape_matches_game_layout() -> None:
    """Sweet Cascade is 3 reels × 3 rows."""
    response = client.post("/games/sweet_cascade/spin")
    body = response.json()

    grid = body["steps"][0]["spin"]["grid"]
    assert len(grid) == 3, "expected 3 rows"
    for row in grid:
        assert len(row) == 3, "expected 3 columns per row"


def test_spin_unknown_game_returns_404() -> None:
    response = client.post("/games/nonexistent_game/spin")

    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "not found" in body["detail"].lower()


def test_total_payout_serialized_as_string_for_decimal_safety() -> None:
    """Pydantic v2 serializes Decimal as string to preserve precision in JSON."""
    response = client.post("/games/sweet_cascade/spin")
    body = response.json()

    assert isinstance(body["total_payout"], str)