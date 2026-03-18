# Kafka Streaming Module for Digital Pulse

A production-ready Apache Kafka integration layer that enables real-time stream processing while maintaining backward compatibility and zero-downtime operation.

## 🎯 Overview

This module provides:

- **Data Ingestion (Producer)** - Ingest CSV/JSON into Kafka
- **Stream Processing (Consumer)** - Process data through ML/AI pipeline
- **Resilience** - Circuit breaker pattern + fallback queue
- **Decoupling** - Analytical functions remain unaware of Kafka
- **Flexibility** - Schema-agnostic data processing

## 📁 Module Structure

```
backend/streaming/
├── __init__.py                 # Module exports
├── circuit_breaker.py          # Circuit breaker pattern implementation
├── serialization.py            # JSON/Avro serialize/deserialize
├── producer.py                 # Kafka producer wrapper
├── consumer.py                 # Kafka consumer wrapper
└── fallback.py                 # Persistent fallback queue

backend/adapters/
├── __init__.py
└── analytics_adapter.py        # Wraps existing analysis functions

config/
├── kafka_config.yaml           # Configuration (YAML)
└── kafka_settings.py           # Configuration manager (Python)

scripts/
├── kafka_producer.py           # Standalone producer CLI
└── kafka_consumer.py           # Standalone consumer CLI

docs/
├── KAFKA_INTEGRATION.md        # Comprehensive guide
└── KAFKA_IMPLEMENTATION_GUIDE.md # Step-by-step implementation
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-kafka.txt
```

### 2. Start Kafka (Docker)

```bash
docker-compose -f docker-compose.kafka.yml up -d
```

### 3. Run Producer

```bash
# Interactive mode
python scripts/kafka_producer.py --interactive
# Enter: {"post_id": "1", "title": "Test", ...}

# Or from CSV
python scripts/kafka_producer.py --csv data.csv
```

### 4. Run Consumer

```bash
# Process messages
python scripts/kafka_consumer.py --batch 10 --stats

# Or continuously
python scripts/kafka_consumer.py
```

## 📊 Architecture Diagram

```
Data Sources (CSV, JSON, API)
           ↓
   [Schema Adapter]
           ↓
   [Circuit Breaker] → [Fallback Queue]
           ↓
   [Kafka Producer]
           ↓
   [raw_data Topic]
           ↓
   [Kafka Consumer]
           ↓
   [Stream Processor] → [Analytics Pipeline]
           ↓
   [Kafka Producer]
           ↓
   [processed_results Topic]
           ↓
   [Database/API]
```

## 🔧 Core Components

### Circuit Breaker

Prevents cascading failures:

```python
from backend.streaming import create_kafka_circuit_breaker

breaker = create_kafka_circuit_breaker("producer_raw_data")
success, result = breaker.call(produce_message, data)

if not success:
    # Fallback handling
    fallback_queue.enqueue(data)
```

**States:** CLOSED (normal) → OPEN (blocked) → HALF_OPEN (recovering)

### Schema Adapter

Normalizes heterogeneous data fields:

```python
from backend.adapters.analytics_adapter import SchemaAdapter

adapter = SchemaAdapter()
normalized = adapter.normalize_post_data({
    "title": "...",
    "likes": 100,     # Field name variations supported
    "custom_field": "..." # Extra fields preserved in metadata
})
```

**Supports:** Reddit, News APIs, CSV, JSON, Social Media

### Producer

Ingests data into Kafka:

```python
from backend.streaming import create_producer

producer = create_producer(
    topic="raw_data",
    enable_circuit_breaker=True,
    fallback_handler=fallback_callback
)

# Single message
producer.produce({"title": "..."})

# Batch from CSV
producer.produce_from_csv("posts.csv")

# Batch from JSON
producer.produce_from_json("posts.jsonl")

producer.close()
```

### Consumer

Processes stream data:

```python
from backend.streaming import create_consumer, StreamProcessor

processor = StreamProcessor()
consumer = create_consumer(
    input_topic="raw_data",
    output_topic="processed_results",
    processor=processor
)

# Batch mode
await consumer.process_batch(max_messages=100)

# Continuous
await consumer.run(batch_size=50)

# Metrics
print(consumer.get_metrics())
```

