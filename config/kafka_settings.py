"""Kafka configuration management - loads from YAML and environment variables."""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml

logger = logging.getLogger(__name__)


@dataclass
class TopicConfig:
    """Topic configuration."""
    name: str
    partitions: int = 3
    replication_factor: int = 1
    retention_ms: int = 604800000
    compression_type: str = "snappy"


@dataclass
class ProducerConfig:
    """Producer configuration."""
    client_id: str
    batch_size: int
    linger_ms: int
    compression_type: str
    acks: str
    retries: int
    retry_backoff_ms: int


@dataclass
class ConsumerConfig:
    """Consumer configuration."""
    group_id: str
    auto_offset_reset: str
    enable_auto_commit: bool
    auto_commit_interval_ms: int
    session_timeout_ms: int
    max_poll_records: int
    poll_timeout_ms: int


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: float
    min_requests: int
    timeout_seconds: int
    max_consecutive_failures: int


@dataclass
class FallbackConfig:
    """Fallback configuration."""
    enabled: bool
    queue_directory: str
    retry_interval_seconds: int
    max_queue_size: int
    batch_size: int


@dataclass
class SerializationConfig:
    """Serialization configuration."""
    format: str
    schema_registry_url: Optional[str] = None
    validate_schema: bool = False


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    metrics_enabled: bool
    metrics_interval_seconds: int
    log_level: str
    log_format: str


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int
    initial_backoff_ms: int
    backoff_multiplier: int
    max_backoff_ms: int


@dataclass
class KafkaSecurityConfig:
    """Kafka security configuration."""
    bootstrap_servers: str
    security_protocol: str
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None


@dataclass
class KafkaConfiguration:
    """Complete Kafka configuration."""
    security: KafkaSecurityConfig
    topics: dict[str, TopicConfig]
    producer: ProducerConfig
    consumer: ConsumerConfig
    circuit_breaker: CircuitBreakerConfig
    fallback: FallbackConfig
    serialization: SerializationConfig
    monitoring: MonitoringConfig
    retry: RetryConfig

    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> "KafkaConfiguration":
        """Load configuration from YAML file and environment variables.
        
        Environment variables override YAML values.
        Searches in order:
        1. Explicit path
        2. ./config/kafka_config.yaml
        3. Uses defaults if neither found
        """
        if yaml_path is None:
            yaml_path = Path(__file__).parent / "kafka_config.yaml"
        else:
            yaml_path = Path(yaml_path)

        # Load YAML
        config_data = {}
        if yaml_path.exists():
            with open(yaml_path) as f:
                config_data = yaml.safe_load(f) or {}
            logger.info(f"Loaded Kafka config from {yaml_path}")
        else:
            logger.warning(f"Kafka config file not found at {yaml_path}, using defaults")

        # Override with environment variables
        kafka_config = config_data.get("kafka", {})
        if os.getenv("KAFKA_BOOTSTRAP_SERVERS"):
            kafka_config["bootstrap_servers"] = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if os.getenv("KAFKA_SECURITY_PROTOCOL"):
            kafka_config["security_protocol"] = os.getenv("KAFKA_SECURITY_PROTOCOL")
        if os.getenv("KAFKA_SASL_USERNAME"):
            kafka_config["sasl_username"] = os.getenv("KAFKA_SASL_USERNAME")
        if os.getenv("KAFKA_SASL_PASSWORD"):
            kafka_config["sasl_password"] = os.getenv("KAFKA_SASL_PASSWORD")
        if os.getenv("KAFKA_SASL_MECHANISM"):
            kafka_config["sasl_mechanism"] = os.getenv("KAFKA_SASL_MECHANISM")

        # Build security config
        security = KafkaSecurityConfig(
            bootstrap_servers=kafka_config.get("bootstrap_servers", "localhost:9092"),
            security_protocol=kafka_config.get("security_protocol", "PLAINTEXT"),
            sasl_mechanism=kafka_config.get("sasl_mechanism"),
            sasl_username=kafka_config.get("sasl_username"),
            sasl_password=kafka_config.get("sasl_password"),
        )

        # Build topics config
        topics = {}
        for topic_key, topic_config in config_data.get("topics", {}).items():
            topics[topic_key] = TopicConfig(**topic_config)

        # Build producer config
        producer_data = config_data.get("producer", {})
        producer = ProducerConfig(**producer_data)

        # Build consumer config
        consumer_data = config_data.get("consumer", {})
        consumer = ConsumerConfig(**consumer_data)

        # Build circuit breaker config
        cb_data = config_data.get("circuit_breaker", {})
        circuit_breaker = CircuitBreakerConfig(**cb_data)

        # Build fallback config
        fallback_data = config_data.get("fallback", {})
        fallback = FallbackConfig(**fallback_data)

        # Build serialization config
        ser_data = config_data.get("serialization", {})
        serialization = SerializationConfig(**ser_data)

        # Build monitoring config
        mon_data = config_data.get("monitoring", {})
        monitoring = MonitoringConfig(**mon_data)

        # Build retry config
        retry_data = config_data.get("retry", {})
        retry = RetryConfig(**retry_data)

        return cls(
            security=security,
            topics=topics,
            producer=producer,
            consumer=consumer,
            circuit_breaker=circuit_breaker,
            fallback=fallback,
            serialization=serialization,
            monitoring=monitoring,
            retry=retry,
        )

    def get_kafka_client_config(self) -> dict:
        """Get configuration dict for confluent-kafka client."""
        config = {
            "bootstrap.servers": self.security.bootstrap_servers,
            "security.protocol": self.security.security_protocol,
        }

        if self.security.security_protocol != "PLAINTEXT":
            config["sasl.mechanism"] = self.security.sasl_mechanism or "PLAIN"
            config["sasl.username"] = self.security.sasl_username
            config["sasl.password"] = self.security.sasl_password

        return config

    def get_producer_config(self) -> dict:
        """Get configuration dict for Kafka producer."""
        base_config = self.get_kafka_client_config()
        return {
            **base_config,
            "client.id": self.producer.client_id,
            "batch.size": self.producer.batch_size,
            "linger.ms": self.producer.linger_ms,
            "compression.type": self.producer.compression_type,
            "acks": self.producer.acks,
            "retries": self.producer.retries,
            "retry.backoff.ms": self.producer.retry_backoff_ms,
        }

    def get_consumer_config(self) -> dict:
        """Get configuration dict for Kafka consumer."""
        base_config = self.get_kafka_client_config()
        return {
            **base_config,
            "group.id": self.consumer.group_id,
            "auto.offset.reset": self.consumer.auto_offset_reset,
            "enable.auto.commit": self.consumer.enable_auto_commit,
            "auto.commit.interval.ms": self.consumer.auto_commit_interval_ms,
            "session.timeout.ms": self.consumer.session_timeout_ms,
            "max.poll.records": self.consumer.max_poll_records,
        }


# Singleton instance
_kafka_config: Optional[KafkaConfiguration] = None


def get_kafka_config() -> KafkaConfiguration:
    """Get or create the Kafka configuration singleton."""
    global _kafka_config
    if _kafka_config is None:
        _kafka_config = KafkaConfiguration.from_yaml()
    return _kafka_config


def reload_kafka_config(yaml_path: Optional[str] = None) -> KafkaConfiguration:
    """Reload Kafka configuration (useful for testing)."""
    global _kafka_config
    _kafka_config = KafkaConfiguration.from_yaml(yaml_path)
    return _kafka_config
