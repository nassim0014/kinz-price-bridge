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

# Log level: DEBUG / INFO / WARNING / ERROR.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
