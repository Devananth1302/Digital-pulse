"""Clustering Processor - Two-tier hierarchical classification.

Single responsibility: Classify records into industries (Tier 1) and 
detect sub-topics (Tier 2) using the HierarchicalClusteringEngine.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.processors.base_processor import BaseProcessor, ProcessorConfig
from backend.processors.clustering_engine import get_clustering_engine

logger = logging.getLogger(__name__)


class ClusteringProcessor(BaseProcessor):
    """Performs hierarchical two-tier clustering."""
    
    def __init__(self, config: ProcessorConfig):
        """Initialize with clustering engine."""
        super().__init__(config)
        self.clustering_engine = get_clustering_engine()
        logger.info("Clustering engine initialized")
    
    async def process_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply hierarchical clustering to record.
        
        Args:
            data: Featured record
            
        Returns:
            Clustered record with industry and subtopic labels
        """
        # Apply clustering
        try:
            clustered = self.clustering_engine.cluster_record(data)
            
            logger.debug(
                f"Clustered post_id={clustered['post_id']}, "
                f"industry={clustered['industry']}, "
                f"subtopic={clustered['subtopic']}"
            )
            
            return clustered
        
        except Exception as e:
            logger.error(f"Clustering error: {e}", exc_info=True)
            raise


async def run_clustering_processor(num_threads: int = 3, timeout_hours: Optional[int] = None):
    """Run clustering processor.
    
    Args:
        num_threads: Number of processing threads
        timeout_hours: Exit after N hours (None = infinite)
    """
    config = ProcessorConfig(
        name="clustering",
        input_topic="featured_data",
        output_topic="clustered_data",
        num_threads=num_threads,
        batch_size=50,
    )
    
    processor = ClusteringProcessor(config)
    await processor.run(timeout_hours=timeout_hours)


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_clustering_processor())
