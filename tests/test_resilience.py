import asyncio

import pytest

from eidolon import resilience
from eidolon.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    RateLimiter,
    RetryConfig,
    retry_with_backoff,
    with_timeout,
)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_recovers():
    breaker = CircuitBreaker(
        name="test",
        failure_threshold=2,
        recovery_timeout=0.01,
        expected_exception=RuntimeError,
    )

    async def fail():
        raise RuntimeError("boom")

    async def succeed():
        return "ok"

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(fail)

    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitBreakerError):
        await breaker.call(fail)

    breaker.last_failure_time = (breaker.last_failure_time or 0) - breaker.recovery_timeout
    result = await breaker.call(succeed)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_retry_with_backoff_retries_on_retryable(monkeypatch):
    sleep_durations = []

    async def fake_sleep(duration: float):
        sleep_durations.append(duration)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    call_count = 0

    class RetryableError(Exception):
        def __init__(self):
            super().__init__("retry me")
            self.type = "api_error"

    async def sometimes_fail():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetryableError()
        return "ok"

    cfg = RetryConfig(
        MAX_RETRIES=3,
        INITIAL_BACKOFF=0.1,
        MAX_BACKOFF=1.0,
        BACKOFF_MULTIPLIER=2.0,
        JITTER=False,
    )

    result = await retry_with_backoff(sometimes_fail, config=cfg)
    assert result == "ok"
    assert call_count == 3
    assert sleep_durations == [0.1, 0.2]


@pytest.mark.asyncio
async def test_retry_with_backoff_stops_on_non_retryable(monkeypatch):
    async def fake_sleep(_):
        raise AssertionError("sleep should not be called for non-retryable errors")

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    async def bad():
        raise ValueError("no retry")

    with pytest.raises(ValueError):
        await retry_with_backoff(bad, config=RetryConfig(MAX_RETRIES=2, JITTER=False))


@pytest.mark.asyncio
async def test_with_timeout_times_out():
    async def slow():
        await asyncio.sleep(0.05)

    with pytest.raises(asyncio.TimeoutError):
        await with_timeout(slow, timeout=0.01)


@pytest.mark.asyncio
async def test_rate_limiter_enforces_limits(monkeypatch):
    current = {"t": 0.0}
    sleep_calls = []

    def fake_time():
        return current["t"]

    async def fake_sleep(duration: float):
        sleep_calls.append(duration)
        current["t"] += duration

    monkeypatch.setattr(resilience.time, "time", fake_time)
    monkeypatch.setattr(resilience.asyncio, "sleep", fake_sleep)

    limiter = RateLimiter(max_requests_per_minute=2, max_tokens_per_minute=10)

    await limiter.acquire(estimated_tokens=5)
    await limiter.acquire(estimated_tokens=4)
    await limiter.acquire(estimated_tokens=4)

    assert sleep_calls  # third call should have waited
    assert sleep_calls[0] >= 60.0
    limiter.record_actual_tokens(2)
    assert limiter.tokens[-1][1] == 2
