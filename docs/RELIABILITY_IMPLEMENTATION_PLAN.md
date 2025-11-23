# Eidolon Reliability Implementation Plan

## Overview

This document provides a concrete, step-by-step implementation plan for enhancing Eidolon's stability and reliability based on the analysis in `RELIABILITY_ANALYSIS.md`.

---

## Phase 1: Critical Fixes (Immediate - Week 1)

### 1.1 Create Resilience Module

**File**: `backend/resilience/__init__.py`

**Purpose**: Central module for timeout, retry, and circuit breaker patterns

**Implementation**:

```python
"""
Resilience patterns for Eidolon: timeouts, retries, circuit breakers
"""
import asyncio
import time
from typing import Callable, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
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
        self.logger = logger.bind(circuit_breaker=name)

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
            self.logger.info("circuit_breaker_half_open", state="attempting recovery")

        # Reject if circuit is open
        if self.state == CircuitState.OPEN:
            self.logger.warning(
                "circuit_breaker_open",
                failure_count=self.failure_count,
                last_failure=self.last_failure_time
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
                self.logger.info("circuit_breaker_closed", state="recovered")

            return result

        except self.expected_exception as e:
            # Failure - increment counter
            self.failure_count += 1
            self.last_failure_time = time.time()

            self.logger.warning(
                "circuit_breaker_failure",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
                error=str(e)
            )

            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.logger.error(
                    "circuit_breaker_opened",
                    failure_count=self.failure_count,
                    recovery_timeout=self.recovery_timeout
                )

            raise

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger.info("circuit_breaker_reset", state="manually reset")


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
                logger.error(
                    "retry_exhausted",
                    attempt=attempt + 1,
                    max_retries=config.MAX_RETRIES,
                    error=str(e),
                    should_retry=should_retry
                )
                raise

            # Calculate backoff with jitter
            backoff = min(
                config.INITIAL_BACKOFF * (config.BACKOFF_MULTIPLIER ** attempt),
                config.MAX_BACKOFF
            )

            if config.JITTER:
                import random
                backoff = backoff * (0.5 + random.random() * 0.5)  # +/- 50% jitter

            logger.warning(
                "retry_attempt",
                attempt=attempt + 1,
                max_retries=config.MAX_RETRIES,
                backoff_seconds=backoff,
                error=str(e)
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
        logger.error("operation_timeout", timeout=timeout, function=func.__name__)
        raise asyncio.TimeoutError(message)


# Global circuit breakers for critical services
AI_API_BREAKER = CircuitBreaker(
    name="ai_api",
    failure_threshold=3,
    recovery_timeout=120.0
)

GIT_OPERATIONS_BREAKER = CircuitBreaker(
    name="git_operations",
    failure_threshold=5,
    recovery_timeout=60.0
)
```

**Benefits**:
- Centralized resilience patterns
- Reusable across all components
- Production-tested patterns
- Comprehensive logging

---

### 1.2 Add Structured Logging

**File**: `backend/logging_config.py`

**Purpose**: Replace print statements with structured logging

**Implementation**:

```python
"""
Structured logging configuration for Eidolon
"""
import structlog
import logging
import sys


def configure_logging(log_level: str = "INFO", json_logs: bool = False):
    """
    Configure structured logging for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: If True, output JSON format (for production)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )

    # Processors for all log entries
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add JSON rendering for production, pretty printing for development
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Get logger instance
def get_logger(name: str = None):
    """Get a configured logger instance"""
    return structlog.get_logger(name)


# Context management helpers
def bind_context(**kwargs):
    """Bind context variables for all subsequent logs"""
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys):
    """Remove context variables"""
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context():
    """Clear all context variables"""
    structlog.contextvars.clear_contextvars()
```

**Migration Strategy**:
1. Add `structlog` to requirements.txt
2. Replace `print()` with `logger.info()`
3. Add context bindings for requests (session_id, user_id, etc.)
4. Add error logging with tracebacks

---

### 1.3 Implement Comprehensive Health Checks

**File**: `backend/health/__init__.py`

**Purpose**: Real health checks that verify system components

**Implementation**:

