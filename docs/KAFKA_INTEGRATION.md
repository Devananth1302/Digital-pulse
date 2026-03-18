# Apache Kafka Integration for Digital Pulse

> **Architecture:** Event-Driven Real-Time Stream Processing with Resilience & Fallback

## 📋 Overview

This document describes the complete Kafka integration layer for Digital Pulse, enabling a transition from static batch processing to real-time streaming while maintaining zero downtime and backward compatibility.

### Core Components

1. **Configuration Management** - YAML config + environment variables
2. **Producer** - Ingests CSV/JSON data into Kafka
3. **Consumer** - Processes streams through analytics pipeline
4. **Circuit Breaker** - Prevents cascading failures
5. **Fallback Queue** - Persistent storage when Kafka unavailable
6. **Adapter Layer** - Decouples analysis from data source

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Data Sources                                 │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐               │
│  │ CSV      │  │ JSON/JSONL   │  │ API Streams │               │
│  └────┬─────┘  └──────┬───────┘  └──────┬──────┘               │
│       │               │                 │                        │
└───────┼───────────────┼─────────────────┼──────────────────────┘
        │               │                 │
        └───────────┬───┴─────────────┬───┘
                    │                 │
            ┌───────▼──────────────────▼────────┐
            │   Schema Adapter (Normalize)      │
            │  - Field mapping                  │
            │  - Type conversion                │
            │  - Validation                     │
            └───────┬──────────────────┬────────┘
                    │                  │
        ┌───────────▼────────┐  ┌──────▼──────────────┐
        │  Circuit Breaker   │  │  Fallback Queue    │
        │  - State tracking  │  │  - Persistent...   │
        │  - Failure detect  │  │  - Local storage   │
        └───────────┬────────┘  └──────┬──────────────┘
                    │                  │
            ┌───────▼──────────────────▼─────────┐
            │   Kafka Producer                    │
            │   Topic: raw_data                   │
            │   Partitions: 3                     │
            └───────┬──────────────────┬──────────┘
                    │                  │
                    └──────────┬─────┬─┘
                               │     │
                    ┌──────────▼─────▼──────────────┐
                    │   Kafka Broker Cluster        │
                    │   Topic: raw_data             │
                    └──────────┬─────┬──────────────┘
                               │     │
                    ┌──────────▼─────▼──────────────┐
                    │   Kafka Consumer              │
                    │   Group: digital-pulse-proc   │
                    └──────────┬──────────┬─────────┘
                               │          │
                    ┌──────────▼──┐  ┌───▼──────────────┐
                    │  Stream     │  │  AI Adapter      │
                    │  Processor  │  │  - Virality      │
                    │             │  │  - Clustering    │
                    │             │  │  - Signals       │
                    │             │  │  - Forecast      │
                    └──────┬───┬──┘  └────┬─────────────┘
                           │   │         │
                    ┌──────▼───▼─────────▼──┐
                    │  Kafka Producer       │
                    │  Topic: processed_results
                    │  (Results Topic)      │
                    └──────┬────────────────┘
                           │
                    ┌──────▼────────────────┐
                    │   Supabase / Database │
                    │   - Results Storage   │
                    │   - Historical Data   │
                    └───────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install confluent-kafka pyyaml

# Kafka broker running (Docker example)
docker run -d --name kafka \
  -p 9092:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:7.0.0
```

### Configuration

#### 1. YAML Configuration (`config/kafka_config.yaml`)

The configuration file contains all Kafka settings. Key sections:

```yaml
kafka:
  bootstrap_servers: "localhost:9092"
  security_protocol: "PLAINTEXT"

topics:
  raw_data:
    name: "raw_data"
    partitions: 3
    retention_ms: 604800000  # 7 days

producer:
  acks: "all"  # Wait for all replicas
  retries: 3

circuit_breaker:
  failure_threshold: 0.5  # 50% failure rate
  timeout_seconds: 60
  max_consecutive_failures: 3

fallback:
  enabled: true
  queue_directory: "./data/kafka_fallback_queue"
  max_queue_size: 10000
```

#### 2. Environment Variables

Override YAML settings with environment variables:

```bash
# Kafka connection
export KAFKA_BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9092"
export KAFKA_SECURITY_PROTOCOL="SASL_SSL"
export KAFKA_SASL_USERNAME="your-username"
export KAFKA_SASL_PASSWORD="your-password"
```

### 3. Running the System

#### **Standalone Producer**

Ingest data into Kafka:

```bash
# From CSV file
python scripts/kafka_producer.py --csv data/posts.csv

