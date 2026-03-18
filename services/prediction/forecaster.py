"""Trend forecasting using rolling averages and velocity."""

import logging
from datetime import datetime, timedelta, timezone

import numpy as np

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)


def _rolling_average(values: list[float], window: int = 3) -> list[float]:
    if len(values) < window:
        return values
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(np.mean(values[start : i + 1]))
    return result


def _calculate_volatility(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.std(values))


def _predict_trend(
    velocities: list[float], engagements: list[float]
) -> tuple[str, float]:
    """Predict trend direction and confidence."""
    if len(velocities) < 2:
        return "stable", 0.5

    recent = np.mean(velocities[-3:]) if len(velocities) >= 3 else velocities[-1]
    earlier = np.mean(velocities[:3]) if len(velocities) >= 3 else velocities[0]

    volatility = _calculate_volatility(velocities)
    max_vel = max(abs(v) for v in velocities) if velocities else 1
    normalized_vol = volatility / max_vel if max_vel > 0 else 0

    # Confidence decreases with volatility
    confidence = max(0.3, 1.0 - normalized_vol)

    if recent > earlier * 1.2:
        return "rising", round(confidence, 2)
    elif recent < earlier * 0.8:
        return "falling", round(confidence, 2)
    else:
        return "stable", round(confidence, 2)


async def generate_forecasts():
    """Generate 48-hour forecasts for top clusters."""
    db = get_supabase()

    # Get active clusters
    clusters = (
        db.table("narrative_clusters")
        .select("*")
        .order("influence_score", desc=True)
        .limit(20)
        .execute()
    )

    if not clusters.data:
        logger.info("No clusters for forecasting")
        return

    now = datetime.now(timezone.utc)
    forecasts = []

    for cluster in clusters.data:
        cid = cluster["cluster_id"]

        # Get hourly engagement data for last 48h
        past_48h = now - timedelta(hours=48)
        posts = (
            db.table("posts")
            .select("engagement_total, engagement_velocity, timestamp")
            .eq("cluster_id", cid)
            .gte("timestamp", past_48h.isoformat())
            .order("timestamp")
            .execute()
        )

        if not posts.data or len(posts.data) < 2:
            continue

        engagements = [p["engagement_total"] for p in posts.data]
        velocities = [p["engagement_velocity"] for p in posts.data]

        # Smooth with rolling average
        smoothed_eng = _rolling_average(engagements)
        smoothed_vel = _rolling_average(velocities)

        trend, confidence = _predict_trend(smoothed_vel, smoothed_eng)

        # Generate 48h forecast data points (every 6h)
        data_points = []
        last_eng = smoothed_eng[-1] if smoothed_eng else 0
        multiplier = 1.15 if trend == "rising" else 0.85 if trend == "falling" else 1.0

        for h in range(0, 49, 6):
            projected = last_eng * (multiplier ** (h / 6))
            data_points.append({
                "hour": h,
                "timestamp": (now + timedelta(hours=h)).isoformat(),
                "projected_engagement": round(projected, 2),
            })

        forecast = {
            "topic": cluster["topic_label"],
            "trend_prediction": trend,
            "confidence_score": confidence,
            "predicted_engagement": round(data_points[-1]["projected_engagement"], 2),
            "forecast_hours": 48,
            "data_points": data_points,
        }
        forecasts.append(forecast)

    if forecasts:
        db.table("forecasts").insert(forecasts).execute()
        logger.info("Generated %d forecasts", len(forecasts))

    return forecasts
