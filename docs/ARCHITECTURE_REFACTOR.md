# Social Analytics Engine - Microservices Refactoring

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MODULAR MICROSERVICE PIPELINE                             │
│                      (Kafka-Based Communication)                             │
└─────────────────────────────────────────────────────────────────────────────┘

DATA SOURCES
    ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ DUAL-PATH INGESTION LAYER                                                 │
│ ┌─────────────────────┐  ┌──────────────────────┐                        │
│ │  Real-time Kafka   │  │  Historical Loader   │                        │
│ │  (raw_data topic)  │  │  (Disk/DB → Merge)   │                        │
│ └──────────┬──────────┘  └──────────┬───────────┘                        │
│            └──────────────┬─────────────┘                                 │
└────────────────────────────┼────────────────────────────────────────────┘
                             ↓
             ┌───────────────────────────────┐
             │  INGESTION PROCESSOR           │
             │  • Validate records            │
             │  • Parse timestamps            │
             │  • Extract metadata            │
             └──────────┬────────────────────┘
                        ↓
             ┌─────────────────────────────┐
             │ ingested_data topic         │
             └──────────┬──────────────────┘
                        ↓
             ┌───────────────────────────────┐
             │  NORMALIZATION PROCESSOR      │
             │  • Field standardization      │
             │  • Type conversion            │
             │  • Schema validation          │
             └──────────┬────────────────────┘
                        ↓
             ┌─────────────────────────────┐
             │ normalized_data topic       │
             └──────────┬──────────────────┘
                        ↓
        ┌───────────────────────────────────────┐
        │  FEATURE ENGINEERING PROCESSOR        │
        │  • Virality scoring                   │
        │  • Engagement metrics                 │
        │  • Time decay calculations            │
        │  • Momentum tracking                  │
        └──────────┬────────────────────────────┘
                   ↓
        ┌─────────────────────────────┐
        │ featured_data topic         │
        └──────────┬──────────────────┘
                   ↓
    ┌─────────────────────────────────────────┐
    │  HIERARCHICAL CLUSTERING PROCESSOR      │
    │  ┌────────────────────────────────┐    │
    │  │ Tier 1: Industry Classification │    │
    │  │ • Zero-Shot models             │    │
    │  │ • Major categories (Tech,      │    │
    │  │   Finance, Healthcare, etc)    │    │
    │  └────────────┬───────────────────┘    │
    │               ↓                         │
    │  ┌────────────────────────────────┐    │
    │  │ Tier 2: Sub-topic Detection    │    │
    │  │ • LDA or clustering within     │    │
    │  │   industry categories          │    │
    │  └────────────┬───────────────────┘    │
    └────────────────┬──────────────────────┘
                     ↓
    ┌──────────────────────────────┐
    │ clustered_data topic         │
    └──────────┬───────────────────┘
               ↓
    ┌────────────────────────────────┐
    │  TRENDING ENGINE PROCESSOR     │
    │  • Time windows (1h, 4h, 24h)  │
    │  • Weighted scoring:           │
    │    - Volume (count)            │
    │    - Velocity (rate)           │
    │    - Sentiment (polarity)      │
    │  • Top 5 extraction            │
    └──────────┬─────────────────────┘
               ↓
    ┌─────────────────────────────┐
    │ trending_signals topic      │
    └──────────┬──────────────────┘
               ↓
    ┌────────────────────────────────┐
    │  FORECASTING PROCESSOR         │
    │  • Trend prediction            │
    │  • Emerging signals            │
    │  • Future virality             │
    └──────────┬─────────────────────┘
               ↓
    ┌─────────────────────────────┐
    │ forecast_results topic      │
    └──────────┬──────────────────┘
               ↓
    OUTPUT STORAGE (Supabase DB)
