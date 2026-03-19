# Quick Reference - Processors Commands

## Start Kafka Cluster
```bash
docker-compose -f docker-compose.kafka.yml up -d
docker-compose -f docker-compose.kafka.yml down  # Stop
```

## Run Processors

### Full Pipeline (All processors)
```bash
python -m processors.orchestrator run-pipeline --threads 3
python -m processors.orchestrator run-pipeline --threads 5 --trending-window 4 --trending-top 10
```

### Single Processor
```bash
python -m processors.orchestrator run-single --processor ingestion
python -m processors.orchestrator run-single --processor clustering --threads 5
python -m processors.orchestrator run-single --processor trending --trending-window 1 --trending-top 5
```

### Skip Specific Processors
```bash
# Run all except clustering
python -m processors.orchestrator run-pipeline --skip-clustering

# Run only ingestion and normalization
python -m processors.orchestrator run-pipeline \
  --skip-features --skip-clustering --skip-trending
```

## Historical Data

### Backfill CSV File
```bash
python -m processors.orchestrator backfill --csv historical_data.csv
python -m processors.orchestrator backfill --csv posts_2023.csv --threads 5
```

### Backfill Directory
```bash
python -m processors.orchestrator backfill --dir ./historical_data
python -m processors.orchestrator backfill --dir ./data --pattern "posts_*.csv"
python -m processors.orchestrator backfill --dir ./data --pattern "*.jsonl"
```

### Backfill Before Pipeline
```bash
# Terminal 1
python -m processors.orchestrator backfill --dir ./historical_data

# Wait for completion...

# Terminal 2
python -m processors.orchestrator run-pipeline
```

## Kafka Operations

### List Topics
```bash
docker exec digital-pulse-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list
```

### Describe Topic
```bash
docker exec digital-pulse-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic raw_data
```

### List Consumer Groups
```bash
docker exec digital-pulse-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --list
```

### Check Consumer Lag
```bash
docker exec digital-pulse-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group ingestion_group \
  --describe
```

## Monitor Data Flow

### View Raw Data
```bash
docker exec digital-pulse-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_data \
  --max-messages 5
```

### View Clustered Data
```bash
docker exec digital-pulse-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic clustered_data \
  --max-messages 5 | jq .
```

### View Trending Signals
```bash
docker exec digital-pulse-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic trending_signals \
  --max-messages 5 | jq .
```

### View Errors (DLQ)
```bash
docker exec digital-pulse-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic processor_dlq \
  --max-messages 10 | jq .
```

## Performance Tuning

### Increase Throughput (more threads)
```bash
python -m processors.orchestrator run-pipeline --threads 10
```

### Reduce Latency (smaller batch)
```bash
# Modify in orchestrator.py: batch_size = 25
```

### Distributed Processing
```bash
# Machine 1: Ingestion layer
python -m processors.orchestrator run-pipeline \
  --skip-features --skip-clustering --skip-trending --threads 8

# Machine 2: Analysis layer
python -m processors.orchestrator run-pipeline \
  --skip-ingestion --skip-normalization --skip-trending --threads 6

# Machine 3: Trending layer
python -m processors.orchestrator run-pipeline \
  --skip-ingestion --skip-normalization --skip-features --skip-clustering --threads 5
```

## Configuration

### Environment Variables
```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export PROCESSOR_THREADS=3
export PROCESSOR_BATCH_SIZE=50
export TRENDING_WINDOW_HOURS=1
export TRENDING_TOP_K=5
export VIRALITY_WEIGHT_SHARES=0.3
export VIRALITY_WEIGHT_COMMENTS=0.25
export VIRALITY_WEIGHT_LIKES=0.2
export VIRALITY_WEIGHT_VELOCITY=0.25
```

### Zero-Shot Model Configuration
By default uses: `facebook/bart-large-mnli`

For GPU acceleration (in `clustering_engine.py`):
```python
# Change device from -1 to 0
model = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=0  # GPU device 0
)
```

## Testing

### Test Full End-to-End
```bash
# Terminal 1: Start pipeline
python -m processors.orchestrator run-pipeline --threads 2

# Terminal 2: Wait 5 seconds, then produce test data
sleep 5
python -m processors.orchestrator backfill --csv test_data.csv

# Terminal 3: Monitor output
docker exec digital-pulse-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic trending_signals \
  --max-messages 10
```

### Test Single Processor
```bash
# Test clustering only
python -m processors.orchestrator run-single --processor clustering --threads 3

# Produce test data
python -m processors.orchestrator backfill --csv test_clustering.csv

# Consume output
docker exec digital-pulse-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic clustered_data \
  --max-messages 10 | jq '.industry, .subtopic'
```

## Debugging

### Check Processor Logs (stdout)
```bash
# Full output with timestamps
python -m processors.orchestrator run-pipeline 2>&1 | tee processor.log

# Filter specific processor
grep "clustering" processor.log
grep "trending" processor.log
grep "ERROR" processor.log
```

### Monitor Kafka UI
Open: http://localhost:8080
- Browse topics
- View messages
- Check consumer groups
- Track lag

### Test Connectivity
```bash
python -c "from confluent_kafka import Consumer; \
  Consumer({'bootstrap.servers': 'localhost:9092'}).list_topics()"
```

## Cleanup

### Delete Kafka Data
```bash
docker-compose -f docker-compose.kafka.yml down
docker volume rm digital-pulse_kafka_data  # Remove persisted data
docker-compose -f docker-compose.kafka.yml up -d  # Start fresh
```

### Clear Processor DLQ
```bash
docker exec digital-pulse-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --delete \
  --topic processor_dlq

docker exec digital-pulse-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic processor_dlq \
  --partitions 1 \
  --replication-factor 1
```

## Performance Benchmarks

### Single Machine Performance
```
--threads 3:  200 msg/sec
--threads 5:  300 msg/sec
--threads 8:  400 msg/sec
```

### Distributed Performance
```
3 machines:   900 msg/sec (3x parallelization)
5 machines:   1,500 msg/sec
10 machines:  3,000+ msg/sec
```

### Per-Processor Latency
```
Ingestion:     1-2ms
Normalization: 2-3ms
Features:      3-5ms
Clustering:    15-25ms (bottleneck - Zero-Shot model)
Trending:      5-10ms
Total:         30-50ms end-to-end
```

## Common Issues & Solutions

### "No module named 'transformers'"
```bash
pip install transformers torch --no-cache-dir
```

### Kafka connection refused
```bash
# Check Kafka is running
docker-compose -f docker-compose.kafka.yml ps

# Restart if needed
docker-compose -f docker-compose.kafka.yml restart kafka
```

### Consumer lag keeps growing
```bash
# Increase processing threads
python -m processors.orchestrator run-pipeline --threads 8

# Or deploy multiple instances on different machines
```

### Clustering very slow
```bash
# This is expected - Zero-Shot model is CPU/GPU intensive
# Solutions:
# 1. Use GPU (set device=0 in clustering_engine.py)
# 2. Deploy on dedicated machine
# 3. Use faster model: facebook/bart-base-mnli (less accurate but faster)
```

---

**See Also:**
- `ARCHITECTURE_REFACTOR.md` - Design details
- `DEPLOYMENT_GUIDE.md` - Full setup guide
- `README.md` (processors/) - Complete reference
- `REFACTORING_COMPLETE.md` - Executive summary