# From JSON/JSONL file
python scripts/kafka_producer.py --json data/posts.jsonl

# Interactive mode
python scripts/kafka_producer.py --interactive

# Test mode
python scripts/kafka_producer.py --test --stats
```

#### **Standalone Consumer**

Process stream and publish results:

```bash
# Continuous processing (Ctrl+C to stop)
python scripts/kafka_consumer.py

# Batch mode (process 50 messages and exit)
python scripts/kafka_consumer.py --batch 50

# Dry-run (test with 10 messages)
python scripts/kafka_consumer.py --dry-run

# Retry fallback queue
python scripts/kafka_consumer.py --retry-fallback

# Show detailed statistics
python scripts/kafka_consumer.py --stats
```

#### **In FastAPI Application**

Integrate into existing FastAPI app:

```python
from backend.streaming import create_producer, create_consumer

# Producer (in upload endpoint)
@app.post("/upload-csv")
async def upload_csv(file: UploadFile):
    # Save file
    filepath = f"uploads/{file.filename}"
    with open(filepath, "wb") as f:
        f.write(await file.read())
    
    # Produce to Kafka
    producer = create_producer()
    success, failed = producer.produce_from_csv(filepath)
    
    return {"success": success, "failed": failed}
```

## 🔧 Core Modules

### 1. Configuration (`config/kafka_settings.py`)

**Purpose:** Load and manage Kafka configuration

**Key Classes:**
- `KafkaConfiguration` - Central config container
- `from_yaml()` - Load from YAML + env overrides
- `get_kafka_config()` - Singleton access

**Usage:**

```python
from config.kafka_settings import get_kafka_config

config = get_kafka_config()
print(config.security.bootstrap_servers)
print(config.topics["raw_data"].partitions)
```

### 2. Schema Adapter (`backend/adapters/analytics_adapter.py`)

**Purpose:** Normalize heterogeneous data fields

**Key Classes:**
- `SchemaAdapter` - Field mapping & normalization
- `AnalyticsAdapter` - Wraps existing analysis functions
- `AnalyticsResult` - Standard result container

**Supports:**
- Reddit posts
- News articles
- CSV uploads
- Social media feeds
- Custom JSON

**Usage:**

```python
from backend.adapters.analytics_adapter import SchemaAdapter, AnalyticsAdapter

# Normalize data from any source
adapter = SchemaAdapter()
normalized = adapter.normalize_post_data({
    "title": "...",
    "content": "...",
    "likes": 100,
    # ... any field names
})

# Run analysis on normalized data
analytics = AnalyticsAdapter()
result = analytics.calculate_virality_score(normalized)
```

### 3. Circuit Breaker (`backend/streaming/circuit_breaker.py`)

**Purpose:** Prevent cascading failures

**States:**
- `CLOSED` - Normal operation
- `OPEN` - Blocked (too many failures)
- `HALF_OPEN` - Testing recovery

**Features:**
- Configurable failure threshold
- Consecutive failure tracking
- Exponential backoff
- Metrics collection

**Usage:**

```python
from backend.streaming.circuit_breaker import create_kafka_circuit_breaker

breaker = create_kafka_circuit_breaker(
    name="producer_raw_data",
    failure_threshold=0.5,
    timeout_seconds=60,
)

# Use in function calls
success, result = breaker.call(produce_message, data)
if not success:
    # Handle fallback
    fallback_handler(data)

# Get metrics
metrics = breaker.get_metrics()
```

### 4. Serialization (`backend/streaming/serialization.py`)

**Purpose:** Serialize/deserialize messages for Kafka

**Supported Formats:**
- **JSON** (default) - Human-readable, flexible schema
- **Avro** - Compact, schema-based

**Usage:**

```python
from backend.streaming.serialization import (
    KafkaMessage,
    serialize_message,
    deserialize_message,
)

# Create and serialize
msg = KafkaMessage(
    key="post_123",
    value={"title": "...", "content": "..."},
)
data = serialize_message(msg, format_type="json")

# Deserialize
msg2 = deserialize_message(data, format_type="json")
```

### 5. Producer (`backend/streaming/producer.py`)

**Purpose:** Ingest data into Kafka

**Features:**
- CSV/JSON ingestion
- Batch processing
- Circuit breaker protection
- Fallback to local storage
- Metrics tracking

**Usage:**

```python
from backend.streaming import create_producer
from backend.streaming.fallback import get_fallback_manager

