"""Configuration for kinz-price-bridge.

Reads from environment variables (or .env file) so the same code runs
in development, CI, and production without code changes.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present — local dev only; production uses real env vars.
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

# Source: competitor-intelligence database (read-only).
KCI_DATABASE_URL = os.environ.get(
    "KCI_DATABASE_URL",
    "sqlite:///data/competitors.db",
)

# Destination: margin-guardian pipeline database (write).
KMG_DATABASE_URL = os.environ.get(
    "KMG_DATABASE_URL",
    "sqlite:///data/margin.db",
)

# Sync interval (minutes). Default: every 30 minutes.
SYNC_INTERVAL_MINUTES = int(os.environ.get("SYNC_INTERVAL_MINUTES", "30"))

# Price outlier guard: reject a new price if it is more than this many
# times higher, or less than 1/this-many times lower, than the last
# snapshot already recorded for the same product+competitor pair. A
# single scraper glitch (misread decimal, wrong currency, stale HTML)
# should not be allowed to blow up downstream margin calculations.
PRICE_OUTLIER_MAX_RATIO = float(os.environ.get("PRICE_OUTLIER_MAX_RATIO", "5.0"))

# Log level: DEBUG / INFO / WARNING / ERROR.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
