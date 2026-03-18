"""Fallback Queue System for when Kafka is unavailable.

Implements persistent local storage so that data is never lost:
1. Queues messages to disk when producer fails or circuit breaker is open
2. Processes queued messages when Kafka becomes available again
3. Supports batch replay and cleanup
"""

import logging
import json
import os
import uuid
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import glob

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Message stored in fallback queue."""
    message_id: str
    data: dict
    timestamp: datetime
    retry_count: int = 0
    last_error: Optional[str] = None

    def save_to_file(self, directory: Path):
        """Save message to JSON file."""
        filename = f"{self.message_id}.json"
        filepath = directory / filename
        
        payload = {
            "message_id": self.message_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "last_error": self.last_error,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f)

    @staticmethod
    def load_from_file(filepath: Path) -> Optional["QueuedMessage"]:
        """Load message from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            
            return QueuedMessage(
                message_id=payload.get("message_id", ""),
                data=payload.get("data", {}),
                timestamp=datetime.fromisoformat(payload.get("timestamp", datetime.now(timezone.utc).isoformat())),
                retry_count=payload.get("retry_count", 0),
                last_error=payload.get("last_error"),
            )
        except Exception as e:
            logger.error(f"Failed to load message from {filepath}: {e}")
            return None


class FallbackQueue:
    """Persistent fallback queue for when Kafka is unavailable."""

    def __init__(
        self,
        queue_directory: str = "./data/kafka_fallback_queue",
        max_queue_size: int = 10000,
    ):
        """Initialize fallback queue.
        
        Args:
            queue_directory: Directory to store queued messages
            max_queue_size: Maximum messages to keep
        """
        self.queue_directory = Path(queue_directory)
        self.max_queue_size = max_queue_size
        self.stats = {
            "enqueued": 0,
            "processed": 0,
            "failed": 0,
            "dropped": 0,
        }

        # Create directory
        self.queue_directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Fallback queue initialized at {self.queue_directory}")

    def enqueue(self, data: dict, message_id: Optional[str] = None) -> str:
        """Enqueue a message to fallback storage.
        
        Args:
            data: Message data
            message_id: Optional message ID (generated if not provided)
            
        Returns:
            Message ID
        """
        if message_id is None:
            message_id = str(uuid.uuid4())

        # Check queue size
        current_size = len(list(self.queue_directory.glob("*.json")))
        if current_size >= self.max_queue_size:
            logger.warning(f"Fallback queue is full ({current_size}/{self.max_queue_size})")
            self.stats["dropped"] += 1
            return message_id

        # Create message
        msg = QueuedMessage(
            message_id=message_id,
            data=data,
            timestamp=datetime.now(timezone.utc),
        )

        # Save to file
        try:
            msg.save_to_file(self.queue_directory)
            self.stats["enqueued"] += 1
            logger.debug(f"Message enqueued: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return message_id

    def dequeue(self, message_id: str) -> Optional[dict]:
        """Retrieve and remove a queued message.
        
        Args:
            message_id: Message ID to dequeue
            
        Returns:
            Message data or None if not found
        """
        filepath = self.queue_directory / f"{message_id}.json"
        if not filepath.exists():
            return None

        try:
            msg = QueuedMessage.load_from_file(filepath)
            if msg:
                filepath.unlink()  # Delete file
                self.stats["processed"] += 1
                logger.debug(f"Message dequeued: {message_id}")
                return msg.data
        except Exception as e:
            logger.error(f"Failed to dequeue message {message_id}: {e}")

        return None

    def get_all_messages(self, limit: Optional[int] = None) -> List[QueuedMessage]:
        """Get all queued messages.
        
        Args:
            limit: Maximum messages to return
            
        Returns:
            List of queued messages
        """
        messages = []
        for filepath in sorted(self.queue_directory.glob("*.json")):
            msg = QueuedMessage.load_from_file(filepath)
            if msg:
                messages.append(msg)
                if limit and len(messages) >= limit:
                    break
        return messages

    def process_queue(
        self,
        processor: Callable[[dict], bool],
        batch_size: int = 50,
        max_retries: int = 3,
    ) -> tuple[int, int]:
        """Process queued messages with a handler function.
        
        Args:
            processor: Function that processes a message and returns True if successful
            batch_size: Batch size for processing
            max_retries: Maximum retries per message
            
        Returns:
            (successful_count, failed_count)
        """
        messages = self.get_all_messages(limit=batch_size)
        successful = 0
        failed = 0

        for msg in messages:
            try:
                if processor(msg.data):
                    # Delete successfully processed message
                    filepath = self.queue_directory / f"{msg.message_id}.json"
                    filepath.unlink()
                    successful += 1
                    self.stats["processed"] += 1
                    logger.debug(f"Processed queued message: {msg.message_id}")
                else:
                    # Increment retry count
                    msg.retry_count += 1
                    if msg.retry_count >= max_retries:
                        # Too many retries, delete message
                        filepath = self.queue_directory / f"{msg.message_id}.json"
                        filepath.unlink()
                        failed += 1
                        self.stats["failed"] += 1
                        logger.warning(f"Abandoned message after {max_retries} retries: {msg.message_id}")
                    else:
                        # Update retry count and keep
                        msg.save_to_file(self.queue_directory)
                        failed += 1

            except Exception as e:
                logger.error(f"Error processing queued message {msg.message_id}: {e}")
                failed += 1

        logger.info(f"Queue processing complete: {successful} successful, {failed} failed")
        return successful, failed

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(list(self.queue_directory.glob("*.json")))

    def clear_queue(self):
        """Clear all queued messages."""
        try:
            for filepath in self.queue_directory.glob("*.json"):
                filepath.unlink()
            logger.info("Fallback queue cleared")
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            **self.stats,
            "current_size": self.get_queue_size(),
            "max_size": self.max_queue_size,
        }


