"""Command-line interface for slot-engine."""
from __future__ import annotations

from pathlib import Path
from sys import path

import typer

from typing import Annotated

from slot_engine import engine
from slot_engine.engine import SpinEngine
from slot_engine.evaluator import Evaluator
from slot_engine.rng import SecureRng, SeededRng
from slot_engine.config import load_game_config
from slot_engine.game import Game

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
    """Run a single spin of the chosen game."""
    path = GAMES_DIR / f"{game}.toml"
    if not path.exists():
        typer.echo(f"Game not found: {game}", err=True)
        typer.echo("Use 'slot-engine list-games' to see available games.", err=True)
        raise typer.Exit(code=1)

    config = load_game_config(path)
    g = Game.from_config(config)

    if seed is not None:
        rng = SeededRng(seed=seed)
        rng_label = f"seeded ({seed})"
    else:
        rng = SecureRng()
        rng_label = "secure (random)"

    engine = g.create_engine(rng)
    result = engine.play()

    typer.echo(f"=== {g.name} | engine={g.engine_name} | rng={rng_label} ===\n")

    typer.echo("Spin window:")
    num_rows = len(result.spin.columns[0])
    for row_idx in range(num_rows):
        row = [col[row_idx] for col in result.spin.columns]
        typer.echo("  " + " | ".join(s.name for s in row))

    typer.echo("\nResult:")
    if not result.evaluation.is_winning:
        typer.echo("  (no wins)")
        return

    for win in result.evaluation.wins:
        typer.echo(
            f"  {win.payline.name:<10} {win.symbol.name} x{win.count} "
            f"-> {win.payout}"
        )
    typer.echo(f"  TOTAL: {result.evaluation.total_payout}")

if __name__ == "__main__":
    app()