"""APScheduler-based scheduler for periodic scraping."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.scrapers.news_scraper import scrape_google_news, store_news_posts
from backend.scrapers.reddit_scraper import scrape_reddit, store_reddit_posts
from backend.pipelines.processing import run_processing_pipeline
from config.settings import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def scrape_and_process():
    """Run full scrape + process cycle."""
    logger.info("Starting scheduled scrape cycle...")

    news_posts = await scrape_google_news()
    reddit_posts = await scrape_reddit()

    await store_news_posts(news_posts)
    await store_reddit_posts(reddit_posts)

    total = len(news_posts) + len(reddit_posts)
    logger.info("Scrape complete: %d total posts collected", total)

    # Run processing pipeline on new data
    await run_processing_pipeline()
    logger.info("Processing pipeline complete")


def start_scheduler():
    """Start the background scraping scheduler."""
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        scrape_and_process,
        trigger=IntervalTrigger(minutes=settings.SCRAPE_INTERVAL_MINUTES),
        id="scrape_cycle",
        name="Periodic scrape and process",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started: scraping every %d minutes",
        settings.SCRAPE_INTERVAL_MINUTES,
    )

    # Run initial scrape on startup
    asyncio.get_event_loop().create_task(scrape_and_process())


def stop_scheduler():
    """Shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
