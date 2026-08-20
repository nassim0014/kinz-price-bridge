"""APScheduler entrypoint — runs the sync job periodically.

Usage:
    python -m scripts.run_sync                   # run once + exit (default)
    python -m scripts.run_sync --watch            # run now, then every SYNC_INTERVAL_MINUTES
    python -m scripts.run_sync --watch --interval 15  # custom interval (minutes)

The --watch mode starts a BlockingScheduler that calls sync_latest_prices()
every SYNC_INTERVAL_MINUTES (default 30) minutes. The first run happens
immediately on startup so you don't wait one interval for the first sync.
"""
from __future__ import annotations

import argparse
import logging
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import LOG_LEVEL, SYNC_INTERVAL_MINUTES
from src.sync import sync_latest_prices

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("kinz-price-bridge")


def run_once() -> dict[str, int]:
    """Run the sync job once and return the summary."""
    log.info("starting sync")
    try:
        result = sync_latest_prices()
        log.info("sync complete: %s", result)
        return result
    except Exception as e:
        log.error("sync failed: %s", e, exc_info=True)
        raise


def run_watch(interval_minutes: int = SYNC_INTERVAL_MINUTES) -> None:
    """Run now, then every `interval_minutes` until interrupted."""
    run_once()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_once,
        "interval",
        minutes=interval_minutes,
        id="sync_latest_prices",
        max_instances=1,
        coalesce=True,
    )
    log.info("scheduler started — next run in %d minutes (Ctrl+C to exit)", interval_minutes)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("scheduler stopped")
        scheduler.shutdown(wait=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="kinz-price-bridge sync runner")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run now, then every SYNC_INTERVAL_MINUTES (default: 30).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=SYNC_INTERVAL_MINUTES,
        help=f"Override the watch interval (minutes). Default: {SYNC_INTERVAL_MINUTES}",
    )
    args = parser.parse_args()

    try:
        if args.watch:
            run_watch(interval_minutes=args.interval)
        else:
            run_once()
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
