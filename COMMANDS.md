# slot-engine — Commands cheatsheet

Reference card for the most common operations. Copy-paste-friendly.

All commands assume you are at the project root and Docker is running.

---

## CLI commands

### List available games

```bash
docker compose run --rm dev slot-engine list-games
```

### Inspect a game's structure (reels, paytable, paylines)

```bash
docker compose run --rm dev slot-engine inspect lucky_sevens
```

### Play one spin (random RNG)

```bash
docker compose run --rm dev slot-engine play lucky_sevens
```

### Play one spin (reproducible with seed)

```bash
docker compose run --rm dev slot-engine play lucky_sevens --seed 42
```

---

## Mass simulation (RTP)

### Quick simulation — 100k spins, fixed seed

```bash
docker compose run --rm dev python -c "
from pathlib import Path
from slot_engine.config import load_game_config
from slot_engine.game import Game
from slot_engine.rng import SeededRng
from slot_engine.simulation import Simulator

config = load_game_config(Path('games/lucky_sevens.toml'))
game = Game.from_config(config)
sim = Simulator(game=game, rng=SeededRng(seed=42))
result = sim.run(num_spins=100_000)

print(f'spins        : {result.num_spins:,}')
print(f'total bet    : {result.total_bet}')
print(f'total payout : {result.total_payout}')
print(f'RTP          : {float(result.rtp) * 100:.4f}%')
print(f'hit rate     : {float(result.hit_rate) * 100:.2f}%')
print(f'max win      : {result.max_win}')
"
```

Approximate timing: ~5 seconds. Error margin: ±0.5-1% on RTP.

### Precise simulation — 1M spins, fixed seed

Same as above but change `num_spins=100_000` to `num_spins=1_000_000`.

Approximate timing: ~30-60 seconds. Error margin: ±0.2% on RTP.

### Multi-seed batch — average across 4 seeds

```bash
docker compose run --rm dev python -c "
from pathlib import Path
from slot_engine.config import load_game_config
from slot_engine.game import Game
from slot_engine.rng import SeededRng
from slot_engine.simulation import Simulator

config = load_game_config(Path('games/lucky_sevens.toml'))
game = Game.from_config(config)

results = []
for seed in [1, 42, 123, 999]:
    sim = Simulator(game=game, rng=SeededRng(seed=seed))
    result = sim.run(num_spins=1_000_000)
    results.append(float(result.rtp) * 100)
    print(f'seed={seed:4d}  RTP={float(result.rtp) * 100:.4f}%  max_win={result.max_win}')

avg = sum(results) / len(results)
print(f'─────────────────────────')
print(f'Average RTP  = {avg:.4f}%')
"
```

Approximate timing: ~3-4 minutes (4 × 1M spins). Use to confirm RTP is stable across seeds.

### Random RNG (non-deterministic)

Replace `SeededRng(seed=42)` with `SecureRng()` and remove the seed parameter:

```python
from slot_engine.rng import SecureRng
sim = Simulator(game=game, rng=SecureRng())
```

Note: results vary every run, useful for "real-world feel" but not for reproducible measurement.

---

## TOML verification

### Check that Pydantic loads what you expect

```bash
docker compose run --rm dev python -c "
from pathlib import Path
from slot_engine.config import load_game_config

config = load_game_config(Path('games/lucky_sevens.toml'))
print('Symbols:', list(config.symbols.keys()))
print('Bell x5:', config.paytable['bell'][5])
print('Seven x5:', config.paytable['seven'][5])
"
```

Useful when you suspect a TOML edit didn't persist (PyCharm not saving, Docker volume cache, etc.).

### Compare host file vs container file

```bash
# What the container reads:
docker compose run --rm dev cat games/lucky_sevens.toml

# What the host has:
cat games/lucky_sevens.toml
```

If they differ, you have a volume mount or cache issue.

---

## Tests

### Run the full test suite

```bash
make test
```

### Run a specific test file

```bash
docker compose run --rm dev pytest tests/test_smoke.py -v
```

### Run tests matching a pattern

```bash
docker compose run --rm dev pytest -v -k "deterministic"
```

---

## Quick TOML edit (terminal-only, no IDE)

When PyCharm refuses to save or you want a one-liner change:

```bash
# Replace a single value (with backup)
sed -i.bak 's/"5" = "200.00"/"5" = "220.00"/' games/lucky_sevens.toml

# Verify
grep -A 4 "paytable.bell" games/lucky_sevens.toml

# Cleanup if happy
rm games/lucky_sevens.toml.bak
```

---

## Targets in the Makefile (existing or to add)

```bash
make test         # run pytest
make fix          # run ruff with --fix
make build        # rebuild the dev image
make demo         # play one spin (alias)
```

---

## Troubleshooting

**Same seed gives different results every run** → likely a non-deterministic dependency leaked in. Inspect engine and RNG usage.

**Same seed gives same results but TOML edits don't show** → volume mount issue or PyCharm not saving. Use the verification commands above.

**RTP measured >> RTP theoretical** → either bug in the engine, or the seed used is statistically lucky. Always verify with multi-seed batch (above).

**`make test` says "no module named X"** → likely missing entry in an `__init__.py` (decorator-based registration won't fire if the module isn't imported). Check the impls/ pattern.