```python
"""
Health check system for Eidolon
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from dataclasses import dataclass, asdict
import structlog

from storage import Database
from cache import CacheManager

logger = structlog.get_logger()


@dataclass
class ComponentHealth:
    """Health status of a single component"""
    healthy: bool
    latency_ms: float
    message: str
    last_check: str


class HealthChecker:
    """Performs health checks on system components"""

    def __init__(self, db: Database, cache: CacheManager = None):
        self.db = db
        self.cache = cache

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance"""
        start = asyncio.get_event_loop().time()

        try:
            async with asyncio.timeout(2.0):
                # Simple query to verify database works
                async with self.db.db.execute("SELECT 1") as cursor:
                    result = await cursor.fetchone()

                if result[0] != 1:
                    raise ValueError("Unexpected database response")

                latency = (asyncio.get_event_loop().time() - start) * 1000

                return ComponentHealth(
                    healthy=True,
                    latency_ms=latency,
                    message="Database operational",
                    last_check=datetime.now(timezone.utc).isoformat()
                )

        except Exception as e:
            latency = (asyncio.get_event_loop().time() - start) * 1000
            logger.error("database_health_check_failed", error=str(e))

            return ComponentHealth(
                healthy=False,
                latency_ms=latency,
                message=f"Database check failed: {str(e)}",
                last_check=datetime.now(timezone.utc).isoformat()
            )

    async def check_cache(self) -> ComponentHealth:
        """Check cache system health"""
        if not self.cache:
            return ComponentHealth(
                healthy=True,
                latency_ms=0,
                message="Cache disabled",
                last_check=datetime.now(timezone.utc).isoformat()
            )

        start = asyncio.get_event_loop().time()

        try:
            async with asyncio.timeout(2.0):
                # Get cache statistics to verify it works
                stats = await self.cache.get_statistics()

                latency = (asyncio.get_event_loop().time() - start) * 1000

                return ComponentHealth(
                    healthy=True,
                    latency_ms=latency,
                    message=f"Cache operational ({stats.total_entries} entries)",
                    last_check=datetime.now(timezone.utc).isoformat()
                )

        except Exception as e:
            latency = (asyncio.get_event_loop().time() - start) * 1000
            logger.error("cache_health_check_failed", error=str(e))

            return ComponentHealth(
                healthy=False,
                latency_ms=latency,
                message=f"Cache check failed: {str(e)}",
                last_check=datetime.now(timezone.utc).isoformat()
            )

    async def check_disk_space(self) -> ComponentHealth:
        """Check available disk space"""
        import shutil

        try:
            stats = shutil.disk_usage("/")
            percent_used = (stats.used / stats.total) * 100
            gb_free = stats.free / (1024**3)

            # Warn if less than 10% or 1GB free
            healthy = percent_used < 90 and gb_free > 1.0

            return ComponentHealth(
                healthy=healthy,
                latency_ms=0,
                message=f"{gb_free:.1f}GB free ({100-percent_used:.1f}% available)",
                last_check=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            logger.error("disk_health_check_failed", error=str(e))

            return ComponentHealth(
                healthy=False,
                latency_ms=0,
                message=f"Disk check failed: {str(e)}",
                last_check=datetime.now(timezone.utc).isoformat()
            )

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of the system

        Returns:
            Dict with health status of all components
        """
        # Run all checks in parallel
        results = await asyncio.gather(
            self.check_database(),
            self.check_cache(),
            self.check_disk_space(),
            return_exceptions=True
        )

        db_health, cache_health, disk_health = results

        # Handle any exceptions from gather
        if isinstance(db_health, Exception):
            db_health = ComponentHealth(False, 0, str(db_health), datetime.now(timezone.utc).isoformat())
        if isinstance(cache_health, Exception):
            cache_health = ComponentHealth(False, 0, str(cache_health), datetime.now(timezone.utc).isoformat())
        if isinstance(disk_health, Exception):
            disk_health = ComponentHealth(False, 0, str(disk_health), datetime.now(timezone.utc).isoformat())

        # Overall status is healthy only if all components are healthy
        all_healthy = db_health.healthy and cache_health.healthy and disk_health.healthy

        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "database": asdict(db_health),
                "cache": asdict(cache_health),
                "disk": asdict(disk_health)
            }
        }
```

---

### 1.4 Update Main App with Health Checks

**File**: `backend/main.py` (modifications)

