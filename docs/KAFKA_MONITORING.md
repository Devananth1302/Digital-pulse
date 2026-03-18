# Kafka Integration - Monitoring & Observability

## Key Metrics to Monitor

### Producer Metrics

```
Metric Name                 | Type      | Description
─────────────────────────────────────────────────────────
messages_sent              | Counter   | Total messages successfully sent to Kafka
messages_failed            | Counter   | Messages that failed to send
messages_queued            | Counter   | Messages sent to fallback queue
batch_size_bytes           | Gauge     | Current batch size before send
producer_latency_ms        | Histogram | Time from receive to Kafka ACK
circuit_breaker_state      | Enum      | CLOSED/OPEN/HALF_OPEN
failure_rate               | Gauge     | Current failure rate (%)
kafka_availability         | Boolean   | Can reach Kafka broker
fallback_queue_size        | Gauge     | Messages waiting in fallback
fallback_queue_disk_usage  | Gauge     | Disk space used by queue files
```

### Consumer Metrics

```
Metric Name                | Type      | Description
───────────────────────────────────────────────────────
messages_received          | Counter   | Total messages consumed from Kafka
messages_processed         | Counter   | Successfully processed messages
messages_failed            | Counter   | Processing failures
messages_dlq               | Counter   | Sent to Dead Letter Queue
processing_latency_ms      | Histogram | Time to process single message
batch_processing_latency   | Histogram | Time to process entire batch
lag_offset                 | Gauge     | Consumer lag (current offset vs latest)
rebalance_count            | Counter   | Consumer group rebalances
processing_error_rate      | Gauge     | Errors as percentage of total
```

### System Health Metrics

```
Metric Name                | Type      | Description
───────────────────────────────────────────────────────
cpu_usage_percent          | Gauge     | CPU utilization of producer/consumer
memory_usage_bytes         | Gauge     | RAM used by producer/consumer
disk_free_bytes            | Gauge     | Available disk for fallback queue
kafka_connection_errors    | Counter   | Failed connection attempts
network_latency_ms         | Gauge     | Network round-trip time to Kafka
database_queries_latency   | Histogram | Supabase query times
```

## Monitoring Setup

### Option 1: Prometheus + Grafana

**Installation:**
```bash
# Add Prometheus and Grafana to docker-compose.kafka.yml
docker-compose -f docker-compose.kafka.yml up -d prometheus grafana
```

**Configuration (prometheus.yml):**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'kafka-integration'
    static_configs:
      - targets: ['localhost:8000']  # FastAPI app endpoint
```

**Grafana Dashboard:**
```json
{
  "dashboard": {
    "title": "Kafka Integration Health",
    "panels": [
      {
        "title": "Messages Processed (1h)",
        "targets": [
          {"expr": "increase(messages_processed[1h])"}
        ]
      },
      {
        "title": "Circuit Breaker State",
        "targets": [
          {"expr": "circuit_breaker_state"}
        ]
      },
      {
        "title": "Fallback Queue Size",
        "targets": [
          {"expr": "fallback_queue_size"}
        ]
      },
      {
        "title": "Processing Latency P95",
        "targets": [
          {"expr": "histogram_quantile(0.95, processing_latency_ms)"}
        ]
      }
    ]
  }
}
```

### Option 2: CloudWatch (AWS)

**Setup in FastAPI app:**
```python
from watchtower import CloudWatchLogHandler
import logging

# Configure CloudWatch
handler = CloudWatchLogHandler()
logger = logging.getLogger(__name__)
logger.addHandler(handler)

# Metrics
cloudwatch = boto3.client('cloudwatch')

def emit_metric(metric_name, value):
    cloudwatch.put_metric_data(
        Namespace='DigitalPulse/Kafka',
        MetricData=[{
            'MetricName': metric_name,
            'Value': value,
            'Unit': 'Count',
            'Timestamp': datetime.now()
        }]
    )
```

### Option 3: Application Insights (Azure)

**Configuration:**
```python
from applicationinsights import TelemetryClient

tc = TelemetryClient('INSTRUMENTATION_KEY')

tc.track_event('MessageProcessed', {
    'topic': 'raw_data',
    'partition': 0,
    'offset': 12345,
    'latency_ms': 45
})

