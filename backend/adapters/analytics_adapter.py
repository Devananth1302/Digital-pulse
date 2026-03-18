"""Analytical Functions Adapter Layer.

This layer abstracts existing analysis functions to make them:
1. Schema-agnostic (handle heterogeneous data fields)
2. Testable in isolation
3. Decoupled from data source (Kafka, CSV, API, etc.)
4. Easy to version and monitor

Functions are wrapped with error handling, logging, and optional tracing.
"""

import logging
import json
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsResult:
    """Standard result wrapper for all analytical operations."""
    success: bool
    operation: str  # e.g., "virality_score", "clustering", "signal_detection"
    result: Any  # The actual computation result
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "operation": self.operation,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalyticsResult":
        """Reconstruct from dictionary."""
        return cls(
            success=data.get("success", False),
            operation=data.get("operation", "unknown"),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
        )


class SchemaAdapter:
    """Normalize heterogeneous data fields to standard schemas."""

    @staticmethod
    def normalize_post_data(raw_data: dict) -> dict:
        """Normalize raw post data from various sources.
        
        Handles:
        - Reddit posts
        - News articles
        - CSV uploads
        - Social media feeds
        - Custom JSON payloads
        
        Returns standardized post schema.
        """
        normalized = {
            "post_id": SchemaAdapter._extract_id(raw_data),
            "title": SchemaAdapter._extract_title(raw_data),
            "content": SchemaAdapter._extract_content(raw_data),
            "timestamp": SchemaAdapter._extract_timestamp(raw_data),
            "source": SchemaAdapter._extract_source(raw_data),
            "url": SchemaAdapter._extract_url(raw_data),
            "metadata": SchemaAdapter._extract_metadata(raw_data),
        }
        
        # Extract engagement metrics
        engagement = SchemaAdapter._extract_engagement(raw_data)
        normalized.update(engagement)
        
        return normalized

    @staticmethod
    def _extract_id(data: dict) -> str:
        """Extract unique identifier from various field names."""
        candidates = ["id", "post_id", "article_id", "url", "link"]
        for field in candidates:
            if field in data and data[field]:
                return str(data[field])
        # Fallback: generate from title + timestamp
        title = data.get("title", "")
        ts = data.get("timestamp", "")
        return f"{title[:20]}_{ts}"[:50]

    @staticmethod
    def _extract_title(data: dict) -> str:
        """Extract title from various field names."""
        candidates = ["title", "headline", "subject", "message", "text"]
        for field in candidates:
            if field in data and data[field]:
                return str(data[field]).strip()[:500]
        return "Untitled"

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Extract content/body from various field names."""
        candidates = ["content", "body", "description", "text", "message", "message"]
        for field in candidates:
            if field in data and data[field]:
                return str(data[field]).strip()[:5000]
        return SchemaAdapter._extract_title(data)

    @staticmethod
    def _extract_timestamp(data: dict) -> datetime:
        """Extract and parse timestamp from various formats."""
        candidates = ["timestamp", "created_at", "published_at", "date", "time"]
        for field in candidates:
            if field in data and data[field]:
                value = data[field]
                try:
                    if isinstance(value, datetime):
                        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
                    if isinstance(value, str):
                        # Try ISO format
                        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                    if isinstance(value, (int, float)):
                        return datetime.fromtimestamp(value, tz=timezone.utc)
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp {field}={value}: {e}")
        return datetime.now(timezone.utc)

    @staticmethod
    def _extract_source(data: dict) -> str:
        """Extract data source."""
        candidates = ["source", "origin", "platform", "type"]
        for field in candidates:
            if field in data and data[field]:
                return str(data[field])
        return "unknown"

    @staticmethod
    def _extract_url(data: dict) -> Optional[str]:
        """Extract URL."""
        candidates = ["url", "link", "uri", "href"]
        for field in candidates:
            if field in data and data[field]:
                return str(data[field])
        return None

    @staticmethod
    def _extract_metadata(data: dict) -> dict:
        """Extract any additional fields as metadata."""
        known_fields = {
            "post_id", "title", "content", "timestamp", "source", "url",
            "likes", "shares", "comments", "views", "retweets", "upvotes",
        }
        metadata = {}
        for key, value in data.items():
            if key not in known_fields:
                try:
                    # Only include JSON-serializable values
                    json.dumps(value)
                    metadata[key] = value
                except (TypeError, ValueError):
                    # Skip non-serializable values
                    pass
        return metadata

    @staticmethod
    def _extract_engagement(data: dict) -> dict:
        """Extract engagement metrics from various field names."""
        engagement = {
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "views": 0,
        }

        # Map common variants
        likes_fields = ["likes", "upvotes", "favourites", "positive_reactions"]
        shares_fields = ["shares", "retweets", "reblogs"]
        comments_fields = ["comments", "replies", "responses", "discussions"]
        views_fields = ["views", "impressions", "reach", "page_views"]

        for field in likes_fields:
            if field in data and data[field]:
                engagement["likes"] = int(data[field])
                break

        for field in shares_fields:
            if field in data and data[field]:
                engagement["shares"] = int(data[field])
                break

        for field in comments_fields:
            if field in data and data[field]:
                engagement["comments"] = int(data[field])
                break

        for field in views_fields:
            if field in data and data[field]:
                engagement["views"] = int(data[field])
                break

        return engagement


class AnalyticsAdapter:
    """Adapter for existing analysis functions.
    
    Wraps functions from:
    - services/alerts/signal_detector
    - services/clustering/narrative_clustering
    - services/prediction/forecaster
    - backend/pipelines/processing
    """

    @staticmethod
    def calculate_virality_score(
        post_data: dict,
        weights: Optional[Dict[str, float]] = None,
    ) -> AnalyticsResult:
        """Calculate virality score for a post.
        
        Args:
            post_data: Normalized post data with engagement metrics
            weights: Custom weight configuration
            
        Returns:
            AnalyticsResult with virality_score
        """
        try:
            # Import here to avoid circular imports
            from backend.pipelines.processing import (
                calculate_virality_score as calc_virality,
                calculate_engagement_total,
                calculate_engagement_velocity,
            )

            # Extract engagement metrics
            shares = post_data.get("shares", 0)
            comments = post_data.get("comments", 0)
            likes = post_data.get("likes", 0)
            timestamp = post_data.get("timestamp")

            # Calculate supporting metrics
            engagement_total = calculate_engagement_total(likes, shares, comments)
            velocity = calculate_engagement_velocity(engagement_total, timestamp)

            # Calculate virality
            virality = calc_virality(shares, comments, likes, velocity)

            return AnalyticsResult(
                success=True,
                operation="virality_score",
                result={
                    "virality_score": float(virality),
                    "engagement_total": float(engagement_total),
                    "engagement_velocity": float(velocity),
                    "post_id": post_data.get("post_id"),
                },
                metadata={"version": "1.0", "model": "weighted_linear"},
            )
        except Exception as e:
            logger.error(f"Virality score calculation failed: {e}", exc_info=True)
            return AnalyticsResult(
                success=False,
                operation="virality_score",
                result=None,
                error=str(e),
            )

    @staticmethod
    def detect_emerging_signals() -> AnalyticsResult:
        """Detect emerging signals from current data.
        
        Returns:
            AnalyticsResult with list of emerging signals
        """
        try:
            import asyncio
            from services.alerts.signal_detector import detect_emerging_signals as detect_signals

            # Run async function
            signals = asyncio.run(detect_signals())

            return AnalyticsResult(
                success=True,
                operation="signal_detection",
                result={
                    "signals": signals or [],
                    "count": len(signals) if signals else 0,
                },
                metadata={"detection_method": "engagement_spike"},
            )
        except Exception as e:
            logger.error(f"Signal detection failed: {e}", exc_info=True)
            return AnalyticsResult(
                success=False,
                operation="signal_detection",
                result=None,
                error=str(e),
            )

    @staticmethod
    def run_clustering(posts: List[dict]) -> AnalyticsResult:
        """Run narrative clustering on posts.
        
        Args:
            posts: List of normalized post data
            
        Returns:
            AnalyticsResult with clustering results
        """
        try:
            import asyncio
            from services.clustering.narrative_clustering import run_clustering

            # Run async function
            clusters = asyncio.run(run_clustering(posts))

            return AnalyticsResult(
                success=True,
                operation="clustering",
                result={
                    "clusters": clusters or [],
                    "count": len(clusters) if clusters else 0,
                },
                metadata={"algorithm": "BERTopic"},
            )
        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)
            return AnalyticsResult(
                success=False,
                operation="clustering",
                result=None,
                error=str(e),
            )

    @staticmethod
    def generate_forecasts() -> AnalyticsResult:
        """Generate engagement forecasts.
        
        Returns:
            AnalyticsResult with forecast data
        """
        try:
            import asyncio
            from services.prediction.forecaster import generate_forecasts

            # Run async function
            forecasts = asyncio.run(generate_forecasts())

            return AnalyticsResult(
                success=True,
                operation="forecasting",
                result={
                    "forecasts": forecasts or [],
                    "count": len(forecasts) if forecasts else 0,
                },
                metadata={"horizon_hours": 48},
            )
        except Exception as e:
            logger.error(f"Forecasting failed: {e}", exc_info=True)
            return AnalyticsResult(
                success=False,
                operation="forecasting",
                result=None,
                error=str(e),
            )


class EngineFactory:
    """Factory for creating processing engines."""

    @staticmethod
    def create_processing_pipeline():
        """Create a full processing pipeline."""
        return AnalyticsAdapter()

    @staticmethod
    def create_schema_adapter():
        """Create a schema adapter."""
        return SchemaAdapter()
