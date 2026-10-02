"""Regression tests for the batched reads in sync_latest_prices.

The sync used to load the entire price_history join into memory and then
run one query per product+competitor pair, so its cost grew with both
table size and batch size. These tests pin the batched shape: the number
of SELECT statements stays flat no matter how many products are in the
batch, while the observable output (latest price wins, duplicate names
resolve newest-first, outlier guard compares against the newest snapshot
per pair) stays exactly what it was.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.database import (
    Base, Competitor, MarketPriceSnapshot, PriceHistory, Product,
)
from src.sync import sync_latest_prices


@pytest.fixture
def kci_session():
    """In-memory SQLite session for the source (KCI) database."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def kmg_session():
    """In-memory SQLite session for the destination (KMG) database."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def _seed(kci, comp_name, prod_name, history):
    """Add a product with a price history: list of (price, age_in_days)."""
    comp = kci.query(Competitor).filter_by(company_name=comp_name).first()
    if comp is None:
        comp = Competitor(company_name=comp_name)
        kci.add(comp)
        kci.flush()
    prod = Product(competitor_id=comp.id, product_name=prod_name,
                   category="Cat", price_tnd=history[0][0])
    kci.add(prod)
    kci.flush()
    now = datetime.now(timezone.utc)
    kci.add_all([
        PriceHistory(product_id=prod.id, price_tnd=price,
                     recorded_at=now - timedelta(days=age))
        for price, age in history
    ])
    kci.commit()


def _select_counter(*sessions):
    """Count SELECT statements issued on the given sessions' engines."""
    counter = {"selects": 0}

    def _before_cursor_execute(conn, cursor, statement, parameters,
                               context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            counter["selects"] += 1

    for session in sessions:
        event.listen(session.get_bind(), "before_cursor_execute",
                     _before_cursor_execute)
    return counter


def test_select_count_stays_flat_as_batch_grows(kci_session, kmg_session):
    """A 12-product batch issues a fixed handful of SELECTs, not 12+ lookups."""
    for i in range(12):
        _seed(kci_session, f"Comp {i}", f"Product {i}",
              [(100.0 + i, 30), (90.0 + i, 1)])

    counter = _select_counter(kci_session, kmg_session)
    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)

    # Same output as before the change.
    assert result == {
        "snapshots_written": 12,
        "products_seen": 12,
        "outliers_rejected": 0,
    }
    snaps = kmg_session.query(MarketPriceSnapshot).all()
    assert len(snaps) == 12
    prices = {s.product_name: s.price_tnd for s in snaps}
    assert prices["Product 3"] == 93.0  # the newer (age 1d) price won

    # The batching itself: a constant budget, independent of batch size.
    # The old per-pair lookup shape would need at least 13 SELECTs here
    # (one full-join scan plus one per pair).
    assert counter["selects"] <= 6


def test_duplicate_named_products_write_one_snapshot(kci_session, kmg_session):
    """Two product rows sharing one name under one competitor resolve to one snapshot."""
    now = datetime.now(timezone.utc)
    comp = Competitor(company_name="Alpha")
    kci_session.add(comp)
    kci_session.flush()
    prod1 = Product(competitor_id=comp.id, product_name="Argan Oil",
                    category="H", price_tnd=45.0)
    prod2 = Product(competitor_id=comp.id, product_name="Argan Oil",
                    category="H", price_tnd=40.0)
    kci_session.add_all([prod1, prod2])
    kci_session.flush()
    kci_session.add_all([
        PriceHistory(product_id=prod1.id, price_tnd=45.0,
                     recorded_at=now - timedelta(days=2)),
        PriceHistory(product_id=prod2.id, price_tnd=40.0,
                     recorded_at=now - timedelta(days=1)),
    ])
    kci_session.commit()

    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result["snapshots_written"] == 1
    assert result["products_seen"] == 1

    snaps = kmg_session.query(MarketPriceSnapshot).all()
    assert len(snaps) == 1
    # The fresher record owns the pair, same as the old full-scan loop.
    assert snaps[0].price_tnd == 40.0


def test_outlier_guard_uses_latest_snapshot_per_pair(kci_session, kmg_session):
    """The guard compares against the newest snapshot for the pair, not any old one."""
    now = datetime.now(timezone.utc)
    kmg_session.add_all([
        MarketPriceSnapshot(product_name="Oil", competitor_name="Alpha",
                            price_tnd=10.0, category="H",
                            captured_at=now - timedelta(days=30)),
        MarketPriceSnapshot(product_name="Oil", competitor_name="Alpha",
                            price_tnd=45.0, category="H",
                            captured_at=now - timedelta(days=1)),
    ])
    kmg_session.commit()

    comp = Competitor(company_name="Alpha")
    kci_session.add(comp)
    kci_session.flush()
    prod = Product(competitor_id=comp.id, product_name="Oil",
                   category="H", price_tnd=40.0)
    kci_session.add(prod)
    kci_session.flush()
    # 40.0 against the latest snapshot (45.0) is a normal change; against
    # the month-old 10.0 it would look like a 4x spike and be rejected.
    kci_session.add(PriceHistory(product_id=prod.id, price_tnd=40.0,
                                 recorded_at=now))
    kci_session.commit()

    result = sync_latest_prices(kci_session=kci_session, kmg_session=kmg_session)
    assert result == {
        "snapshots_written": 1,
        "products_seen": 1,
        "outliers_rejected": 0,
    }
