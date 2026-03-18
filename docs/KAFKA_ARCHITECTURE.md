# Kafka Integration - Architecture & Diagrams

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          KAFKA STREAMING SYSTEM                              │
│                    Digital Pulse Real-Time Data Processing                   │
└──────────────────────────────────────────────────────────────────────────────┘

                              ┌─ INGESTION LAYER ─┐
                              │                   │
        ┌─────────────────────────────────────────────────────┐
        │                 Data Sources                         │
        │  ┌────────┬────────┬────────┬──────────────────┐   │
        │  │  CSV   │  JSON  │  API   │  Real-time       │   │
        │  │ Files  │ Files  │ Feeds  │  Streams         │   │
        │  └────────┴────────┴────────┴──────────────────┘   │
        └─────────────────────────────────────────────────────┘
                                   ↓
                    ┌──────────────────────────────┐
                    │    Schema Adapter Layer       │
                    │  • Field Normalization        │
                    │  • Type Conversion            │
                    │  • Metadata Extraction        │
                    │  • Validation                 │
                    └────────────┬─────────────────┘
                                 ↓
        ┌────────────────────────────────────────────────────┐
        │          Resilience & Fallback                     │
        │  ┌──────────────────────────────────────────────┐ │
        │  │  Circuit Breaker (CLOSED→OPEN→HALF_OPEN)    │ │
        │  │  • Failure Detection                         │ │
        │  │  • Automatic State Management                │ │
        │  │  • Exponential Backoff                       │ │
        │  │  • Metrics Collection                        │ │
        │  └──────────────────┬───────────────────────────┘ │
        │                     ├──→ Fallback Queue (When Open)│
        │                     │    • Local JSON Storage     │
        │                     │    • Persistence            │
        │                     │    • Auto Retry             │
        │                     │    • Size Limited           │
        │                     ↓                             │
        │              Kafka Producer                        │
        │              • Batching                            │
        │              • Compression                         │
        │              • Serialization                       │
        └────────────────┬─────────────────────────────────┘
                         ↓
        ╔═════════════════════════════════════════════════════╗
        ║         KAFKA MESSAGE BROKER CLUSTER                ║
        ║                                                     ║
        ║  Topic: raw_data                                    ║
        ║  ┌──────────────────────────────────────┐          ║
        ║  │  Partition 0  │  Partition 1  │  P2 │          ║
        ║  │  Offset 0   ..│  Offset 0   ..│     │          ║
        ║  │  ↓           │  ↓           │     │          ║
        ║  │ [Messages]   │ [Messages]   │     │          ║
        ║  └──────────────────────────────────────┘          ║
        ║                                                     ║
        ║  Retention: 7 days | Replication: 1                │
        ║  Compression: snappy                               │
        ╚════════────────┬──────────────────────────────────╝
                         ↓
        ┌────────────────────────────────────────────────────┐
        │          Stream Processing Layer                   │
        │  ┌────────────────────────────────────────────┐   │
        │  │  Kafka Consumer                            │   │
        │  │  • Message Polling                         │   │
        │  │  • Batch/Continuous Processing             │   │
        │  │  • Deserialization                         │   │
        │  │  • Manual Offset Commits (Exactly-once)    │   │
        │  │  • Dead Letter Queue Support               │   │
        │  └────────────────┬───────────────────────────┘   │
        │                   ↓                                 │
        │  ┌────────────────────────────────────────────┐   │
        │  │  Stream Processor                          │   │
        │  │  • Passes to Analytics Adapter             │   │
        │  │  • Error Handling                          │   │
        │  │  • Metrics Collection                      │   │
        │  └────────────────┬───────────────────────────┘   │
        │                   ↓                                 │
        │  ┌────────────────────────────────────────────┐   │
        │  │  Analytics Adapter → Existing Functions    │   │
        │  │  ┌─────────────────────────────────────┐  │   │
        │  │  │ • Calculate Virality Score          │  │   │
        │  │  │ • Narrative Clustering (BERTopic)   │  │   │
        │  │  │ • Detect Emerging Signals           │  │   │
        │  │  │ • Generate Forecasts                │  │   │
        │  │  │ (All wrapped, no modifications)     │  │   │
        │  │  └──────────────┬─────────────────────┘  │   │
        │  │                 ↓                         │   │
        │  │  Processed Results Composition            │   │
        │  │  • Post ID, Title, Content               │   │
        │  │  • All Calculated Metrics                 │   │
        │  │  • Timestamp, Source                      │   │
        │  │  • Operation Log                          │   │
        │  └────────────────┬───────────────────────────┘   │
        │                   ↓                                 │
        │              Kafka Producer                        │
        │              (Output Results)                      │
        └────────────────┬──────────────────────────────────┘
                         ↓
        ╔═════════════════════════════════════════════════════╗
        ║    KAFKA TOPIC: processed_results                  ║
        ║                                                     ║
        ║    Partition 0  │  Partition 1  │  Partition 2    ║
        ║    [Results]    │  [Results]    │  [Results]      ║
        ╚════════────────┬──────────────────────────────────╝
                         ↓
        ┌────────────────────────────────────────────────────┐
        │      Output Storage & Consumption                  │
        │  • Supabase Database                               │
        │  • API Endpoints                                   │
        │  • Dashboard Display                               │
        │  • PDF Reports                                     │
        └────────────────────────────────────────────────────┘
