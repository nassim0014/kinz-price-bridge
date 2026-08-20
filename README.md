# kinz-price-bridge

A bridge service that synchronises competitor price data from the
**kinz-competitor-intelligence** database into KINZ's margin and
accounting pipelines (kinz-margin-guardian-pipeline, Odoo).

## Purpose

The competitor-intelligence dashboard tracks competitor prices scraped
from the web. The margin-guardian pipeline tracks KINZ's own COGS and
margins. This bridge closes the loop: it periodically pulls the latest
competitor prices, normalises them, and pushes them into the margin
pipeline so margin analysis can compare KINZ's prices against the
market in real time.

## Status

**Scaffold** — created by the genesis loop on 2026-08-20. No
functional code yet. See `docs/IMPROVEMENTS.md` for the backlog.

## Stack

- Python 3.12
- SQLAlchemy 2.x (database ORM)
- FastAPI (API surface)
- APScheduler (periodic sync)
- pytest + ruff (testing + linting)

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -q          # no tests yet — will pass vacuously
ruff check .
```

## Layout

```
src/
  __init__.py
  config.py          # environment + settings
  database.py         # SQLAlchemy engine + models
  sync.py             # the bridge job
  api.py              # FastAPI app with /health endpoint
tests/
  __init__.py
  test_smoke.py       # import smoke test
  test_api.py         # /health endpoint tests
  test_sync.py        # sync job integration tests
scripts/
  run_sync.py         # APScheduler entrypoint (run once or --watch)
docs/
  IMPROVEMENTS.md     # backlog
Dockerfile            # single-stage Python 3.12-slim
docker-compose.yml    # sync scheduler service + healthcheck
CLAUDE.md             # agent guidance
```

## Docker

```bash
# Build and run the sync scheduler (default: every 30 min)
docker compose up --build -d

# Run the FastAPI app instead (for health probes)
docker compose run --rm bridge uvicorn src.api:app --host 0.0.0.0 --port 8000

# Check health
curl http://localhost:8000/health
```

## Owner

Nassim K. — KINZ (`kinzoils.com`), Tunisian natural cosmetics.
