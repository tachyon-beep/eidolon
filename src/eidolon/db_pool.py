"""
Database connection pooling for Eidolon

Provides efficient connection reuse, reducing overhead and improving
performance for concurrent database operations.
"""
import asyncio
import aiosqlite
from typing import Optional
from contextlib import asynccontextmanager
from eidolon.logging_config import get_logger
from eidolon.metrics import db_connections_active, db_connection_errors_total

logger = get_logger(__name__)


class ConnectionPool:
    """
    Connection pool for aiosqlite

    Maintains a pool of reusable database connections to reduce
    connection overhead and improve concurrency.
    """

    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 30.0):
        """
        Initialize connection pool

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool
            timeout: Timeout for acquiring connection (seconds)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout

        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._total_connections = 0
        self._initialized = False
        self._lock = asyncio.Lock()

        logger.info(
            "connection_pool_created",
            db_path=db_path,
            pool_size=pool_size,
            timeout=timeout
        )

    async def initialize(self):
        """
        Initialize the connection pool

        Creates initial connections and prepares pool for use.
        """
        if self._initialized:
            logger.warning("connection_pool_already_initialized")
            return

        async with self._lock:
            logger.info("initializing_connection_pool", pool_size=self.pool_size)

            for i in range(self.pool_size):
                try:
                    conn = await aiosqlite.connect(self.db_path, timeout=self.timeout)

                    # Enable WAL mode for better concurrency
                    await conn.execute("PRAGMA journal_mode=WAL")

                    # Enable foreign keys
                    await conn.execute("PRAGMA foreign_keys=ON")

                    await self._pool.put(conn)
                    self._total_connections += 1

                    logger.debug(
                        "connection_created",
                        connection_number=i + 1,
                        total=self._total_connections
                    )

                except Exception as e:
                    logger.error(
                        "connection_creation_failed",
                        connection_number=i + 1,
                        error=str(e)
                    )
                    db_connection_errors_total.inc()
                    # Continue creating other connections

            self._initialized = True
            db_connections_active.set(self._total_connections)

            logger.info(
                "connection_pool_initialized",
                connections_created=self._total_connections,
                target_size=self.pool_size
            )

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool

        Usage:
            async with pool.acquire() as conn:
                await conn.execute("SELECT ...")

        Yields:
            Database connection

        Raises:
            asyncio.TimeoutError: If connection not available within timeout
        """
        if not self._initialized:
            raise RuntimeError("Connection pool not initialized. Call initialize() first.")

        conn = None
        try:
            # Wait for available connection
            conn = await asyncio.wait_for(
                self._pool.get(),
                timeout=self.timeout
            )

            logger.debug("connection_acquired", pool_size=self._pool.qsize())

            yield conn

        except asyncio.TimeoutError:
            logger.error(
                "connection_acquisition_timeout",
                timeout=self.timeout,
                pool_size=self._pool.qsize()
            )
            db_connection_errors_total.inc()
            raise

        except Exception as e:
            logger.error("connection_error", error=str(e))
            db_connection_errors_total.inc()

            # If connection is bad, create a new one
            if conn:
                try:
                    await conn.close()
                except:
                    pass

                try:
                    conn = await aiosqlite.connect(self.db_path, timeout=self.timeout)
                    await conn.execute("PRAGMA journal_mode=WAL")
                    await conn.execute("PRAGMA foreign_keys=ON")
                    logger.info("connection_recreated")
                except Exception as create_error:
                    logger.error("connection_recreation_failed", error=str(create_error))
                    conn = None

            raise

        finally:
            # Return connection to pool
            if conn:
                try:
                    await self._pool.put(conn)
                    logger.debug(
                        "connection_released",
                        pool_size=self._pool.qsize() + 1  # +1 because we just put it back
                    )
                except Exception as e:
                    logger.error("connection_release_failed", error=str(e))

    async def close(self):
        """
        Close all connections in the pool

        Should be called during application shutdown.
        """
        if not self._initialized:
            return

        logger.info("closing_connection_pool", total_connections=self._total_connections)

        closed_count = 0
        error_count = 0

        # Close all connections
        while not self._pool.empty():
            try:
                conn = await self._pool.get()
                await conn.close()
                closed_count += 1
                logger.debug("connection_closed", closed_count=closed_count)
            except Exception as e:
                error_count += 1
                logger.error("connection_close_failed", error=str(e))

        db_connections_active.set(0)

        logger.info(
            "connection_pool_closed",
            connections_closed=closed_count,
            errors=error_count
        )

        self._initialized = False
        self._total_connections = 0

    async def health_check(self) -> bool:
        """
        Check if connection pool is healthy

        Returns:
            True if pool is operational, False otherwise
        """
        if not self._initialized:
            return False

        try:
            async with self.acquire() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("connection_pool_health_check_failed", error=str(e))
            return False

    def get_stats(self) -> dict:
        """
        Get connection pool statistics

        Returns:
            Dict with pool statistics
        """
        return {
            'initialized': self._initialized,
            'pool_size': self.pool_size,
            'total_connections': self._total_connections,
            'available_connections': self._pool.qsize() if self._initialized else 0,
            'in_use_connections': self._total_connections - (self._pool.qsize() if self._initialized else 0)
        }
