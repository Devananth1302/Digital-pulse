#!/usr/bin/env python3
"""Standalone Kafka Producer Script for Digital Pulse.

Ingests data from CSV/JSON files or stdin into Kafka 'raw_data' topic.

Usage:
    python scripts/kafka_producer.py --csv data/posts.csv
    python scripts/kafka_producer.py --json data/posts.json
    python scripts/kafka_producer.py --interactive
    python scripts/kafka_producer.py --help

Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS: Kafka broker addresses (default: localhost:9092)
    KAFKA_SECURITY_PROTOCOL: PLAINTEXT, SASL_PLAINTEXT, SSL (default: PLAINTEXT)
    KAFKA_SASL_USERNAME: SASL username
    KAFKA_SASL_PASSWORD: SASL password
"""

import sys
import logging
import argparse
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.streaming import create_producer
from backend.streaming.fallback import get_fallback_manager
from config.kafka_settings import get_kafka_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_fallback_handler(fallback_mgr):
    """Create a fallback handler for producer failures."""
    def handler(data):
        message_id = fallback_mgr.handle_producer_failure(data)
        logger.warning(f"Message queued to fallback: {message_id}")
    return handler


async def ingest_csv(csv_path: str, producer):
    """Ingest data from CSV file."""
    logger.info(f"Ingesting from CSV: {csv_path}")
    success, failed = producer.produce_from_csv(csv_path)
    logger.info(f"CSV ingestion complete: {success} successful, {failed} failed")
    return success, failed


async def ingest_json(json_path: str, producer):
    """Ingest data from JSON file."""
    logger.info(f"Ingesting from JSON: {json_path}")
    success, failed = producer.produce_from_json(json_path)
    logger.info(f"JSON ingestion complete: {success} successful, {failed} failed")
    return success, failed


async def interactive_mode(producer):
    """Interactive mode - read from stdin."""
    logger.info("Interactive mode - enter JSON objects (one per line, 'quit' to exit)")
    total_success = 0
    total_failed = 0

    try:
        while True:
            try:
                line = input("Enter JSON: ").strip()
                if line.lower() == "quit":
                    break

                data = json.loads(line)
                if producer.produce(data):
                    total_success += 1
                    logger.info(f"Message sent ({total_success} total)")
                else:
                    total_failed += 1
                    logger.error(f"Failed to send message")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
            except Exception as e:
                logger.error(f"Error: {e}")

    except KeyboardInterrupt:
        logger.info("Interactive mode interrupted")

    return total_success, total_failed


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Kafka Producer for Digital Pulse - Ingest data into Kafka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python kafka_producer.py --csv data/posts.csv
  python kafka_producer.py --json data/posts.jsonl
  python kafka_producer.py --interactive
  python kafka_producer.py --test
        """
    )

    parser.add_argument("--csv", type=str, help="Ingest from CSV file")
    parser.add_argument("--json", type=str, help="Ingest from JSON/JSONL file")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--test", action="store_true", help="Test mode with sample data")
    parser.add_argument("--topic", type=str, default="raw_data", help="Target topic (default: raw_data)")
    parser.add_argument("--no-fallback", action="store_true", help="Disable fallback queue")
    parser.add_argument("--stats", action="store_true", help="Show producer statistics")

    args = parser.parse_args()

    # Load configuration
    config = get_kafka_config()
    logger.info(f"Kafka config: {config.security.bootstrap_servers}")

    # Initialize fallback manager
    fallback_mgr = get_fallback_manager(
        queue_directory=config.fallback.queue_directory,
        max_queue_size=config.fallback.max_queue_size,
    )

    # Create producer with fallback handler
    fallback_handler = None if args.no_fallback else create_fallback_handler(fallback_mgr)
    producer = create_producer(
        topic=args.topic,
        enable_circuit_breaker=True,
        fallback_handler=fallback_handler,
    )

    try:
        if args.csv:
            success, failed = await ingest_csv(args.csv, producer)
        elif args.json:
            success, failed = await ingest_json(args.json, producer)
        elif args.interactive:
            success, failed = await interactive_mode(producer)
        elif args.test:
            logger.info("Running in test mode")
            test_data = {
                "post_id": "test_post_1",
                "title": "Test Post",
                "content": "This is a test post",
                "timestamp": "2024-03-18T10:00:00Z",
                "likes": 100,
                "shares": 50,
                "comments": 25,
            }
            success, failed = 1 if producer.produce(test_data) else 0, 0
        else:
            parser.print_help()
            return

        # Show statistics
        if args.stats:
            logger.info(f"Producer stats: {producer.get_stats()}")
            logger.info(f"Circuit breaker: {producer.get_circuit_breaker_status()}")
            logger.info(f"Fallback queue: {fallback_mgr.get_stats()}")

        logger.info(f"Finished: {success} successful, {failed} failed")

    except KeyboardInterrupt:
        logger.info("Producer interrupted")
    except Exception as e:
        logger.error(f"Producer error: {e}", exc_info=True)
        return 1
    finally:
        producer.close()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
