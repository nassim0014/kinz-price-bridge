"""SQLAlchemy models for kinz-price-bridge.

Placeholder — the actual models will mirror the subset of
competitor-intelligence tables this bridge reads from (Competitor,
Product, PriceHistory) and the margin-guardian tables it writes to.
Defined here so the bridge can be tested in isolation against a
test database.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from src.config import KCI_DATABASE_URL, KMG_DATABASE_URL


def _naive_utcnow() -> datetime:
    """Naive UTC now for DateTime column defaults.

    Replaces datetime.utcnow (deprecated, scheduled for removal). These
    columns hold naive UTC, so compute in UTC explicitly and drop tzinfo.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# ── Source models (read from competitor-intelligence DB) ──────────────

class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True)
    company_name = Column(String, nullable=False, unique=True)
    website = Column(String, nullable=True)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    price_tnd = Column(Float, nullable=True)

    competitor = relationship("Competitor", back_populates="products")


Competitor.products = relationship("Product", back_populates="competitor")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price_tnd = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=_naive_utcnow)
    source = Column(String, nullable=True)


# ── Destination model (write to margin-guardian DB) ───────────────────

class MarketPriceSnapshot(Base):
    """A snapshot of competitor prices for a product, written periodically."""

    __tablename__ = "market_price_snapshots"

    id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    competitor_name = Column(String, nullable=False)
    price_tnd = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    captured_at = Column(DateTime, nullable=False, default=_naive_utcnow)


# ── Engine + session factories ────────────────────────────────────────

def _make_engine(database_url: str):
    """create_engine(), plus WAL mode + a busy timeout for SQLite URLs.

    This bridge is a third process that opens the *same on-disk SQLite
    files* kinz-competitor-intelligence's own app and
    kinz-margin-guardian-pipeline's own app each already read/write on
    their own schedules (see kinz-competitor-intelligence/src/database.py,
    which sets this up for exactly this reason). Without it, a write from
    this bridge landing mid-write from either of those other processes
    fails instantly with "database is locked" instead of waiting.

    journal_mode=WAL is persisted in the database file itself, but
    busy_timeout is a per-connection setting — it must be applied via a
    connect listener so every pooled connection gets it, not just the
    first one opened at import time.
    """
    if not database_url.startswith("sqlite"):
        return create_engine(database_url, future=True)

    engine = create_engine(
        database_url,
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    # A file-based URL (as opposed to ":memory:"/pure in-memory) needs its
    # parent directory to exist *before* the connect below, or sqlite3 fails
    # with "unable to open database file" instead of creating the file.
    # `data/` is gitignored and not guaranteed to exist on a fresh checkout.
    db_path = engine.url.database
    if db_path and db_path != ":memory:":
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()

    with engine.connect():
        pass  # apply WAL to the file before anything else touches it

    return engine


kci_engine = _make_engine(KCI_DATABASE_URL)
KciSessionLocal = sessionmaker(bind=kci_engine, expire_on_commit=False)

kmg_engine = _make_engine(KMG_DATABASE_URL)
KmgSessionLocal = sessionmaker(bind=kmg_engine, expire_on_commit=False)


def init_databases() -> None:
    """Create tables in both databases (development/CI only)."""
    Base.metadata.create_all(kci_engine)
    Base.metadata.create_all(kmg_engine)
