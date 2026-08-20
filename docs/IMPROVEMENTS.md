# Improvement Backlog — kinz-price-bridge

Tracked here so loop agents know what is safe to pick up. One item per
PR, smallest first.

## Now

### 1. Add CI workflow ✅ (PR #1 — pending merge)
`.github/workflows/ci.yml` — lint + tests on push and pull_request.
Same shape as kinz-competitor-intelligence's `tests.yml`. No browser
needed; the scaffold has no Playwright deps.

### 2. Implement the sync job end-to-end
`src/sync.py` has a placeholder. Wire it to actually query the latest
price per product from the KCI DB, normalise, and upsert into the KMG
DB. Add integration tests against in-memory SQLite databases.

### 3. Add APScheduler entrypoint
`scripts/run_sync.py` — a CLI entrypoint that starts APScheduler and
runs `sync_latest_prices()` every `SYNC_INTERVAL_MINUTES` minutes.

### 4. Add FastAPI health endpoint ✅ (this PR)
`src/api.py` — a minimal FastAPI app with `/health` (returns 200 + JSON
status) so the service is probeable from Docker/k8s health checks.
Tests in `tests/test_api.py` (3 tests: 200 response, ok status, ISO
timestamp).

### 5. Dockerfile + docker-compose
`Dockerfile` (single-stage, Python 3.12-slim) + `docker-compose.yml`
that runs the sync scheduler.

## Done

- **Initial scaffold** — genesis loop 2026-08-20. README, .gitignore,
  pyproject.toml, requirements.txt, src/ (config, database, sync),
  tests/test_smoke.py (4 tests), CLAUDE.md, docs/IMPROVEMENTS.md.
