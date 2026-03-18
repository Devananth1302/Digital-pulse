"""Script to run a one-off scrape + processing cycle.

Usage:
    python scripts/run_scrape.py
"""

import asyncio
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    from backend.scrapers.news_scraper import scrape_google_news, store_news_posts
    from backend.scrapers.reddit_scraper import scrape_reddit, store_reddit_posts
    from backend.pipelines.processing import run_processing_pipeline

    print("Starting one-off scrape cycle...")

    news = await scrape_google_news()
    print(f"Scraped {len(news)} Google News posts")

    reddit = await scrape_reddit()
    print(f"Scraped {len(reddit)} Reddit posts")

    await store_news_posts(news)
    await store_reddit_posts(reddit)
    print("Posts stored in database")

    print("Running processing pipeline...")
    await run_processing_pipeline()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
