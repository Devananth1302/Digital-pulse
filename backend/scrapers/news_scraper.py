"""Google News RSS scraper for Digital Pulse."""

import hashlib
import logging
from datetime import datetime, timezone

import feedparser
import httpx

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)

# Google News RSS feeds by topic
RSS_FEEDS = {
    "top_stories": "https://news.google.com/rss",
    "india": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRE55YXpBU0FtVnVLQUFQAQ?ceid=IN:en&oc=3",
    "technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pKVGlnQVAB",
    "business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pKVGlnQVAB",
    "entertainment": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pKVGlnQVAB",
}


def _make_post_id(title: str, source: str) -> str:
    raw = f"{source}:{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _detect_region(title: str, content: str) -> str | None:
    text = f"{title} {content}".lower()
    india_keywords = [
        "india", "delhi", "mumbai", "bangalore", "chennai", "kolkata",
        "hyderabad", "modi", "bjp", "congress", "rupee",
    ]
    if any(kw in text for kw in india_keywords):
        return "India"
    return None


async def scrape_google_news() -> list[dict]:
    """Fetch and parse Google News RSS feeds."""
    posts = []

    async with httpx.AsyncClient(timeout=30) as client:
        for category, url in RSS_FEEDS.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:20]:  # top 20 per feed
                    title = entry.get("title", "")
                    content = entry.get("summary", entry.get("description", ""))
                    published = entry.get("published_parsed")

                    if published:
                        ts = datetime(*published[:6], tzinfo=timezone.utc)
                    else:
                        ts = datetime.now(timezone.utc)

                    post = {
                        "post_id": _make_post_id(title, "google_news"),
                        "title": title,
                        "content": content,
                        "timestamp": ts.isoformat(),
                        "source": "google_news",
                        "likes": 0,
                        "shares": 0,
                        "comments": 0,
                        "region": _detect_region(title, content),
                    }
                    posts.append(post)

                logger.info("Scraped %d posts from Google News [%s]", len(feed.entries[:20]), category)

            except Exception as e:
                logger.error("Error scraping Google News [%s]: %s", category, e)

    return posts


async def store_news_posts(posts: list[dict]) -> int:
    """Upsert scraped posts into Supabase. Returns number of new posts."""
    if not posts:
        return 0

    db = get_supabase()
    stored = 0

    for post in posts:
        try:
            db.table("posts").upsert(post, on_conflict="post_id").execute()
            stored += 1
        except Exception as e:
            logger.error("Error storing post %s: %s", post["post_id"], e)

    logger.info("Stored %d/%d news posts", stored, len(posts))
    return stored
