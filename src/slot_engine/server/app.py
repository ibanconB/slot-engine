"""FastAPI app exposing slot-engine games over HTTP"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from slot_engine.config import load_game_config
from slot_engine.domain import Payline
from slot_engine.domain.play_result import PlayResult, PlayStep
from slot_engine.domain.spin_result import SpinResult
from slot_engine.game import Game
from slot_engine.rng import SecureRng
from slot_engine.server.dto import (
    EvaluationDTO,
    LineWinDTO,
    PlayResponseDTO,
    SpinDTO,
    StepDTO,
)

GAMES_DIR = Path("games")

app = FastAPI(
    title="slot-engine",
    description="HTTP API for slot game engines.",
    version="0.1.0",
)

def _spin_to_dto(spin: SpinResult) -> SpinDTO:
    """Conver column-major SpinResult to row-major SpinDTO for JSON"""
    if not spin.columns:
        return SpinDTO(grid=())
    num_rows = len(spin.columns[0])
    grid = tuple(
        tuple(col[row_idx].name for col in spin.columns)
        for row_idx in range(num_rows)
    )
    return SpinDTO(grid=grid)

def _step_to_dto(step: PlayStep) -> StepDTO:
    return StepDTO(
        spin=_spin_to_dto(step.spin),
        evaluation=EvaluationDTO(
            wins=tuple(
                LineWinDTO(
                    payline=w.payline.name,
                    symbol=w.symbol.name,
                    count=w.count,
                    payout=w.payout,
                )
                for w in step.evaluation.wins
            ),
            total_payout=step.evaluation.total_payout,
            is_winning=step.evaluation.is_winning,
        ),
        multiplier=step.multiplier,
    )

def _result_to_dto(result: PlayResult, game: Game) -> PlayResponseDTO:
    return PlayResponseDTO(
        game=game.name,
        engine=game.engine_name,
        steps=tuple(_step_to_dto(step) for step in result.steps),
        total_payout=result.total_payout,
        is_winning=result.is_winning,
    )

@app.post(
    "/games/{game_name}/spin",
    response_model=PlayResponseDTO,
    summary="Play one spin (or a full cascade) of a game",
)
def spin(game_name: str) -> PlayResponseDTO:
    """Execute one play and return the result.

    Production RNG (SecureRng) is used. Results are not reproducible.
    """
    path = GAMES_DIR / f"{game_name}.toml"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Game '{game_name}' not found",
        )

    config = load_game_config(path)
    game = Game.from_config(config)
    engine = game.create_engine(rng=SecureRng())
    result = engine.play()

    return _result_to_dto(result, game)

