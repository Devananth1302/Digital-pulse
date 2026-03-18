# Kafka Integration - Quick Reference

## 🎯 Essential Commands

### Start Kafka (Docker)
```bash
docker-compose -f docker-compose.kafka.yml up -d
```

### Check Status
```bash
docker-compose -f docker-compose.kafka.yml ps
```

### Stop Kafka
```bash
docker-compose -f docker-compose.kafka.yml down
```

### View Logs
```bash
docker-compose -f docker-compose.kafka.yml logs kafka
```

## 📝 Producer Commands

### Interactive Mode (stdin)
```bash
python scripts/kafka_producer.py --interactive
```

### From CSV File
```bash
python scripts/kafka_producer.py --csv data/posts.csv
```

### From JSON/JSONL File
```bash
python scripts/kafka_producer.py --json data/posts.jsonl
```

### Test Mode
```bash
python scripts/kafka_producer.py --test --stats
```

### Custom Topic
```bash
python scripts/kafka_producer.py --csv data.csv --topic my_topic
```

### Show Statistics
```bash
python scripts/kafka_producer.py --test --stats
```

## 📊 Consumer Commands

### Batch Processing (N messages, then exit)
```bash
python scripts/kafka_consumer.py --batch 50 --stats
```

### Continuous Processing
```bash
python scripts/kafka_consumer.py
```

### Dry Run (test, 10 messages max)
```bash
python scripts/kafka_consumer.py --dry-run
```

### Retry Fallback Queue
```bash
python scripts/kafka_consumer.py --retry-fallback
```

### Debug Mode
```bash
python scripts/kafka_consumer.py --log-level DEBUG
```

### Custom Topics
```bash
python scripts/kafka_consumer.py --input-topic raw_data --output-topic results
```

## 🔍 Debugging

### Check Kafka Topics
```bash
kafka-topics --bootstrap-server localhost:9092 --list
```

### Check Consumer Group
```bash
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group digital-pulse-processors --describe
```

### Reset Consumer Offset
```bash
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group digital-pulse-processors --reset-offsets --to-earliest --execute
```

### Check Circuit Breaker
```python
python -c "
from backend.streaming import create_producer
p = create_producer()
import json
print(json.dumps(p.get_circuit_breaker_status(), indent=2))
"
```

### Check Fallback Queue
```bash
ls -lah ./data/kafka_fallback_queue/
wc -l ./data/kafka_fallback_queue/*.json
```

### Clear Fallback Queue (WARNING!)
```python
python -c "
from backend.streaming.fallback import get_fallback_manager
fm = get_fallback_manager()
fm.queue.clear_queue()
print('Queue cleared')
"
```

## ⚙️ Configuration

### Main Config File
```
config/kafka_config.yaml
```

### Override Kafka Broker
```bash
export KAFKA_BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9092,kafka3:9092"
```

### Enable SASL/SSL
```bash
export KAFKA_SECURITY_PROTOCOL="SASL_SSL"
export KAFKA_SASL_USERNAME="your_user"
export KAFKA_SASL_PASSWORD="your_pass"
```

### Verify Config Loading
```python
python -c "
from config.kafka_settings import get_kafka_config
c = get_kafka_config()
print(f'Bootstrap: {c.security.bootstrap_servers}')
print(f'Topics: {list(c.topics.keys())}')
"
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `config/kafka_config.yaml` | YAML configuration |
| `config/kafka_settings.py` | Config manager |
| `backend/streaming/producer.py` | Producer wrapper |
| `backend/streaming/consumer.py` | Consumer wrapper |
| `backend/streaming/circuit_breaker.py` | Resilience pattern |
| `backend/streaming/fallback.py` | Fallback queue |
| `backend/adapters/analytics_adapter.py` | Analytics wrapper |
| `scripts/kafka_producer.py` | Producer CLI |
| `scripts/kafka_consumer.py` | Consumer CLI |
| `docker-compose.kafka.yml` | Docker setup |

## 📚 Documentation

| File | Content |
|------|---------|
| `docs/KAFKA_INTEGRATION.md` | Full architecture guide |
| `docs/KAFKA_IMPLEMENTATION_GUIDE.md` | Step-by-step setup |
| `docs/KAFKA_SUMMARY.md` | Executive summary |
| `docs/KAFKA_DEPLOYMENT_CHECKLIST.md` | Pre-deployment checks |
| `backend/streaming/README.md` | Module documentation |

## 🧪 Testing

### Run All Tests
```bash
pytest tests/test_kafka_examples.py -v
```

### Run Specific Test
```bash
pytest tests/test_kafka_examples.py::TestSchemaAdapter -v
```

### Run with Coverage
```bash
pytest tests/test_kafka_examples.py --cov=backend.streaming
```

## 📊 Metrics Queries

### Producer Stats
```python
from backend.streaming import create_producer
producer = create_producer()
print(producer.get_stats())
# Output: {'messages_sent': 100, 'messages_failed': 5, ...}
```

### Consumer Stats
```python
from backend.streaming import create_consumer
consumer = create_consumer()
print(consumer.get_metrics())
# Output: {'messages_received': 100, 'messages_processed': 95, ...}
```

### Circuit Breaker Status
```python
from backend.streaming import create_producer
producer = create_producer()
print(producer.get_circuit_breaker_status())
# Output: {'state': 'CLOSED', 'metrics': {...}}
```

### Fallback Queue Status
```python
from backend.streaming.fallback import get_fallback_manager
fm = get_fallback_manager()
print(fm.get_stats())
# Output: {'queue': {...}, 'last_retry': '...'}
```

## 🚨 Common Issues

### "Connection refused"
```bash
# Check if Kafka is running
docker-compose -f docker-compose.kafka.yml ps