```python
# Add health checker to startup
from health import HealthChecker

health_checker: HealthChecker = None

@app.on_event("startup")
async def startup():
    """Initialize database and orchestrator on startup"""
    global db, orchestrator, health_checker

    # Configure logging
    from logging_config import configure_logging
    configure_logging(log_level="INFO", json_logs=False)

    db = Database("eidolon.db")
    await db.connect()

    orchestrator = AgentOrchestrator(db)
    await orchestrator.initialize()

    # Initialize health checker
    health_checker = HealthChecker(db, orchestrator.cache)

    # Create and include routes
    router = create_routes(db, orchestrator)
    app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    """Comprehensive health check endpoint"""
    if health_checker is None:
        return {"status": "initializing"}

    return await health_checker.get_health_status()


@app.get("/health/ready")
async def readiness():
    """Readiness probe for Kubernetes/load balancers"""
    if health_checker is None:
        return {"ready": False, "reason": "initializing"}

    health_status = await health_checker.get_health_status()

    return {
        "ready": health_status["status"] == "healthy",
        "status": health_status["status"]
    }


@app.get("/health/live")
async def liveness():
    """Liveness probe for Kubernetes"""
    # Simple check - is the process alive and responsive?
    return {"alive": True}
```

---

### 1.5 Add Requirements

**File**: `backend/requirements.txt` (additions)

```text
# Existing dependencies...

# Resilience & Observability
structlog>=23.1.0
prometheus-client>=0.18.0
python-json-logger>=2.0.7
```

---

## Phase 2: Resilience Patterns (Week 2)

### 2.1 Update Orchestrator with Timeouts & Retries

**File**: `backend/agents/orchestrator.py` (key modifications)

**Changes**:
1. Import resilience module
2. Wrap AI API calls with timeout + retry + circuit breaker
3. Wrap git operations with timeout
4. Add structured logging

**Example**:

```python
from resilience import (
    retry_with_backoff,
    with_timeout,
    TimeoutConfig,
    RetryConfig,
    AI_API_BREAKER
)
from logging_config import get_logger

logger = get_logger(__name__)

# In _analyze_function method:
async def _analyze_function(self, ...) -> Optional[List[Card]]:
    """Analyze a single function with resilience patterns"""

    # Check cache first
    if self.cache:
        cached = await self.cache.get_cached_result(...)
        if cached:
            logger.info("cache_hit", function=func.name, file=module_file)
            return create_cards_from_cache(cached)

    # AI analysis with timeout, retry, and circuit breaker
    try:
        async def call_ai():
            return await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

        # Wrap with timeout
        async def call_with_timeout():
            return await with_timeout(
                call_ai,
                timeout=TimeoutConfig.AI_API_TIMEOUT,
                timeout_message=f"AI analysis of {func.name} timed out"
            )

        # Wrap with circuit breaker
        async def call_with_breaker():
            return await AI_API_BREAKER.call(call_with_timeout)

        # Wrap with retry logic
        response = await retry_with_backoff(
            call_with_breaker,
            config=RetryConfig()
        )

        logger.info(
            "function_analyzed",
            function=func.name,
            tokens=response.usage.total_tokens
        )

        # Process response...

    except asyncio.TimeoutError as e:
        logger.error("function_analysis_timeout", function=func.name, error=str(e))
        self.progress['errors'].append(f"Timeout analyzing {func.name}")
        return None

    except Exception as e:
        logger.error("function_analysis_failed", function=func.name, error=str(e))
        self.progress['errors'].append(f"Error analyzing {func.name}: {str(e)}")
        return None
```

---

### 2.2 Add Rate Limiting

**File**: `backend/resilience/rate_limiter.py`

