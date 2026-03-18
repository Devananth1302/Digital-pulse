#!/usr/bin/env python3
"""Example tests for Kafka streaming module.

Run with: pytest tests/test_kafka_examples.py -v

These examples demonstrate how to test each component of the Kafka integration.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path

# Test imports
from backend.streaming import (
    create_producer,
    create_consumer,
    StreamProcessor,
)
from backend.adapters.analytics_adapter import SchemaAdapter, AnalyticsAdapter
from backend.streaming.circuit_breaker import CircuitBreaker, CircuitState
from backend.streaming.serialization import (
    KafkaMessage,
    serialize_message,
    deserialize_message,
    JSONSerializer,
)
from backend.streaming.fallback import FallbackQueue
from config.kafka_settings import get_kafka_config


class TestSchemaAdapter:
    """Test schema normalization."""

    def test_normalize_post_data(self):
        """Test normalizing various data sources."""
        adapter = SchemaAdapter()

        # Test Reddit-style data
        reddit_data = {
            "id": "abc123",
            "title": "Test Post",
            "selftext": "Post content",
            "created_utc": 1710816000,
            "score": 100,
            "num_comments": 25,
        }
        
        normalized = adapter.normalize_post_data(reddit_data)
        assert normalized["title"] == "Test Post"
        assert normalized["content"] == "Post content"
        assert "post_id" in normalized
        
    def test_extract_engagement(self):
        """Test engagement metric extraction."""
        adapter = SchemaAdapter()
        
        data = {
            "upvotes": 100,
            "reblogs": 50,
            "replies": 25,
        }
        
        engagement = adapter._extract_engagement(data)
        assert engagement["likes"] == 100
        assert engagement["shares"] == 50
        assert engagement["comments"] == 25

    def test_extract_timestamp(self):
        """Test timestamp parsing from various formats."""
        adapter = SchemaAdapter()
        
        # ISO format
        ts = adapter._extract_timestamp(
            {"timestamp": "2024-03-18T10:00:00Z"}
        )
        assert ts.year == 2024
        
        # Unix timestamp
        ts = adapter._extract_timestamp(
            {"created_at": 1710816000}
        )
        assert ts.year == 2024


class TestAnalyticsAdapter:
    """Test analytics function wrappers."""

    def test_virality_calculation(self):
        """Test virality score calculation."""
        adapter = AnalyticsAdapter()
        
        test_data = {
            "post_id": "test_1",
            "title": "Test",
            "content": "Test content",
            "timestamp": "2024-03-18T10:00:00Z",
            "likes": 100,
            "shares": 50,
            "comments": 25,
        }
        
        result = adapter.calculate_virality_score(test_data)
        assert result.success
        assert "virality_score" in result.result
        assert result.result["virality_score"] > 0


class TestSerialization:
    """Test message serialization."""

    def test_json_serialization(self):
        """Test JSON serialize/deserialize."""
        serializer = JSONSerializer()
        
        msg = KafkaMessage(
            key="test_1",
            value={"title": "Test", "content": "Content"},
        )
        
        # Serialize
        data = serializer.serialize(msg)
        assert isinstance(data, bytes)
        
        # Deserialize
        msg2 = serializer.deserialize(data)
        assert msg2.key == "test_1"
        assert msg2.value["title"] == "Test"

    def test_schema_validation(self):
        """Test message schema validation."""
        serializer = JSONSerializer()
        
        valid_data = {
            "value": {"title": "Test"},
            "key": "test_1"
        }
        assert serializer.validate_schema(valid_data)
        
        invalid_data = {"key": "test_1"}
        assert not serializer.validate_schema(invalid_data)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        breaker = CircuitBreaker(
            "test",
            failure_threshold=0.5,
            min_requests=3,
        )
        
        assert breaker.state == CircuitState.CLOSED
        
        # Simulate failures
        def failing_func():
            raise Exception("Test failure")
        
        for i in range(3):
            success, result = breaker.call(failing_func)
            assert not success
        
        # Should be open now
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        breaker = CircuitBreaker(
            "test",
            failure_threshold=0.5,
            min_requests=2,
            timeout_seconds=0,  # Immediate transition
        )
        
        # Cause failures
        def failing():
            raise Exception("fail")
        
        breaker.call(failing)
        breaker.call(failing)
        
        assert breaker.state == CircuitState.OPEN
        
        # Successful call in half-open should close it
        breaker._state = CircuitState.HALF_OPEN
        
        def succeeding():
            return "success"
        
        success, result = breaker.call(succeeding)
        assert success
        assert breaker.state == CircuitState.CLOSED

    def test_force_open_close(self):
        """Test manual circuit breaker control."""
        breaker = CircuitBreaker("test")
        
        breaker.force_open()
        assert breaker.state == CircuitState.OPEN
        
        breaker.force_closed()
        assert breaker.state == CircuitState.CLOSED


class TestFallbackQueue:
    """Test fallback queue functionality."""

    def test_enqueue_dequeue(self):
        """Test queue basic operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = FallbackQueue(queue_directory=tmpdir)
            
            data = {"post_id": "1", "title": "Test"}
            msg_id = queue.enqueue(data)
            
            assert len(msg_id) > 0
            assert queue.get_queue_size() == 1
            
            # Dequeue
            dequeued = queue.dequeue(msg_id)
            assert dequeued["post_id"] == "1"
            assert queue.get_queue_size() == 0

    def test_queue_size_limit(self):
        """Test queue size limit enforcement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = FallbackQueue(
                queue_directory=tmpdir,
                max_queue_size=3
            )
            
            # Fill queue to limit
            for i in range(3):
                queue.enqueue({"id": i})
            
            assert queue.get_queue_size() == 3
            
            # Try to exceed limit
            msg_id = queue.enqueue({"id": 4})
            assert queue.get_queue_size() == 3  # Still at limit
            assert queue.stats["dropped"] > 0

    def test_queue_processing(self):
        """Test batch queue processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = FallbackQueue(queue_directory=tmpdir)
            
            # Queue some messages
            for i in range(5):
                queue.enqueue({"id": i})
            
            # Process with success
            processed = 0
            def processor(data):
                nonlocal processed
                processed += 1
                return True
            
            success, failed = queue.process_queue(processor, batch_size=10)
            assert success == 5
            assert failed == 0
            assert queue.get_queue_size() == 0


