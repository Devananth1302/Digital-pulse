"""Trending News Engine - Windowed top-5 trending extraction.

Single responsibility: Extract top 5 trending items per time window
using weighted formula: volume × velocity × sentiment.

No database writes - output to trending_signals Kafka topic only.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)


class TrendingNewsEngine:
    """Extracts trending news using time windows and weighted scoring."""
    
    def __init__(self, window_hours: int = 1):
        """Initialize trending engine.
        
        Args:
            window_hours: Time window in hours (1, 4, or 24)
        """
        self.window_hours = window_hours
        
        # In-memory buffer: timestamp_bucket → list of records
        self.buffer = defaultdict(list)
        
        # Weights for trending score calculation
        self.volume_weight = 0.3      # 30% - How many posts
        self.velocity_weight = 0.4    # 40% - How fast they're coming
        self.sentiment_weight = 0.3   # 30% - Positive sentiment
    
    def _get_time_bucket(self, timestamp_str: str) -> str:
        """Get bucket key for timestamp.
        
        Args:
            timestamp_str: ISO format timestamp
            
        Returns:
            Bucket key (e.g., "2024-01-15_10:00" for 1-hour buckets)
        """
        try:
            if isinstance(timestamp_str, str):
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                dt = timestamp_str
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Floor to window boundary
            minutes_to_floor = (dt.minute // (self.window_hours * 60)) * (self.window_hours * 60)
            floored = dt.replace(minute=minutes_to_floor, second=0, microsecond=0)
            
            return floored.isoformat()
        except Exception as e:
            logger.warning(f"Could not parse timestamp {timestamp_str}: {e}")
            return datetime.now(timezone.utc).isoformat()
    
    def _calculate_trending_score(
        self,
        volume: float,
        velocity: float,
        sentiment: float,
        max_volume: float = 1.0,
        max_velocity: float = 1.0,
        max_sentiment: float = 1.0
    ) -> float:
        """Calculate weighted trending score.
        
        Weighted formula:
        TrendScore = 0.3 × (volume / max_volume) +
                     0.4 × (velocity / max_velocity) +
                     0.3 × (sentiment / max_sentiment)
        
        Args:
            volume: Count of posts about topic
            velocity: Rate of posts (per hour)
            sentiment: Average sentiment score (0-1)
            max_*: Maximum values for normalization
            
        Returns:
            Trending score (0-1)
        """
        # Avoid division by zero
        normalized_volume = (volume / max_volume) if max_volume > 0 else 0
        normalized_velocity = (velocity / max_velocity) if max_velocity > 0 else 0
        normalized_sentiment = (sentiment / max_sentiment) if max_sentiment > 0 else 0
        
        # Clamp to [0, 1]
        normalized_volume = min(1.0, max(0.0, normalized_volume))
        normalized_velocity = min(1.0, max(0.0, normalized_velocity))
        normalized_sentiment = min(1.0, max(0.0, normalized_sentiment))
        
        score = (
            self.volume_weight * normalized_volume +
            self.velocity_weight * normalized_velocity +
            self.sentiment_weight * normalized_sentiment
        )
        
        return round(score, 4)
    
    def _extract_sentiment_score(self, data: Dict[str, Any]) -> float:
        """Extract sentiment score or calculate from engagement.
        
        Args:
            data: Record with engagement metrics
            
        Returns:
            Sentiment score (0-1, where 1 is very positive)
        """
        # Check if sentiment already computed
        if 'sentiment_score' in data:
            return float(data['sentiment_score'])
        
        # Calculate from virality as proxy for positive sentiment
        # (high engagement usually indicates positive reception)
        virality = data.get('virality_score', 0)
        # Normalize to 0-1 range (assuming max virality is around 1000)
        sentiment = min(1.0, virality / 1000.0)
        
        return round(sentiment, 4)
    
    def add_record_to_window(self, data: Dict[str, Any]):
        """Add record to current time window buffer."""
        bucket = self._get_time_bucket(data.get('timestamp', datetime.now(timezone.utc).isoformat()))
        self.buffer[bucket].append(data)
    
    def get_trending_by_category(
        self,
        time_bucket: str,
        top_k: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get top-K trending items by industry/subtopic per time window.
        
        Args:
            time_bucket: Time bucket to analyze
            top_k: Number of top items per category
            
        Returns:
            Dict mapping category → list of top trending records
        """
        records = self.buffer.get(time_bucket, [])
        
        if not records:
            logger.debug(f"No records in buffer for {time_bucket}")
            return {}
        
        # Group by industry → subtopic
        categories = defaultdict(list)
        for record in records:
            industry = record.get('industry', 'Other')
            subtopic = record.get('subtopic', 'general')
            category_key = f"{industry}::{subtopic}"
            categories[category_key].append(record)
        
        # Calculate trending scores per category
        trending_by_category = {}
        
        for category_key, category_records in categories.items():
            # Count and velocity
            volume = len(category_records)
            velocity = volume / self.window_hours
            
            # Average sentiment
            sentiments = [self._extract_sentiment_score(rec) for rec in category_records]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            
            # Calculate trending scores for each record
            max_virality = max([rec.get('virality_score', 0) for rec in category_records]) if category_records else 1.0
            max_velocity_single = max([rec.get('engagement_velocity', 0) for rec in category_records]) if category_records else 1.0
            
            scored_records = []
            for record in category_records:
                trending_score = self._calculate_trending_score(
                    volume=1,  # Individual contribution
                    velocity=record.get('engagement_velocity', 0),
                    sentiment=self._extract_sentiment_score(record),
                    max_volume=volume,
                    max_velocity=max_velocity_single or 1.0,
                    max_sentiment=1.0,
                )
                
                scored_records.append({
                    **record,
                    'trending_score': trending_score,
                    'category_trending_volume': volume,
                    'category_trending_velocity': velocity,
                    'category_trending_sentiment': avg_sentiment,
                })
            
            # Sort by trending score and take top-K
            scored_records.sort(key=lambda x: x['trending_score'], reverse=True)
            trending_by_category[category_key] = scored_records[:top_k]
        
        return trending_by_category
    
    def flush_window(self, time_bucket: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Flush and score a time window, return top-K results.
        
        Args:
            time_bucket: Window to flush
            top_k: Number of top items to return
            
        Returns:
            List of top-K trending records across all categories
        """
        trending_by_category = self.get_trending_by_category(time_bucket, top_k=top_k)
        
        # Flatten and sort globally by trending score
        all_trending = []
        for category_key, records in trending_by_category.items():
            all_trending.extend(records)
        
        all_trending.sort(key=lambda x: x['trending_score'], reverse=True)
        
        # Remove buffer to free memory
        if time_bucket in self.buffer:
            del self.buffer[time_bucket]
        
        return all_trending[:top_k]


# Singleton instance
_trending_engine = None


def get_trending_engine(window_hours: int = 1) -> TrendingNewsEngine:
    """Get or create trending engine."""
    global _trending_engine
    if _trending_engine is None:
        _trending_engine = TrendingNewsEngine(window_hours=window_hours)
    return _trending_engine


if __name__ == "__main__":
    # Test the trending engine
    logging.basicConfig(level=logging.INFO)
    
    engine = get_trending_engine(window_hours=1)
    
    # Simulate records
    test_records = [
        {
            "post_id": f"post_{i}",
            "title": f"Test post {i}",
            "content": "Test content",
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=i*5)).isoformat(),
            "industry": "Technology",
            "subtopic": "artificial_intelligence",
            "virality_score": 100 + i*10,
            "engagement_velocity": 5.0 + i*0.5,
        }
        for i in range(20)
    ]
    
    for record in test_records:
        engine.add_record_to_window(record)
    
    now_bucket = engine._get_time_bucket(datetime.now(timezone.utc).isoformat())
    top_trending = engine.flush_window(now_bucket, top_k=5)
    
    print(f"\nTop 5 Trending News ({len(top_trending)} found):")
    for i, record in enumerate(top_trending, 1):
        print(f"{i}. {record['title']}")
        print(f"   Trending Score: {record['trending_score']}")
        print(f"   Industry: {record['industry']} | Subtopic: {record['subtopic']}")
        print()
