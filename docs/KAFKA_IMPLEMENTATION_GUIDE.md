# Kafka Integration Implementation Guide

## Phase 1: Setup (30 min)

### 1.1 Install Dependencies

```bash
# Option 1: Just Kafka
pip install -r requirements-kafka.txt

# Option 2: Full installation (if you want to test)
pip install confluent-kafka pyyaml aiofiles
```

### 1.2 Verify Configuration

```bash
# Create config YAML if not exists
ls config/kafka_config.yaml

# Test config loading
python -c "from config.kafka_settings import get_kafka_config; c = get_kafka_config(); print(f'Bootstrap: {c.security.bootstrap_servers}')"
```

### 1.3 Set Up Local Kafka (for testing)

```bash
# Using Docker Compose
docker-compose up -d

# Or manually
docker run -d --name zookeeper -p 2181:2181 \
  -e ZOOKEEPER_CLIENT_PORT=2181 \
  confluentinc/cp-zookeeper:7.0.0

docker run -d --name kafka -p 9092:9092 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_EXTERNAL://localhost:9092 \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_EXTERNAL:PLAINTEXT \
  -e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
  confluentinc/cp-kafka:7.0.0
```

## Phase 2: Running Examples

### 2.1 Test Producer

```bash
# Interactive mode - send test messages
python scripts/kafka_producer.py --interactive

# Example input:
# {"post_id": "1", "title": "Test", "content": "Hello", "timestamp": "2024-03-18T10:00:00Z", "likes": 100, "shares": 50, "comments": 25}

# CSV mode
python scripts/kafka_producer.py --csv data/sample_posts.csv

# Show stats
python scripts/kafka_producer.py --test --stats
```

### 2.2 Test Consumer

```bash
# Process messages
python scripts/kafka_consumer.py --batch 10 --stats

# Dry run (process up to 10 messages)
python scripts/kafka_consumer.py --dry-run

# Continuous mode
python scripts/kafka_consumer.py
```

### 2.3 Test Fallback

```bash
# Stop Kafka
docker stop kafka

# Run producer - should queue messages
python scripts/kafka_producer.py --interactive

# Restart Kafka
docker start kafka

# Retry queue
python scripts/kafka_consumer.py --retry-fallback
```

## Phase 3: Integration Steps

### 3.1 Add to Existing Endpoints

Update `backend/api/upload.py`:

```python
from backend.streaming import create_producer
from backend.streaming.fallback import get_fallback_manager

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV and produce to Kafka"""
    # Save file
    upload_path = f"uploads/{file.filename}"
    with open(upload_path, "wb") as f:
        f.write(await file.read())
    
    # Fallback manager
    fallback = get_fallback_manager()
    fallback_handler = lambda data: fallback.handle_producer_failure(data)
    
    # Produce to Kafka
    producer = create_producer(fallback_handler=fallback_handler)
    success, failed = producer.produce_from_csv(upload_path)
    producer.close()
    
    return {
        "success": success,
        "failed": failed,
        "total": success + failed,
    }
```

### 3.2 Add Consumer to Startup

Update `backend/main.py`:

```python
import asyncio
from backend.streaming import create_consumer

# Global consumer task
consumer_task = None

@app.on_event("startup")
async def startup_event():
    global consumer_task
    logger.info("Starting Kafka consumer...")
    
    # Start consumer in background
    consumer = create_consumer()
    consumer_task = asyncio.create_task(consumer.run(batch_size=10))

@app.on_event("shutdown")
async def shutdown_event():
    global consumer_task
    if consumer_task:
        consumer_task.cancel()
    logger.info("Kafka consumer stopped")
```

### 3.3 Add Monitoring Endpoint

```python
from backend.streaming import get_circuit_breaker_manager
from backend.streaming.fallback import get_fallback_manager

@app.get("/health/kafka")
async def kafka_health():
    """Check Kafka system health"""
    cbm = get_circuit_breaker_manager()
    fallback = get_fallback_manager()
    
    return {
        "status": "healthy",
        "circuit_breakers": cbm.get_all_metrics(),
        "fallback_queue": fallback.get_stats(),
    }
```

## Phase 4: Testing

### 4.1 Unit Tests

Create `tests/test_kafka_producer.py`:

```python
import pytest
from backend.streaming import create_producer
from backend.adapters.analytics_adapter import SchemaAdapter

def test_schema_adapter():
    """Test schema normalization"""
    adapter = SchemaAdapter()
    
    raw_data = {
        "title": "Test",
        "likes": 100,
        "custom_field": "value"
    }
    
    normalized = adapter.normalize_post_data(raw_data)
    
    assert normalized["title"] == "Test"
    assert normalized["likes"] == 100
    assert normalized["custom_field"] == "value"

def test_producer_creation():
    """Test producer initialization"""
    producer = create_producer(enable_circuit_breaker=True)
    assert producer is not None
    assert producer.circuit_breaker is not None
    producer.close()

@pytest.mark.asyncio
async def test_fallback_queue():
    """Test fallback queue"""
    from backend.streaming.fallback import get_fallback_manager
    
    fallback = get_fallback_manager()
    msg_id = fallback.queue.enqueue({"test": "data"})
    
    data = fallback.queue.dequeue(msg_id)
    assert data is not None
    assert data["test"] == "data"
```

