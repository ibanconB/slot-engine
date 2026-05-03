# slot-engine — Roadmap

> Vision: build a learning platform for slot game development. The end state is a system that lets you (1) design and implement multiple slot games each with their own engine logic, (2) verify their RTP through statistical simulation, and (3) serve them through an HTTP API with sessions, wallet and transactions.

This document is the long-term plan. It is intentionally high-level; the concrete to-do list lives in the project task tracker.

---

## Architectural decisions

These decisions shape every phase that follows. They are documented here so future-you (and any collaborator) understands *why* the codebase looks the way it does.

### AD-1 — One engine per game

Each game has its own engine class. There is no generic mega-engine with feature toggles. Engines may share helpers via composition (e.g. all classic-line games can reuse the same line evaluator), but each game's engine class is the single source of truth for that game's behaviour.

Rationale: easier to read each game in isolation, easier to test, no hidden coupling between games. The cost (some duplication) is acceptable given the goal is learning.

The shared infrastructure (`SpinEngine`, `Evaluator`, `Reel`, `Paytable`, etc.) remains generic and gets reused as building blocks.

### AD-2 — TOML declares content, code implements behaviour

The TOML file describes **what the game contains**: symbols, reel strips, paytable values, payline shapes. It does **not** describe behaviour: nothing in the TOML says "this symbol is wild and substitutes any other".

All behaviour lives in the engine code for that game. Two games can have identical TOML structure but completely different runtime behaviour because their engines interpret the data differently.

Rationale: configuration that contains logic becomes a second, badly-typed programming language inside text files. Keeping logic in Python (with type hints, tests, IDE support) is always better.

### AD-3 — RTP verification before server work

The HTTP server work (sessions, wallet, persistence) only starts once we have multiple games whose RTP is measured and meets target. A game without verified RTP is not shippable, so serving it makes no sense.

Rationale: building the RTP simulator first also forces engines to stay deterministic, reproducible, and fast — properties that pay off everywhere else.

### AD-4 — Inter-spin state introduced when needed, not before

State carried between spins (free spins counter, sticky wilds, bonus mode) will be added when we implement the first game that requires it (around Phase 13). Engines are stateless until then.

Rationale: rule of three. Designing a state-passing protocol without a real consumer leads to either over-generic mush or premature specialization.

---

## Block 1 — Professional foundations

Finish the old roadmap. These are the last pieces before refactoring towards multi-game architecture.

### Phase 8 — CLI with Typer

Replace `scripts/demo.py` with a proper CLI exposed as `slot-engine`. Subcommands:

- `slot-engine play --game <name> [--spins N] [--seed N]`
- `slot-engine inspect --game <name>` — pretty-print reels, paytable, paylines
- `slot-engine list-games` — list available games in `games/`

Learning goals: command design, type-driven CLIs, packaging entry points (`pyproject.toml [project.scripts]`).

### Phase 9 — Tests with Pytest

Add the test infrastructure: `tests/` directory, fixtures for common objects (symbols, reels, paytables), unit tests for every domain class and the evaluator, integration tests for `Game.from_config`. CI hook so `make test` runs them.

Learning goals: test-driven mindset, fixtures, parametrize, coverage, fast feedback loops.

---

## Block 2 — Multi-engine architecture

This is where the project starts to look like a real slot platform.

### Phase 10 — Engine registry and protocol

Define a `GameEngine` Protocol describing what every game engine must expose (`spin(rng) -> SpinResult` minimally). Build a registry mapping `engine_name -> engine_class`. Add an `engine = "..."` field to the TOML. `Game.from_config` looks up the engine in the registry.

Refactor: rename current `SpinEngine` to `ClassicLinesEngine` (or similar) and register it as the default for existing games.

Learning goals: protocols vs ABCs, plugin patterns, registries, backward compatibility during refactor.

### Phase 11 — First injectable feature: wilds

Implement wild substitution in the matcher (`MatchFn`) used by the evaluator. Add a wild symbol to a game and verify it pays as expected. The wild is part of the *engine's behaviour*, not the TOML configuration.

Learning goals: strategy pattern in practice, validating an extensibility model with the smallest possible change.

### Phase 12 — Second game type with distinct mechanics

