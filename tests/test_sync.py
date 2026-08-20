"""Integration tests for the sync job.

Uses in-memory SQLite databases for both source (KCI) and destination
(KMG) so the tests run in isolation — no real database needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database import (
    Base, Competitor, MarketPriceSnapshot, PriceHistory, Product,
)
from src.sync import sync_latest_prices


@pytest.fixture
def kci_session():
    """In-memory SQLite session for the source (KCI) database."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def kmg_session():
    """In-memory SQLite session for the destination (KMG) database."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


def test_sync_empty_kci_writes_nothing(kci_session, kmg_session):
    """An empty source DB produces zero snapshots."""
    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result == {"snapshots_written": 0, "products_seen": 0}
    assert kmg_session.query(MarketPriceSnapshot).count() == 0


def test_sync_writes_one_snapshot_per_product(kci_session, kmg_session):
    """Each product with a price history gets exactly one snapshot."""
    now = datetime.now(timezone.utc)
    comp = Competitor(company_name="Alpha Cosmetics", website="https://alpha.tn")
    kci_session.add(comp)
    kci_session.flush()

    prod1 = Product(competitor_id=comp.id, product_name="Argan Oil 100ml",
                    category="Huiles", price_tnd=45.0)
    prod2 = Product(competitor_id=comp.id, product_name="Shea Butter 200g",
                    category="Beurres", price_tnd=30.0)
    kci_session.add_all([prod1, prod2])
    kci_session.flush()

    kci_session.add_all([
        PriceHistory(product_id=prod1.id, price_tnd=50.0,
                     recorded_at=now - timedelta(days=10)),
        PriceHistory(product_id=prod1.id, price_tnd=45.0, recorded_at=now),
        PriceHistory(product_id=prod2.id, price_tnd=30.0, recorded_at=now),
    ])
    kci_session.commit()

    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result["snapshots_written"] == 2
    assert result["products_seen"] == 2

    snapshots = kmg_session.query(MarketPriceSnapshot).all()
    assert len(snapshots) == 2
    # The latest price for prod1 should be 45.0, not 50.0
    prod1_snap = next(s for s in snapshots if s.product_name == "Argan Oil 100ml")
    assert prod1_snap.price_tnd == 45.0
    assert prod1_snap.competitor_name == "Alpha Cosmetics"
    assert prod1_snap.category == "Huiles"


def test_sync_picks_latest_price(kci_session, kmg_session):
    """When a product has multiple price records, the most recent one wins."""
    now = datetime.now(timezone.utc)
    comp = Competitor(company_name="Beta Naturals")
    kci_session.add(comp)
    kci_session.flush()

    prod = Product(competitor_id=comp.id, product_name="Rose Water 200ml",
                   category="Toners", price_tnd=15.0)
    kci_session.add(prod)
    kci_session.flush()

    old_price = 20.0
    new_price = 12.0
    kci_session.add_all([
        PriceHistory(product_id=prod.id, price_tnd=old_price,
                     recorded_at=now - timedelta(days=30)),
        PriceHistory(product_id=prod.id, price_tnd=new_price,
                     recorded_at=now - timedelta(days=1)),
        PriceHistory(product_id=prod.id, price_tnd=18.0,
                     recorded_at=now - timedelta(days=15)),
    ])
    kci_session.commit()

    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result["snapshots_written"] == 1

    snap = kmg_session.query(MarketPriceSnapshot).first()
    assert snap.price_tnd == new_price  # the most recent record


def test_sync_handles_multiple_competitors(kci_session, kmg_session):
    """Two competitors selling the same product name get separate snapshots."""
    now = datetime.now(timezone.utc)
    comp1 = Competitor(company_name="Comp A")
    comp2 = Competitor(company_name="Comp B")
    kci_session.add_all([comp1, comp2])
    kci_session.flush()

    prod1 = Product(competitor_id=comp1.id, product_name="Argan Oil",
                   category="Huiles", price_tnd=40.0)
    prod2 = Product(competitor_id=comp2.id, product_name="Argan Oil",
                    category="Huiles", price_tnd=35.0)
    kci_session.add_all([prod1, prod2])
    kci_session.flush()

    kci_session.add_all([
        PriceHistory(product_id=prod1.id, price_tnd=40.0, recorded_at=now),
        PriceHistory(product_id=prod2.id, price_tnd=35.0, recorded_at=now),
    ])
    kci_session.commit()

    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result["snapshots_written"] == 2
    assert result["products_seen"] == 2

    snapshots = kmg_session.query(MarketPriceSnapshot).all()
    competitor_names = {s.competitor_name for s in snapshots}
    assert competitor_names == {"Comp A", "Comp B"}


def test_sync_ignores_products_without_price_history(kci_session, kmg_session):
    """A product with no PriceHistory rows is skipped."""
    now = datetime.now(timezone.utc)
    comp = Competitor(company_name="Gamma Labs")
    kci_session.add(comp)
    kci_session.flush()

    # Product WITH price history
    prod1 = Product(competitor_id=comp.id, product_name="With History",
                    category="Cat", price_tnd=10.0)
    # Product WITHOUT price history
    prod2 = Product(competitor_id=comp.id, product_name="No History",
                    category="Cat", price_tnd=20.0)
    kci_session.add_all([prod1, prod2])
    kci_session.flush()

    kci_session.add(PriceHistory(product_id=prod1.id, price_tnd=10.0,
                                  recorded_at=now))
    kci_session.commit()

    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result["snapshots_written"] == 1
    assert result["products_seen"] == 1

    snap = kmg_session.query(MarketPriceSnapshot).first()
    assert snap.product_name == "With History"