class FallbackManager:
    """Manages fallback operations when Kafka is unavailable."""

    def __init__(
        self,
        queue_directory: str = "./data/kafka_fallback_queue",
        max_queue_size: int = 10000,
        retry_interval_seconds: int = 30,
    ):
        """Initialize fallback manager.
        
        Args:
            queue_directory: Directory for fallback storage
            max_queue_size: Maximum queue size
            retry_interval_seconds: Interval to retry processing
        """
        self.queue = FallbackQueue(queue_directory, max_queue_size)
        self.retry_interval_seconds = retry_interval_seconds
        self.last_retry_time = datetime.now(timezone.utc)

    def handle_producer_failure(
        self,
        data: dict,
        message_id: Optional[str] = None,
    ) -> str:
        """Handle producer failure by queueing to fallback.
        
        Args:
            data: Message data
            message_id: Optional message ID
            
        Returns:
            Message ID
        """
        logger.warning(f"Producer failure - queuing message to fallback")
        return self.queue.enqueue(data, message_id)

    def should_retry_processing(self) -> bool:
        """Check if should retry processing queued messages."""
        elapsed = (datetime.now(timezone.utc) - self.last_retry_time).total_seconds()
        return elapsed >= self.retry_interval_seconds

    async def retry_processing(self, processor: Callable[[dict], bool]) -> tuple[int, int]:
        """Retry processing queued messages.
        
        Args:
            processor: Function to process messages
            
        Returns:
            (successful_count, failed_count)
        """
        if not self.should_retry_processing():
            return 0, 0

        queue_size = self.queue.get_queue_size()
        if queue_size == 0:
            return 0, 0

        logger.info(f"Retrying {queue_size} queued messages")
        self.last_retry_time = datetime.now(timezone.utc)
        return self.queue.process_queue(processor)

    def get_stats(self) -> dict:
        """Get fallback manager statistics."""
        return {
            "queue": self.queue.get_stats(),
            "last_retry": self.last_retry_time.isoformat(),
        }


# Singleton instance
_fallback_manager: Optional[FallbackManager] = None


def get_fallback_manager(
    queue_directory: str = "./data/kafka_fallback_queue",
    max_queue_size: int = 10000,
    retry_interval_seconds: int = 30,
) -> FallbackManager:
    """Get or create fallback manager singleton."""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = FallbackManager(
            queue_directory=queue_directory,
            max_queue_size=max_queue_size,
            retry_interval_seconds=retry_interval_seconds,
        )
    return _fallback_manager
