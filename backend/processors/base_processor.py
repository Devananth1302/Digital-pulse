"""Base Processor Framework - Abstract processor for all micro-processors.

All processors follow this pattern:
1. Read from input_topic
2. Process records independently (no multi-record dependencies)
3. Write to output_topic
4. Send failures to DLQ
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import threading

from confluent_kafka import Consumer, Producer, KafkaError
from config.kafka_settings import get_kafka_config

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Configuration for a processor."""
    name: str
    input_topic: str
    output_topic: str
    dlq_topic: str = "processor_dlq"
    num_threads: int = 3
    batch_size: int = 50
    enable_circuit_breaker: bool = True


@dataclass
class ProcessorMetrics:
    """Metrics for a processor."""
    records_processed: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    records_dlq: int = 0
    processing_errors: List[str] = None
    
    def __post_init__(self):
        if self.processing_errors is None:
            self.processing_errors = []


class BaseProcessor(ABC):
    """Abstract base class for all data processors."""
    
    def __init__(self, config: ProcessorConfig):
        """Initialize processor with configuration."""
        self.config = config
        self.metrics = ProcessorMetrics()
        
        # Kafka config
        kafka_config = get_kafka_config()
        self.kafka_config = kafka_config
        
        # Consumer
        consumer_config = kafka_config.get_consumer_config()
        consumer_config['group.id'] = f"{config.name}_group"
        consumer_config['auto.offset.reset'] = 'earliest'
        self.consumer = Consumer(consumer_config)
        self.consumer.subscribe([config.input_topic])
        
        # Producer
        producer_config = kafka_config.get_producer_config()
        self.producer = Producer(producer_config)
        
        # Thread pool for async processing
        self.executor = ThreadPoolExecutor(max_workers=config.num_threads)
        self.running = False
        self.lock = threading.Lock()
        
        logger.info(f"Processor '{config.name}' initialized: {config.input_topic} → {config.output_topic}")
    
    @abstractmethod
    async def process_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single record. Override in subclass.
        
        Args:
            data: Input record
            
        Returns:
            Processed record or None if should skip
        """
        pass
    
    def _send_to_dlq(self, record: Dict[str, Any], error: str):
        """Send failed record to DLQ."""
        dlq_payload = {
            "processor": self.config.name,
            "original_record": record,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            self.producer.produce(
                self.config.dlq_topic,
                value=json.dumps(dlq_payload).encode('utf-8'),
                callback=self._delivery_report
            )
            self.metrics.records_dlq += 1
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")
    
    def _delivery_report(self, err, msg):
        """Callback for producer delivery."""
        if err:
            logger.warning(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
    async def _process_single_record_async(self, record_data: Dict[str, Any]) -> bool:
        """Process single record and handle errors."""
        self.metrics.records_processed += 1
        
        try:
            result = await self.process_record(record_data)
            
            if result is not None:
                # Send to output topic
                self.producer.produce(
                    self.config.output_topic,
                    value=json.dumps(result).encode('utf-8'),
                    key=record_data.get('post_id', '').encode('utf-8') if record_data.get('post_id') else None,
                    callback=self._delivery_report
                )
                self.metrics.records_succeeded += 1
                return True
            else:
                logger.debug(f"Record skipped by processor")
                return True
                
        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            self.metrics.records_failed += 1
            self.metrics.processing_errors.append(str(e))
            self._send_to_dlq(record_data, str(e))
            return False
    
    async def process_batch(self, records: List[Dict[str, Any]]) -> tuple[int, int]:
        """Process batch of records concurrently."""
        tasks = [self._process_single_record_async(rec) for rec in records]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        succeeded = sum(1 for r in results if r)
        failed = len(results) - succeeded
        
        return succeeded, failed
    
    async def run(self, timeout_hours: Optional[int] = None):
        """Run processor continuously.
        
        Args:
            timeout_hours: Exit after N hours (None = run forever)
        """
        self.running = True
        logger.info(f"Starting processor '{self.config.name}'...")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            while self.running:
                # Check timeout
                if timeout_hours:
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() / 3600
                    if elapsed > timeout_hours:
                        logger.info(f"Timeout reached: {elapsed:.1f} hours")
                        break
                
                # Poll messages
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        continue
                
                # Parse message
                try:
                    record_data = json.loads(msg.value().decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    continue
                
                # Process asynchronously
                await self._process_single_record_async(record_data)
                
                # Commit offset
                self.consumer.commit(asynchronous=False)
                
        except KeyboardInterrupt:
            logger.info("Processor interrupted by user")
        finally:
            self.running = False
            self.stop()
    
    def stop(self):
        """Stop processor gracefully."""
        logger.info(f"Stopping processor '{self.config.name}'...")
        
        self.consumer.close()
        self.producer.flush(timeout=10)
        self.executor.shutdown(wait=True)
        
        logger.info(f"Processor stopped. Stats: {self.get_stats()}")
    
    def get_stats(self) -> dict:
        """Get processor statistics."""
        return {
            "processor": self.config.name,
            "records_processed": self.metrics.records_processed,
            "records_succeeded": self.metrics.records_succeeded,
            "records_failed": self.metrics.records_failed,
            "records_dlq": self.metrics.records_dlq,
            "success_rate": (
                self.metrics.records_succeeded / self.metrics.records_processed * 100
                if self.metrics.records_processed > 0 else 0
            ),
        }
