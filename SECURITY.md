# Security Policy

## Supported Versions

Only the latest `main` branch is supported.

## Reporting a Vulnerability

Email: nassim@kinzoils.com

Please include a description, reproduction steps, impact, and suggested fix.
Response within 48 hours.

## Security Measures

- **Ruff** lint checks in CI
- **Pre-commit hooks** for ruff
- Database credentials via environment variables
- Non-root Docker container (`appuser`)
- Health check endpoint for probe-based monitoring
- No secrets in the repository (`.gitignore` covers `.env`, `*.db`)

## Architecture

The bridge service reads from the competitor-intelligence database
(read-only) and writes to the margin-guardian database. The only API
routes are `GET /health`, `GET /sync-status`, and `GET /metrics`.
