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