"""Basic tests for the processing pipeline."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.pipelines.processing import (
    calculate_engagement_total,
    calculate_virality_score,
    calculate_time_decay,
    calculate_engagement_velocity,
    get_virality_breakdown,
)
from datetime import datetime, timezone


def test_engagement_total():
    assert calculate_engagement_total(100, 50, 30) == 180.0
    assert calculate_engagement_total(0, 0, 0) == 0.0


def test_virality_score():
    # Score = Shares*0.4 + Comments*0.3 + Likes*0.2 + Velocity*0.1
    score = calculate_virality_score(shares=100, comments=50, likes=200, velocity=10)
    expected = 100 * 0.4 + 50 * 0.3 + 200 * 0.2 + 10 * 0.1
    assert abs(score - expected) < 0.01


def test_time_decay():
    now = datetime.now(timezone.utc).isoformat()
    decay = calculate_time_decay(now)
    assert 0.99 < decay <= 1.0  # Just created, minimal decay


def test_engagement_velocity():
    now = datetime.now(timezone.utc).isoformat()
    velocity = calculate_engagement_velocity(100.0, now)
    assert velocity > 0  # Should be engagement / small hours


def test_virality_breakdown():
    breakdown = get_virality_breakdown("test123", shares=100, comments=50, likes=200, velocity=10)
    assert breakdown["post_id"] == "test123"
    assert breakdown["total_score"] > 0
    assert breakdown["shares_component"] == 100 * 0.4
    assert breakdown["comments_component"] == 50 * 0.3
    assert breakdown["likes_component"] == 200 * 0.2
    assert "explanation" in breakdown


if __name__ == "__main__":
    test_engagement_total()
    test_virality_score()
    test_time_decay()
    test_engagement_velocity()
    test_virality_breakdown()
    print("All tests passed!")
