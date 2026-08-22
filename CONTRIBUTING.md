# Contributing to kinz-price-bridge

## Development setup

```bash
git clone https://github.com/nassim0014/kinz-price-bridge.git
cd kinz-price-bridge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running tests

```bash
./venv/bin/pytest -q                      # expect ~33 tests
./venv/bin/ruff check .                    # expect clean
```

## API endpoints

```bash
# Start the sync scheduler (default: every 30 min)
python -m scripts.run_sync --watch

# Or run the API server for health probes
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /health` — service health check
- `GET /sync-status` — last sync result + next scheduled run
- `GET /metrics` — sync count, last result, timestamp (for Prometheus)

## Docker

```bash
docker compose up --build -d
curl http://localhost:8000/health
```

## CI

CI runs ruff + pytest on every push and pull_request to main.

## Pull request workflow

1. Create a branch from `main`.
2. Make your changes. Keep diffs small (≤400 lines).
3. Run `pytest -q` and `ruff check .` locally.
4. Open a PR with a clear description.
5. Squash-merge when CI is green.