# Initialize
fallback = get_fallback_manager()
fallback_handler = lambda data: fallback.handle_producer_failure(data)
producer = create_producer(
    topic="raw_data",
    fallback_handler=fallback_handler,
)

# Single message
producer.produce({"title": "...", "content": "..."})

# Batch
producer.produce_batch([data1, data2, data3])

# From CSV
producer.produce_from_csv("data.csv")

# Close
producer.close()
```

### 6. Consumer (`backend/streaming/consumer.py`)

**Purpose:** Process stream data through analysis pipeline

**Features:**
- Batch and continuous processing
- Exactly-once semantics (manual commits)
- Dead letter queue support
- Circuit breaker protection
- Metrics collection

**Usage:**

```python
from backend.streaming import create_consumer, StreamProcessor

# Initialize
processor = StreamProcessor()
consumer = create_consumer(
    input_topic="raw_data",
    output_topic="processed_results",
    processor=processor,
)

# Batch processing
await consumer.process_batch(max_messages=100)

# Continuous
await consumer.run(batch_size=50)

# Get metrics
print(consumer.get_metrics())
```

### 7. Fallback Queue (`backend/streaming/fallback.py`)

**Purpose:** Persistent storage when Kafka unavailable

**Features:**
- JSON file-based storage
- Automatic retry with exponential backoff
- Configurable queue size
- Metrics tracking
- Graceful degradation

**Usage:**

```python
from backend.streaming.fallback import get_fallback_manager

fallback = get_fallback_manager(
    queue_directory="./data/kafka_queue",
    max_queue_size=10000,
    retry_interval_seconds=30,
)

# Queue message when producer fails
msg_id = fallback.handle_producer_failure(data)

# Retry processing later
success, failed = await fallback.retry_processing(processor)

# Check status
stats = fallback.get_stats()
```

## 🔄 Data Flow Examples

### Scenario 1: CSV Ingestion to Kafka

```python
from backend.streaming import create_producer

# Create producer with fallback
producer = create_producer(enable_circuit_breaker=True)

# Ingest CSV
success, failed = producer.produce_from_csv("posts.csv")

# Monitor
print(f"Sent: {success}, Failed: {failed}")
print(f"Circuit breaker: {producer.get_circuit_breaker_status()}")

# Close
producer.close()
```

### Scenario 2: Stream Processing Pipeline

```python
from backend.streaming import create_consumer, create_producer

# Create producer for output
output_producer = create_producer(topic="processed_results")

# Create consumer
consumer = create_consumer(
    input_topic="raw_data",
    output_topic="processed_results",
    producer=output_producer,
)

# Process messages
await consumer.process_batch(max_messages=100)
```

### Scenario 3: Fallback Handling

```python
from backend.streaming import create_producer
from backend.streaming.fallback import get_fallback_manager

fallback = get_fallback_manager()

def fallback_handler(data):
    """Called when producer fails"""
    msg_id = fallback.handle_producer_failure(data)
    print(f"Queued: {msg_id}")

producer = create_producer(fallback_handler=fallback_handler)

# When Kafka unavailable or circuit breaker opens:
# producer.produce() -> circuit breaker open -> fallback_handler() called
producer.produce(data)

# Later, when Kafka recovers:
async def retry():
    success, failed = await fallback.retry_processing(producer.produce)
    print(f"Retried: {success}/{failed}")

await retry()
```

## ⚙️ Configuration Reference

### Kafka Connection

```yaml
kafka:
  bootstrap_servers: "localhost:9092"  # Comma-separated
  security_protocol: PLAINTEXT
  sasl_mechanism: PLAIN
  sasl_username: ""  # Env var override
  sasl_password: ""  # Env var override
```

### Topics

```yaml
topics:
  raw_data:
    name: "raw_data"
    partitions: 3
    replication_factor: 1
    retention_ms: 604800000
    compression_type: "snappy"
  processed_results:
    name: "processed_results"
    partitions: 3
    replication_factor: 1
```

### Producer Settings

```yaml
producer:
  batch_size: 16384              # Bytes
  linger_ms: 100                 # Accumulation time
  acks: "all"                    # Wait for all replicas
  retries: 3
  retry_backoff_ms: 100
  compression_type: "snappy"
```

### Consumer Settings

```yaml
consumer:
  auto_offset_reset: "earliest"  # Start from beginning
  enable_auto_commit: false      # Manual commits
  max_poll_records: 100
  session_timeout_ms: 30000
