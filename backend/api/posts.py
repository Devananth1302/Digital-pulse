"""API endpoints for posts."""

from fastapi import APIRouter, Query

from backend.core.database import get_supabase
from backend.core.cache import timed_cache

router = APIRouter()


@router.get("")
@timed_cache(ttl=30)
async def get_posts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str | None = None,
    sort_by: str = Query(
        "timestamp",
        pattern="^(timestamp|virality_score|engagement_total|engagement_score)$",
    ),
):
    """Get all ingested posts with optional filters."""
    db = get_supabase()
    query = db.table("posts").select("*")

    if source:
        query = query.eq("source", source)

    result = (
        query.order(sort_by, desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    return {
        "posts": result.data,
        "total": len(result.data),
        "offset": offset,
        "limit": limit,
    }
