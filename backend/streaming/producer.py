"""Kafka Producer for ingesting data streams.

Responsibilities:
1. Ingest structured (CSV) and semi-structured (JSON) data
2. Normalize data using SchemaAdapter
3. Publish to 'raw_data' topic
4. Handle failures gracefully with retries
5. Support batch and streaming mode
"""

import logging
import json
import csv
import asyncio
from typing import Optional, Callable, Any, List, Dict
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from confluent_kafka import Producer, KafkaError
except ImportError:
    Producer = None
    KafkaError = None

from config.kafka_settings import get_kafka_config
from backend.streaming.circuit_breaker import create_kafka_circuit_breaker, CircuitState
from backend.streaming.serialization import serialize_message, KafkaMessage, MessageValidator
from backend.adapters.analytics_adapter import SchemaAdapter

logger = logging.getLogger(__name__)


@dataclass
class ProducerStats:
    """Statistics for producer."""
    messages_sent: int = 0
    messages_failed: int = 0
    messages_queued: int = 0
    bytes_sent: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> dict:
        return {
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed,
            "messages_queued": self.messages_queued,
            "bytes_sent": self.bytes_sent,
            "error_count": len(self.errors),
        }


class KafkaProducerWrapper:
    """Robustly produces messages to Kafka with circuit breaker protection."""

    def __init__(
        self,
        topic: str = "raw_data",
        enable_circuit_breaker: bool = True,
        fallback_handler: Optional[Callable] = None,
    ):
        """Initialize producer.
        
        Args:
            topic: Target topic name
            enable_circuit_breaker: Enable circuit breaker pattern
            fallback_handler: Callback for messages when Kafka unavailable
        """
        self.topic = topic
        self.enable_circuit_breaker = enable_circuit_breaker
        self.fallback_handler = fallback_handler
        self.stats = ProducerStats()

        # Load configuration
        self.config = get_kafka_config()
        self.producer_config = self.config.get_producer_config()

        # Initialize producer
        self.producer = None
        self._init_producer()

        # Circuit breaker
        if enable_circuit_breaker:
            self.circuit_breaker = create_kafka_circuit_breaker(
                name=f"producer_{topic}",
                failure_threshold=self.config.circuit_breaker.failure_threshold,
                min_requests=self.config.circuit_breaker.min_requests,
                timeout_seconds=self.config.circuit_breaker.timeout_seconds,
            )
        else:
            self.circuit_breaker = None

    def _init_producer(self):
        """Initialize Kafka producer."""
        if Producer is None:
            logger.warning("confluent-kafka not installed, producer will fallback to local storage")
            return

        try:
            self.producer = Producer(
                self.producer_config,
                logger=logging.getLogger("kafka"),
            )
            logger.info(f"Kafka Producer initialized for topic: {self.topic}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None

    def produce(self, data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """Produce a single message.
        
        Args:
            data: Message data (will be normalized)
            key: Optional key for partitioning
            
        Returns:
            True if queued/sent, False if failed
        """
        # Normalize data using schema adapter
        try:
            normalized = SchemaAdapter.normalize_post_data(data)
        except Exception as e:
            logger.error(f"Data normalization failed: {e}")
            self.stats.messages_failed += 1
            self.stats.errors.append(f"normalization: {str(e)}")
            return False

        # Validate schema
        valid, error_msg = MessageValidator.validate_raw_data(normalized)
        if not valid:
            logger.error(f"Schema validation failed: {error_msg}")
            self.stats.messages_failed += 1
            self.stats.errors.append(f"validation: {error_msg}")
            return False

        # Serialize message
        try:
            message = KafkaMessage(
                key=key or str(normalized.get("post_id")),
                value=normalized,
            )
            serialized = serialize_message(message, format_type=self.config.serialization.format)
        except Exception as e:
            logger.error(f"Message serialization failed: {e}")
            self.stats.messages_failed += 1
            self.stats.errors.append(f"serialization: {str(e)}")
            return False

        # Produce to Kafka
        if self.producer:
            def on_delivery(err, msg):
                if err:
                    logger.error(f"Message delivery failed: {err}")
                    self.stats.messages_failed += 1
                    if self.fallback_handler:
                        self.fallback_handler(normalized)
                else:
                    self.stats.messages_sent += 1
                    logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

            try:
                if self.circuit_breaker:
                    success, result = self.circuit_breaker.call(
                        self.producer.produce,
                        self.topic,
                        value=serialized,
                        key=message.key.encode("utf-8") if message.key else None,
                        on_delivery=on_delivery,
                    )
                    if not success:
                        logger.warning(f"Circuit breaker blocked produce (circuit state: {self.circuit_breaker.state})")
                        if self.fallback_handler:
                            self.fallback_handler(normalized)
                        self.stats.messages_queued += 1
                        return True  # Queued for fallback
                else:
                    self.producer.produce(
                        self.topic,
                        value=serialized,
                        key=message.key.encode("utf-8") if message.key else None,
                        on_delivery=on_delivery,
                    )

                self.stats.messages_queued += 1
                self.producer.flush(timeout=1)
                return True

            except Exception as e:
                logger.error(f"Produce failed: {e}")
                self.stats.messages_failed += 1
                self.stats.errors.append(f"produce: {str(e)}")
                if self.fallback_handler:
                    self.fallback_handler(normalized)
                return False
        else:
            # No Kafka producer, use fallback
            if self.fallback_handler:
                self.fallback_handler(normalized)
            self.stats.messages_queued += 1
            return True

    def produce_batch(self, data_list: List[Dict[str, Any]]) -> tuple[int, int]:
        """Produce multiple messages.
        
        Args:
            data_list: List of message data
            
        Returns:
            (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        for item in data_list:
            if self.produce(item):
                successful += 1
            else:
                failed += 1

        logger.info(f"Batch produce: {successful} successful, {failed} failed")
        return successful, failed

    def produce_from_csv(self, csv_path: str, key_field: Optional[str] = None) -> tuple[int, int]:
        """Ingest data from CSV file.
        
        Args:
            csv_path: Path to CSV file
            key_field: Field to use as message key
            
        Returns:
            (successful_count, failed_count)
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return 0, 0

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                total = 0
                successful = 0
                failed = 0

                for row in reader:
                    total += 1
                    key = row.get(key_field) if key_field else None
                    if self.produce(row, key=key):
                        successful += 1
                    else:
                        failed += 1

                logger.info(f"CSV ingestion complete: {total} rows, {successful} sent, {failed} failed")
                return successful, failed

        except Exception as e:
            logger.error(f"CSV ingestion failed: {e}", exc_info=True)
            return 0, 0

    def produce_from_json(self, json_path: str) -> tuple[int, int]:
        """Ingest data from JSON file.
        
        Args:
            json_path: Path to JSON file or JSONL file
            
        Returns:
            (successful_count, failed_count)
        """
        json_path = Path(json_path)
        if not json_path.exists():
            logger.error(f"JSON file not found: {json_path}")
            return 0, 0

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read()

            successful = 0
            failed = 0

            # Try JSONL first
            if json_path.suffix == ".jsonl":
                for line in content.split('\n'):
                    if line.strip():
                        try:
                            row = json.loads(line)
                            if self.produce(row):
                                successful += 1
                            else:
                                failed += 1
                        except json.JSONDecodeError:
                            failed += 1
            else:
                # Try JSON array
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for row in data:
                            if self.produce(row):
                                successful += 1
                            else:
                                failed += 1
                    else:
                        if self.produce(data):
                            successful += 1
                        else:
                            failed += 1
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}")
                    return 0, 0

            logger.info(f"JSON ingestion complete: {successful} sent, {failed} failed")
            return successful, failed

        except Exception as e:
            logger.error(f"JSON ingestion failed: {e}", exc_info=True)
            return 0, 0

    def close(self, timeout_ms: int = 10000):
        """Close producer and flush pending messages."""
        if self.producer:
            try:
                self.producer.flush(timeout_ms // 1000)
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")

    def get_stats(self) -> dict:
        """Get producer statistics."""
        return self.stats.to_dict()

    def get_circuit_breaker_status(self) -> Optional[dict]:
        """Get circuit breaker status."""
        if self.circuit_breaker:
            return self.circuit_breaker.get_metrics()
        return None


def create_producer(
    topic: str = "raw_data",
    enable_circuit_breaker: bool = True,
    fallback_handler: Optional[Callable] = None,
) -> KafkaProducerWrapper:
    """Factory function to create a producer."""
    return KafkaProducerWrapper(
        topic=topic,
        enable_circuit_breaker=enable_circuit_breaker,
        fallback_handler=fallback_handler,
    )
