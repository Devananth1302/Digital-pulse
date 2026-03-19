"""Ingestion Processor - Validates and parses incoming data.

Single responsibility: Accept data from real-time or historical sources,
validate format, extract metadata, output to ingested_data topic.

NO data transformation - only validation and structure extraction.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.processors.base_processor import BaseProcessor, ProcessorConfig

logger = logging.getLogger(__name__)


class IngestionProcessor(BaseProcessor):
    """Validates and ingests raw data from various sources."""
    
    async def process_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and parse incoming record.
        
        Args:
            data: Raw data record
            
        Returns:
            Validated record or None
        """
        # Required fields
        required_fields = ['title', 'content', 'timestamp']
        
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate timestamp format
        timestamp_str = data.get('timestamp')
        try:
            if isinstance(timestamp_str, str):
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                dt = timestamp_str
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}. Error: {e}")
        
        # Extract source metadata
        source = data.get('source', 'unknown')
        valid_sources = ['reddit', 'news_api', 'google_news', 'twitter', 'csv_upload', 'historical']
        if source not in valid_sources:
            logger.warning(f"Unknown source: {source}, assuming 'unknown'")
        
        # Build output record (pass-through with added metadata)
        output = {
            **data,  # Include all original fields
            'post_id': data.get('post_id', f"{source}_{data.get('title', '')[:50]}_{timestamp_str}"),
            'source': source,
            'ingested_at': datetime.now(timezone.utc).isoformat(),
            'ingestion_valid': True,
        }
        
        # Validate engagement fields are numeric if present
        engagement_fields = ['likes', 'shares', 'comments', 'retweets', 'upvotes', 'downvotes']
        for field in engagement_fields:
            if field in output and output[field] is not None:
                try:
                    output[field] = int(output[field]) if output[field] else 0
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value for {field}: {output[field]}")
        
        logger.debug(f"Ingestion validated for post_id: {output['post_id']}")
        return output


async def run_ingestion_processor(num_threads: int = 3, timeout_hours: Optional[int] = None):
    """Run ingestion processor.
    
    Args:
        num_threads: Number of processing threads
        timeout_hours: Exit after N hours (None = infinite)
    """
    config = ProcessorConfig(
        name="ingestion",
        input_topic="raw_data",
        output_topic="ingested_data",
        num_threads=num_threads,
        batch_size=50,
    )
    
    processor = IngestionProcessor(config)
    await processor.run(timeout_hours=timeout_hours)


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_ingestion_processor())
