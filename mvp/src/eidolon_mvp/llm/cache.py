"""Simple in-memory cache for LLM responses."""

from typing import Any, Optional


class Cache:
    """Simple in-memory cache.

    In production, this could be Redis or similar.
    For MVP, we keep it simple with a dict.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to store
        """
        self._cache[key] = value

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached items."""
        return len(self._cache)
