"""SQLAlchemy models for kinz-price-bridge.

Placeholder — the actual models will mirror the subset of
competitor-intelligence tables this bridge reads from (Competitor,
Product, PriceHistory) and the margin-guardian tables it writes to.
Defined here so the bridge can be tested in isolation against a
test database.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine
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

kci_engine = create_engine(KCI_DATABASE_URL, future=True)
KciSessionLocal = sessionmaker(bind=kci_engine, expire_on_commit=False)

kmg_engine = create_engine(KMG_DATABASE_URL, future=True)
KmgSessionLocal = sessionmaker(bind=kmg_engine, expire_on_commit=False)


def init_databases() -> None:
    """Create tables in both databases (development/CI only)."""
    Base.metadata.create_all(kci_engine)
    Base.metadata.create_all(kmg_engine)