tc.track_metric('CircuitBreakerState', 
    1,  # 1=CLOSED, 0=OPEN, 0.5=HALF_OPEN
    properties={'service': 'kafka-producer'}
)
```

## Alerting Rules

### Alert 1: High Failure Rate
```yaml
alert: HighKafkaFailureRate
expr: failure_rate > 50
for: 5m
annotations:
  summary: "Kafka producer failure rate above 50%"
  description: "{{ $value }}% of messages failed in last 5 minutes"
  action: "Check Kafka broker logs, network connectivity, and configuration"
```

### Alert 2: Circuit Breaker Open
```yaml
alert: CircuitBreakerOpen
expr: circuit_breaker_state == 0  # OPEN
for: 1m
annotations:
  summary: "Kafka circuit breaker is OPEN"
  description: "Producer circuit breaker opened at {{ $timestamp }}"
  action: "Investigate Kafka connectivity, restart producer if needed"
```

### Alert 3: Fallback Queue Growing
```yaml
alert: FallbackQueueGrowing
expr: increase(fallback_queue_size[5m]) > 100
for: 5m
annotations:
  summary: "Fallback queue growing faster than recovery"
  description: "{{ $value }} messages queued in last 5 minutes"
  action: "Kafka down for extended period, escalate to infrastructure team"
```

### Alert 4: Consumer Lag
```yaml
alert: HighConsumerLag
expr: lag_offset > 10000
for: 10m
annotations:
  summary: "Consumer more than 10k messages behind"
  description: "Lag: {{ $value }} messages"
  action: "Scale consumer instances or check processing performance"
```

### Alert 5: Processing Errors
```yaml
alert: HighProcessingErrorRate
expr: (messages_failed / messages_processed) > 0.05
for: 5m
annotations:
  summary: "Processing error rate above 5%"
  description: "{{ $value | humanizePercentage }} of messages failing"
  action: "Check analytics functions, data schema changes, database issues"
```

### Alert 6: Disk Space
```yaml
alert: LowDiskSpace
expr: disk_free_bytes < 5368709120  # 5GB
for: 1m
annotations:
  summary: "Disk space low for fallback queue"
  description: "{{ $value | humanize }}B remaining"
  action: "Clean old fallback queue files or expand storage"
```

## Health Checks

### HTTP Health Endpoint

**Add to FastAPI (backend/main.py):**
```python
from fastapi import APIRouter, HTTPException

health_router = APIRouter(prefix="/health", tags=["health"])

@health_router.get("/kafka/producer")
async def health_producer():
    """Check producer connectivity"""
    return {
        "status": "healthy",
        "kafka_available": kafka_producer.is_healthy(),
        "circuit_breaker_state": kafka_producer.breaker.state.name,
        "messages_sent": kafka_producer.metrics.messages_sent,
        "messages_queued": kafka_producer.metrics.messages_queued,
    }

@health_router.get("/kafka/consumer")
async def health_consumer():
    """Check consumer status"""
    return {
        "status": "healthy",
        "consumer_active": consumer_app.is_running,
        "lag_offset": consumer_app.get_lag(),
        "messages_processed": consumer_app.metrics.messages_processed,
        "messages_failed": consumer_app.metrics.messages_failed,
    }

@health_router.get("/kafka/fallback")
async def health_fallback():
    """Check fallback queue status"""
    return {
        "status": "healthy",
        "queue_size": fallback_manager.get_queue_size(),
        "disk_usage_bytes": fallback_manager.get_disk_usage(),
        "pending_retry": fallback_manager.get_pending_count(),
    }

app.include_router(health_router)
```

**Usage:**
```bash
# Check producer
curl http://localhost:8000/health/kafka/producer

# Check consumer
curl http://localhost:8000/health/kafka/consumer

# Check fallback
curl http://localhost:8000/health/kafka/fallback

# Load balancer / K8s health probe
curl http://localhost:8000/health/kafka/producer 2>/dev/null | \
  jq -e '.status == "healthy"'
```

## Logging Setup

### Log Levels & Configuration

**Development:**
```python
import logging

# Verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Kafka library logging
logging.getLogger('confluent_kafka').setLevel(logging.DEBUG)
```

**Production:**
```python
# Structured logging
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()
log.msg("event", status="success", latency_ms=45)
```

### Log Examples

**Producer Log Pattern:**
```
2024-01-15T10:23:45.123Z [producer] INFO Batch produced
  batch_id: b3c2d8f5-e1a2-4c9d-b7e3-f2c8a1d9e4b5
  messages: 1000
  bytes: 524288
  latency_ms: 234
  circuit_breaker: CLOSED

