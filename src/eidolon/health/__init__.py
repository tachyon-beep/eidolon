"""
Health check system for Eidolon

Provides comprehensive health checks for all system components:
- Database connectivity and performance
- Cache system health
- Disk space availability
- Memory usage

Integrates with load balancers and Kubernetes probes.
"""
import asyncio
import shutil
import psutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ComponentHealth:
    """Health status of a single component"""
    healthy: bool
    latency_ms: float
    message: str
    last_check: str
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """Performs health checks on system components"""

    def __init__(self, db=None, cache=None):
        """
        Initialize health checker

        Args:
            db: Database instance
            cache: Cache manager instance
        """
        self.db = db
        self.cache = cache

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance"""
        if not self.db:
            return ComponentHealth(
                healthy=False,
                latency_ms=0,
                message="Database not initialized",
                last_check=datetime.now(timezone.utc).isoformat()
            )

        start = asyncio.get_event_loop().time()

        try:
            async with asyncio.timeout(2.0):
                # Simple query to verify database works
                async with self.db.db.execute("SELECT 1") as cursor:
                    result = await cursor.fetchone()

                if result[0] != 1:
                    raise ValueError("Unexpected database response")

                # Check database file size
                import os
                db_size = os.path.getsize(self.db.db_path) if hasattr(self.db, 'db_path') else 0
                db_size_mb = db_size / (1024 * 1024)

                latency = (asyncio.get_event_loop().time() - start) * 1000

                return ComponentHealth(
                    healthy=True,
                    latency_ms=latency,
                    message="Database operational",
                    last_check=datetime.now(timezone.utc).isoformat(),
                    details={
                        "size_mb": round(db_size_mb, 2),
                        "query_time_ms": round(latency, 2)
                    }
                )

        except Exception as e:
            latency = (asyncio.get_event_loop().time() - start) * 1000

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
                    message=f"Cache operational",
                    last_check=datetime.now(timezone.utc).isoformat(),
                    details={
                        "entries": stats.total_entries,
                        "size_mb": round(stats.total_size_bytes / (1024 * 1024), 2),
                        "hit_rate": round(stats.hit_rate, 1)
                    }
                )

        except Exception as e:
            latency = (asyncio.get_event_loop().time() - start) * 1000

            return ComponentHealth(
                healthy=False,
                latency_ms=latency,
                message=f"Cache check failed: {str(e)}",
                last_check=datetime.now(timezone.utc).isoformat()
            )

    async def check_disk_space(self) -> ComponentHealth:
        """Check available disk space"""
        try:
            stats = shutil.disk_usage("/")
            percent_used = (stats.used / stats.total) * 100
            gb_free = stats.free / (1024**3)
            gb_total = stats.total / (1024**3)

            # Warn if less than 10% or 1GB free
            healthy = percent_used < 90 and gb_free > 1.0

            return ComponentHealth(
                healthy=healthy,
                latency_ms=0,
                message=f"{gb_free:.1f}GB free of {gb_total:.1f}GB ({100-percent_used:.1f}% available)",
                last_check=datetime.now(timezone.utc).isoformat(),
                details={
                    "free_gb": round(gb_free, 2),
                    "total_gb": round(gb_total, 2),
                    "percent_used": round(percent_used, 1)
                }
            )

        except Exception as e:
            return ComponentHealth(
                healthy=False,
                latency_ms=0,
                message=f"Disk check failed: {str(e)}",
                last_check=datetime.now(timezone.utc).isoformat()
            )

    async def check_memory(self) -> ComponentHealth:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)

            # Warn if less than 10% available
            healthy = percent_used < 90

            return ComponentHealth(
                healthy=healthy,
                latency_ms=0,
                message=f"{available_gb:.1f}GB available of {total_gb:.1f}GB ({100-percent_used:.1f}% free)",
                last_check=datetime.now(timezone.utc).isoformat(),
                details={
                    "available_gb": round(available_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "percent_used": round(percent_used, 1)
                }
            )

        except Exception as e:
            return ComponentHealth(
                healthy=False,
                latency_ms=0,
                message=f"Memory check failed: {str(e)}",
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
            self.check_memory(),
            return_exceptions=True
        )

        db_health, cache_health, disk_health, memory_health = results

        # Handle any exceptions from gather
        def ensure_health(result, name):
            if isinstance(result, Exception):
                return ComponentHealth(
                    healthy=False,
                    latency_ms=0,
                    message=f"{name} check failed: {str(result)}",
                    last_check=datetime.now(timezone.utc).isoformat()
                )
            return result

        db_health = ensure_health(db_health, "Database")
        cache_health = ensure_health(cache_health, "Cache")
        disk_health = ensure_health(disk_health, "Disk")
        memory_health = ensure_health(memory_health, "Memory")

        # Overall status is healthy only if all components are healthy
        all_healthy = all([
            db_health.healthy,
            cache_health.healthy,
            disk_health.healthy,
            memory_health.healthy
        ])

        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "database": asdict(db_health),
                "cache": asdict(cache_health),
                "disk": asdict(disk_health),
                "memory": asdict(memory_health)
            }
        }

    async def get_readiness(self) -> Dict[str, Any]:
        """
        Kubernetes readiness probe

        Returns whether the service is ready to accept traffic
        """
        # For readiness, we only care about critical components
        db_check = await self.check_database()

        ready = db_check.healthy

        return {
            "ready": ready,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": db_check.healthy
            }
        }

    async def get_liveness(self) -> Dict[str, Any]:
        """
        Kubernetes liveness probe

        Returns whether the service is alive (doesn't check dependencies)
        """
        return {
            "alive": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
