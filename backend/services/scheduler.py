"""Scheduler service for Digital Pulse.

Runs the full ingestion pipeline on a configurable interval using APScheduler.
Pipeline: RSS -> NewsAPI -> normalize -> score -> Supabase -> clustering -> signals -> forecast
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.services.ingestion_service import run_ingestion_pipeline
from backend.pipelines.processing import run_processing_pipeline
from config.settings import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def run_full_cycle():
    """Run complete pipeline: ingest -> process -> cluster -> detect -> forecast."""
    logger.info("=== Starting scheduled pipeline cycle ===")

    try:
        # Step 1: Ingest from all sources
        stats = await run_ingestion_pipeline()
        logger.info(
            "Ingestion: %d collected, %d stored",
            stats["collected"], stats["stored"],
        )

        # Step 2: Run processing (feature engineering, clustering, signals, forecast)
        if stats["stored"] > 0:
            await run_processing_pipeline()
            logger.info("Processing pipeline complete")
        else:
            logger.info("No new posts, skipping processing")

    except Exception as e:
        logger.error("Pipeline cycle failed: %s", e, exc_info=True)

    logger.info("=== Pipeline cycle finished ===")


def start_scheduler():
    """Start the background scheduler."""
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        run_full_cycle,
        trigger=IntervalTrigger(minutes=settings.SCRAPE_INTERVAL_MINUTES),
        id="ingestion_cycle",
        name="Periodic ingestion and processing",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started: running every %d minutes",
        settings.SCRAPE_INTERVAL_MINUTES,
    )
    # NOTE: initial run is triggered by main.py startup_event


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
