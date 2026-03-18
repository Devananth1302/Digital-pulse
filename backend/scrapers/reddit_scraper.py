"""Reddit public API scraper for Digital Pulse."""

import hashlib
import logging
from datetime import datetime, timezone

import httpx

from backend.core.database import get_supabase
from config.settings import settings

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "worldnews", "technology", "india", "politics",
    "business", "science", "entertainment",
]


def _make_post_id(reddit_id: str) -> str:
    return hashlib.sha256(f"reddit:{reddit_id}".encode()).hexdigest()[:16]


def _detect_region(title: str, subreddit: str) -> str | None:
    if subreddit.lower() == "india":
        return "India"
    text = title.lower()
    india_kw = ["india", "delhi", "mumbai", "modi", "bjp"]
    if any(kw in text for kw in india_kw):
        return "India"
    return None


async def _get_auth_headers() -> dict:
    """Get OAuth token for Reddit API."""
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_SECRET:
        return {"User-Agent": settings.REDDIT_USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_SECRET),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": settings.REDDIT_USER_AGENT},
            )
            resp.raise_for_status()
            token = resp.json()["access_token"]
            return {
                "Authorization": f"Bearer {token}",
                "User-Agent": settings.REDDIT_USER_AGENT,
            }
        except Exception as e:
            logger.warning("Reddit OAuth failed, using public API: %s", e)
            return {"User-Agent": settings.REDDIT_USER_AGENT}


async def scrape_reddit() -> list[dict]:
    """Fetch hot posts from target subreddits."""
    posts = []
    headers = await _get_auth_headers()
    use_oauth = "Authorization" in headers
    base_url = "https://oauth.reddit.com" if use_oauth else "https://www.reddit.com"

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        for sub in SUBREDDITS:
            try:
                url = f"{base_url}/r/{sub}/hot.json?limit=25"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                for child in data.get("data", {}).get("children", []):
                    d = child["data"]
                    post = {
                        "post_id": _make_post_id(d["id"]),
                        "title": d.get("title", ""),
                        "content": d.get("selftext", d.get("title", ""))[:2000],
                        "timestamp": datetime.fromtimestamp(
                            d.get("created_utc", 0), tz=timezone.utc
                        ).isoformat(),
                        "source": "reddit",
                        "likes": d.get("ups", 0),
                        "shares": 0,  # Reddit doesn't expose shares
                        "comments": d.get("num_comments", 0),
                        "region": _detect_region(d.get("title", ""), sub),
                    }
                    posts.append(post)

                logger.info("Scraped %d posts from r/%s", len(data.get("data", {}).get("children", [])), sub)

            except Exception as e:
                logger.error("Error scraping r/%s: %s", sub, e)

    return posts


async def store_reddit_posts(posts: list[dict]) -> int:
    """Upsert Reddit posts into Supabase."""
    if not posts:
        return 0

    db = get_supabase()
    stored = 0

    for post in posts:
        try:
            db.table("posts").upsert(post, on_conflict="post_id").execute()
            stored += 1
        except Exception as e:
            logger.error("Error storing reddit post %s: %s", post["post_id"], e)

    logger.info("Stored %d/%d reddit posts", stored, len(posts))
    return stored
