"""Trending Processor - Extracts top-K trending news per window.

Single responsibility: Buffer clustered records in time windows,
calculate trending scores, extract top-5 per category, output to
trending_signals topic.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from backend.processors.base_processor import BaseProcessor, ProcessorConfig
from backend.processors.trending_engine import get_trending_engine

logger = logging.getLogger(__name__)


class TrendingProcessor(BaseProcessor):
    """Extracts and publishes top-K trending news per time window."""
    
    def __init__(self, config: ProcessorConfig, window_hours: int = 1, top_k: int = 5):
        """Initialize trending processor.
        
        Args:
            config: Processor configuration
            window_hours: Time window in hours (1, 4, or 24)
            top_k: Number of top items to extract per category
        """
        super().__init__(config)
        self.window_hours = window_hours
        self.top_k = top_k
        self.trending_engine = get_trending_engine(window_hours=window_hours)
        
        # Background task for window flushing
        self.flush_task = None
        
        logger.info(f"Trending processor initialized: {window_hours}h window, top-{top_k}")
    
    async def process_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Buffer record in current time window.
        
        Per the microservice pattern, this processor doesn't output
        in real-time. Instead, it buffers records and flushes windows
        periodically via a background task.
        
        Args:
            data: Clustered record
            
        Returns:
            None (buffered internally, not forwarded)
        """
        self.trending_engine.add_record_to_window(data)
        return None  # Don't forward individual records
    
    async def _flush_periodic(self):
        """Periodically flush completed time windows."""
        while self.running:
            try:
                # Wait for window duration
                await asyncio.sleep(self.window_hours * 3600)
                
                # Get the bucket that just completed
                now = datetime.now(timezone.utc)
                completed_bucket = (now - timedelta(hours=self.window_hours)).isoformat()
                
                # Flush and get top-K
                top_trending = self.trending_engine.flush_window(
                    completed_bucket,
                    top_k=self.top_k
                )
                
                if not top_trending:
                    logger.debug(f"No trending data for window ending at {completed_bucket}")
                    continue
                
                # Output as trending signals
                for record in top_trending:
                    signal = {
                        "signal_type": "trending",
                        "window_hours": self.window_hours,
                        "window_end": completed_bucket,
                        "rank": top_trending.index(record) + 1,
                        "trending_score": record.get('trending_score'),
                        "post_id": record.get('post_id'),
                        "title": record.get('title'),
                        "industry": record.get('industry'),
                        "subtopic": record.get('subtopic'),
                        "virality_score": record.get('virality_score'),
                        "engagement_velocity": record.get('engagement_velocity'),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "record": record,  # Full record for downstream
                    }
                    
                    # Publish trending signal
                    self.producer.produce(
                        self.config.output_topic,
                        value=json.dumps(signal).encode('utf-8'),
                        key=f"{record.get('industry')}_{record.get('subtopic')}".encode('utf-8'),
                        callback=self._delivery_report
                    )
                    
                    logger.info(
                        f"Trending signal published: rank={signal['rank']}, "
                        f"industry={signal['industry']}, "
                        f"trending_score={signal['trending_score']}"
                    )
                
                logger.info(f"Flushed window: {len(top_trending)} trending items")
                self.producer.flush()
                
            except asyncio.CancelledError:
                logger.info("Flush task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}", exc_info=True)
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def run(self, timeout_hours: Optional[int] = None):
        """Run processor with periodic window flushing.
        
        Args:
            timeout_hours: Exit after N hours (None = infinite)
        """
        self.running = True
        logger.info(f"Starting trending processor (window: {self.window_hours}h)...")
        
        # Start background flush task
        self.flush_task = asyncio.create_task(self._flush_periodic())
        
        try:
            await super().run(timeout_hours=timeout_hours)
        finally:
            if self.flush_task and not self.flush_task.done():
                self.flush_task.cancel()
                try:
                    await self.flush_task
                except asyncio.CancelledError:
                    pass
    
    def stop(self):
        """Stop processor and cancel flush task."""
        if self.flush_task and not self.flush_task.done():
            self.flush_task.cancel()
        
        super().stop()


async def run_trending_processor(
    window_hours: int = 1,
    top_k: int = 5,
    num_threads: int = 3,
    timeout_hours: Optional[int] = None
):
    """Run trending processor.
    
    Args:
        window_hours: Time window in hours
        top_k: Number of top items per window
        num_threads: Number of processing threads
        timeout_hours: Exit after N hours (None = infinite)
    """
    config = ProcessorConfig(
        name="trending",
        input_topic="clustered_data",
        output_topic="trending_signals",
        num_threads=num_threads,
        batch_size=100,  # Larger batches for trending
    )
    
    processor = TrendingProcessor(config, window_hours=window_hours, top_k=top_k)
    await processor.run(timeout_hours=timeout_hours)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run with 1-hour windows and top-5
    asyncio.run(run_trending_processor(window_hours=1, top_k=5))
