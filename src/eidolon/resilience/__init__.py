"""
Resilience patterns for Eidolon: timeouts, retries, circuit breakers

This module provides production-grade reliability patterns to handle
transient failures, prevent cascade failures, and ensure graceful degradation.
"""
import asyncio
import time
import random
from typing import Callable, Any, Optional, List, TypeVar
from dataclasses import dataclass
from enum import Enum

# Use print for now, will be replaced with structlog after logging config
import sys

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class TimeoutConfig:
    """Timeout configurations for different operations"""
    AI_API_TIMEOUT: float = 90.0  # 90 seconds for AI responses
    GIT_OPERATION_TIMEOUT: float = 30.0
    FILE_IO_TIMEOUT: float = 10.0
    DB_QUERY_TIMEOUT: float = 5.0
    ANALYSIS_MAX_DURATION: float = 3600.0  # 1 hour max per analysis


@dataclass
class RetryConfig:
    """Retry configurations with exponential backoff"""
    MAX_RETRIES: int = 3
    INITIAL_BACKOFF: float = 1.0  # seconds
    MAX_BACKOFF: float = 60.0
    BACKOFF_MULTIPLIER: float = 2.0
    JITTER: bool = True  # Add randomness to prevent thundering herd

    # Anthropic error types that should be retried
    RETRYABLE_ERROR_TYPES: List[str] = None

    def __post_init__(self):
        if self.RETRYABLE_ERROR_TYPES is None:
            self.RETRYABLE_ERROR_TYPES = [
                'rate_limit_error',
                'overloaded_error',
                'timeout',
                'api_error'  # Generic API errors might be transient
            ]


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Prevents repeated calls to failing services by "opening" after threshold failures.
    Automatically attempts recovery after timeout period.
    """

    def __init__(self,
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        return (
            self.state == CircuitState.OPEN and
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from func if not retryable
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            print(f"[CircuitBreaker:{self.name}] Attempting recovery (HALF_OPEN)", file=sys.stderr)

        # Reject if circuit is open
        if self.state == CircuitState.OPEN:
            print(
                f"[CircuitBreaker:{self.name}] OPEN - rejecting request "
                f"(failures: {self.failure_count}/{self.failure_threshold})",
                file=sys.stderr
            )
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Will retry after {self.recovery_timeout}s"
            )

        try:
            # Execute function
            result = await func(*args, **kwargs)

            # Success - reset if we were testing recovery
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                print(f"[CircuitBreaker:{self.name}] Recovered (CLOSED)", file=sys.stderr)

            return result

        except self.expected_exception as e:
            # Failure - increment counter
            self.failure_count += 1
            self.last_failure_time = time.time()

            print(
                f"[CircuitBreaker:{self.name}] Failure {self.failure_count}/{self.failure_threshold}: {str(e)[:100]}",
                file=sys.stderr
            )

            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                print(
                    f"[CircuitBreaker:{self.name}] OPENED - too many failures "
                    f"(recovery in {self.recovery_timeout}s)",
                    file=sys.stderr
                )

            raise

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        print(f"[CircuitBreaker:{self.name}] Manually reset", file=sys.stderr)


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Retry async function with exponential backoff

    Args:
        func: Async function to retry
        *args, **kwargs: Arguments to pass to func
        config: RetryConfig instance (uses defaults if None)

    Returns:
        Result from successful func call

    Raises:
        Exception: Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.MAX_RETRIES + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Check if this error type should be retried
            error_type = getattr(e, 'type', type(e).__name__)
            should_retry = any(
                retry_type in str(error_type).lower()
                for retry_type in config.RETRYABLE_ERROR_TYPES
            )

            # Don't retry if this is the last attempt or error not retryable
            if attempt >= config.MAX_RETRIES or not should_retry:
                if not should_retry:
                    print(
                        f"[Retry] Error type '{error_type}' not retryable, failing immediately",
                        file=sys.stderr
                    )
                else:
                    print(
                        f"[Retry] Exhausted all {config.MAX_RETRIES} retries: {str(e)[:100]}",
                        file=sys.stderr
                    )
                raise

            # Calculate backoff with jitter
            backoff = min(
                config.INITIAL_BACKOFF * (config.BACKOFF_MULTIPLIER ** attempt),
                config.MAX_BACKOFF
            )

            if config.JITTER:
                backoff = backoff * (0.5 + random.random() * 0.5)  # +/- 50% jitter

            print(
                f"[Retry] Attempt {attempt + 1}/{config.MAX_RETRIES} failed: {str(e)[:100]}. "
                f"Retrying in {backoff:.1f}s...",
                file=sys.stderr
            )

            await asyncio.sleep(backoff)

    # Should never reach here, but just in case
    raise last_exception


async def with_timeout(
    func: Callable,
    *args,
    timeout: float,
    timeout_message: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Execute async function with timeout

    Args:
        func: Async function to execute
        *args, **kwargs: Arguments to pass to func
        timeout: Timeout in seconds
        timeout_message: Custom message for timeout error

    Returns:
        Result from func

    Raises:
        asyncio.TimeoutError: If operation exceeds timeout
    """
    try:
        async with asyncio.timeout(timeout):
            return await func(*args, **kwargs)
    except asyncio.TimeoutError:
        message = timeout_message or f"Operation timed out after {timeout}s"
        print(f"[Timeout] {message}", file=sys.stderr)
        raise asyncio.TimeoutError(message)


