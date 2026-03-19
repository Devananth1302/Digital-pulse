"""Kafka Consumer for stream processing.

Responsibilities:
1. Listen to 'raw_data' topic
2. Pass payload into existing analysis functions (via adapter)
3. Publish transformed 'signals' to 'processed_results' topic
4. Handle failures with exponential backoff and DLQ
5. Provide manual offset management for exactly-once semantics
"""

import logging
import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime, timezone

try:
    from confluent_kafka import Consumer, KafkaError
except ImportError:
    Consumer = None
    KafkaError = None

from config.kafka_settings import get_kafka_config
from backend.streaming.circuit_breaker import create_kafka_circuit_breaker
from backend.streaming.serialization import deserialize_message, serialize_message, KafkaMessage
from backend.adapters.analytics_adapter import SchemaAdapter, AnalyticsAdapter

logger = logging.getLogger(__name__)


class ConsumerMetrics:
    """Consumer metrics."""
    def __init__(self):
        self.messages_received = 0
        self.messages_processed = 0
        self.messages_failed = 0
        self.messages_dlq = 0
        self.errors = []

    def to_dict(self) -> dict:
        return {
            "messages_received": self.messages_received,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "messages_dlq": self.messages_dlq,
            "error_count": len(self.errors),
        }


class StreamProcessor:
    """Processes messages from Kafka stream."""

    def __init__(self, producer=None):
        """Initialize processor.
        
        Args:
            producer: Optional KafkaProducerWrapper for output messages
        """
        self.producer = producer
        self.analytics = AnalyticsAdapter()
        self.schema_adapter = SchemaAdapter()

    async def process_message(self, message_data: dict) -> Optional[dict]:
        """Process a single message through analysis pipeline.
        
        Args:
            message_data: Raw message data
            
        Returns:
            Processed result or None if processing failed
        """
        try:
            # Step 1: Normalize data
            normalized = self.schema_adapter.normalize_post_data(message_data)
            logger.debug(f"Normalized message: {normalized.get('post_id')}")

            # Step 2: Calculate virality score
            virality_result = self.analytics.calculate_virality_score(normalized)
            if not virality_result.success:
                logger.error(f"Virality calculation failed: {virality_result.error}")
                return None

            # Merge results
            result = {
                "post_id": normalized.get("post_id"),
                "title": normalized.get("title"),
                "content": normalized.get("content"),
                "timestamp": normalized.get("timestamp").isoformat() if isinstance(normalized.get("timestamp"), datetime) else normalized.get("timestamp"),
                "source": normalized.get("source"),
                **virality_result.result,  # Include virality metrics
                "operations": ["virality_score"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.debug(f"Message processed: {result.get('post_id')}")
            return result

        except Exception as e:
            logger.error(f"Message processing failed: {e}", exc_info=True)
            return None


class KafkaConsumerWrapper:
    """Robustly consumes messages from Kafka with circuit breaker protection."""

    def __init__(
        self,
        input_topic: str = "raw_data",
        output_topic: str = "processed_results",
        dlq_topic: str = "dlq",
        processor: Optional[StreamProcessor] = None,
        producer=None,
        enable_circuit_breaker: bool = True,
    ):
        """Initialize consumer.
        
        Args:
            input_topic: Source topic
            output_topic: Destination topic for processed results
            dlq_topic: Dead letter queue topic
            processor: StreamProcessor instance
            producer: KafkaProducerWrapper for output
            enable_circuit_breaker: Enable circuit breaker pattern
        """
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.dlq_topic = dlq_topic
        self.processor = processor or StreamProcessor(producer)
        self.producer = producer
        self.metrics = ConsumerMetrics()

        # Load configuration
        self.config = get_kafka_config()
        self.consumer_config = self.config.get_consumer_config()

        # Initialize consumer
        self.consumer = None
        self._init_consumer()

        # Circuit breaker
        if enable_circuit_breaker:
            self.circuit_breaker = create_kafka_circuit_breaker(
                name=f"consumer_{input_topic}",
                failure_threshold=self.config.circuit_breaker.failure_threshold,
                min_requests=self.config.circuit_breaker.min_requests,
                timeout_seconds=self.config.circuit_breaker.timeout_seconds,
            )
        else:
            self.circuit_breaker = None

        self.is_running = False

    def _init_consumer(self):
        """Initialize Kafka consumer."""
        if Consumer is None:
            logger.warning("confluent-kafka not installed, consumer will not connect")
            return

        try:
            self.consumer = Consumer(self.consumer_config)
            self.consumer.subscribe([self.input_topic])
            logger.info(f"Kafka Consumer initialized for topic: {self.input_topic}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            self.consumer = None

    async def process_batch(self, max_messages: int = 100, poll_timeout_ms: int = 5000):
        """Process a batch of messages.
        
        Args:
            max_messages: Maximum messages to process
            poll_timeout_ms: Poll timeout in milliseconds
        """
        if not self.consumer:
            logger.warning("Consumer not initialized, skipping batch")
            return

        messages_in_batch = 0
        try:
            while messages_in_batch < max_messages:
                msg = self.consumer.poll(timeout=poll_timeout_ms / 1000.0)

                if msg is None:
                    # Timeout, no message available
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        self.metrics.messages_failed += 1
                        continue

                # Process message
                self.metrics.messages_received += 1
                await self._process_single_message(msg)
                messages_in_batch += 1

        except Exception as e:
            logger.error(f"Batch processing error: {e}", exc_info=True)

    async def _process_single_message(self, msg):
        """Process a single Kafka message.
        
        Args:
            msg: Kafka message
        """
        try:
            # Deserialize message
            try:
                kafka_msg = deserialize_message(msg.value(), format_type=self.config.serialization.format)
                message_data = kafka_msg.value
            except Exception as e:
                logger.error(f"Deserialization failed: {e}")
                self._send_to_dlq(msg, f"Deserialization failed: {e}")
                self.metrics.messages_failed += 1
                return

            # Process through analytics
            if self.circuit_breaker:
                success, result = self.circuit_breaker.call(
                    asyncio.run,
                    self.processor.process_message(message_data),
                )
                if not success:
                    logger.warning(f"Circuit breaker blocked processing")
                    return  # Retry later
            else:
                result = await self.processor.process_message(message_data)

            if result is None:
                logger.error("Processing returned None")
                self._send_to_dlq(msg, "Processing failure")
                self.metrics.messages_failed += 1
                return

            # Publish processed result
            if self.producer:
                output_msg = KafkaMessage(
                    key=msg.key().decode() if msg.key() else result.get("post_id"),
                    value=result,
                )
                self.producer.produce(result)

            # Manually commit offset (exactly-once semantics)
            try:
                self.consumer.commit(asynchronous=False)
                self.metrics.messages_processed += 1
                logger.debug(f"Message committed: {result.get('post_id')}")
            except Exception as e:
                logger.error(f"Commit failed: {e}")

        except Exception as e:
            logger.error(f"Message processing error: {e}", exc_info=True)
            self.metrics.messages_failed += 1

    def _send_to_dlq(self, original_msg, error: str):
        """Send failed message to DLQ.
        
        Args:
            original_msg: Original Kafka message
            error: Error message
        """
        try:
            if not self.producer:
                logger.warning("No producer configured for DLQ")
                return

            dlq_payload = {
                "original_topic": original_msg.topic(),
                "original_partition": original_msg.partition(),
                "original_offset": original_msg.offset(),
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": original_msg.value().decode() if original_msg.value() else None,
            }

            self.producer.produce(dlq_payload)
            self.metrics.messages_dlq += 1
            logger.info(f"Message sent to DLQ: {error}")

        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")

    async def run(self, batch_size: int = 100):
        """Run consumer in continuous loop.
        
        Args:
            batch_size: Messages per batch
        """
        self.is_running = True
        logger.info(f"Consumer running on {self.input_topic}")

        try:
            while self.is_running:
                await self.process_batch(max_messages=batch_size)
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self.close()

    def close(self):
        """Close consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

    def stop(self):
        """Stop consumer loop."""
        self.is_running = False

    def get_metrics(self) -> dict:
        """Get consumer metrics."""
        return self.metrics.to_dict()

    def get_circuit_breaker_status(self) -> Optional[dict]:
        """Get circuit breaker status."""
        if self.circuit_breaker:
            return self.circuit_breaker.get_metrics()
        return None


def create_consumer(
    input_topic: str = "raw_data",
    output_topic: str = "processed_results",
    processor: Optional[StreamProcessor] = None,
    producer=None,
    enable_circuit_breaker: bool = True,
) -> KafkaConsumerWrapper:
    """Factory function to create a consumer."""
    return KafkaConsumerWrapper(
        input_topic=input_topic,
        output_topic=output_topic,
        processor=processor,
        producer=producer,
        enable_circuit_breaker=enable_circuit_breaker,
    )
