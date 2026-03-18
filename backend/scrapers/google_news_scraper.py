"""Google News RSS scraper for Digital Pulse.

Fetches articles from Google News India RSS feed using feedparser.
Returns normalized post dicts ready for the ingestion pipeline.
"""

import hashlib
import logging
from datetime import datetime, timezone

import feedparser
import httpx

logger = logging.getLogger(__name__)

RSS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

# Additional category feeds for broader coverage
CATEGORY_FEEDS = {
    "top": RSS_URL,
    "technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "entertainment": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "sports": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
}


def _make_post_id(title: str) -> str:
    """Deterministic ID from title."""
    return hashlib.sha256(f"gnews:{title}".encode()).hexdigest()[:16]


def _detect_region(title: str, summary: str) -> str | None:
    text = f"{title} {summary}".lower()
    india_keywords = [
        "india", "delhi", "mumbai", "bangalore", "bengaluru", "chennai",
        "kolkata", "hyderabad", "pune", "jaipur", "lucknow",
        "modi", "bjp", "congress", "rupee", "sensex", "nifty",
    ]
    if any(kw in text for kw in india_keywords):
        return "India"
    return None


async def scrape_google_news_rss() -> list[dict]:
    """Fetch and parse Google News India RSS feeds.

    Returns a list of normalized post dicts.
    """
    posts = []
    seen_ids = set()

    async with httpx.AsyncClient(timeout=30) as client:
        for category, url in CATEGORY_FEEDS.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:25]:
                    title = entry.get("title", "").strip()
                    summary = entry.get("summary", entry.get("description", "")).strip()

                    if not title:
                        continue

                    post_id = _make_post_id(title)
                    if post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)

                    # Parse timestamp
                    published = entry.get("published_parsed")
                    if published:
                        ts = datetime(*published[:6], tzinfo=timezone.utc)
                    else:
                        ts = datetime.now(timezone.utc)

                    post = {
                        "post_id": post_id,
                        "title": title,
                        "content": summary,
                        "timestamp": ts.isoformat(),
                        "source": "google_news",
                        "likes": 0,
                        "shares": 0,
                        "comments": 0,
                        "region": _detect_region(title, summary),
                    }
                    posts.append(post)

                logger.info(
                    "Google News RSS [%s]: scraped %d articles",
                    category, min(25, len(feed.entries)),
                )

            except Exception as e:
                logger.error("Google News RSS [%s] error: %s", category, e)

    logger.info("Google News RSS total: %d unique articles", len(posts))
    return posts
