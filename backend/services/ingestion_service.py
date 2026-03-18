"""Multi-source ingestion service for Digital Pulse.

Pipeline: Google News RSS -> NewsAPI -> Merge -> Normalize -> Score -> Supabase
"""

import logging
from datetime import datetime, timezone

from backend.core.database import get_supabase
from backend.scrapers.google_news_scraper import scrape_google_news_rss
from backend.scrapers.newsapi_scraper import scrape_newsapi
from backend.pipelines.processing import (
    calculate_engagement_total,
    calculate_engagement_velocity,
    calculate_time_decay,
    calculate_virality_score,
)

logger = logging.getLogger(__name__)


def normalize_post(raw: dict) -> dict | None:
    """Normalize a raw post dict to the canonical schema.

    Ensures all required fields exist and are properly typed.
    """
    title = str(raw.get("title", "")).strip()
    if not title:
        return None

    content = str(raw.get("content", "")).strip() or title

    # Parse timestamp
    ts_raw = raw.get("timestamp")
    if isinstance(ts_raw, str):
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)
    elif isinstance(ts_raw, (int, float)):
        ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
    elif isinstance(ts_raw, datetime):
        ts = ts_raw if ts_raw.tzinfo else ts_raw.replace(tzinfo=timezone.utc)
    else:
        ts = datetime.now(timezone.utc)

    return {
        "post_id": str(raw.get("post_id", "")),
        "title": title[:500],
        "content": content[:5000],
        "timestamp": ts.isoformat(),
        "source": str(raw.get("source", "unknown")),
        "likes": int(raw.get("likes", 0) or 0),
        "shares": int(raw.get("shares", 0) or 0),
        "comments": int(raw.get("comments", 0) or 0),
        "region": raw.get("region"),
    }


def compute_engagement_score(post: dict) -> dict:
    """Calculate engagement metrics and virality/engagement_score for a post."""
    likes = post.get("likes", 0)
    shares = post.get("shares", 0)
    comments = post.get("comments", 0)
    timestamp = post["timestamp"]

    eng_total = calculate_engagement_total(likes, shares, comments)
    velocity = calculate_engagement_velocity(eng_total, timestamp)
    decay = calculate_time_decay(timestamp)
    virality = calculate_virality_score(shares, comments, likes, velocity)

    post["engagement_total"] = eng_total
    post["engagement_velocity"] = velocity
    post["time_decay"] = decay
    post["virality_score"] = virality
    post["engagement_score"] = virality  # alias as requested
    return post


async def collect_all_sources() -> list[dict]:
    """Collect posts from all configured sources.

    Pipeline: Google News RSS -> NewsAPI -> Merge
    """
    logger.info("Collecting from all sources...")

    # Step 1: Google News RSS
    rss_posts = await scrape_google_news_rss()
    logger.info("RSS: %d posts", len(rss_posts))

    # Step 2: NewsAPI
    newsapi_posts = await scrape_newsapi()
    logger.info("NewsAPI: %d posts", len(newsapi_posts))

    # Step 3: Merge and deduplicate by post_id
    all_posts = rss_posts + newsapi_posts
    seen = set()
    merged = []
    for p in all_posts:
        pid = p.get("post_id")
        if pid and pid not in seen:
            seen.add(pid)
            merged.append(p)

    logger.info("Merged: %d unique posts", len(merged))
    return merged


async def run_ingestion_pipeline(raw_posts: list[dict] | None = None) -> dict:
    """Full ingestion pipeline.

    If raw_posts is None, collects from RSS + NewsAPI.
    Otherwise processes the provided posts (e.g. from CSV upload).

    Returns summary stats.
    """
    # Collect
    if raw_posts is None:
        raw_posts = await collect_all_sources()

    if not raw_posts:
        logger.info("No posts to ingest")
        return {"collected": 0, "normalized": 0, "stored": 0}

    # Normalize
    normalized = []
    for raw in raw_posts:
        post = normalize_post(raw)
        if post and post["post_id"]:
            normalized.append(post)

    logger.info("Normalized: %d posts", len(normalized))

    # Score
    scored = [compute_engagement_score(p) for p in normalized]

    # Store in Supabase
    db = get_supabase()
    stored = 0
    for post in scored:
        try:
            db.table("posts").upsert(post, on_conflict="post_id").execute()
            stored += 1
        except Exception as e:
            logger.error("Failed to store post %s: %s", post["post_id"], e)

    logger.info(
        "Ingestion complete: %d collected -> %d normalized -> %d stored",
        len(raw_posts), len(normalized), stored,
    )

    return {
        "collected": len(raw_posts),
        "normalized": len(normalized),
        "stored": stored,
    }