Build a second game whose engine works differently from the classic lines game. Likely candidates: a *scatter pays* game (any-position symbol counts) or a *cluster pays* game (groups of 5+ adjacent symbols). The exact game we decide together based on what teaches the most.

Learning goals: prove that the architecture supports genuinely different games, not just variants of the same idea.

### Phase 13 — State between spins: free spins / bonus rounds

Introduce the first game with stateful behaviour. Define a session-state contract that the engine reads and updates. The engine becomes `spin(state) -> (result, new_state)` for stateful games (stateless ones still work as `spin() -> result`).

This is the foundation for everything in Block 4 (the server needs to persist this state).

Learning goals: state machines, immutable state updates, designing protocols informed by real requirements.

---

## Block 3 — RTP evaluator

Once we have a few games with diverse mechanics, we need to know what their RTP actually is. This block builds the math verification harness.

### Phase 14 — Mass-spin simulator

A runner that executes N million spins with a seeded RNG, collects raw results, and emits a structured report. Must be fast (vectorize where possible, parallelize across cores). Must be reproducible (same seed = same outcome).

Learning goals: performance optimization in Python, multiprocessing, reproducibility.

### Phase 15 — Statistical metrics

From a simulation run, compute: RTP (return-to-player percentage), hit rate, max win, win distribution histogram, volatility/variance, longest losing streak. These are the standard metrics game studios report.

Learning goals: applied statistics, confidence intervals, presenting numerical results.

### Phase 16 — RTP test framework

Pytest integration: write tests that assert "this game has RTP between 95.9% and 96.1% over 10M spins". These tests are slow (run them in CI weekly, not on every commit) but they are the contract that says "this game is mathematically correct".

Learning goals: slow-test management, statistical assertions, confidence-interval-aware testing.

### Phase 17 — Game design loop

First real cycle of "Claude is the game designer". I send a Game Design Document with target RTP, hit rate, volatility, and feature descriptions. You implement the engine and TOML. We run the simulator. We iterate on numbers until the math matches the design.

This phase repeats every time we want a new game.

Learning goals: math tuning, balancing, the iterative dance between design and implementation.

---

## Block 4 — Game server

Now we wrap the engines in something playable.

### Phase 18 — HTTP API base with FastAPI

A `/spin` endpoint that takes `game_name + bet_amount` and returns a `SpinResult`. No persistence yet, no wallet, no auth. Just proves the engines work behind HTTP.

Learning goals: FastAPI fundamentals, request/response models, dependency injection.

### Phase 19 — Wallet and transactions (in-memory)

Player has a balance. Bet debits the balance before the spin. Win credits it after. Transactions are recorded as a ledger. All in memory for now — no database.

Learning goals: financial domain modelling (always Decimal, never float), idempotency, transactional thinking.

### Phase 20 — Sessions

A session represents a player's active interaction with one game. Sessions hold the game state (free spins remaining, bonus mode, etc.). The `/spin` endpoint operates on a session.

Learning goals: session lifecycle, request-scoped state, separation of concerns.

### Phase 21 — Persistence

Move wallets, transactions, and sessions to a database. SQLModel + SQLite for development, PostgreSQL for production via Docker. Migrations with Alembic.

Learning goals: ORMs, schema design, migrations, dev/prod parity.

### Phase 22 — Stateful bonus persistence

Tie Phase 13's stateful engines to the persisted sessions from Phase 21. Free spins now survive across HTTP requests; the server resumes a bonus round where the player left off.

Learning goals: persistent state machines, recovery semantics.

### Phase 23 — Authentication

Basic login (email + password), JWT-based auth on protected endpoints. Player ID required to spin.

Learning goals: auth fundamentals, password hashing (Argon2), JWT lifecycle, security basics.

---

## Block 5 — Production-readiness (post-MVP)

Discussed when we get there. Topics likely to include: structured logging, metrics (Prometheus), healthchecks, GitHub Actions CI, comprehensive Docker compose with Postgres, deployment docs.

---

## How to use this roadmap

- **It is a map, not a contract.** Phases will get reordered, split, or rethought as we learn things. That is healthy. Update this document when that happens.
- **One block at a time.** Don't think about Block 4 while building Block 2. Tunnel vision is a feature here.
- **Each phase ends with a working system.** No half-finished phases sitting in branches. If a phase turns out to be too big, split it before merging.
- **The task tracker holds the active to-do list.** This document holds the long-term direction.