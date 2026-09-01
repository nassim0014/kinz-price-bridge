"""The bridge sync job — pulls competitor prices and writes market snapshots.

Queries the latest price per product from the KCI DB, normalises them,
and writes them to the KMG DB as MarketPriceSnapshot rows. Each call
produces one batch of snapshots with a shared captured_at timestamp.

A price outlier guard sits in front of the write: if a product's new
price is wildly higher or lower than the last snapshot already on file
for that product+competitor pair, the write is skipped and a structured
warning is logged instead of letting a scraper glitch poison the margin
pipeline. See `_is_price_outlier` and `PRICE_OUTLIER_MAX_RATIO`.

The session factories default to the module-level ones (which read from
env vars), but both can be passed in for testing against in-memory SQLite.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.config import PRICE_OUTLIER_MAX_RATIO
from src.database import (
    Competitor, KciSessionLocal, KmgSessionLocal,
    MarketPriceSnapshot, PriceHistory, Product,
)
from src.logging_config import get_logger

log = get_logger(__name__)


def _is_price_outlier(new_price: float, last_price: float) -> bool:
    """True if `new_price` deviates too far from `last_price` to be trusted.

    A scraper glitch (misread decimal, wrong currency, stale/broken HTML)
    can produce a price that is wildly higher or lower than reality. Rather
    than let that silently poison the margin pipeline, flag anything more
    than PRICE_OUTLIER_MAX_RATIO times higher or lower than the last known
    price for the same product+competitor pair.

    A non-positive last_price can't yield a meaningful ratio (already
    corrupt data) — treat it as "not an outlier" rather than divide by
    zero, and let the new value through so it can self-correct.
    """
    if last_price <= 0:
        return False
    ratio = new_price / last_price
    return ratio > PRICE_OUTLIER_MAX_RATIO or ratio < (1 / PRICE_OUTLIER_MAX_RATIO)


def _latest_snapshot_price(
    kmg: Session, product_name: str, competitor_name: str
) -> Optional[float]:
    """The price on the most recent MarketPriceSnapshot for this pair, if any."""
    last = (
        kmg.query(MarketPriceSnapshot)
        .filter_by(product_name=product_name, competitor_name=competitor_name)
        .order_by(MarketPriceSnapshot.captured_at.desc())
        .first()
    )
    return last.price_tnd if last is not None else None


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
        {"snapshots_written": N, "products_seen": M, "outliers_rejected": K}
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
        rejected = 0
        captured_at = datetime.now(timezone.utc)

        for ph, prod, comp in latest_prices:
            key = f"{comp.company_name}::{prod.product_name}"
            if key in seen_products:
                continue
            seen_products.add(key)

            last_price = _latest_snapshot_price(kmg, prod.product_name, comp.company_name)
            if last_price is not None and _is_price_outlier(ph.price_tnd, last_price):
                rejected += 1
                log.warning(
                    "sync_price_outlier_rejected",
                    extra={
                        "product_name": prod.product_name,
                        "competitor_name": comp.company_name,
                        "new_price": ph.price_tnd,
                        "last_price": last_price,
                        "max_ratio": PRICE_OUTLIER_MAX_RATIO,
                    },
                )
                continue

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
            extra={
                "snapshots_written": written,
                "products_seen": len(seen_products),
                "outliers_rejected": rejected,
            },
        )
        return {
            "snapshots_written": written,
            "products_seen": len(seen_products),
            "outliers_rejected": rejected,
        }
    except Exception as e:
        kmg.rollback()
        log.error("sync_failed", extra={"error": str(e), "error_type": type(e).__name__})
        raise
    finally:
        if owns_kci:
            kci.close()
        if owns_kmg:
            kmg.close()
