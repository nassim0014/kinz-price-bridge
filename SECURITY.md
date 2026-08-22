# Security Policy

## Supported Versions

Only the latest `main` branch is supported with security updates.

## Reporting a Vulnerability

Email: nassim@kinzoils.com

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within 48 hours.

## Security Measures

- **Ruff** lint checks in CI (error-only rules: E9, F, B)
- **Pre-commit hooks** for ruff (optional, `.pre-commit-config.yaml`)
- No secrets in the repository (gitignored `data/competitors_seed.json`)
- SQLite WAL mode for concurrent read/write safety
- No direct database writes from the dashboard (read-only)
- API uses FastAPI with input validation via Pydantic

## Data Privacy

- Competitor contact data (77 real contacts) is gitignored and never committed
- Scraping is rate-limited and respects robots.txt
- No PII is stored beyond publicly available business contact information
