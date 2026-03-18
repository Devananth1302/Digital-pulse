"""Emerging signal detection: finds rapidly growing narratives.

Detects signals via TWO methods:
1. Engagement growth  – engagement_total spikes between time windows
2. Volume growth      – post count per cluster spikes between time windows
3. New topic burst    – a cluster that appears only in the current window
"""

import logging
from datetime import datetime, timedelta, timezone

from backend.core.database import get_supabase
from config.settings import settings

logger = logging.getLogger(__name__)


async def detect_emerging_signals():
    """Detect narratives with rapid growth in engagement OR post volume."""
    db = get_supabase()
    now = datetime.now(timezone.utc)
    window_hours = settings.EMERGING_TIME_WINDOW_HOURS
    window_start = now - timedelta(hours=window_hours)
    comparison_start = window_start - timedelta(hours=window_hours)

    # ── Fetch posts in current window ─────────────────────────────────────
    # Use created_at (ingestion time), NOT timestamp (publish date).
    # Publish dates are spread across days; created_at reflects scrape batches.
    recent = (
        db.table("posts")
        .select("cluster_id, engagement_total")
        .gte("created_at", window_start.isoformat())
        .not_.is_("cluster_id", "null")
        .execute()
    )

    # ── Fetch posts in previous window ────────────────────────────────────
    previous = (
        db.table("posts")
        .select("cluster_id, engagement_total")
        .gte("created_at", comparison_start.isoformat())
        .lt("created_at", window_start.isoformat())
        .not_.is_("cluster_id", "null")
        .execute()
    )

    # ── Aggregate by cluster ──────────────────────────────────────────────
    def aggregate(rows):
        eng = {}   # cluster_id -> total engagement
        count = {} # cluster_id -> post count
        for r in rows.data:
            cid = r["cluster_id"]
            eng[cid] = eng.get(cid, 0) + (r["engagement_total"] or 0)
            count[cid] = count.get(cid, 0) + 1
        return eng, count

    curr_eng, curr_count = aggregate(recent)
    prev_eng, prev_count = aggregate(previous)

    all_clusters = set(curr_count.keys()) | set(prev_count.keys())
    emerging = []
    seen_clusters = set()

    for cid in all_clusters:
        c_eng = curr_eng.get(cid, 0)
        p_eng = prev_eng.get(cid, 0)
        c_cnt = curr_count.get(cid, 0)
        p_cnt = prev_count.get(cid, 0)

        signal_reason = None
        growth_rate = 0.0

        # ── Method 1: Engagement growth ───────────────────────────────────
        if p_eng >= 1:
            eng_growth = c_eng / p_eng
            if eng_growth >= settings.EMERGING_GROWTH_RATE_THRESHOLD:
                growth_rate = eng_growth
                signal_reason = "engagement_spike"

        # ── Method 2: Volume growth ──────────────────────────────────────
        if signal_reason is None and p_cnt >= 1:
            vol_growth = c_cnt / p_cnt
            if vol_growth >= 1.5:  # 50% more posts than previous window
                growth_rate = vol_growth
                signal_reason = "volume_spike"

        # ── Method 3: New topic burst ────────────────────────────────────
        if signal_reason is None and c_cnt >= 3 and p_cnt == 0:
            growth_rate = float(c_cnt)
            signal_reason = "new_topic"

        if signal_reason and cid not in seen_clusters:
            seen_clusters.add(cid)

            # Look up cluster topic label
            cluster = (
                db.table("narrative_clusters")
                .select("topic_label")
                .eq("cluster_id", cid)
                .execute()
            )
            topic = cluster.data[0]["topic_label"] if cluster.data else f"Cluster {cid}"

            severity = (
                "high" if growth_rate > 3.0
                else "medium" if growth_rate > 1.5
                else "low"
            )

            signal = {
                "cluster_id": cid,
                "topic": topic,
                "growth_rate": round(growth_rate, 4),
                "current_engagement": round(c_eng, 2),
                "previous_engagement": round(p_eng, 2),
                "detected_at": now.isoformat(),
                "severity": severity,
            }
            emerging.append(signal)

    # ── Store signals ─────────────────────────────────────────────────────
    if emerging:
        try:
            db.table("emerging_signals").insert(emerging).execute()
        except Exception as exc:
            logger.error("Failed to store emerging signals: %s", exc)
        logger.info(
            "Detected %d emerging signals (%s)",
            len(emerging),
            ", ".join(f"{s['topic'][:25]}={s['severity']}" for s in emerging[:5]),
        )
    else:
        logger.info("No emerging signals detected")

    return emerging