```python
"""
Rate limiter for API calls
"""
import asyncio
import time
from collections import deque
from typing import Optional
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """
    Token bucket rate limiter for API calls

    Ensures we don't exceed Anthropic API rate limits
    """

    def __init__(self,
                 max_requests_per_minute: int = 50,
                 max_tokens_per_minute: int = 40000,
                 max_requests_per_day: int = 5000):
        self.max_rpm = max_requests_per_minute
        self.max_tpm = max_tokens_per_minute
        self.max_rpd = max_requests_per_day

        # Request timestamps
        self.requests_minute = deque()
        self.requests_day = deque()

        # Token usage
        self.tokens_minute = deque()

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

            # Clean old entries
            self._cleanup_old_entries(now)

            # Check if we would exceed limits
            while (
                len(self.requests_minute) >= self.max_rpm or
                sum(t[1] for t in self.tokens_minute) + estimated_tokens > self.max_tpm or
                len(self.requests_day) >= self.max_rpd
            ):
                # Calculate wait time
                wait_time = self._calculate_wait_time(now, estimated_tokens)

                logger.warning(
                    "rate_limit_wait",
                    wait_seconds=wait_time,
                    requests_minute=len(self.requests_minute),
                    tokens_minute=sum(t[1] for t in self.tokens_minute),
                    requests_day=len(self.requests_day)
                )

                await asyncio.sleep(wait_time)
                now = time.time()
                self._cleanup_old_entries(now)

            # Record this request
            self.requests_minute.append(now)
            self.requests_day.append(now)
            self.tokens_minute.append((now, estimated_tokens))

    def _cleanup_old_entries(self, now: float):
        """Remove entries outside the time windows"""
        # Clean minute window
        while self.requests_minute and self.requests_minute[0] < now - 60:
            self.requests_minute.popleft()

        while self.tokens_minute and self.tokens_minute[0][0] < now - 60:
            self.tokens_minute.popleft()

        # Clean day window
        while self.requests_day and self.requests_day[0] < now - 86400:
            self.requests_day.popleft()

    def _calculate_wait_time(self, now: float, estimated_tokens: int) -> float:
        """Calculate how long to wait before retrying"""
        wait_times = []

        # Wait for minute window
        if self.requests_minute and len(self.requests_minute) >= self.max_rpm:
            oldest = self.requests_minute[0]
            wait_times.append(60 - (now - oldest) + 0.1)

        # Wait for token window
        if self.tokens_minute:
            total_tokens = sum(t[1] for t in self.tokens_minute)
            if total_tokens + estimated_tokens > self.max_tpm:
                oldest = self.tokens_minute[0][0]
                wait_times.append(60 - (now - oldest) + 0.1)

        # Wait for day window
        if self.requests_day and len(self.requests_day) >= self.max_rpd:
            oldest = self.requests_day[0]
            wait_times.append(86400 - (now - oldest) + 1)

        return max(wait_times) if wait_times else 0.1

    def record_actual_tokens(self, tokens_used: int):
        """Update token usage with actual value after API call"""
        # Remove the estimated tokens and add actual
        if self.tokens_minute:
            self.tokens_minute[-1] = (self.tokens_minute[-1][0], tokens_used)
```

---

## Phase 3: Observability (Week 3)

### 3.1 Add Prometheus Metrics

**File**: `backend/metrics/__init__.py`

```python
"""
Prometheus metrics for Eidolon
"""
from prometheus_client import Counter, Histogram, Gauge, Info

# Analysis metrics
analysis_total = Counter(
    'eidolon_analyses_total',
    'Total number of analyses started',
    ['mode', 'status']
)

analysis_duration = Histogram(
    'eidolon_analysis_duration_seconds',
    'Analysis duration in seconds',
    ['mode'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

active_analyses = Gauge(
    'eidolon_active_analyses',
    'Number of currently running analyses'
)

# AI API metrics
ai_api_calls_total = Counter(
    'eidolon_ai_api_calls_total',
    'Total AI API calls',
    ['status', 'model']
)

ai_api_tokens_total = Counter(
    'eidolon_ai_api_tokens_total',
    'Total tokens used',
    ['type']  # input or output
)

ai_api_latency = Histogram(
    'eidolon_ai_api_latency_seconds',
    'AI API call latency',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 90]
)

# Cache metrics
cache_operations_total = Counter(
    'eidolon_cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation=get/set, result=hit/miss/error
)

cache_size_bytes = Gauge(
    'eidolon_cache_size_bytes',
    'Current cache size in bytes'
)

cache_entries = Gauge(
    'eidolon_cache_entries',
    'Number of entries in cache'
)

# Database metrics
db_queries_total = Counter(
    'eidolon_db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

db_query_duration = Histogram(
    'eidolon_db_query_duration_seconds',
    'Database query duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

# System info
system_info = Info(
    'eidolon_system',
    'Eidolon system information'
)
```

---

## Summary

This implementation plan provides:

1. **Immediate fixes** for critical stability issues (timeouts, retries, health checks)
2. **Resilience patterns** that prevent cascade failures
3. **Observability** for production monitoring
4. **Clear migration path** with concrete code examples

### Next Steps:

1. Review and approve this plan
2. Start with Phase 1 (Week 1)
3. Test each phase thoroughly
4. Deploy incrementally with monitoring

Would you like me to start implementing any of these phases?
