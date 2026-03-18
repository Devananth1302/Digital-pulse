"""API endpoints for emerging signals."""

from fastapi import APIRouter, Query

from backend.core.database import get_supabase
from backend.core.cache import timed_cache

router = APIRouter()


@router.get("")
@timed_cache(ttl=30)
async def get_emerging_signals(
    limit: int = Query(20, ge=1, le=100),
    severity: str | None = None,
):
    """Get emerging signal alerts."""
    db = get_supabase()
    query = db.table("emerging_signals").select("*")

    if severity:
        query = query.eq("severity", severity)

    result = query.order("detected_at", desc=True).limit(limit).execute()

    return {
        "signals": result.data,
        "total": len(result.data),
    }
