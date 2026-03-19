"""Feature Engineering Processor - Calculates engagement metrics and virality scores.

Single responsibility: Calculate all numerical features needed by downstream
processors (virality score, velocity, time decay, momentum).
"""

import logging
import math
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.processors.base_processor import BaseProcessor, ProcessorConfig
from config.settings import settings

logger = logging.getLogger(__name__)


class FeatureEngineeringProcessor(BaseProcessor):
    """Calculates engagement features and virality metrics."""
    
    @staticmethod
    def calculate_engagement_total(likes: int, shares: int, comments: int) -> float:
        """Total engagement metric."""
        return float(likes + shares + comments)
    
    @staticmethod
    def calculate_time_decay(timestamp_str: str, half_life_hours: float = 24.0) -> float:
        """Exponential time decay: posts lose relevance over time."""
        try:
            if isinstance(timestamp_str, str):
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                ts = timestamp_str
            
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Could not parse timestamp: {e}")
            return 0.5
        
        now = datetime.now(timezone.utc)
        hours_old = max((now - ts).total_seconds() / 3600.0, 0.0)
        return math.exp(-0.693 * hours_old / half_life_hours)
    
    @staticmethod
    def calculate_engagement_velocity(engagement_total: float, timestamp_str: str) -> float:
        """Engagement per hour since posting."""
        try:
            if isinstance(timestamp_str, str):
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                ts = timestamp_str
            
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Could not parse timestamp: {e}")
            return engagement_total / 2.0
        
        now = datetime.now(timezone.utc)
        hours = max((now - ts).total_seconds() / 3600.0, 0.1)
        return engagement_total / hours
    
    @staticmethod
    def calculate_virality_score(shares: int, comments: int, likes: int, velocity: float) -> float:
        """Weighted virality score using configured weights."""
        score = (
            shares * settings.VIRALITY_WEIGHT_SHARES
            + comments * settings.VIRALITY_WEIGHT_COMMENTS
            + likes * settings.VIRALITY_WEIGHT_LIKES
            + velocity * settings.VIRALITY_WEIGHT_VELOCITY
        )
        return round(score, 4)
    
    async def process_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Calculate all engagement features.
        
        Args:
            data: Normalized record with engagement metrics
            
        Returns:
            Record with calculated features
        """
        # Extract engagement
        likes = data.get('likes', 0) or 0
        shares = data.get('shares', 0) or 0
        comments = data.get('comments', 0) or 0
        timestamp = data.get('timestamp')
        
        # Calculate features
        engagement_total = self.calculate_engagement_total(likes, shares, comments)
        time_decay = self.calculate_time_decay(timestamp)
        velocity = self.calculate_engagement_velocity(engagement_total, timestamp)
        virality_score = self.calculate_virality_score(shares, comments, likes, velocity)
        
        # Calculate momentum (if we have previous velocity stored)
        previous_velocity = data.get('previous_velocity')
        momentum = 0.0
        momentum_label = "stable"
        
        if previous_velocity is not None and previous_velocity > 0:
            momentum = (velocity - previous_velocity) / previous_velocity
            if momentum > 0.5:
                momentum_label = "accelerating"
            elif momentum > 0.1:
                momentum_label = "growing"
            elif momentum < -0.3:
                momentum_label = "declining"
            elif momentum < -0.1:
                momentum_label = "slowing"
        
        # Engagement breakdown (for analysis)
        s = shares * settings.VIRALITY_WEIGHT_SHARES
        c = comments * settings.VIRALITY_WEIGHT_COMMENTS
        l = likes * settings.VIRALITY_WEIGHT_LIKES
        v = velocity * settings.VIRALITY_WEIGHT_VELOCITY
        total = s + c + l + v
        
        s_pct = (s / total * 100) if total > 0 else 25
        c_pct = (c / total * 100) if total > 0 else 25
        l_pct = (l / total * 100) if total > 0 else 25
        v_pct = (v / total * 100) if total > 0 else 25
        
        # Add calculated features
        result = {
            **data,  # Include all original fields
            
            # Engagement metrics
            'engagement_total': round(engagement_total, 2),
            'engagement_velocity': round(velocity, 2),
            'engagement_per_hour': round(velocity, 2),
            
            # Decay and time-based features
            'time_decay_factor': round(time_decay, 4),
            
            # Virality score
            'virality_score': virality_score,
            
            # Momentum tracking
            'momentum': round(momentum, 4),
            'momentum_label': momentum_label,
            'previous_velocity': velocity,  # Store for next window
            
            # Component breakdown
            'virality_shares_component': round(s, 4),
            'virality_comments_component': round(c, 4),
            'virality_likes_component': round(l, 4),
            'virality_velocity_component': round(v, 4),
            'virality_shares_pct': round(s_pct, 2),
            'virality_comments_pct': round(c_pct, 2),
            'virality_likes_pct': round(l_pct, 2),
            'virality_velocity_pct': round(v_pct, 2),
            
            # Feature engineering timestamp
            'features_calculated_at': datetime.now(timezone.utc).isoformat(),
        }
        
        logger.debug(f"Features calculated - post_id: {result['post_id']}, virality: {virality_score}")
        return result


async def run_features_processor(num_threads: int = 3, timeout_hours: Optional[int] = None):
    """Run feature engineering processor.
    
    Args:
        num_threads: Number of processing threads
        timeout_hours: Exit after N hours (None = infinite)
    """
    config = ProcessorConfig(
        name="features",
        input_topic="normalized_data",
        output_topic="featured_data",
        num_threads=num_threads,
        batch_size=50,
    )
    
    processor = FeatureEngineeringProcessor(config)
    await processor.run(timeout_hours=timeout_hours)


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_features_processor())
