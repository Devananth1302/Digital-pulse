"""Historical Data Loader - Dual-path ingestion system.

Loads historical datasets from disk/database and merges them with
real-time Kafka streams, ensuring analytical models use both for context.

Responsibilities:
1. Load historical CSV/Parquet files
2. Publish to raw_data topic for processing
3. Track offsets for backfill synchronization
4. Provide unified API for historical + real-time consumption
"""

import logging
import json
import csv
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from confluent_kafka import Producer
from config.kafka_settings import get_kafka_config

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Loads and publishes historical datasets."""
    
    def __init__(self, kafka_topic: str = "raw_data"):
        """Initialize loader.
        
        Args:
            kafka_topic: Target Kafka topic for publishing
        """
        self.kafka_topic = kafka_topic
        
        # Initialize Kafka producer
        kafka_config = get_kafka_config()
        producer_config = kafka_config.get_producer_config()
        self.producer = Producer(producer_config)
        
        # Statistics
        self.records_loaded = 0
        self.records_published = 0
        self.records_failed = 0
    
    def _delivery_report(self, err, msg):
        """Callback for producer delivery."""
        if err:
            logger.warning(f"Message delivery failed: {err}")
            self.records_failed += 1
        else:
            self.records_published += 1
            logger.debug(f"Record published to {msg.topic()} [{msg.partition()}]")
    
    async def load_csv(
        self,
        csv_path: str,
        source_name: str = "historical_csv",
        batch_size: int = 50,
        skip_rows: int = 0
    ) -> tuple[int, int, int]:
        """Load historical data from CSV file.
        
        Args:
            csv_path: Path to CSV file
            source_name: Source identifier (appears in post records)
            batch_size: Records per batch before publish
            skip_rows: Skip first N rows (for resuming interrupted loads)
            
        Returns:
            (total_records, published, failed)
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return 0, 0, 0
        
        logger.info(f"Loading CSV: {csv_path}")
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_idx, row in enumerate(reader):
                    if row_idx < skip_rows:
                        logger.debug(f"Skipping row {row_idx}")
                        continue
                    
                    # Add source metadata
                    record = {
                        **row,
                        'source': source_name,
                        'source_file': csv_path.name,
                        'source_row': row_idx,
                        'timestamp': row.get('timestamp', datetime.now(timezone.utc).isoformat()),
                    }
                    
                    # Publish to Kafka
                    try:
                        self.producer.produce(
                            self.kafka_topic,
                            value=json.dumps(record).encode('utf-8'),
                            key=f"{source_name}_{row_idx}".encode('utf-8'),
                            callback=self._delivery_report
                        )
                        self.records_loaded += 1
                        
                        # Batch flush
                        if self.records_loaded % batch_size == 0:
                            self.producer.flush(timeout=5)
                            logger.info(
                                f"Batch published: {self.records_loaded} total, "
                                f"{self.records_published} published, "
                                f"{self.records_failed} failed"
                            )
                            
                            # Yield control to event loop
                            await asyncio.sleep(0.01)
                    
                    except Exception as e:
                        logger.error(f"Error publishing record: {e}")
                        self.records_failed += 1
                        continue
            
            # Final flush
            self.producer.flush(timeout=10)
            
            logger.info(
                f"CSV load complete: {self.records_loaded} records, "
                f"{self.records_published} published, {self.records_failed} failed"
            )
            
            return self.records_loaded, self.records_published, self.records_failed
        
        except Exception as e:
            logger.error(f"CSV loading error: {e}", exc_info=True)
            return self.records_loaded, self.records_published, self.records_failed
    
    async def load_jsonl(
        self,
        jsonl_path: str,
        source_name: str = "historical_jsonl",
        batch_size: int = 50,
        skip_rows: int = 0
    ) -> tuple[int, int, int]:
        """Load historical data from JSONL file.
        
        Args:
            jsonl_path: Path to JSONL file (one JSON object per line)
            source_name: Source identifier
            batch_size: Records per batch
            skip_rows: Skip first N rows
            
        Returns:
            (total_records, published, failed)
        """
        jsonl_path = Path(jsonl_path)
        if not jsonl_path.exists():
            logger.error(f"JSONL file not found: {jsonl_path}")
            return 0, 0, 0
        
        logger.info(f"Loading JSONL: {jsonl_path}")
        
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for row_idx, line in enumerate(f):
                    if row_idx < skip_rows:
                        continue
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        obj = json.loads(line)
                        
                        record = {
                            **obj,
                            'source': source_name,
                            'source_file': jsonl_path.name,
                            'source_row': row_idx,
                            'timestamp': obj.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        }
                        
                        self.producer.produce(
                            self.kafka_topic,
                            value=json.dumps(record).encode('utf-8'),
                            key=f"{source_name}_{row_idx}".encode('utf-8'),
                            callback=self._delivery_report
                        )
                        self.records_loaded += 1
                        
                        if self.records_loaded % batch_size == 0:
                            self.producer.flush(timeout=5)
                            logger.info(
                                f"Batch published: {self.records_loaded} total, "
                                f"{self.records_published} published"
                            )
                            await asyncio.sleep(0.01)
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON at line {row_idx}: {e}")
                        self.records_failed += 1
                        continue
            
            self.producer.flush(timeout=10)
            
            logger.info(
                f"JSONL load complete: {self.records_loaded} records, "
                f"{self.records_published} published, {self.records_failed} failed"
            )
            
            return self.records_loaded, self.records_published, self.records_failed
        
        except Exception as e:
            logger.error(f"JSONL loading error: {e}", exc_info=True)
            return self.records_loaded, self.records_published, self.records_failed
    
    async def backfill_from_directory(
        self,
        directory: str,
        pattern: str = "*.csv",
        source_prefix: str = "historical"
    ) -> Dict[str, tuple[int, int, int]]:
        """Load all matching files from directory.
        
        Args:
            directory: Directory containing files
            pattern: Glob pattern (*.csv, *.jsonl, etc.)
            source_prefix: Prefix for source names
            
        Returns:
            Dict mapping filename → (total, published, failed)
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Directory not found: {directory}")
            return {}
        
        results = {}
        files = list(dir_path.glob(pattern))
        
        logger.info(f"Found {len(files)} files matching {pattern}")
        
        for file_path in files:
            source_name = f"{source_prefix}_{file_path.stem}"
            
            if file_path.suffix == '.csv':
                total, pub, failed = await self.load_csv(
                    str(file_path),
                    source_name=source_name
                )
            elif file_path.suffix == '.jsonl':
                total, pub, failed = await self.load_jsonl(
                    str(file_path),
                    source_name=source_name
                )
            else:
                logger.warning(f"Skipping unsupported file type: {file_path}")
                continue
            
            results[file_path.name] = (total, pub, failed)
        
        return results
    
    def get_stats(self) -> dict:
        """Get loading statistics."""
        return {
            "records_loaded": self.records_loaded,
            "records_published": self.records_published,
            "records_failed": self.records_failed,
            "success_rate": (
                self.records_published / self.records_loaded * 100
                if self.records_loaded > 0 else 0
            ),
        }


async def backfill_historical(
    csv_path: Optional[str] = None,
    directory: Optional[str] = None,
    pattern: str = "*.csv"
) -> Dict[str, Any]:
    """CLI helper for backfilling historical data.
    
    Args:
        csv_path: Single CSV file to load
        directory: Directory with multiple files
        pattern: Glob pattern for directory mode
        
    Returns:
        Loading statistics
    """
    loader = HistoricalDataLoader()
    
    if csv_path:
        total, pub, failed = await loader.load_csv(csv_path)
        return loader.get_stats()
    elif directory:
        results = await loader.backfill_from_directory(directory, pattern=pattern)
        return {
            **loader.get_stats(),
            "files": results,
        }
    else:
        raise ValueError("Must provide either csv_path or directory")


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example: python historical_loader.py --csv historical_data.csv
    #          python historical_loader.py --dir ./data --pattern "*.csv"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--csv" and len(sys.argv) > 2:
            stats = asyncio.run(backfill_historical(csv_path=sys.argv[2]))
            print(json.dumps(stats, indent=2))
        elif sys.argv[1] == "--dir" and len(sys.argv) > 2:
            stats = asyncio.run(backfill_historical(directory=sys.argv[2]))
            print(json.dumps(stats, indent=2))
        else:
            print("Usage: python historical_loader.py --csv <file.csv>")
            print("       python historical_loader.py --dir <directory> [--pattern '*.csv']")
    else:
        print("Please provide --csv <file> or --dir <directory>")