### Fallback Queue

Persists data when Kafka unavailable:

```python
from backend.streaming.fallback import get_fallback_manager

fallback = get_fallback_manager()

# Queue message
msg_id = fallback.handle_producer_failure(data)

# Later, retry
success, failed = await fallback.retry_processing(producer.produce)
```

## 📝 Configuration

### YAML Configuration (`config/kafka_config.yaml`)

```yaml
kafka:
  bootstrap_servers: "localhost:9092"
  security_protocol: "PLAINTEXT"  # or SASL_SSL, SSL, etc.

topics:
  raw_data:
    partitions: 3
    retention_ms: 604800000  # 7 days

producer:
  acks: "all"
  retries: 3
  compression_type: "snappy"

consumer:
  auto_offset_reset: "earliest"
  enable_auto_commit: false  # Manual commits for exactly-once

circuit_breaker:
  failure_threshold: 0.5
  timeout_seconds: 60

fallback:
  enabled: true
  queue_directory: "./data/kafka_fallback_queue"
  max_queue_size: 10000
```

### Environment Variables

Override YAML with environment variables:

```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9092"
export KAFKA_SECURITY_PROTOCOL="SASL_SSL"
export KAFKA_SASL_USERNAME="user"
export KAFKA_SASL_PASSWORD="password"
```

## 📊 Monitoring

### Producer Metrics

```python
stats = producer.get_stats()
# {
#   "messages_sent": 1000,
#   "messages_failed": 5,
#   "messages_queued": 1005,
#   "error_count": 5
# }

cb_status = producer.get_circuit_breaker_status()
# {"state": "CLOSED", "metrics": {...}}
```

### Consumer Metrics

```python
metrics = consumer.get_metrics()
# {
#   "messages_received": 1000,
#   "messages_processed": 995,
#   "messages_failed": 5,
#   "messages_dlq": 5
# }
```

### Health Endpoint

```python
@app.get("/health/kafka")
async def kafka_health():
    return {
        "circuit_breakers": get_circuit_breaker_manager().get_all_metrics(),
        "fallback_queue": get_fallback_manager().get_stats(),
    }
```

## 🛡️ Error Handling

| Scenario | Handling |
|----------|----------|
| Kafka unavailable | Circuit breaker opens → Fallback queue activated |
| Serialization error | Message sent to DLQ → Logged & counted |
| Processing error | Message retried → DLQ if exceeds max retries |
| Network timeout | Exponential backoff → Circuit breaker evaluates |

## 🧪 Testing

### Unit Tests

```python
from backend.streaming import create_producer
from backend.adapters.analytics_adapter import SchemaAdapter

def test_schema_adapter():
    adapter = SchemaAdapter()
    normalized = adapter.normalize_post_data({
        "title": "Test",
        "likes": 100
    })
    assert normalized["title"] == "Test"
    assert normalized["likes"] == 100

def test_producer_creation():
    producer = create_producer()
    assert producer.circuit_breaker is not None
    producer.close()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end():
    producer = create_producer()
    consumer = create_consumer()
    
    producer.produce({
        "post_id": "1",
        "title": "Test",
        "content": "Content",
        "timestamp": "2024-03-18T10:00:00Z",
        "likes": 100
    })
    
    await consumer.process_batch(max_messages=1)
    assert consumer.get_metrics()["messages_processed"] >= 1
```

## 🚀 Deployment

### Docker Compose

```bash
# Start Kafka
docker-compose -f docker-compose.kafka.yml up -d

# Check health
docker-compose -f docker-compose.kafka.yml ps

# View logs
docker-compose -f docker-compose.kafka.yml logs kafka
```

### Kubernetes (Helm)

```bash
# Using Bitnami Helm chart
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install kafka bitnami/kafka
```

### Manual Installation

