"""NewsAPI scraper for Digital Pulse.

Fetches top headlines from NewsAPI (India) and returns normalized post dicts.
Requires NEWS_API_KEY environment variable.
"""

import hashlib
import logging
from datetime import datetime, timezone

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"


def _make_post_id(title: str) -> str:
    return hashlib.sha256(f"newsapi:{title}".encode()).hexdigest()[:16]


def _detect_region(title: str, description: str) -> str | None:
    text = f"{title} {description}".lower()
    india_keywords = [
        "india", "delhi", "mumbai", "bangalore", "bengaluru", "chennai",
        "kolkata", "hyderabad", "pune", "jaipur", "lucknow",
        "modi", "bjp", "congress", "rupee", "sensex", "nifty",
    ]
    if any(kw in text for kw in india_keywords):
        return "India"
    return None


async def scrape_newsapi() -> list[dict]:
    """Fetch top headlines from NewsAPI for India.

    Returns a list of normalized post dicts.
    Falls back gracefully if NEWS_API_KEY is not set.
    """
    if not settings.NEWS_API_KEY:
        logger.warning("NEWS_API_KEY not set, skipping NewsAPI scrape")
        return []

    posts = []

    # Fetch from multiple categories for broader coverage
    categories = ["general", "technology", "business", "entertainment", "science"]

    async with httpx.AsyncClient(timeout=30) as client:
        for category in categories:
            try:
                response = await client.get(
                    f"{NEWSAPI_BASE}/top-headlines",
                    params={
                        "country": "in",
                        "category": category,
                        "pageSize": 20,
                        "apiKey": settings.NEWS_API_KEY,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "ok":
                    logger.error("NewsAPI error: %s", data.get("message", "Unknown"))
                    continue

                for article in data.get("articles", []):
                    title = (article.get("title") or "").strip()
                    description = (article.get("description") or "").strip()

                    if not title or title == "[Removed]":
                        continue

                    # Parse timestamp
                    published_str = article.get("publishedAt", "")
                    try:
                        ts = datetime.fromisoformat(
                            published_str.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        ts = datetime.now(timezone.utc)

                    # Extract source name
                    source_name = "newsapi"
                    article_source = article.get("source", {})
                    if isinstance(article_source, dict) and article_source.get("name"):
                        source_name = f"newsapi:{article_source['name']}"

                    post = {
                        "post_id": _make_post_id(title),
                        "title": title,
                        "content": description or title,
                        "timestamp": ts.isoformat(),
                        "source": source_name,
                        "likes": 0,
                        "shares": 0,
                        "comments": 0,
                        "region": _detect_region(title, description),
                    }
                    posts.append(post)

                logger.info(
                    "NewsAPI [%s]: fetched %d articles",
                    category, len(data.get("articles", [])),
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error("NewsAPI: Invalid API key")
                    return posts
                elif e.response.status_code == 429:
                    logger.warning("NewsAPI: Rate limit hit, stopping")
                    return posts
                else:
                    logger.error("NewsAPI [%s] HTTP error: %s", category, e)
            except Exception as e:
                logger.error("NewsAPI [%s] error: %s", category, e)

    # Deduplicate by post_id
    seen = set()
    unique = []
    for p in posts:
        if p["post_id"] not in seen:
            seen.add(p["post_id"])
            unique.append(p)

    logger.info("NewsAPI total: %d unique articles", len(unique))
    return unique
