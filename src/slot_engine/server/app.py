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
    WalletDTO, RoundDTO,
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

def _play_to_round_dto(result: PlayResult, *, kind: str) -> "RoundDTO":
    return RoundDTO(
        kind=kind,
        steps=tuple(_step_to_dto(step) for step in result.steps),
        total_payout=result.total_payout,
        is_winning=result.is_winning,
        free_spins_triggered=result.free_spins_triggered,
    )


def _settle(
    result: PlayResult,
    wallet_store: WalletStore,
    fs_store: FreeSpinsStore,
    player_id: str,
    game_name: str,
    *,
    was_free: bool,
) -> None:
    """Apply a play's effects: credit win + grant any triggered FS."""
    if result.total_payout > 0:
        credit_win(
            wallet_store,
            player_id,
            result.total_payout,
            metadata={"game": game_name, "was_free_spin": str(was_free)},
        )
    if result.free_spins_triggered > 0:
        grant_free_spins(
            fs_store, player_id, game_name, result.free_spins_triggered
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
    summary="Play a full round: initial spin + all triggered free spins",
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
    engine = game.create_engine(rng=SecureRng())

    rounds: list[RoundDTO] = []
    total_bet = Decimal("0")

    # Decide: does the player start with FS pending or pay?
    has_pending_fs = peek_free_spins(fs_store, body.player_id, game_name) > 0

    if not has_pending_fs:
        # Initial paid spin
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

        result = engine.play()
        rounds.append(_play_to_round_dto(result, kind="paid"))
        _settle(result, wallet_store, fs_store, body.player_id, game_name, was_free=False)

    # Auto-drain any pending FS (pre-existing or just triggered)
    while peek_free_spins(fs_store, body.player_id, game_name) > 0:
        use_one_free_spin(fs_store, body.player_id, game_name)
        result = engine.play()
        rounds.append(_play_to_round_dto(result, kind="free"))
        _settle(result, wallet_store, fs_store, body.player_id, game_name, was_free=True)

    total_payout = sum(
        (r.total_payout for r in rounds),
        start=Decimal("0"),
    )
    balance_after = wallet_store.get_or_create_wallet(body.player_id).balance

    return SpinResponseDTO(
        game=game.name,
        engine=game.engine_name,
        rounds=tuple(rounds),
        bet=total_bet,
        total_payout=total_payout,
        balance_after=balance_after,
        free_spins_remaining=peek_free_spins(fs_store, body.player_id, game_name),
    )