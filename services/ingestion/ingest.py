"""Data ingestion service: normalize and validate incoming data."""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"post_id", "title", "content", "timestamp", "source"}


def normalize_post(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a raw post dict to the canonical schema."""
    missing = REQUIRED_FIELDS - set(raw.keys())
    if missing:
        logger.warning("Post missing fields %s, skipping", missing)
        return None

    # Normalize timestamp
    ts = raw["timestamp"]
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)
    elif isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts, tz=timezone.utc)

    return {
        "post_id": str(raw["post_id"]),
        "title": str(raw.get("title", ""))[:500],
        "content": str(raw.get("content", ""))[:5000],
        "timestamp": ts.isoformat(),
        "source": str(raw.get("source", "unknown")),
        "likes": int(raw.get("likes", 0)),
        "shares": int(raw.get("shares", 0)),
        "comments": int(raw.get("comments", 0)),
        "region": raw.get("region"),
    }


async def ingest_posts(raw_posts: list[dict]) -> int:
    """Normalize and store a batch of posts. Returns count stored."""
    db = get_supabase()
    stored = 0

    for raw in raw_posts:
        post = normalize_post(raw)
        if post is None:
            continue
        try:
            db.table("posts").upsert(post, on_conflict="post_id").execute()
            stored += 1
        except Exception as e:
            logger.error("Error ingesting post %s: %s", post.get("post_id"), e)

    logger.info("Ingested %d/%d posts", stored, len(raw_posts))
    return stored
