"""
Cache Manager for Eidolon Analysis Results

Caches agent analysis results to avoid re-analyzing unchanged code.
Uses file content hashing to detect changes and invalidate cache.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import aiosqlite


@dataclass
class CacheEntry:
    """Represents a cached analysis result"""
    id: str
    file_path: str
    file_hash: str
    scope: str  # 'System', 'Module', 'Function', 'Class'
    target: str  # Function/class name or 'module' for whole module
    findings: List[str]
    cards_data: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    created_at: float
    last_accessed: float
    access_count: int


@dataclass
class CacheStats:
    """Cache statistics"""
    total_entries: int
    total_size_bytes: int
    hits: int
    misses: int
    hit_rate: float
    oldest_entry: Optional[float]
    newest_entry: Optional[float]
    most_accessed_file: Optional[str]


class CacheManager:
    """Manages caching of analysis results to avoid re-analyzing unchanged code"""

    def __init__(self, db_path: str = "monad.db"):
        self.db_path = db_path
        self.session_hits = 0
        self.session_misses = 0

    async def initialize(self):
        """Initialize the cache table"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    target TEXT NOT NULL,
                    findings TEXT,
                    cards_data TEXT,
                    metrics TEXT,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)

            # Create indexes for faster lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_file_hash
                ON analysis_cache(file_path, file_hash, scope, target)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_file_path
                ON analysis_cache(file_path)
            """)

            await db.commit()

    @staticmethod
    def hash_file(file_path: str) -> str:
        """
        Calculate SHA256 hash of file contents

        Args:
            file_path: Path to the file

        Returns:
            Hex string of SHA256 hash
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return ""

    @staticmethod
    def _make_cache_key(file_path: str, file_hash: str, scope: str, target: str) -> str:
        """Generate a unique cache key"""
        key_parts = f"{file_path}:{file_hash}:{scope}:{target}"
        return hashlib.md5(key_parts.encode()).hexdigest()

    async def get_cached_result(
        self,
        file_path: str,
        scope: str,
        target: str
    ) -> Optional[CacheEntry]:
        """
        Retrieve cached analysis result if file hasn't changed

        Args:
            file_path: Path to the analyzed file
            scope: Analysis scope ('System', 'Module', 'Function', 'Class')
            target: Target name (function name, class name, or 'module')

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        # Calculate current file hash
        current_hash = self.hash_file(file_path)
        if not current_hash:
            self.session_misses += 1
            return None

        # Generate cache key
        cache_key = self._make_cache_key(file_path, current_hash, scope, target)

        # Query database
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, file_path, file_hash, scope, target, findings, cards_data,
                       metrics, created_at, last_accessed, access_count
                FROM analysis_cache
                WHERE id = ?
            """, (cache_key,)) as cursor:
                row = await cursor.fetchone()

                if row:
                    # Cache hit - update access stats
                    await db.execute("""
                        UPDATE analysis_cache
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE id = ?
                    """, (time.time(), cache_key))
                    await db.commit()

                    self.session_hits += 1

                    return CacheEntry(
                        id=row[0],
                        file_path=row[1],
                        file_hash=row[2],
                        scope=row[3],
                        target=row[4],
                        findings=json.loads(row[5]) if row[5] else [],
                        cards_data=json.loads(row[6]) if row[6] else [],
                        metrics=json.loads(row[7]) if row[7] else {},
                        created_at=row[8],
                        last_accessed=row[9],
                        access_count=row[10]
                    )
                else:
                    # Cache miss
                    self.session_misses += 1
                    return None

    async def store_result(
        self,
        file_path: str,
        scope: str,
        target: str,
        findings: List[str],
        cards_data: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Store analysis result in cache

        Args:
            file_path: Path to the analyzed file
            scope: Analysis scope
            target: Target name
            findings: List of findings from analysis
            cards_data: List of card data dictionaries
            metrics: Metrics dictionary (complexity, LOC, etc.)

        Returns:
            Cache key for the stored entry
        """
        # Calculate file hash
        file_hash = self.hash_file(file_path)
        if not file_hash:
            return ""

        # Generate cache key
        cache_key = self._make_cache_key(file_path, file_hash, scope, target)

        # Store in database
        async with aiosqlite.connect(self.db_path) as db:
            now = time.time()

            await db.execute("""
                INSERT OR REPLACE INTO analysis_cache
                (id, file_path, file_hash, scope, target, findings, cards_data,
                 metrics, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                cache_key,
                file_path,
                file_hash,
                scope,
                target,
                json.dumps(findings, default=str),
                json.dumps(cards_data, default=str),
                json.dumps(metrics, default=str),
                now,
                now
            ))

            await db.commit()

        return cache_key

    async def invalidate_file(self, file_path: str) -> int:
        """
        Invalidate all cache entries for a specific file

        Args:
            file_path: Path to the file

        Returns:
            Number of entries removed
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM analysis_cache
                WHERE file_path = ?
            """, (file_path,))

            deleted = cursor.rowcount
            await db.commit()

            return deleted

    async def invalidate_by_pattern(self, path_pattern: str) -> int:
        """
        Invalidate cache entries matching a path pattern

        Args:
            path_pattern: SQL LIKE pattern for file paths

        Returns:
            Number of entries removed
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM analysis_cache
                WHERE file_path LIKE ?
            """, (path_pattern,))

            deleted = cursor.rowcount
            await db.commit()

            return deleted

    async def clear_all(self) -> int:
        """
        Clear entire cache

        Returns:
            Number of entries removed
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM analysis_cache")
            deleted = cursor.rowcount
            await db.commit()

            return deleted

    async def prune_old_entries(self, max_age_days: int = 30) -> int:
        """
        Remove cache entries older than specified age

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of entries removed
        """
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM analysis_cache
                WHERE last_accessed < ?
            """, (cutoff_time,))

            deleted = cursor.rowcount
            await db.commit()

            return deleted

    async def get_statistics(self) -> CacheStats:
        """
        Get cache statistics

        Returns:
            CacheStats object with cache metrics
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Count total entries
            async with db.execute("SELECT COUNT(*) FROM analysis_cache") as cursor:
                row = await cursor.fetchone()
                total_entries = row[0] if row else 0

            # Calculate total size (approximate)
            async with db.execute("""
                SELECT SUM(LENGTH(findings) + LENGTH(cards_data) + LENGTH(metrics))
                FROM analysis_cache
            """) as cursor:
                row = await cursor.fetchone()
                total_size = row[0] if row and row[0] else 0

            # Get oldest and newest entries
            async with db.execute("""
                SELECT MIN(created_at), MAX(created_at) FROM analysis_cache
            """) as cursor:
                row = await cursor.fetchone()
                oldest = row[0] if row and row[0] else None
                newest = row[1] if row and row[1] else None

            # Get most accessed file
            async with db.execute("""
                SELECT file_path, SUM(access_count) as total_accesses
                FROM analysis_cache
                GROUP BY file_path
                ORDER BY total_accesses DESC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                most_accessed = row[0] if row else None

            # Calculate hit rate
            total_requests = self.session_hits + self.session_misses
            hit_rate = (self.session_hits / total_requests * 100) if total_requests > 0 else 0.0

            return CacheStats(
                total_entries=total_entries,
                total_size_bytes=total_size,
                hits=self.session_hits,
                misses=self.session_misses,
                hit_rate=hit_rate,
                oldest_entry=oldest,
                newest_entry=newest,
                most_accessed_file=most_accessed
            )

    async def get_file_cache_info(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get all cached entries for a specific file

        Args:
            file_path: Path to the file

        Returns:
            List of cache entry info dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT scope, target, file_hash, created_at, last_accessed, access_count
                FROM analysis_cache
                WHERE file_path = ?
                ORDER BY created_at DESC
            """, (file_path,)) as cursor:
                rows = await cursor.fetchall()

                return [
                    {
                        'scope': row[0],
                        'target': row[1],
                        'file_hash': row[2],
                        'created_at': row[3],
                        'last_accessed': row[4],
                        'access_count': row[5]
                    }
                    for row in rows
                ]
