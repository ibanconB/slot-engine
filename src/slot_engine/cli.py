"""Command-line interface for slot-engine."""
from __future__ import annotations

from pathlib import Path
from sys import path

import typer
import secrets
import statistics

from typing import Annotated

from slot_engine import engine
from slot_engine.engine import SpinEngine
from slot_engine.evaluator import Evaluator
from slot_engine.rng import SecureRng, SeededRng
from slot_engine.config import load_game_config
from slot_engine.game import Game
from slot_engine.simulation import Simulator

GAMES_DIR = Path("games")

app = typer.Typer(
    name="slot-engine",
    help="Slot game engine: load games from TOML, run spins, inspect configs.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Slot game engine CLI."""

@app.command(name="list-games")
def list_games() -> None:
    """List all available games in the games directory"""
    if not GAMES_DIR.exists():
        typer.echo(f"Games directory not found: {GAMES_DIR.resolve()}")
        raise typer.Exit(code=1)

    toml_files = sorted(GAMES_DIR.glob("*.toml"))
    if not toml_files:
        typer.echo(f"No games found in: {GAMES_DIR.resolve()}")
        return

    typer.echo(f"Available games: ({toml_files}):\n")
    for path in toml_files:
        try:
            config = load_game_config(path)
            typer.echo(f"  {path.stem:<20} {config.game.name}")
        except Exception as exc:
            typer.echo(f" {path.stem:<20} (invalid: {exc})", err=True)

@app.command()
def inspect(game: str) -> None:
    """Inspect a game's configuration: reels, paytable, paylines."""
    path = GAMES_DIR / f"{game}.toml"
    if not path.exists():
        typer.echo(f"Game not found: {game}", err=True)
        typer.echo("Use 'slot-engine list-games' to see available games.", err=True)
        raise typer.Exit(code=1)

    config = load_game_config(path)
    g = Game.from_config(config)

    typer.echo(f"=== {g.name} ===\n")
    typer.echo(f"  window_size : {g.window_size}")
    typer.echo(f"  reels       : {len(g.reels)}")
    typer.echo(f"  paylines    : {len(g.paylines)}")
    typer.echo(f"  symbols     : {len(g.symbols)}")

    typer.echo("\nSymbols:")
    for name, sym in g.symbols.items():
        flags = []
        if sym.is_wild:
            flags.append("wild")
        if sym.is_scatter:
            flags.append("scatter")
        suffix = f" [{', '.join(flags)}]" if flags else ""
        typer.echo(f"  - {name}{suffix}")

    typer.echo("\nReels:")
    for i, reel in enumerate(g.reels):
        typer.echo(f"  reel[{i}] : {reel.length} symbols")

    typer.echo("\nPaytable:")
    grouped: dict[str, list[tuple[int, object]]] = {}
    for (sym, count), payout in g.paytable.payouts.items():
        grouped.setdefault(sym.name, []).append((count, payout))
    for sym_name in sorted(grouped):
        entries = sorted(grouped[sym_name])
        formatted = "  ".join(f"x{c}={p}" for c, p in entries)
        typer.echo(f"  {sym_name:<10} {formatted}")

    typer.echo("\nPaylines:")
    for p in g.paylines:
        typer.echo(f"  {p.name:<10} rows={list(p.rows)}")

@app.command()
def play(
    game: str,
    seed: Annotated[
        int | None,
        typer.Option(help="Optional seed for reproducible spins."),
    ] = None,
) -> None:
    """Run a single play (one spin or full cascade) of the chosen game."""
    path = GAMES_DIR / f"{game}.toml"
    if not path.exists():
        typer.echo(f"Game not found: {game}", err=True)
        typer.echo("Use 'slot-engine list-games' to see available games.", err=True)
        raise typer.Exit(code=1)

    config = load_game_config(path)
    g = Game.from_config(config)

    if seed is None:
        seed = secrets.randbelow(1_000_000)
        seed_label = f"seed={seed} (random)"
    else:
        seed_label = f"seed={seed}"

    rng = SeededRng(seed=seed)

    engine = g.create_engine(rng)
    result = engine.play()

    typer.echo(f"=== {g.name} | engine={g.engine_name} | rng={seed_label} ===")

    for step_idx, step in enumerate(result.steps):
        header = "Initial spin" if step_idx == 0 else f"Cascade step {step_idx}"
        typer.echo(f"\n[{header}] (multiplier x{step.multiplier})")

        num_rows = len(step.spin.columns[0])
        for row_idx in range(num_rows):
            row = [col[row_idx] for col in step.spin.columns]
            typer.echo("  " + " | ".join(s.name for s in row))

        if not step.evaluation.is_winning:
            typer.echo("  (no wins)")
            continue

        for win in step.evaluation.wins:
            base = win.payout
            applied = base * step.multiplier
            typer.echo(
                f"  {win.payline.name:<10} {win.symbol.name} x{win.count} "
                f"-> {base} × {step.multiplier} = {applied}"
            )

    typer.echo(f"\nTOTAL: {result.total_payout}")



@app.command()
def simulate(
    game: str,
    spins: Annotated[
        int,
        typer.Option(help="Number of plays to simulate per run."),
    ] = 100_000,
    seed: Annotated[
        int | None,
        typer.Option(help="Single deterministic seed. Mutually exclusive with --seeds and --secure."),
    ] = None,
    seeds: Annotated[
        int | None,
        typer.Option(help="Run N independent simulations (random seeds). Mutually exclusive with --seed."),
    ] = None,
    secure: Annotated[
        bool,
        typer.Option(help="Use SecureRng (production-grade, non-reproducible). For final validation before certification."),
    ] = False,
) -> None:
    """Simulate plays and report RTP, hit rate, and max win.

    Examples:
      slot-engine simulate sweet_cascade
      slot-engine simulate sweet_cascade --seed 42 --spins 1000000
      slot-engine simulate sweet_cascade --seeds 5 --spins 1000000
      slot-engine simulate sweet_cascade --secure --spins 1000000
      slot-engine simulate sweet_cascade --secure --seeds 5 --spins 1000000
    """
    if secure and seed is not None:
        typer.echo(
            "Error: --secure and --seed are mutually exclusive "
            "(SecureRng has no seed concept).",
            err=True,
        )
        raise typer.Exit(code=1)

    if seed is not None and seeds is not None:
        typer.echo("Error: --seed and --seeds are mutually exclusive.", err=True)
        raise typer.Exit(code=1)

    if spins <= 0:
        typer.echo(f"Error: --spins must be > 0, got {spins}.", err=True)
        raise typer.Exit(code=1)

    if seeds is not None and seeds <= 0:
        typer.echo(f"Error: --seeds must be > 0, got {seeds}.", err=True)
        raise typer.Exit(code=1)

    path = GAMES_DIR / f"{game}.toml"
    if not path.exists():
        typer.echo(f"Game not found: {game}", err=True)
        typer.echo("Use 'slot-engine list-games' to see available games.", err=True)
        raise typer.Exit(code=1)

    config = load_game_config(path)
    g = Game.from_config(config)

    # Build the list of (rng, label) pairs to run
    if secure:
        n_runs = seeds if seeds is not None else 1
        runs = [(SecureRng(), f"run #{i+1}") for i in range(n_runs)]
    elif seed is not None:
        runs = [(SeededRng(seed=seed), f"seed={seed}")]
    elif seeds is not None:
        seed_list = [secrets.randbelow(1_000_000) for _ in range(seeds)]
        runs = [(SeededRng(seed=s), f"seed={s}") for s in seed_list]
    else:
        s = secrets.randbelow(1_000_000)
        runs = [(SeededRng(seed=s), f"seed={s} (random)")]

    n = len(runs)

    # Header
    if n == 1:
        rng_label = "rng=secure (production)" if secure else runs[0][1]
        typer.echo(f"=== {g.name} | engine={g.engine_name} | {rng_label} ===\n")
    else:
        run_kind = "secure runs" if secure else "seeds"
        typer.echo(
            f"=== {g.name} | engine={g.engine_name} | "
            f"{n} {run_kind} × {spins:,} plays ===\n"
        )

    # Run simulations
    rtps: list[float] = []
    for rng, run_label in runs:
        sim = Simulator(game=g, rng=rng)
        result = sim.run(num_spins=spins)
        rtp_pct = float(result.rtp) * 100
        hit_rate_pct = float(result.hit_rate) * 100
        rtps.append(rtp_pct)

        if n == 1:
            typer.echo(f"  spins        : {result.num_spins:,}")
            typer.echo(f"  total bet    : {result.total_bet}")
            typer.echo(f"  total payout : {result.total_payout}")
            typer.echo(f"  RTP          : {rtp_pct:.4f}%")
            typer.echo(f"  hit rate     : {hit_rate_pct:.2f}%")
            typer.echo(f"  max win      : {result.max_win}")
        else:
            label = f"{run_label:<14}"
            typer.echo(
                f"  {label}  RTP={rtp_pct:.4f}%  "
                f"max_win={result.max_win}  hit_rate={hit_rate_pct:.2f}%"
            )

    # Summary for multi-run
    if n > 1:
        avg = sum(rtps) / n
        std = statistics.stdev(rtps)
        typer.echo("  ─────────────────────────────────────")
        typer.echo(f"  Average RTP  = {avg:.4f}%")
        typer.echo(f"  Range        = {min(rtps):.2f}% — {max(rtps):.2f}%")
        typer.echo(f"  Std dev      = {std:.2f}pt")

    # Warning when secure mode is used
    if secure:
        typer.echo("\n  Production-grade RNG: results NOT reproducible.")

if __name__ == "__main__":
    app()