```

## Module Responsibilities

### 1. Ingestion Processor (processor_ingestion.py)
- **Input**: Real-time Kafka stream OR historical files
- **Output**: ingested_data topic
- **Responsibilities**:
  - Parse CSV/JSON formats
  - Validate required fields
  - Extract metadata (source, timestamp)
  - No data transformation (pass-through validation only)

### 2. Normalization Processor (processor_normalization.py)
- **Input**: ingested_data topic
- **Output**: normalized_data topic
- **Responsibilities**:
  - Standardize field names across sources
  - Type conversion (strings → timestamps, ints)
  - Schema validation
  - Extract core fields (title, content, engagement)

### 3. Feature Engineering Processor (processor_features.py)
- **Input**: normalized_data topic
- **Output**: featured_data topic
- **Responsibilities**:
  - Calculate virality scores
  - Engagement totals and velocity
  - Time decay factors
  - Momentum tracking

### 4. Hierarchical Clustering Processor (processor_clustering.py)
- **Input**: featured_data topic
- **Output**: clustered_data topic
- **Responsibilities**:
  - **Tier 1**: Industry/category classification (Zero-Shot)
  - **Tier 2**: Sub-topic detection within categories (LDA/K-means)
  - Attach cluster labels to records

### 5. Trending Engine Processor (processor_trending.py)
- **Input**: clustered_data topic
- **Output**: trending_signals topic
- **Responsibilities**:
  - Time windowing (1h, 4h, 24h)
  - Weighted score calculation: volume×velocity×sentiment
  - Extract top-5 per window/category
  - No database writes (only Kafka output)

### 6. Historical Data Loader (historical_loader.py)
- **Input**: CSV/Parquet files, Kafka offsets
- **Output**: ingested_data topic
- **Responsibilities**:
  - Load historical datasets
  - Merge with real-time streams
  - Maintain offset tracking
  - Backfill models with historical context

## Kafka Topic Structure

```
Topic Name              | Partition Strategy        | Retention
─────────────────────────────────────────────────────────────────
raw_data                | By source_id (3-5 part)   | 7 days
ingested_data           | By post_id (10 part)      | 7 days
normalized_data         | By post_id (10 part)      | 7 days
featured_data           | By post_id (10 part)      | 7 days
clustered_data          | By industry (5 part)      | 7 days
trending_signals        | By time_window (3 part)   | 1 day
forecast_results        | By post_id (10 part)      | 30 days
```

## Scalability Strategy

### Multi-threaded Consumer Pattern
- Each processor runs multiple consumer threads (configurable: 3-10)
- ThreadPoolExecutor for async processing
- Per-partition thread affinity (avoid rebalancing)
- Batch processing within threads (size: 50-100 records)

### Horizontal Scaling
- Deploy N copies of each processor
- Kafka consumer groups handle distribution
- No shared state (except database for final writes)
- Stateless processors = infinite horizontal scale

## Historical Data Integration

```
Historical CSV/Parquet → Load to Memory
         ↓
Create "Historical" Kafka Partition
         ↓
Consume in parallel with Real-time
         ↓
Merge in aggregation windows
         ↓
Use both for model training context
```

## Trending News Algorithm

```
For each time window (1h, 4h, 24h):
  For each industry category:
    For each post in window:
      TrendScore = (
        0.3 × (volume / max_volume) +
        0.4 × (velocity / max_velocity) +
        0.3 × (sentiment_score / max_sentiment)
      )
    Rank by TrendScore
    Extract Top 5
    Output to trending_signals topic
```

## Configuration & Deployment

Each processor loads config from environment:
```
KAFKA_BOOTSTRAP_SERVERS
KAFKA_INPUT_TOPIC
KAFKA_OUTPUT_TOPIC
PROCESSOR_THREADS
BATCH_SIZE
WINDOW_SIZE_HOURS
```

No hardcoded values. All configuration via env vars or YAML.

## Error Handling & Resilience

- Dead Letter Queue (DLQ) topic for failed records
- Circuit breaker per processor
- Fallback to local queue if Kafka unavailable
- Structured logging at each step
- Metrics collection (throughput, latency, error rate)