# Start Kafka
docker-compose -f docker-compose.kafka.yml up -d
```

### "Circuit breaker stuck OPEN"
```python
from backend.streaming import create_producer
producer = create_producer()
producer.circuit_breaker.force_closed()
```

### "Queue growing too large"
```bash
# Check size
wc -l ./data/kafka_fallback_queue/*.json

# Retry processing
python scripts/kafka_consumer.py --retry-fallback

# Or clear if needed (after backing up)
python -c "from backend.streaming.fallback import get_fallback_manager; get_fallback_manager().queue.clear_queue()"
```

### "Consumer lag is high"
```bash
# Increase batch size
python scripts/kafka_consumer.py --batch 200

# Or run multiple instances
# (modify docker-compose to scale)
```

### "Messages not appearing in output topic"
```bash
# Check consumer is running
ps aux | grep kafka_consumer

# Check circuit breaker
python -c "from backend.streaming import create_consumer; c = create_consumer(); print(c.get_circuit_breaker_status())"

# Check metrics
python -c "from backend.streaming import create_consumer; print(create_consumer().get_metrics())"
```

## 🔗 Integration Template

### Add to FastAPI (for uploads)
```python
from backend.streaming import create_producer
from backend.streaming.fallback import get_fallback_manager

@app.post("/upload-csv")
async def upload_csv(file: UploadFile):
    # Save file
    filepath = f"uploads/{file.filename}"
    # ... save logic ...
    
    # Fallback
    fallback = get_fallback_manager()
    handler = lambda data: fallback.handle_producer_failure(data)
    
    # Produce
    producer = create_producer(fallback_handler=handler)
    success, failed = producer.produce_from_csv(filepath)
    producer.close()
    
    return {"success": success, "failed": failed}
```

### Add Consumer to Startup
```python
import asyncio

consumer_task = None

@app.on_event("startup")
async def startup():
    global consumer_task
    from backend.streaming import create_consumer
    consumer = create_consumer()
    consumer_task = asyncio.create_task(consumer.run(batch_size=10))

@app.on_event("shutdown")
async def shutdown():
    if consumer_task:
        consumer_task.cancel()
```

### Add Health Endpoint
```python
@app.get("/health/kafka")
async def kafka_health():
    from backend.streaming import get_circuit_breaker_manager
    from backend.streaming.fallback import get_fallback_manager
    
    return {
        "breakers": get_circuit_breaker_manager().get_all_metrics(),
        "queue": get_fallback_manager().get_stats(),
    }
```

## 🎯 Typical Workflow

### Development
```bash
# 1. Start Kafka
docker-compose -f docker-compose.kafka.yml up -d

# 2. Test producer
python scripts/kafka_producer.py --test --stats

# 3. Test consumer
python scripts/kafka_consumer.py --batch 10

# 4. Test fallback
docker stop kafka_kafka_1
python scripts/kafka_producer.py --test
docker start kafka_kafka_1
python scripts/kafka_consumer.py --retry-fallback
```

### Deployment
```bash
# 1. Install dependencies
pip install -r requirements-kafka.txt

# 2. Configure environment
export KAFKA_BOOTSTRAP_SERVERS="prod-kafka:9092"

# 3. Start consumer
python scripts/kafka_consumer.py &

# 4. Integrate producer in FastAPI
# (update api endpoints)

# 5. Monitor health
curl http://localhost:8000/health/kafka
```

## 📞 Support

**Documentation:** `docs/KAFKA_INTEGRATION.md`
**Quick Start:** `docs/KAFKA_IMPLEMENTATION_GUIDE.md`
**Module Docs:** `backend/streaming/README.md`
**Issues:** Check `docs/KAFKA_INTEGRATION.md` troubleshooting section

---

**Last Updated:** 2024-03-18
**Version:** 1.0
**Status:** Production Ready ✅
