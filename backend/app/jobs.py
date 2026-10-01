"""APScheduler job: re-run saved watches and persist only NEW infringements."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db import cache_purge_expired, due_watches
from app.scanner import execute_scan

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def run_due_watches() -> None:
    """Called on an interval. Each due watch is re-scanned with cache bypassed."""
    cache_purge_expired()
    watches = due_watches()
    if not watches:
        logger.debug("Watch tick: nothing due")
        return

    logger.info("Watch tick: %s due scan(s)", len(watches))
    for watch in watches:
        try:
            result = execute_scan(
                watch.product_name,
                watch.official_price,
                watch.image_url,
                use_cache=False,
                rescan_interval_hours=watch.interval_hours,
            )
            logger.info(
                "Watch %s rescan complete: risk=%s new=%s flagged=%s",
                watch.id,
                result.risk_score,
                len(result.new_infringements),
                len(result.flagged_listings),
            )
        except Exception:
            logger.exception("Watch %s rescan failed", watch.id)


def start_scheduler() -> None:
    if scheduler.running:
        return
    # Tick every hour; due_watches() applies each watch's N-hour interval
    scheduler.add_job(
        run_due_watches,
        trigger=IntervalTrigger(hours=1),
        id="watch_rescan_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("APScheduler started (hourly tick for N-hour watch intervals)")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