### 4.2 Integration Tests

Create `tests/test_kafka_integration.py`:

```python
import asyncio
import pytest
from backend.streaming import create_producer, create_consumer

@pytest.mark.asyncio
async def test_end_to_end_flow():
    """Test complete producer-consumer flow"""
    
    # Create producer and consumer
    producer = create_producer()
    consumer = create_consumer()
    
    # Produce test data
    test_data = {
        "post_id": "test_1",
        "title": "Integration Test",
        "content": "Testing full pipeline",
        "timestamp": "2024-03-18T10:00:00Z",
        "likes": 100,
        "shares": 50,
        "comments": 25,
    }
    
    producer.produce(test_data)
    producer.close()
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Process one batch
    await consumer.process_batch(max_messages=1)
    
    metrics = consumer.get_metrics()
    assert metrics["messages_processed"] >= 1
    
    consumer.close()
```

### 4.3 Circuit Breaker Tests

```python
from backend.streaming.circuit_breaker import CircuitBreaker

def test_circuit_breaker_opens():
    """Test circuit breaker opening"""
    breaker = CircuitBreaker(
        "test",
        failure_threshold=0.5,
        min_requests=3,
        timeout_seconds=60,
    )
    
    def failing_func():
        raise Exception("Test failure")
    
    # Cause failures
    for i in range(3):
        success, result = breaker.call(failing_func)
        assert not success
    
    # Circuit should be open
    assert breaker.state.value == "OPEN"
    
    # New requests should fail immediately
    success, result = breaker.call(failing_func)
    assert not success and result is None
```

## Phase 5: Production Deployment

### 5.1 Configuration for Production

Environment variables:

```bash
# production.env
KAFKA_BOOTSTRAP_SERVERS=kafka-1.prod:9092,kafka-2.prod:9092,kafka-3.prod:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_USERNAME=prod-user
KAFKA_SASL_PASSWORD=secure-password
KAFKA_SASL_MECHANISM=SCRAM-SHA-256

# Application config
APP_ENV=production
LOG_LEVEL=INFO
```

### 5.2 Docker Setup

`Dockerfile.kafka`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-kafka.txt ./
RUN pip install -r requirements.txt -r requirements-kafka.txt

COPY . .

CMD ["python", "scripts/kafka_consumer.py", "--log-level", "INFO"]
```

`docker-compose.prod.yml`:

```yaml
version: '3'

services:
  kafka-consumer:
    build:
      context: .
      dockerfile: Dockerfile.kafka
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - LOG_LEVEL=INFO
    depends_on:
      - kafka
    restart: unless-stopped

  kafka-producer:
    image: confluentinc/cp-kafka:7.0.0
    # Topics management...
```

### 5.3 Monitoring Stakes

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, Gauge

kafka_messages_produced = Counter(
    'kafka_messages_produced_total',
    'Total messages produced',
    ['topic']
)

kafka_processing_time = Histogram(
    'kafka_processing_time_seconds',
    'Message processing time'
)

kafka_circuit_breaker_state = Gauge(
    'kafka_circuit_breaker_state',
    'Circuit breaker state',
    ['name']
)
```

## Phase 6: Operations

### 6.1 Monitoring Commands

```bash
# Check queue size
python -c "from backend.streaming.fallback import get_fallback_manager; print(get_fallback_manager().get_stats())"

# View circuit breaker status
python -c "from backend.streaming import get_circuit_breaker_manager; import json; print(json.dumps(get_circuit_breaker_manager().get_all_metrics(), indent=2))"

# List Kafka topics
kafka-topics --bootstrap-server localhost:9092 --list

# Check consumer group
kafka-consumer-groups --bootstrap-server localhost:9092 --group digital-pulse-processors --describe
```

### 6.2 Common Issues

**Queue Growing Too Fast:**
```bash
# Check fallback queue
ls -lh ./data/kafka_fallback_queue/ | wc -l

# Clear if needed (after backing up)
python -c "from backend.streaming.fallback import get_fallback_manager; get_fallback_manager().queue.clear_queue()"
```

**Consumer Lag:**
```bash
# Increase batch size
python scripts/kafka_consumer.py --batch 200

# Or run multiple consumer instances
docker-compose scale kafka-consumer=3
```

**Producer Failures:**
```bash
# Check circuit breaker
python -c "from backend.streaming import create_producer; p = create_producer(); print(p.get_circuit_breaker_status())"

# Force reset if stuck
python -c "from backend.streaming import create_producer; p = create_producer(); p.circuit_breaker.force_closed() if p.circuit_breaker else None"
```

## Validation Checklist

- [ ] Configuration loaded correctly
- [ ] Kafka topics created
- [ ] Producer can send messages
- [ ] Consumer can receive messages
- [ ] Circuit breaker opens on failures
- [ ] Fallback queue works
- [ ] Fallback queue retries on recovery
- [ ] Metrics collected
- [ ] Error logging working
- [ ] End-to-end pipeline tested

## References

- [Confluent Kafka Python Client](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [Circuit Breaker Pattern](https://en.wikipedia.org/wiki/Circuit_breaker)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Digital Pulse KAFKA_INTEGRATION.md](./KAFKA_INTEGRATION.md)
