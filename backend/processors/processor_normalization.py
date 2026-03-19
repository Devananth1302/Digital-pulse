"""Normalization Processor - Standardizes field names and types across sources.

Single responsibility: Normalize heterogeneous data from different sources
into a consistent schema. Handle field name variations (upvotes→likes, etc.)
and type conversions.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.processors.base_processor import BaseProcessor, ProcessorConfig

logger = logging.getLogger(__name__)


class NormalizationProcessor(BaseProcessor):
    """Normalizes heterogeneous data into standard schema."""
    
    # Field mappings: source_field → standard_field
    ENGAGEMENT_FIELD_MAPPINGS = {
        'likes': 'likes',
        'thumbs_up': 'likes',
        'upvotes': 'likes',
        'reactions': 'likes',
        
        'shares': 'shares',
        'reblogs': 'shares',
        'reposts': 'shares',
        'forwards': 'shares',
        
        'comments': 'comments',
        'replies': 'comments',
        'responses': 'comments',
        
        'retweets': 'shares',  # Twitter special case
        'downvotes': 'negative_engagement',
        'thumbs_down': 'negative_engagement',
    }
    
    TITLE_FIELD_MAPPINGS = {
        'title': 'title',
        'headline': 'title',
        'subject': 'title',
        'subject_line': 'title',
    }
    
    CONTENT_FIELD_MAPPINGS = {
        'content': 'content',
        'body': 'content',
        'text': 'content',
        'message': 'content',
        'description': 'content',
    }
    
    def _normalize_field_name(self, data: Dict[str, Any], mapping: Dict) -> Optional[Any]:
        """Find field value using mapping, return first match."""
        for source_name, standard_name in mapping.items():
            if source_name in data and data[source_name] is not None:
                return data[source_name], source_name
        return None, None
    
    def _normalize_engagement(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Extract and normalize engagement metrics."""
        engagement = {
            'likes': 0,
            'shares': 0,
            'comments': 0,
            'negative_engagement': 0,
        }
        
        for field, standard in self.ENGAGEMENT_FIELD_MAPPINGS.items():
            if field in data and data[field] is not None:
                try:
                    value = int(data[field]) if data[field] else 0
                    engagement[standard] = max(engagement[standard], value)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert {field}={data[field]} to int")
        
        return engagement
    
    def _normalize_text_field(self, data: Dict[str, Any], mapping: Dict, max_length: int = 1000) -> str:
        """Extract and normalize text field."""
        value, source_field = self._normalize_field_name(data, mapping)
        
        if value is None:
            return ""
        
        # Convert to string and truncate
        text = str(value).strip()
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    async def process_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize heterogeneous data into standard schema.
        
        Args:
            data: Ingested record (may have variant field names)
            
        Returns:
            Normalized record with standard field names
        """
        # Extract standard fields
        title = self._normalize_text_field(data, self.TITLE_FIELD_MAPPINGS, max_length=500)
        content = self._normalize_text_field(data, self.CONTENT_FIELD_MAPPINGS, max_length=5000)
        
        if not title and not content:
            raise ValueError("Record must have either title or content")
        
        # Normalize engagement
        engagement = self._normalize_engagement(data)
        
        # Extract timestamp
        timestamp = data.get('timestamp')
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                dt = timestamp
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            timestamp_iso = dt.isoformat()
        except Exception as e:
            logger.warning(f"Could not parse timestamp {timestamp}: {e}")
            timestamp_iso = datetime.now(timezone.utc).isoformat()
        
        # Build normalized record
        normalized = {
            # Core identifiers
            'post_id': data.get('post_id'),
            'source': data.get('source', 'unknown'),
            
            # Content
            'title': title,
            'content': content,
            'timestamp': timestamp_iso,
            
            # Engagement (standardized)
            'likes': engagement['likes'],
            'shares': engagement['shares'],
            'comments': engagement['comments'],
            'negative_engagement': engagement['negative_engagement'],
            
            # Metadata
            'author': data.get('author', 'unknown'),
            'url': data.get('url', ''),
            
            # Tracking
            'ingested_at': data.get('ingested_at'),
            'normalized_at': datetime.now(timezone.utc).isoformat(),
            
            # Preserve extra fields (may contain domain-specific data)
            **{k: v for k, v in data.items() 
               if k not in ['title', 'content', 'timestamp', 'likes', 'shares', 
                           'comments', 'author', 'url', 'post_id', 'source', 'ingested_at']
               and not any(k in mapping for mapping in [self.TITLE_FIELD_MAPPINGS, 
                          self.CONTENT_FIELD_MAPPINGS, self.ENGAGEMENT_FIELD_MAPPINGS])}
        }
        
        logger.debug(f"Normalized post_id: {normalized['post_id']}")
        return normalized


async def run_normalization_processor(num_threads: int = 3, timeout_hours: Optional[int] = None):
    """Run normalization processor.
    
    Args:
        num_threads: Number of processing threads
        timeout_hours: Exit after N hours (None = infinite)
    """
    config = ProcessorConfig(
        name="normalization",
        input_topic="ingested_data",
        output_topic="normalized_data",
        num_threads=num_threads,
        batch_size=50,
    )
    
    processor = NormalizationProcessor(config)
    await processor.run(timeout_hours=timeout_hours)


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_normalization_processor())