```

### Circuit Breaker

```yaml
circuit_breaker:
  failure_threshold: 0.5         # 50% failure opens circuit
  min_requests: 5                # Evaluate after 5 requests
  timeout_seconds: 60            # Recovery timeout
  max_consecutive_failures: 3    # Max consecutive failures
```

### Fallback

```yaml
fallback:
  enabled: true
  queue_directory: "./data/kafka_fallback_queue"
  retry_interval_seconds: 30
  max_queue_size: 10000
  batch_size: 50                 # Process 50 at a time
```

## 📊 Monitoring & Diagnostics

### Producer Metrics

```python
stats = producer.get_stats()
# {
#   "messages_sent": 1000,
#   "messages_failed": 5,
#   "messages_queued": 1005,
#   "bytes_sent": 500000,
#   "error_count": 5,
# }

cb_status = producer.get_circuit_breaker_status()
# {
#   "name": "producer_raw_data",
#   "state": "CLOSED",
#   "metrics": {...}
# }
```

### Consumer Metrics

```python
metrics = consumer.get_metrics()
# {
#   "messages_received": 1000,
#   "messages_processed": 995,
#   "messages_failed": 5,
#   "messages_dlq": 5,
#   "error_count": 5,
# }
```

### Fallback Queue Status

```python
fallback_stats = fallback.get_stats()
# {
#   "queue": {
#     "enqueued": 50,
#     "processed": 45,
#     "failed": 5,
#     "current_size": 5,
#     "max_size": 10000,
#   },
#   "last_retry": "2024-03-18T10:00:00Z",
# }
```

## 🛡️ Error Handling

### Failure Scenarios

| Scenario | Handling |
|----------|----------|
| **Kafka unavailable** | Circuit breaker opens → fallback queue activated |
| **Serialization error** | Message sent to DLQ → logged |
| **Processing error** | Message retried → DLQ if exceeds max retries |
| **Network timeout** | Exponential backoff → circuit breaker evaluates |

### Circuit Breaker States

```
CLOSED (✓ Normal)
  ↓
  [Failures exceed threshold]
  ↓
OPEN (✗ Blocked)
  ↓
  [Timeout elapsed]
  ↓
HALF_OPEN (⚠ Testing)
  ↓
  [Success] → CLOSED | [Failure] → OPEN
```

## 🚨 Troubleshooting

### Producer not connecting

```bash
# Check configuration
python -c "from config.kafka_settings import get_kafka_config; print(get_kafka_config().security.bootstrap_servers)"

# Test connection
python -c "from confluent_kafka import Producer; p = Producer({'bootstrap.servers': 'localhost:9092'}); print('OK')"
```

### Circuit breaker stuck OPEN

```python
# Force close
breaker.force_closed()

# Or reset
breaker.reset()
```

### Check fallback queue

```bash
ls -la ./data/kafka_fallback_queue/
python -c "from backend.streaming.fallback import get_fallback_manager; fm = get_fallback_manager(); print(fm.get_stats())"
```

### Enable debug logging

```bash
python scripts/kafka_consumer.py --log-level DEBUG
```

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Broker addresses |
| `KAFKA_SECURITY_PROTOCOL` | `PLAINTEXT` | Connection type |
| `KAFKA_SASL_USERNAME` | - | SASL username |
| `KAFKA_SASL_PASSWORD` | - | SASL password |
| `KAFKA_SASL_MECHANISM` | `PLAIN` | SASL mechanism |

## 🔐 Production Checklist

- [ ] Configure SASL/SSL security
- [ ] Set replication factor > 1
- [ ] Configure retention policies
- [ ] Enable schema validation
- [ ] Set up monitoring/alerting
- [ ] Test circuit breaker behavior
- [ ] Verify fallback queue capacity
- [ ] Enable application metrics
- [ ] Configure log aggregation
- [ ] Document custom adaptations

## 📚 Next Steps

1. **Monitoring** - Integrate with Prometheus/Grafana
2. **Schema Registry** - Use Confluent Schema Registry for Avro
3. **Advanced Patterns** - Implement:
   - Multi-partition ordered processing
   - Exactly-once transactional processing
   - Stateful stream processing (Faust)
4. **Performance Tuning** - Configure batch sizes, compression, etc.
5. **Testing** - Write integration tests with embedded Kafka

## 🤝 Contributing

When extending the Kafka integration:

1. Maintain separation of concerns (producer, consumer, fallback)
2. Keep analytical functions uncoupled
3. Add comprehensive logging
4. Include metrics collection
5. Document configuration options
6. Add error handling with fallbacks

## 📄 License

Same as Digital Pulse project
