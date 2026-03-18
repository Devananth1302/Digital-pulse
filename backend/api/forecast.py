"""API endpoint for trend forecasting."""

from fastapi import APIRouter, Query

from backend.core.database import get_supabase
from backend.core.cache import timed_cache

router = APIRouter()


@router.get("")
@timed_cache(ttl=60)
async def get_forecasts(
    limit: int = Query(10, ge=1, le=50),
    trend: str | None = None,
):
    """Get 48-hour trend forecasts."""
    db = get_supabase()
    query = db.table("forecasts").select("*")

    if trend:
        query = query.eq("trend_prediction", trend)

    result = query.order("created_at", desc=True).limit(limit).execute()

    return {
        "forecasts": result.data,
        "total": len(result.data),
    }