2024-01-15T10:24:01.456Z [producer] WARN Circuit breaker opening
  failure_rate: 51%
  consecutive_failures: 3
  action: fallback_activated

2024-01-15T10:24:15.789Z [fallback] INFO Message queued locally
  message_id: m8f3d7c2-b1e4-4a9c-d5e2-f3c7b8a1d9e6
  queue_size: 45
  retry_scheduled: 2024-01-15T10:24:45.789Z
```

**Consumer Log Pattern:**
```
2024-01-15T10:25:00.123Z [consumer] INFO Processing batch
  batch_id: c4d9e3f8-a2b5-4c1f-d8e4-a3d6c7b2e5f1
  messages: 500
  partition: 0
  offset_start: 10000
  offset_end: 10500

2024-01-15T10:25:05.456Z [analytics] INFO Virality calculated
  post_id: p7e2d5c3-b8a1-4f9d-c6e2-d3f4a5b8c1d7
  virality_score: 87.5
  engagement_total: 1245
  latency_ms: 12

2024-01-15T10:25:10.789Z [consumer] ERROR Processing failed
  message_id: m9f4e8d3-c2f5-4d0e-e7f3-a4d7c8b1e2f5
  error: "ValidationError: missing field 'title'"
  action: sent_to_dlq
```

## Observability Dashboard Queries

### Prometheus Query Examples

```
# Messages sent per second (1m average)
rate(messages_sent[1m])

# Messages failed per second (5m average)
rate(messages_failed[5m])

# Fallback queue growth rate
increase(messages_queued[5m])

# Processing latency 95th percentile
histogram_quantile(0.95, processing_latency_ms)

# Consumer lag in seconds
lag_offset / 10  # Assuming ~10 messages/sec

# Circuit breaker state over time
circuit_breaker_state

# Error rate percentage
(messages_failed / messages_processed) * 100

# Total throughput (messages/sec)
rate(messages_processed[1m])

# Fallback queue as % of max capacity
(fallback_queue_size / max_fallback_queue_size) * 100
```

### Dashboard Panels

1. **Throughput Panel**
   - X-axis: Time (last 24h)
   - Y-axis: Messages/second
   - Lines: Sent, Processed, Failed (stacked)
   - Color: Green (sent), Blue (processed), Red (failed)

2. **Circuit Breaker Status Panel**
   - Display: Current state with color
   - Green: CLOSED (normal)
   - Red: OPEN (failing)
   - Yellow: HALF_OPEN (recovering)
   - Transitions: Show last 10 state changes with timestamps

3. **Latency Panel**
   - Display: P50, P95, P99 latency (ms)
   - Sparkline showing trend
   - Alert if P95 > 500ms

4. **Queue Status Panel**
   - Gauge: Fallback queue size vs max
   - Counter: Files pending retry
   - Timeline: Last flush timestamp

5. **Error Analysis Panel**
   - Table: Top 10 error types
   - Chart: Error rate trend (%)
   - Links: DLQ message browser

## Debugging Tips

### Check Producer Status
```bash
curl -s http://localhost:8000/health/kafka/producer | jq .
```

### Check Consumer Status
```bash
curl -s http://localhost:8000/health/kafka/consumer | jq .
```

### View Fallback Queue
```bash
ls -lah ./data/kafka_fallback_queue/ | head -20
cat ./data/kafka_fallback_queue/message_*.json | jq .
```

### Monitor Real-time Logs
```bash
tail -f /var/log/kafka-integration/producer.log | jq .
tail -f /var/log/kafka-integration/consumer.log | jq .
```

### Test Kafka Connectivity
```python
from confluent_kafka import Producer
import socket

# Check network
socket.create_connection(('kafka-broker', 9092), timeout=5)

# Check producer
p = Producer({'bootstrap.servers': 'kafka-broker:9092'})
p.produce('test', 'test')
p.flush()
```

### Distributed Tracing Setup

**Using Jaeger:**
```python
from jaeger_client import Config
from opentelemetry import trace

config = Config(
    config={
        'sampler': {'type': 'const', 'param': 1},
        'logging': True,
    },
    service_name="digital-pulse-kafka"
)
config.initialize_tracer()

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_message") as span:
    span.set_attribute("kafka.partition", 0)
    span.set_attribute("kafka.offset", 12345)
    # processing logic
```

---

**Recommendation:** Start with basic metrics (messages sent/processed/failed, circuit breaker state, queue size) and add detailed observability as needs become clear.