```

## Circuit Breaker State Machine

```
                    ┏━━━━━━━━━━━━━━━━┓
                    ┃    CLOSED       ┃  ✓ Normal Operation
                    ┃  (Requests      ┃
                    ┃   pass through) ┃
                    ┗────────┬────────┛
                             │
                    [Failure Rate High]
                    [or Consecutive Failures]
                             ↓
                    ┏━━━━━━━━━━━━━━━━┓
                    ┃     OPEN        ┃  ✗ All Requests Blocked
                    ┃  (Fast Fail)    ┃     Fallback Activated
                    ┃                 ┃
                    ┃  Return Error   ┃
                    ┃  (No DB calls)  ┃
                    ┗────────┬────────┛
                             │
                    [Timeout Elapsed]
                    [~60 seconds]
                             ↓
                    ┏━━━━━━━━━━━━━━━━┓
                    ┃  HALF_OPEN      ┃  ⚠ Testing Recovery
                    ┃  (Limited       ┃
                    ┃   requests)     ┃
                    ┗────────┬────────┘
                             │
            [Success] ╱       │       ╲ [Failure]
                     ╱        │        ╲
                    ↓         │         ↓
            ┌──────────┐      │      ┌──────────┐
            │  CLOSED  │      │      │   OPEN   │
            │ (Reset)  │      │      │ (Back to │
            └──────────┘      │      │  blocking)
                          [Repeat]   └──────────┘
```

## Data Flow Example: CSV Ingestion

```
1. USER ACTION
   └─→ python scripts/kafka_producer.py --csv posts.csv

2. PRODUCER INITIALIZATION
   ├─→ Load config (YAML + env vars)
   ├─→ Create circuit breaker
   └─→ Initialize Kafka producer

3. CSV PROCESSING
   ├─→ Read file line by line
   ├─→ For each row:
   │  ├─→ NORMALIZE via SchemaAdapter
   │  │  ├─→ Extract: id, title, content, timestamp
   │  │  ├─→ Map engagement: likes,shares,comments
   │  │  ├─→ Type conversion & validation
   │  │  └─→ Preserve custom fields as metadata
   │  │
   │  ├─→ SERIALIZE
   │  │  ├─→ Convert to JSON
   │  │  └─→ Encode as UTF-8 bytes
   │  │
   │  ├─→ PRODUCE via CIRCUIT BREAKER
   │  │  ├─→ Call breaker.call(producer.produce, data)
   │  │  │
   │  │  ├─→ IF CLOSED (Normal):
   │  │  │   ├─→ Send to Kafka
   │  │  │   ├─→ Wait for acknowledgment
   │  │  │   ├─→ Increment metric: messages_sent
   │  │  │   └─→ Continue
   │  │  │
   │  │  ├─→ ELSE IF OPEN (Failed):
   │  │  │   ├─→ Call fallback_handler()
   │  │  │   ├─→ Queue to ./data/kafka_fallback_queue/
   │  │  │   ├─→ Increment metric: messages_queued
   │  │  │   └─→ Return success (will retry later)
   │  │  │
   │  │  └─→ ON FAILURE:
   │  │      ├─→ Update failure count
   │  │      ├─→ Check if threshold exceeded
   │  │      ├─→ IF YES: Open circuit
   │  │      ├─→ Call fallback_handler()
   │  │      └─→ Increment: messages_failed
   │  │
   │  └─→ NEXT ROW

