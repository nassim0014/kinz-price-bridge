"""Smoke tests — verify the scaffold imports cleanly."""
from __future__ import annotations


def test_src_imports():
    """The package must import without error."""
    import src
    assert src.__version__ == "0.1.0"


def test_config_imports():
    """Config module must load (reads env vars with defaults)."""
    from src import config
    assert config.SYNC_INTERVAL_MINUTES == 30  # default
    assert config.LOG_LEVEL == "INFO"  # default


def test_database_imports():
    """Database models must be importable."""
    from src.database import (
        Base, Competitor, Product, PriceHistory, MarketPriceSnapshot,
        kci_engine, kmg_engine, init_databases,
    )
    assert Competitor.__tablename__ == "competitors"
    assert MarketPriceSnapshot.__tablename__ == "market_price_snapshots"


def test_sync_imports():
    """Sync module must be importable."""
    from src.sync import sync_latest_prices
    assert callable(sync_latest_prices)
