"""Modular Streaming Processors - Kafka-based microservice pipeline.

Each processor is responsible for a single transformation step:

1. processor_ingestion - Validates and parses incoming data
2. processor_normalization - Standardizes field names and types
3. processor_features - Calculates virality scores and engagement metrics
4. processor_clustering - Hierarchical two-tier classification
5. processor_trending - Extracts and publishes top-K trending signals
6. historical_loader - Backfills historical data from files

Architecture: raw_data → ingested → normalized → featured → clustered → trending_signals

All processors are stateless microservices communicating via Kafka topics.
Horizontal scaling: Deploy N copies of each processor, Kafka handles distribution.
"""

import logging

# Import main processors for easy access
from backend.processors.processor_ingestion import run_ingestion_processor
from backend.processors.processor_normalization import run_normalization_processor
from backend.processors.processor_features import run_features_processor
from backend.processors.processor_clustering import run_clustering_processor
from backend.processors.processor_trending import run_trending_processor
from backend.processors.historical_loader import backfill_historical

# Import engines
from backend.processors.clustering_engine import get_clustering_engine
from backend.processors.trending_engine import get_trending_engine

logger = logging.getLogger(__name__)

__all__ = [
    'run_ingestion_processor',
    'run_normalization_processor',
    'run_features_processor',
    'run_clustering_processor',
    'run_trending_processor',
    'backfill_historical',
    'get_clustering_engine',
    'get_trending_engine',
]
