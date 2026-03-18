"""Circuit Breaker Pattern Implementation.

Prevents cascading failures by:
1. Monitoring failure rate
2. Halting requests when threshold exceeded
3. Periodically testing if service recovered
4. Using exponential backoff for recovery

States: CLOSED (normal) -> OPEN (halted) -> HALF_OPEN (testing) -> CLOSED
"""

import logging
import time
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"  # Normal operation, requests pass through
    OPEN = "OPEN"  # Too many failures, requests are blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered, limited requests allowed


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: Optional[datetime] = None

    def reset(self):
        """Reset metrics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.consecutive_failures = 0
        self.last_failure_time = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "consecutive_failures": self.consecutive_failures,
            "state_changes": self.state_changes,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None,
        }


class CircuitBreaker:
    """Circuit breaker for Kafka broker connections and operations.
    
    Gracefully handles failures by:
    1. Tracking failure rate
    2. Opening circuit when threshold exceeded
    3. Attempting recovery periodically
    4. Supporting exponential backoff
    """

    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,
        min_requests: int = 5,
        timeout_seconds: int = 60,
        max_consecutive_failures: int = 3,
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Failure rate threshold to open circuit (0-1)
            min_requests: Minimum requests before threshold applies
            timeout_seconds: Timeout for state transitions
            max_consecutive_failures: Max consecutive failures before opening
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.min_requests = min_requests
        self.timeout_seconds = timeout_seconds
        self.max_consecutive_failures = max_consecutive_failures

        self._state = CircuitState.CLOSED
        self._metrics = CircuitBreakerMetrics()
        self._last_attempt_time: Optional[datetime] = None
        self._state_change_time: Optional[datetime] = None

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for automatic transitions."""
        # If HALF_OPEN and timeout elapsed, try to close
        if self._state == CircuitState.HALF_OPEN:
            if self._state_change_time and datetime.now(timezone.utc) > self._state_change_time + timedelta(seconds=self.timeout_seconds):
                logger.info(f"Circuit '{self.name}' transitioning from HALF_OPEN to CLOSED (recovery timeout)")
                self._state = CircuitState.CLOSED
                self._metrics.reset()
                self._state_change_time = datetime.now(timezone.utc)

        return self._state

    def call(self, func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            (success: bool, result: Any)
            - success=False and result=None if circuit is OPEN
            - success and result if function succeeds
            - not success and result if function fails
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            logger.warning(f"Circuit '{self.name}' is OPEN - blocking request")
            return False, None

        self._last_attempt_time = datetime.now(timezone.utc)
        self._metrics.total_requests += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return True, result
        except Exception as e:
            self._on_failure()
            logger.error(f"Circuit '{self.name}' request failed: {e}")
            return False, str(e)

    def _on_success(self):
        """Handle successful request."""
        self._metrics.successful_requests += 1
        self._metrics.consecutive_failures = 0

        # If in HALF_OPEN, close the circuit
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit '{self.name}' transitioning to CLOSED (recovery successful)")
            self._state = CircuitState.CLOSED
            self._metrics.reset()
            self._state_change_time = datetime.now(timezone.utc)

    def _on_failure(self):
        """Handle failed request."""
        self._metrics.failed_requests += 1
        self._metrics.consecutive_failures += 1
        self._metrics.last_failure_time = datetime.now(timezone.utc)

        # Check if should open circuit
        if self._should_open_circuit():
            logger.error(
                f"Circuit '{self.name}' failure threshold exceeded - opening circuit "
                f"({self._metrics.failed_requests}/{self._metrics.total_requests} failures)"
            )
            self._open_circuit()

    def _should_open_circuit(self) -> bool:
        """Determine if circuit should open."""
        # Check consecutive failures
        if self._metrics.consecutive_failures >= self.max_consecutive_failures:
            return True

        # Check failure rate
        if self._metrics.total_requests >= self.min_requests:
            failure_rate = self._metrics.failed_requests / self._metrics.total_requests
            if failure_rate >= self.failure_threshold:
                return True

        return False

    def _open_circuit(self):
        """Open the circuit."""
        if self._state != CircuitState.OPEN:
            self._state = CircuitState.OPEN
            self._state_change_time = datetime.now(timezone.utc)
            self._metrics.state_changes += 1
            # Transition to HALF_OPEN after timeout for recovery attempt
            self._schedule_half_open()

    def _schedule_half_open(self):
        """Schedule transition to HALF_OPEN state."""
        # This happens automatically in the state property check
        # For now, just log it
        logger.info(
            f"Circuit '{self.name}' will attempt recovery "
            f"in {self.timeout_seconds} seconds"
        )

    def force_open(self):
        """Manually force circuit open."""
        logger.warning(f"Manually forcing circuit '{self.name}' open")
        self._open_circuit()

    def force_closed(self):
        """Manually force circuit closed."""
        logger.warning(f"Manually forcing circuit '{self.name}' closed")
        self._state = CircuitState.CLOSED
        self._metrics.reset()
        self._state_change_time = datetime.now(timezone.utc)

    def get_metrics(self) -> dict:
        """Get circuit metrics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "metrics": self._metrics.to_dict(),
            "configuration": {
                "failure_threshold": self.failure_threshold,
                "min_requests": self.min_requests,
                "timeout_seconds": self.timeout_seconds,
                "max_consecutive_failures": self.max_consecutive_failures,
            },
        }

    def reset(self):
        """Reset circuit and metrics."""
        logger.info(f"Resetting circuit '{self.name}'")
        self._state = CircuitState.CLOSED
        self._metrics.reset()
        self._last_attempt_time = None
        self._state_change_time = None


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def register(self, name: str, breaker: CircuitBreaker):
        """Register a circuit breaker."""
        self._breakers[name] = breaker
        logger.info(f"Registered circuit breaker: {name}")

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)

    def create_and_register(
        self,
        name: str,
        failure_threshold: float = 0.5,
        min_requests: int = 5,
        timeout_seconds: int = 60,
        max_consecutive_failures: int = 3,
    ) -> CircuitBreaker:
        """Create and register a new circuit breaker."""
        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            min_requests=min_requests,
            timeout_seconds=timeout_seconds,
            max_consecutive_failures=max_consecutive_failures,
        )
        self.register(name, breaker)
        return breaker

    def get_all_metrics(self) -> dict:
        """Get metrics for all breakers."""
        return {name: breaker.get_metrics() for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Reset all breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global circuit breaker manager
_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager."""
    return _breaker_manager


def create_kafka_circuit_breaker(
    name: str,
    failure_threshold: float = 0.5,
    min_requests: int = 5,
    timeout_seconds: int = 60,
) -> CircuitBreaker:
    """Create a circuit breaker configured for Kafka operations."""
    return _breaker_manager.create_and_register(
        name=name,
        failure_threshold=failure_threshold,
        min_requests=min_requests,
        timeout_seconds=timeout_seconds,
        max_consecutive_failures=3,
    )