4. COMPLETION
   ├─→ Display statistics
   │  ├─→ Total: 1000
   │  ├─→ Sent: 998
   │  ├─→ Failed: 2
   │  ├─→ Fallback Queued: 2
   │  └─→ Circuit Breaker: CLOSED
   │
   └─→ Producer closed (flush remaining)
```

## Data Flow Example: Message Processing

```
1. CONSUMER POLLING
   └─→ kafka_consumer.poll(timeout=5s)
       └─→ Returns message from raw_data topic

2. MESSAGE RECEIVED
   ├─→ Metadata: topic, partition, offset, key
   └─→ Value: serialized JSON bytes

3. DESERIALIZATION
   ├─→ Decode UTF-8 bytes → JSON string
   ├─→ Parse JSON → Python dict
   └─→ Extract: key, value, headers, timestamp

4. NORMALIZATION
   └─→ SchemaAdapter.normalize_post_data(data)
       ├─→ Extract fields (handling variations)
       ├─→ Convert types (string → int, ISO → datetime)
       ├─→ Validate required fields
       └─→ Preserve metadata

5. PROCESSING via ANALYTICS ADAPTER
   ├─→ AnalyticsAdapter.calculate_virality_score()
   │  ├─→ Call: calculate_engagement_total()
   │  ├─→ Call: calculate_engagement_velocity()
   │  ├─→ Call: calculate_virality_score()
   │  └─→ Return: {virality_score: X, engagement_total: Y, ...}
   │
   └─→ Merge results with original data
       └─→ Create processed result document

6. RESULT SERIALIZATION
   ├─→ Convert to JSON
   ├─→ Create KafkaMessage
   └─→ Serialize to bytes

7. OUTPUT PRODUCTION
   ├─→ Produce to processed_results topic
   ├─→ Wait for acknowledgment
   └─→ Increment metric: messages_produced

8. OFFSET COMMIT (Exactly-once)
   ├─→ Manual commit (enable_auto_commit=False)
   ├─→ Offset stored after processing complete
   └─→ Crash-safe: offset only committed if processing successful

9. METRICS UPDATE
   └─→ Increment: messages_processed

10. ERROR HANDLING (if any step fails)
    ├─→ Create error message with details
    ├─→ Send to DLQ topic
    ├─→ Increment: messages_dlq
    └─→ Continue with next message
```

## Fallback Queue Flow

```
PRODUCER FAILURE DETECTION
        │
        ├─→ Network Timeout
        ├─→ Connection Refused
        ├─→ Circuit Breaker OPEN
        └─→ Any Producer Exception
        │
        ↓
CIRCUIT BREAKER OPENS
        │
        ↓
FALLBACK HANDLER ACTIVATED
        │
        └─→ fallback.handle_producer_failure(data)
            │
            ↓
            CREATE QueuedMessage
            ├─→ message_id: UUID
            ├─→ data: {...}
            ├─→ timestamp: now
            ├─→ retry_count: 0
            └─→ last_error: null
            │
            ↓
            SAVE TO DISK
            └─→ ./data/kafka_fallback_queue/{message_id}.json
                ├─→ Create file atomically
                ├─→ Check queue size limit
                └─→ Log file saved
            │
            ↓
