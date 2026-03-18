#!/usr/bin/env python3
"""Standalone Kafka Consumer Script for Digital Pulse.

Consumes raw data from 'raw_data' topic, processes via analytics,
and publishes results to 'processed_results' topic.

Usage:
    python scripts/kafka_consumer.py
    python scripts/kafka_consumer.py --batch 50
    python scripts/kafka_consumer.py --dry-run
    python scripts/kafka_consumer.py --stats
    python scripts/kafka_consumer.py --help

Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS: Kafka broker addresses
    KAFKA_SECURITY_PROTOCOL: PLAINTEXT, SASL_PLAINTEXT, SSL
"""

import sys
import logging
import argparse
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.streaming import (
    create_consumer,
    StreamProcessor,
    create_producer,
)
from backend.streaming.fallback import get_fallback_manager
from config.kafka_settings import get_kafka_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ConsumerApp:
    """Orchestrates consumer application."""

    def __init__(self, args):
        """Initialize consumer app.
        
        Args:
            args: Parsed command line arguments
        """
        self.args = args
        self.config = get_kafka_config()

        # Fallback manager
        self.fallback_mgr = get_fallback_manager(
            queue_directory=self.config.fallback.queue_directory,
            max_queue_size=self.config.fallback.max_queue_size,
            retry_interval_seconds=self.config.fallback.retry_interval_seconds,
        )

        # Producer (for output messages)
        self.producer = create_producer(
            topic=args.output_topic or "processed_results",
            enable_circuit_breaker=True,
        )

        # Stream processor
        self.processor = StreamProcessor(producer=self.producer)

        # Consumer
        self.consumer = create_consumer(
            input_topic=args.input_topic or "raw_data",
            output_topic=args.output_topic or "processed_results",
            processor=self.processor,
            producer=self.producer,
            enable_circuit_breaker=True,
        )

    async def run_batch(self):
        """Run consumer in batch mode."""
        logger.info(f"Running in batch mode (batch_size={self.args.batch})")
        try:
            await self.consumer.process_batch(
                max_messages=self.args.batch,
                poll_timeout_ms=self.config.consumer.poll_timeout_ms,
            )
        except Exception as e:
            logger.error(f"Batch processing error: {e}", exc_info=True)
            return 1

        self._print_stats()
        return 0

    async def run_continuous(self):
        """Run consumer in continuous mode."""
        logger.info("Running consumer in continuous mode")
        logger.info(f"Input topic: {self.consumer.input_topic}")
        logger.info(f"Output topic: {self.consumer.output_topic}")
        logger.info(f"Press Ctrl+C to stop")

        try:
            await self.consumer.run(batch_size=self.args.batch)
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
            return 0
        except Exception as e:
            logger.error(f"Consumer error: {e}", exc_info=True)
            return 1
        finally:
            self.consumer.close()
            self.producer.close()

        return 0

    async def run_dry_run(self):
        """Run in dry-run mode (process one batch and exit)."""
        logger.info("Running in dry-run mode")
        try:
            await self.consumer.process_batch(
                max_messages=min(self.args.batch, 10),
                poll_timeout_ms=self.config.consumer.poll_timeout_ms,
            )
        except Exception as e:
            logger.error(f"Dry-run error: {e}", exc_info=True)
            return 1

        self._print_stats()
        return 0

    async def retry_fallback_queue(self):
        """Retry processing fallback queue."""
        queue_size = self.fallback_mgr.queue.get_queue_size()
        if queue_size == 0:
            logger.info("Fallback queue is empty")
            return 0

        logger.info(f"Processing {queue_size} messages from fallback queue")

        def processor(data):
            try:
                # Use producer to send to Kafka (which will use fallback if needed)
                return self.producer.produce(data)
            except Exception as e:
                logger.error(f"Fallback processing error: {e}")
                return False

        success, failed = await self.fallback_mgr.retry_processing(processor)
        logger.info(f"Fallback retry complete: {success} successful, {failed} failed")
        return 0

    def _print_stats(self):
        """Print statistics."""
        if not self.args.stats:
            return

        logger.info("=== Consumer Statistics ===")
        logger.info(f"Consumer: {self.consumer.get_metrics()}")
        logger.info(f"Producer: {self.producer.get_stats()}")
        if self.consumer.circuit_breaker:
            logger.info(f"Circuit Breaker: {self.consumer.circuit_breaker.get_metrics()}")
        logger.info(f"Fallback Queue: {self.fallback_mgr.get_stats()}")

    async def run(self):
        """Run the consumer app."""
        if self.args.retry_fallback:
            return await self.retry_fallback_queue()
        elif self.args.dry_run:
            return await self.run_dry_run()
        elif self.args.batch:
            return await self.run_batch()
        else:
            return await self.run_continuous()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Kafka Consumer for Digital Pulse - Process streaming data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run consumer continuously
  python kafka_consumer.py

  # Process 50 messages and exit
  python kafka_consumer.py --batch 50

  # Test mode - process 10 messages
  python kafka_consumer.py --dry-run

  # Retry messages from fallback queue
  python kafka_consumer.py --retry-fallback

  # Show statistics
  python kafka_consumer.py --stats
        """
    )

    parser.add_argument(
        "--input-topic",
        type=str,
        default="raw_data",
        help="Input topic (default: raw_data)",
    )
    parser.add_argument(
        "--output-topic",
        type=str,
        default="processed_results",
        help="Output topic (default: processed_results)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        help="Process N messages and exit (default: continuous)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test mode - process up to 10 messages and exit",
    )
    parser.add_argument(
        "--retry-fallback",
        action="store_true",
        help="Retry messages from fallback queue",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics at end",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    args = parser.parse_args()

    # Update logging level
    logging.getLogger().setLevel(args.log_level)

    # Load configuration
    config = get_kafka_config()
    logger.info(f"Kafka config loaded: {config.security.bootstrap_servers}")

    # Create and run app
    app = ConsumerApp(args)
    try:
        exit_code = await app.run()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted")
        exit_code = 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        exit_code = 1
    finally:
        app.consumer.close()
        app.producer.close()

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
