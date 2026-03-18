"""API endpoint for the Pulse Score (0-100)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from backend.core.database import get_supabase
from backend.core.cache import timed_cache

router = APIRouter()


@router.get("")
@timed_cache(ttl=60)  # Cache pulse score for 60 seconds
async def get_pulse_score():
    """
    Calculate and return the overall Pulse Score (0-100).

    The score reflects the current intensity of cultural/narrative activity:
    - High engagement velocity = higher score
    - More emerging signals = higher score
    - More active clusters = higher score
    """
    db = get_supabase()
    now = datetime.now(timezone.utc)
    past_24h = now - timedelta(hours=24)

    # Component 1: Engagement intensity (0-40 points)
    # Limit to 500 most recent for performance
    recent_posts = (
        db.table("posts")
        .select("virality_score, engagement_velocity")
        .gte("timestamp", past_24h.isoformat())
        .order("timestamp", desc=True)
        .limit(500)
        .execute()
    )
    posts = recent_posts.data or []
    avg_virality = (
        sum(p["virality_score"] for p in posts) / len(posts)
        if posts else 0
    )
    # Normalize: assume 100 is a high virality score
    engagement_component = min(40, (avg_virality / 100) * 40)

    # Component 2: Emerging signals (0-30 points)
    signals = (
        db.table("emerging_signals")
        .select("severity")
        .gte("detected_at", past_24h.isoformat())
        .limit(100)
        .execute()
    )
    signal_data = signals.data or []
    signal_score = sum(
        3 if s["severity"] == "high" else 2 if s["severity"] == "medium" else 1
        for s in signal_data
    )
    signal_component = min(30, signal_score * 3)

    # Component 3: Cluster activity (0-30 points)
    clusters = (
        db.table("narrative_clusters")
        .select("post_count, influence_score")
        .gte("created_at", past_24h.isoformat())
        .limit(50)
        .execute()
    )
    cluster_data = clusters.data or []
    active_clusters = len(cluster_data)
    cluster_component = min(30, active_clusters * 5)

    total = round(engagement_component + signal_component + cluster_component, 1)

    # Determine trend
    prev_score = (
        db.table("pulse_scores")
        .select("score")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    prev = prev_score.data[0]["score"] if prev_score.data else total
    if total > prev * 1.1:
        direction = "rising"
    elif total < prev * 0.9:
        direction = "falling"
    else:
        direction = "stable"

    # Top narratives
    top_clusters = (
        db.table("narrative_clusters")
        .select("topic_label")
        .order("influence_score", desc=True)
        .limit(5)
        .execute()
    )
    top_narratives = [c["topic_label"] for c in (top_clusters.data or [])]

    result = {
        "score": total,
        "breakdown": {
            "engagement_intensity": round(engagement_component, 1),
            "emerging_signals": round(signal_component, 1),
            "cluster_activity": round(cluster_component, 1),
        },
        "top_narratives": top_narratives,
        "trend_direction": direction,
        "timestamp": now.isoformat(),
        "meta": {
            "posts_analyzed": len(posts),
            "signals_detected": len(signal_data),
            "active_clusters": active_clusters,
        },
    }

    # Store score
    db.table("pulse_scores").insert({
        "score": total,
        "breakdown": result["breakdown"],
        "top_narratives": top_narratives,
        "trend_direction": direction,
    }).execute()

    return result
