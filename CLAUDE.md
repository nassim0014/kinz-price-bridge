# kinz-price-bridge — Agent Guidance

## What this is

A bridge service that synchronises competitor price data from
**kinz-competitor-intelligence** into KINZ's margin and accounting
pipelines. Created by the genesis loop on 2026-08-20.

## Rules (inherited from the loop engine)

1. **Never push directly to `main`** — open a PR, squash-merge.
2. **Squash-merge only** — so a revert is one command.
3. **Never create GitHub issues** — owner wants 0%.
4. **Never change repository visibility.**
5. **Never rewrite git history or force-push.**
6. **Never delete a branch other than one created this run.**

## Development workflow

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -q              # expect 4 smoke tests pass
ruff check .           # expect clean
```

## CI

Add `.github/workflows/ci.yml` as the first PR after this scaffold
lands (see `docs/IMPROVEMENTS.md` item 1).

## Database URLs

- `KCI_DATABASE_URL` — read from competitor-intelligence (default:
  `sqlite:///data/competitors.db`)
- `KMG_DATABASE_URL` — write to margin-guardian (default:
  `sqlite:///data/margin.db`)

Both default to local SQLite for development. Production uses
PostgreSQL.
