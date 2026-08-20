"""The bridge sync job — pulls competitor prices and writes market snapshots.

Queries the latest price per product from the KCI DB, normalises them,
and writes them to the KMG DB as MarketPriceSnapshot rows. Each call
produces one batch of snapshots with a shared captured_at timestamp.

The session factories default to the module-level ones (which read from
env vars), but both can be passed in for testing against in-memory SQLite.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.database import (
    Competitor, KciSessionLocal, KmgSessionLocal,
    MarketPriceSnapshot, PriceHistory, Product,
)
from src.logging_config import get_logger

log = get_logger(__name__)


def sync_latest_prices(
    kci_session: Optional[Session] = None,
    kmg_session: Optional[Session] = None,
) -> dict[str, int]:
    """Pull the latest price for each product and write a market snapshot.

    Args:
        kci_session: optional SQLAlchemy session for the source DB.
                     Defaults to the module-level KciSessionLocal().
        kmg_session: optional SQLAlchemy session for the destination DB.
                     Defaults to the module-level KmgSessionLocal().

    Returns:
        {"snapshots_written": N, "products_seen": M}
    """
    owns_kci = kci_session is None
    owns_kmg = kmg_session is None
    kci = kci_session or KciSessionLocal()
    kmg = kmg_session or KmgSessionLocal()
    try:
        # Get the latest price per product. Order by recorded_at DESC so
        # the first row per product key is the most recent.
        latest_prices = (
            kci.query(PriceHistory, Product, Competitor)
            .join(Product, PriceHistory.product_id == Product.id)
            .join(Competitor, Product.competitor_id == Competitor.id)
            .order_by(PriceHistory.recorded_at.desc())
            .all()
        )

        seen_products: set[str] = set()
        written = 0
        captured_at = datetime.now(timezone.utc)

        for ph, prod, comp in latest_prices:
            key = f"{comp.company_name}::{prod.product_name}"
            if key in seen_products:
                continue
            seen_products.add(key)

            kmg.add(MarketPriceSnapshot(
                product_name=prod.product_name,
                competitor_name=comp.company_name,
                price_tnd=ph.price_tnd,
                category=prod.category,
                captured_at=captured_at,
            ))
            written += 1

        kmg.commit()
        log.info(
            "sync_complete",
            extra={"snapshots_written": written, "products_seen": len(seen_products)},
        )
        return {"snapshots_written": written, "products_seen": len(seen_products)}
    except Exception as e:
        kmg.rollback()
        log.error("sync_failed", extra={"error": str(e), "error_type": type(e).__name__})
        raise
    finally:
        if owns_kci:
            kci.close()
        if owns_kmg:
            kmg.close()
