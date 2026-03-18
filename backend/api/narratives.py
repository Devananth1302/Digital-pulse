"""API endpoints for narratives."""

from fastapi import APIRouter, Query

from backend.core.database import get_supabase
from backend.core.cache import timed_cache
from backend.pipelines.processing import get_virality_breakdown, calculate_engagement_velocity, calculate_engagement_total

router = APIRouter()


@router.get("")
@timed_cache(ttl=30)
async def get_narratives(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str | None = None,
    cluster_id: int | None = None,
    sort_by: str = Query("virality_score", pattern="^(virality_score|timestamp|engagement_total)$"),
):
    """Get narrative posts with optional filters."""
    db = get_supabase()
    query = db.table("posts").select("*")

    if source:
        query = query.eq("source", source)
    if cluster_id is not None:
        query = query.eq("cluster_id", cluster_id)

    result = (
        query.order(sort_by, desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    # Also fetch cluster info
    clusters = db.table("narrative_clusters").select("*").order("influence_score", desc=True).execute()

    return {
        "posts": result.data,
        "clusters": clusters.data,
        "total": len(result.data),
        "offset": offset,
        "limit": limit,
    }


@router.get("/{post_id}")
async def get_narrative_detail(post_id: str):
    """Get a single narrative post with virality breakdown."""
    db = get_supabase()
    result = db.table("posts").select("*").eq("post_id", post_id).execute()

    if not result.data:
        return {"error": "Post not found"}

    post = result.data[0]

    # Ensure engagement values have fallbacks
    likes = post.get("likes", 0) or 0
    shares = post.get("shares", 0) or 0
    comments = post.get("comments", 0) or 0

    eng_total = calculate_engagement_total(likes, shares, comments)
    velocity = calculate_engagement_velocity(eng_total, post["timestamp"])

    # Get previous velocity for momentum calculation (if available)
    previous_velocity = post.get("engagement_velocity", velocity)

    breakdown = get_virality_breakdown(
        post["post_id"],
        shares,
        comments,
        likes,
        velocity,
        previous_velocity=previous_velocity,
        title=post.get("title", ""),
        timestamp_str=post.get("timestamp", ""),
    )

    # Get cluster info if assigned
    cluster = None
    if post.get("cluster_id"):
        cluster_result = (
            db.table("narrative_clusters")
            .select("*")
            .eq("cluster_id", post["cluster_id"])
            .execute()
        )
        if cluster_result.data:
            cluster = cluster_result.data[0]

    return {
        "post": post,
        "virality_breakdown": breakdown,
        "cluster": cluster,
    }
