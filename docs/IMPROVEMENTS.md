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

### 3. ~~Add APScheduler entrypoint~~ ✅
`scripts/run_sync.py` — CLI entrypoint that starts APScheduler and runs
`sync_latest_prices()` every `SYNC_INTERVAL_MINUTES` minutes. Two modes:
default (run once + exit) and `--watch` (blocking scheduler). 6 tests
in `tests/test_run_sync.py` (CLI parsing, run_once mock, exception
handling, --watch flag, --interval override).

### 4. Add FastAPI health endpoint ✅ (this PR)
`src/api.py` — a minimal FastAPI app with `/health` (returns 200 + JSON
status) so the service is probeable from Docker/k8s health checks.
Tests in `tests/test_api.py` (3 tests: 200 response, ok status, ISO
timestamp).

### 5. ~~Dockerfile + docker-compose~~ ✅
`Dockerfile` (single-stage, Python 3.12-slim, non-root user) +
`docker-compose.yml` (sync scheduler service with healthcheck on
:8000). `.dockerignore` excludes venv/data/git. Default CMD runs
`scripts/run_sync --watch`.

## Done

- **Initial scaffold** — genesis loop 2026-08-20. README, .gitignore,
  pyproject.toml, requirements.txt, src/ (config, database, sync),
  tests/test_smoke.py (4 tests), CLAUDE.md, docs/IMPROVEMENTS.md.

## Next (post-backlog)

### 6. Structured logging ✅
Added `src/logging_config.py` with a `JSONFormatter` that emits one
JSON object per log line (timestamp, level, logger, message + any
extra fields). Wired into `src/sync.py` and `scripts/run_sync.py`.
Sync success/failure now logs structured fields
(`snapshots_written`, `products_seen`, `error_type`) that Docker/k8s
log aggregation (Loki, Elasticsearch) can parse without regex.

7 new tests in `tests/test_logging_config.py` cover: basic JSON
formatting, extra-field merging, exception info, ISO-8601 timestamp,
logger handler setup, no-propagation, JSON stdout output.
