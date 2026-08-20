"""The bridge sync job — pulls competitor prices and writes market snapshots.

Placeholder: the actual sync logic will query the latest prices from the
competitor-intelligence DB, normalise them, and upsert them into the
margin-guardian DB as MarketPriceSnapshot rows.
"""
from __future__ import annotations

from datetime import datetime

from src.database import (
    Competitor, KciSessionLocal, KmgSessionLocal,
    MarketPriceSnapshot, PriceHistory, Product,
)


def sync_latest_prices() -> dict[str, int]:
    """Pull the latest price for each product and write a market snapshot.

    Returns a summary dict: {"snapshots_written": N, "products_seen": M}.
    """
    kci = KciSessionLocal()
    kmg = KmgSessionLocal()
    try:
        # Get the latest price per product.
        latest_prices = (
            kci.query(PriceHistory, Product, Competitor)
            .join(Product, PriceHistory.product_id == Product.id)
            .join(Competitor, Product.competitor_id == Competitor.id)
            .order_by(PriceHistory.recorded_at.desc())
            .all()
        )

        seen_products: set[str] = set()
        written = 0
        captured_at = datetime.utcnow()

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
        return {"snapshots_written": written, "products_seen": len(seen_products)}
    except Exception:
        kmg.rollback()
        raise
    finally:
        kci.close()
        kmg.close()
