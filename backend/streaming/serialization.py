"""Message Serialization and Deserialization.

Supports multiple formats:
- JSON (default, human-readable)
- Avro (schema-based, compact)

Provides schema validation and error handling.
"""

import json
import logging
from typing import Any, Optional, Type
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class KafkaMessage:
    """Standard Kafka message format."""
    key: Optional[str] = None
    value: dict = None
    headers: dict = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.value is None:
            self.value = {}
        if self.headers is None:
            self.headers = {}


class Serializer(ABC):
    """Base class for message serializers."""

    @abstractmethod
    def serialize(self, message: KafkaMessage) -> bytes:
        """Serialize message to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> KafkaMessage:
        """Deserialize message from bytes."""
        pass

    @abstractmethod
    def validate_schema(self, data: dict) -> bool:
        """Validate message against schema."""
        pass


class JSONSerializer(Serializer):
    """JSON serializer - human-readable, flexible schema."""

    def __init__(self, validate_schema: bool = False):
        self.validate_schema_enabled = validate_schema

    def serialize(self, message: KafkaMessage) -> bytes:
        """Serialize to JSON."""
        try:
            payload = {
                "key": message.key,
                "value": message.value,
                "headers": message.headers,
                "timestamp": message.timestamp.isoformat(),
            }
            return json.dumps(payload).encode("utf-8")
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> KafkaMessage:
        """Deserialize from JSON."""
        try:
            payload = json.loads(data.decode("utf-8"))
            return KafkaMessage(
                key=payload.get("key"),
                value=payload.get("value", {}),
                headers=payload.get("headers", {}),
                timestamp=datetime.fromisoformat(payload.get("timestamp", datetime.now(timezone.utc).isoformat())),
            )
        except Exception as e:
            logger.error(f"JSON deserialization failed: {e}")
            raise

    def validate_schema(self, data: dict) -> bool:
        """JSON is schema-flexible, always validate passes."""
        # For JSON, we can do basic validation
        required_fields = {"value"}
        return all(field in data for field in required_fields)


class AvroSerializer(Serializer):
    """Avro serializer - schema-based, compact."""

    SCHEMA_REGISTRY_URL: Optional[str] = None

    def __init__(self, schema_registry_url: Optional[str] = None, validate_schema: bool = True):
        self.schema_registry_url = schema_registry_url or self.SCHEMA_REGISTRY_URL
        self.validate_schema_enabled = validate_schema

        # Try to import avro
        try:
            import avro
            import avro.io
            import avro.datafile
            self.avro = avro
        except ImportError:
            logger.warning("Avro not installed - install with: pip install avro-python3")
            raise

    def serialize(self, message: KafkaMessage) -> bytes:
        """Serialize to Avro."""
        # Simplified Avro serialization
        # In production, integrate with Confluent Schema Registry
        try:
            import io
            import avro.io
            import avro.schema

            schema_str = """{
                "type": "record",
                "name": "KafkaMessage",
                "fields": [
                    {"name": "key", "type": ["null", "string"]},
                    {"name": "value", "type": "string"},
                    {"name": "timestamp", "type": "string"}
                ]
            }"""

            schema = avro.schema.parse(schema_str)
            payload = {
                "key": message.key,
                "value": json.dumps(message.value),
                "timestamp": message.timestamp.isoformat(),
            }

            writer = avro.io.DatumWriter(schema)
            output = io.BytesIO()
            encoder = avro.io.BinaryEncoder(output)
            writer.write(payload, encoder)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Avro serialization failed: {e}")
            raise

    def deserialize(self, data: bytes) -> KafkaMessage:
        """Deserialize from Avro."""
        try:
            import io
            import avro.io
            import avro.schema

            schema_str = """{
                "type": "record",
                "name": "KafkaMessage",
                "fields": [
                    {"name": "key", "type": ["null", "string"]},
                    {"name": "value", "type": "string"},
                    {"name": "timestamp", "type": "string"}
                ]
            }"""

            schema = avro.schema.parse(schema_str)
            reader = avro.io.DatumReader(schema)
            input_stream = io.BytesIO(data)
            decoder = avro.io.BinaryDecoder(input_stream)
            payload = reader.read(decoder)

            return KafkaMessage(
                key=payload.get("key"),
                value=json.loads(payload.get("value", "{}")),
                headers={},
                timestamp=datetime.fromisoformat(payload.get("timestamp", datetime.now(timezone.utc).isoformat())),
            )
        except Exception as e:
            logger.error(f"Avro deserialization failed: {e}")
            raise

    def validate_schema(self, data: dict) -> bool:
        """Validate against Avro schema."""
        # Check required fields
        required_fields = {"value"}
        return all(field in data for field in required_fields)


class SerializerFactory:
    """Factory for creating serializers."""

    _serializers = {
        "json": JSONSerializer,
        "avro": AvroSerializer,
    }

    @classmethod
    def create(cls, format_type: str, **kwargs) -> Serializer:
        """Create a serializer by format.
        
        Args:
            format_type: "json" or "avro"
            **kwargs: Additional arguments for serializer
            
        Returns:
            Serializer instance
        """
        serializer_class = cls._serializers.get(format_type.lower())
        if not serializer_class:
            logger.warning(f"Unknown serializer format: {format_type}, defaulting to JSON")
            return JSONSerializer(**kwargs)
        
        try:
            return serializer_class(**kwargs)
        except ImportError as e:
            logger.warning(f"Serializer {format_type} not available: {e}, falling back to JSON")
            return JSONSerializer()

    @classmethod
    def register(cls, format_type: str, serializer_class: Type[Serializer]):
        """Register a custom serializer."""
        cls._serializers[format_type.lower()] = serializer_class
        logger.info(f"Registered serializer: {format_type}")


# Convenience functions
def serialize_message(message: KafkaMessage, format_type: str = "json") -> bytes:
    """Serialize a message."""
    serializer = SerializerFactory.create(format_type)
    return serializer.serialize(message)


def deserialize_message(data: bytes, format_type: str = "json") -> KafkaMessage:
    """Deserialize a message."""
    serializer = SerializerFactory.create(format_type)
    return serializer.deserialize(data)


class MessageValidator:
    """Validates message schemas."""

    @staticmethod
    def validate_raw_data(data: dict) -> tuple[bool, Optional[str]]:
        """Validate raw data message."""
        required_fields = {"post_id", "title", "content", "timestamp"}
        missing = required_fields - set(data.keys())
        if missing:
            return False, f"Missing fields: {missing}"
        return True, None

    @staticmethod
    def validate_processed_result(data: dict) -> tuple[bool, Optional[str]]:
        """Validate processed result message."""
        required_fields = {"post_id", "virality_score", "operation"}
        missing = required_fields - set(data.keys())
        if missing:
            return False, f"Missing fields: {missing}"
        return True, None


def get_serializer(format_type: str = "json", validate_schema: bool = False) -> Serializer:
    """Get a serializer instance."""
    return SerializerFactory.create(format_type, validate_schema=validate_schema)