Install Kafka from [kafka.apache.org](https://kafka.apache.org/):

```bash
bin/zookeeper-server-start.sh config/zookeeper.properties
bin/kafka-server-start.sh config/server.properties

# Create topics
bin/kafka-topics.sh --create --topic raw_data --partitions 3 \
  --replication-factor 1 --bootstrap-server localhost:9092

bin/kafka-topics.sh --create --topic processed_results --partitions 3 \
  --bootstrap-server localhost:9092
```

## 📚 API Reference

### Producer

```python
create_producer(
    topic: str = "raw_data",
    enable_circuit_breaker: bool = True,
    fallback_handler: Optional[Callable] = None
) -> KafkaProducerWrapper
```

**Methods:**
- `produce(data: dict, key: str) → bool`
- `produce_batch(data_list: List[dict]) → Tuple[int, int]`
- `produce_from_csv(csv_path: str) → Tuple[int, int]`
- `produce_from_json(json_path: str) → Tuple[int, int]`
- `get_stats() → dict`
- `close()`

### Consumer

```python
create_consumer(
    input_topic: str = "raw_data",
    output_topic: str = "processed_results",
    processor: Optional[StreamProcessor] = None,
    producer: Optional[KafkaProducerWrapper] = None,
    enable_circuit_breaker: bool = True
) -> KafkaConsumerWrapper
```

**Methods:**
- `process_batch(max_messages: int, poll_timeout_ms: int) → None`
- `run(batch_size: int) → None`
- `get_metrics() → dict`
- `close()`
- `stop()`

### Fallback Manager

```python
get_fallback_manager(
    queue_directory: str = "./data/kafka_fallback_queue",
    max_queue_size: int = 10000,
    retry_interval_seconds: int = 30
) -> FallbackManager
```

**Methods:**
- `handle_producer_failure(data: dict) → str`
- `should_retry_processing() → bool`
- `retry_processing(processor: Callable) → Tuple[int, int]`
- `get_stats() → dict`

## 🔐 Security

### SASL/SSL Configuration

```yaml
kafka:
  security_protocol: "SASL_SSL"
  sasl_mechanism: "SCRAM-SHA-256"
  sasl_username: "${KAFKA_SASL_USERNAME}"
  sasl_password: "${KAFKA_SASL_PASSWORD}"
```

### TLS Certificates

```bash
# Set in producer config
export KAFKA_CA_CERT_PATH="/path/to/ca-cert"
export KAFKA_CLIENT_CERT_PATH="/path/to/client-cert"
export KAFKA_CLIENT_KEY_PATH="/path/to/client-key"
```

## 📖 Documentation

- [Kafka Integration Guide](./KAFKA_INTEGRATION.md) - Comprehensive design & architecture
- [Implementation Guide](./KAFKA_IMPLEMENTATION_GUIDE.md) - Step-by-step implementation
- [Confluent Kafka Docs](https://docs.confluent.io/kafka-clients/python/)

## 🐛 Troubleshooting

### Kafka Connection Failed

```bash
# Check if Kafka is running
kafka-broker-api-versions --bootstrap-server localhost:9092

# Check Docker container
docker-compose -f docker-compose.kafka.yml logs kafka
```

### Circuit Breaker Stuck OPEN

```python
from backend.streaming import create_producer

producer = create_producer()
if producer.circuit_breaker:
    producer.circuit_breaker.force_closed()
```

### Queue Growing

```bash
# Check queue size
ls -la ./data/kafka_fallback_queue/ | wc -l

# Retry processing
python scripts/kafka_consumer.py --retry-fallback
```

## 🤝 Contributing

1. Keep streaming layer decoupled from analytics
2. Add logging to all operations
3. Include metrics collection
4. Write tests for new features
5. Document configuration options
6. Add error handling with fallbacks

## 📄 License

Same as Digital Pulse project

---

**Next Steps:**
1. Review [KAFKA_INTEGRATION.md](./KAFKA_INTEGRATION.md) for detailed architecture
2. Follow [KAFKA_IMPLEMENTATION_GUIDE.md](./KAFKA_IMPLEMENTATION_GUIDE.md) for setup
3. Run example scripts to test
4. Integrate into FastAPI application
5. Deploy to production with monitoring
