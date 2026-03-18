"""Kafka streaming module for Digital Pulse.

This module provides a complete Kafka integration layer that:
1. Produces: Ingests CSV/JSON data into Kafka
2. Consumes: Processes streams and publishes results
3. Fallback: Gracefully handles Kafka unavailability
4. Circuit Breaker: Prevents cascading failures
"""

from backend.streaming.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitState,
    create_kafka_circuit_breaker,
    get_circuit_breaker_manager,
)

from backend.streaming.serialization import (
    Serializer,
    JSONSerializer,
    AvroSerializer,
    SerializerFactory,
    serialize_message,
    deserialize_message,
    KafkaMessage,
    MessageValidator,
    get_serializer,
)

from backend.streaming.producer import (
    KafkaProducerWrapper,
    create_producer,
)

from backend.streaming.consumer import (
    KafkaConsumerWrapper,
    StreamProcessor,
    create_consumer,
)

from backend.streaming.fallback import (
    FallbackQueue,
    FallbackManager,
    QueuedMessage,
    get_fallback_manager,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitState",
    "create_kafka_circuit_breaker",
    "get_circuit_breaker_manager",
    # Serialization
    "Serializer",
    "JSONSerializer",
    "AvroSerializer",
    "SerializerFactory",
    "serialize_message",
    "deserialize_message",
    "KafkaMessage",
    "MessageValidator",
    "get_serializer",
    # Producer
    "KafkaProducerWrapper",
    "create_producer",
    # Consumer
    "KafkaConsumerWrapper",
    "StreamProcessor",
    "create_consumer",
    # Fallback
    "FallbackQueue",
    "FallbackManager",
    "QueuedMessage",
    "get_fallback_manager",
]
