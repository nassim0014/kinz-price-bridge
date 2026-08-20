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
  database.py         # SQLAlchemy engine + models (placeholder)
  sync.py             # the bridge job (placeholder)
tests/
  __init__.py
  test_smoke.py       # import smoke test
docs/
  IMPROVEMENTS.md     # backlog
CLAUDE.md             # agent guidance
```

## Owner

Nassim K. — KINZ (`kinzoils.com`), Tunisian natural cosmetics.
