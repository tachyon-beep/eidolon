import asyncio
import pytest

from eidolon.health import HealthChecker, ComponentHealth


@pytest.mark.asyncio
async def test_health_checker_without_db_or_cache():
    checker = HealthChecker(db=None, cache=None)
    status = await checker.get_health_status()
    assert status["status"] in {"healthy", "degraded"}
    components = status["components"]
    assert "database" in components and "cache" in components

    readiness = await checker.get_readiness()
    assert readiness["ready"] is False  # no DB

    liveness = await checker.get_liveness()
    assert liveness["alive"] is True


@pytest.mark.asyncio
async def test_component_health_serialization():
    ch = ComponentHealth(healthy=True, latency_ms=1.2, message="ok", last_check="now", details={"a": 1})
    assert ch.healthy is True