class TestKafkaConfiguration:
    """Test Kafka configuration loading."""

    def test_config_loading(self):
        """Test YAML configuration loading."""
        config = get_kafka_config()
        
        assert config.security.bootstrap_servers
        assert config.topics["raw_data"].name == "raw_data"
        assert config.producer.acks == "all"
        assert config.consumer.group_id == "digital-pulse-processors"

    def test_producer_config_generation(self):
        """Test producer config generation."""
        config = get_kafka_config()
        producer_config = config.get_producer_config()
        
        assert "bootstrap.servers" in producer_config
        assert producer_config["acks"] == "all"
        assert "batch.size" in producer_config

    def test_consumer_config_generation(self):
        """Test consumer config generation."""
        config = get_kafka_config()
        consumer_config = config.get_consumer_config()
        
        assert "bootstrap.servers" in consumer_config
        assert consumer_config["group.id"] == "digital-pulse-processors"


class TestProducerCreation:
    """Test producer initialization."""

    def test_producer_creates_successfully(self):
        """Test producer can be created."""
        producer = create_producer(
            topic="test_topic",
            enable_circuit_breaker=True,
        )
        
        assert producer is not None
        assert producer.topic == "test_topic"
        assert producer.circuit_breaker is not None
        producer.close()

    def test_producer_without_circuit_breaker(self):
        """Test producer without circuit breaker."""
        producer = create_producer(
            topic="test_topic",
            enable_circuit_breaker=False,
        )
        
        assert producer.circuit_breaker is None
        producer.close()


class TestConsumerCreation:
    """Test consumer initialization."""

    def test_consumer_creates_successfully(self):
        """Test consumer can be created."""
        consumer = create_consumer(
            input_topic="raw_data",
            output_topic="processed_results",
        )
        
        assert consumer is not None
        assert consumer.input_topic == "raw_data"
        consumer.close()

    def test_stream_processor_creation(self):
        """Test stream processor creation."""
        processor = StreamProcessor()
        
        assert processor is not None
        assert processor.analytics is not None


# Integration tests (require running Kafka)
class TestIntegration:
    """Integration tests (skipped if Kafka unavailable)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_csv_ingestion_to_topic(self):
        """Test CSV ingestion to Kafka topic."""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("post_id,title,content,timestamp,likes\n")
            f.write("1,Test1,Content1,2024-03-18T10:00:00Z,100\n")
            f.write("2,Test2,Content2,2024-03-18T11:00:00Z,200\n")
            csv_path = f.name
        
        try:
            producer = create_producer()
            success, failed = producer.produce_from_csv(csv_path)
            
            assert success >= 2 or failed <= 0  # Should succeed or handle gracefully
            producer.close()
        finally:
            Path(csv_path).unlink()


# Performance tests
class TestPerformance:
    """Performance tests."""

    def test_serialization_speed(self):
        """Test serialization performance."""
        serializer = JSONSerializer()
        msg = KafkaMessage(
            key="test",
            value={"title": "Test", "content": "Content" * 100}
        )
        
        # Should serialize quickly
        import time
        start = time.time()
        for _ in range(1000):
            serializer.serialize(msg)
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # 1000 msgs in < 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