APPLICATION CONTINUES RUNNING
(Zero downtime - buffered in local storage)
            │
            ↓
FALLBACK RETRY LOGIC (Background)
            │
            ├─→ Every retry_interval_seconds (default: 30s)
            │
            ├─→ Check: Is Kafka available?
            │
            ├─→ IF YES:
            │   ├─→ Load messages from queue
            │   ├─→ For each message:
            │   │   ├─→ Try to produce to Kafka
            │   │   ├─→ IF SUCCESS: Delete file, retry_count=0
            │   │   ├─→ IF FAIL: Increment retry_count
            │   │   └─→ IF retry_count > max_retries: Delete & log
            │   │
            │   └─→ Report metrics
            │
            └─→ IF NO:
                └─→ Continue waiting
```

## Resilience Patterns

### Pattern 1: Graceful Degradation
```
Normal Mode:
  Data → Kafka → Processing → Results → DB
  (Fast, real-time)

Degraded Mode (Kafka Down):
  Data → Local Queue → Processing Resumes → DB
  (Slower, but zero data loss)
```

### Pattern 2: Bulkhead Pattern
```
Each consumer batch processing in isolation:
  Batch 1: [Msg1, Msg2, Msg3] → Process independently
  Batch 2: [Msg4, Msg5, Msg6] → Process independently
  Batch 3: [Msg7, Msg8, Msg9] → Process independently

If one batch fails, others continue
```

### Pattern 3: Exponential Backoff
```
Attempt 1: Failure → Wait 100ms
Attempt 2: Failure → Wait 200ms
Attempt 3: Failure → Wait 400ms
Attempt 4: Failure → Wait 800ms
...
Max Wait: 10000ms (10 seconds)
```

## Deployment Topology

```
DEVELOPMENT
┌─────────────────────────────────────┐
│  Local Kafka (Docker Compose)       │
│  - Zookeeper + Kafka + Kafka UI     │
│  - Single broker                    │
│  - PLAINTEXT security               │
└─────────────────────────────────────┘
        ↑       ↑       ↑
        │       │       │
┌───────┴───┬───┴───┬───┴────────┐
│  Producer │Consumer│  App       │
│  Script   │ Script │  (Local)   │
└───────────┴───────┴────────────┘


PRODUCTION
┌─────────────────────────────────────────────────────┐
│  Managed Kafka Cluster (Confluent/AWS/Bitnami)     │
│  - 3+ Brokers (HA)                                 │
│  - Zookeeper Quorum                                │
│  - SASL/SSL Security                               │
│  - Monitoring & Alerting                           │
└─────────────────────────────────────────────────────┘
    ↑       ↑         ↑          ↑           ↑
    │       │         │          │           │
┌───┴──┬────┴──┬──────┴───┬──────┴─┬────────┴────┐
│ App  │  API  │ Consumer │ Fallback│  Monitoring│
│Upload│ Data  │ Service  │ Handler │  (Metrics) │
└──────┴───────┴──────────┴─────────┴────────────┘
```

## Settings & Configuration Hierarchy

```
DEFAULT (Hardcoded in Code)
        ↓ (Override if YAML exists)
YAML Config File (config/kafka_config.yaml)
        ↓ (Override if env var set)
ENVIRONMENT VARIABLES
        ↓
FINAL CONFIG (Used by Application)

Example:
  Default: bootstrap_servers = "localhost:9092"
  YAML:    bootstrap_servers = "kafka:29092"
  ENV:     export KAFKA_BOOTSTRAP_SERVERS="prod-kafka:9092"
  Final:   "prod-kafka:9092"  ← This is used
```

---

This architecture ensures:
- **Resilience:** Circuit breaker + fallback queue
- **Scalability:** Partitioned topics + consumer groups
- **Observability:** Metrics at every layer
- **Maintainability:** Clear separation of concerns
- **Zero downtime:** Graceful degradation when Kafka unavailable
- **Data safety:** No message loss with persistent fallback queue
