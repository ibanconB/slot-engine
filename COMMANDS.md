## Mass simulation (RTP)

### Single random run
```bash
docker compose run --rm dev slot-engine simulate sweet_cascade
```

### Single deterministic run (reproducible)
```bash
docker compose run --rm dev slot-engine simulate sweet_cascade --seed 42 --spins 1000000
```

### Multi-seed batch (validation)
```bash
docker compose run --rm dev slot-engine simulate sweet_cascade --seeds 5 --spins 1000000
```

### Pre-certification with production RNG
```bash
docker compose run --rm dev slot-engine simulate sweet_cascade --secure --seeds 5 --spins 1000000
```

## HTTP API

The server runs at `http://localhost:8000`. Launch with `make serve`.

### Wallet

#### View balance + history
```bash
curl http://localhost:8000/players/alice/wallet | jq
```

#### Deposit
```bash
curl -X POST http://localhost:8000/players/alice/wallet/deposit \
    -H "Content-Type: application/json" \
    -d '{"amount": "100.00"}' | jq
```

### Free Spins

#### View FS counters
```bash
curl http://localhost:8000/players/alice/free-spins | jq
```

#### Grant FS (admin / testing)
```bash
curl -X POST http://localhost:8000/players/alice/free-spins/grant \
    -H "Content-Type: application/json" \
    -d '{"game": "lucky_bonus", "amount": 8}' | jq
```

### Spin

#### Paid spin
```bash
curl -X POST http://localhost:8000/games/lucky_bonus/spin \
    -H "Content-Type: application/json" \
    -d '{"player_id": "alice", "bet_per_line": "1.00"}' | jq
```

#### Spin (server decides: free if available, else paid)
The same curl works for both. If the player has FS, the bet is ignored and a free spin is consumed.

#### Auto-drain all free spins
```bash
while true; do
    response=$(curl -s -X POST http://localhost:8000/games/lucky_bonus/spin \
        -H "Content-Type: application/json" \
        -d '{"player_id": "alice"}')
    was_free=$(echo "$response" | jq -r '.was_free_spin')
    payout=$(echo "$response" | jq -r '.total_payout')
    remaining=$(echo "$response" | jq -r '.free_spins_remaining')
    echo "free=$was_free  payout=$payout  remaining=$remaining"
    [ "$remaining" == "0" ] && break
done
```

#### View OpenAPI docs
Open in browser: `http://localhost:8000/docs`