# Global circuit breakers for critical services
AI_API_BREAKER = CircuitBreaker(
    name="ai_api",
    failure_threshold=3,  # More aggressive for expensive AI calls
    recovery_timeout=120.0  # 2 minutes recovery
)

GIT_OPERATIONS_BREAKER = CircuitBreaker(
    name="git_operations",
    failure_threshold=5,
    recovery_timeout=60.0
)

DATABASE_BREAKER = CircuitBreaker(
    name="database",
    failure_threshold=3,
    recovery_timeout=30.0
)


# Rate limiter for API calls
class RateLimiter:
    """
    Token bucket rate limiter for API calls

    Ensures we don't exceed Anthropic API rate limits
    """

    def __init__(self,
                 max_requests_per_minute: int = 50,
                 max_tokens_per_minute: int = 40000):
        self.max_rpm = max_requests_per_minute
        self.max_tpm = max_tokens_per_minute

        # Request timestamps and token usage
        self.requests = []
        self.tokens = []

        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000):
        """
        Acquire permission to make an API call

        Args:
            estimated_tokens: Estimated tokens for this request

        Blocks until rate limit allows the request
        """
        async with self.lock:
            now = time.time()

            # Clean entries older than 1 minute
            self.requests = [t for t in self.requests if t > now - 60]
            self.tokens = [(t, tokens) for t, tokens in self.tokens if t > now - 60]

            # Check if we would exceed limits
            current_tokens = sum(tokens for _, tokens in self.tokens)

            while (
                len(self.requests) >= self.max_rpm or
                current_tokens + estimated_tokens > self.max_tpm
            ):
                # Calculate wait time
                if self.requests and len(self.requests) >= self.max_rpm:
                    oldest_request = min(self.requests)
                    wait_time = 60 - (now - oldest_request) + 0.1
                elif self.tokens:
                    oldest_token = min(t for t, _ in self.tokens)
                    wait_time = 60 - (now - oldest_token) + 0.1
                else:
                    wait_time = 1.0

                print(
                    f"[RateLimiter] Waiting {wait_time:.1f}s "
                    f"(requests: {len(self.requests)}/{self.max_rpm}, "
                    f"tokens: {current_tokens}/{self.max_tpm})",
                    file=sys.stderr
                )

                await asyncio.sleep(wait_time)
                now = time.time()

                # Re-clean after sleeping
                self.requests = [t for t in self.requests if t > now - 60]
                self.tokens = [(t, tokens) for t, tokens in self.tokens if t > now - 60]
                current_tokens = sum(tokens for _, tokens in self.tokens)

            # Record this request
            self.requests.append(now)
            self.tokens.append((now, estimated_tokens))

    def record_actual_tokens(self, tokens_used: int):
        """Update last entry with actual token usage"""
        if self.tokens:
            # Update the most recent entry
            timestamp = self.tokens[-1][0]
            self.tokens[-1] = (timestamp, tokens_used)


# Global rate limiter instance
AI_RATE_LIMITER = RateLimiter(
    max_requests_per_minute=50,
    max_tokens_per_minute=40000
)
