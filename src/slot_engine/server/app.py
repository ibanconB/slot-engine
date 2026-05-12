"""FastAPI app exposing slot-engine games over HTTP."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException

from slot_engine.config import load_game_config
from slot_engine.domain.play_result import PlayResult, PlayStep
from slot_engine.domain.spin_result import SpinResult
from slot_engine.free_spins import (
    FreeSpinsStore,
    grant as grant_free_spins,
    peek as peek_free_spins,
    use_one as use_one_free_spin,
)
from slot_engine.game import Game
from slot_engine.rng import SecureRng
from slot_engine.server.dto import (
    DepositRequestDTO,
    EvaluationDTO,
    GrantFreeSpinsRequestDTO,
    LineWinDTO,
    PlayerFreeSpinsDTO,
    PlayResponseDTO,
    SpinDTO,
    SpinRequestDTO,
    SpinResponseDTO,
    StepDTO,
    TransactionDTO,
    WalletDTO,
)
from slot_engine.wallet import (
    InsufficientFundsError,
    Transaction,
    WalletStore,
    credit_win,
    deposit,
    place_bet,
)


GAMES_DIR = Path("games")

app = FastAPI(
    title="slot-engine",
    description="HTTP API for slot game engines.",
    version="0.1.0",
)


# --- Dependency injection: stores -------------------------------------------

_wallet_store = WalletStore()
_free_spins_store = FreeSpinsStore()


def get_wallet_store() -> WalletStore:
    """Provider for the WalletStore singleton."""
    return _wallet_store


def get_free_spins_store() -> FreeSpinsStore:
    """Provider for the FreeSpinsStore singleton."""
    return _free_spins_store


# --- Domain → DTO translation -----------------------------------------------

def _spin_to_dto(spin: SpinResult) -> SpinDTO:
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


def _transaction_to_dto(tx: Transaction) -> TransactionDTO:
    return TransactionDTO(
        id=str(tx.id),
        type=tx.type.value,
        amount=tx.amount,
        balance_after=tx.balance_after,
        timestamp=tx.timestamp.isoformat(),
        metadata=dict(tx.metadata),
    )


# --- Wallet routes ----------------------------------------------------------

@app.get(
    "/players/{player_id}/wallet",
    response_model=WalletDTO,
    summary="View a player's wallet (balance + transaction history)",
)
def get_wallet(
    player_id: str,
    store: WalletStore = Depends(get_wallet_store),
) -> WalletDTO:
    wallet = store.get_or_create_wallet(player_id)
    transactions = tuple(_transaction_to_dto(t) for t in store.transactions_for(player_id))
    return WalletDTO(
        player_id=wallet.player_id,
        balance=wallet.balance,
        transactions=transactions,
    )


@app.post(
    "/players/{player_id}/wallet/deposit",
    response_model=WalletDTO,
    summary="Deposit funds into a player's wallet (manual / admin)",
)
def deposit_to_wallet(
    player_id: str,
    body: DepositRequestDTO,
    store: WalletStore = Depends(get_wallet_store),
) -> WalletDTO:
    if body.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Deposit amount must be > 0, got {body.amount}",
        )

    deposit(store, player_id, body.amount, metadata={"source": "manual"})

    wallet = store.get_or_create_wallet(player_id)
    transactions = tuple(_transaction_to_dto(t) for t in store.transactions_for(player_id))
    return WalletDTO(
        player_id=wallet.player_id,
        balance=wallet.balance,
        transactions=transactions,
    )


# --- Free spins routes ------------------------------------------------------

@app.get(
    "/players/{player_id}/free-spins",
    response_model=PlayerFreeSpinsDTO,
    summary="Get all free spins counts for a player, by game",
)
def get_free_spins(
    player_id: str,
    store: FreeSpinsStore = Depends(get_free_spins_store),
) -> PlayerFreeSpinsDTO:
    return PlayerFreeSpinsDTO(
        player_id=player_id,
        free_spins=store.all_for_player(player_id),
    )


@app.post(
    "/players/{player_id}/free-spins/grant",
    response_model=PlayerFreeSpinsDTO,
    summary="Manually grant free spins to a player (admin / testing)",
)
def grant_free_spins_endpoint(
    player_id: str,
    body: GrantFreeSpinsRequestDTO,
    store: FreeSpinsStore = Depends(get_free_spins_store),
) -> PlayerFreeSpinsDTO:
    if body.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"amount must be > 0, got {body.amount}",
        )
    grant_free_spins(store, player_id, body.game, body.amount)
    return PlayerFreeSpinsDTO(
        player_id=player_id,
        free_spins=store.all_for_player(player_id),
    )


# --- Spin route -------------------------------------------------------------

@app.post(
    "/games/{game_name}/spin",
    response_model=SpinResponseDTO,
    summary="Spin: uses a free spin if available, otherwise pays from wallet",
)
def spin(
    game_name: str,
    body: SpinRequestDTO,
    wallet_store: WalletStore = Depends(get_wallet_store),
    fs_store: FreeSpinsStore = Depends(get_free_spins_store),
) -> SpinResponseDTO:
    path = GAMES_DIR / f"{game_name}.toml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    config = load_game_config(path)
    game = Game.from_config(config)

    # Decide: free spin or paid?
    available_fs = peek_free_spins(fs_store, body.player_id, game_name)
    was_free_spin = available_fs > 0

    if was_free_spin:
        use_one_free_spin(fs_store, body.player_id, game_name)
        total_bet = Decimal("0")
    else:
        if body.bet_per_line is None or body.bet_per_line <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "bet_per_line is required and must be > 0 when no free spins "
                    "are available"
                ),
            )
        total_bet = body.bet_per_line * Decimal(len(game.paylines))
        try:
            place_bet(
                wallet_store,
                body.player_id,
                total_bet,
                metadata={"game": game_name, "bet_per_line": str(body.bet_per_line)},
            )
        except InsufficientFundsError as exc:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Insufficient funds: balance {exc.balance}, "
                    f"required {exc.requested}"
                ),
            )

    # Play
    engine = game.create_engine(rng=SecureRng())
    result = engine.play()

    # Credit win if any
    if result.total_payout > 0:
        credit_win(
            wallet_store,
            body.player_id,
            result.total_payout,
            metadata={
                "game": game_name,
                "was_free_spin": str(was_free_spin),
            },
        )

    # Grant any free spins triggered by this play
    if result.free_spins_triggered > 0:
        grant_free_spins(
            fs_store, body.player_id, game_name, result.free_spins_triggered
        )

    fs_remaining = peek_free_spins(fs_store, body.player_id, game_name)
    play_dto = _result_to_dto(result, game)
    balance_after = wallet_store.get_or_create_wallet(body.player_id).balance

    return SpinResponseDTO(
        **play_dto.model_dump(),
        bet=total_bet,
        balance_after=balance_after,
        was_free_spin=was_free_spin,
        free_spins_triggered=result.free_spins_triggered,
        free_spins_remaining=fs_remaining,
    )