"""Upstream tool caching for performance optimization.

This module provides caching for upstream MCP server tools to reduce
repeated network requests and improve list_tools() performance.
"""

import asyncio
import logging
import time
from typing import Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached tool data with timestamp."""
    tools: list[dict[str, Any]]
    timestamp: float
    server_name: str


class UpstreamToolCache:
    """Cache for upstream server tools with TTL-based expiration.

    Features:
    - Configurable TTL (default 5 minutes)
    - Per-server caching
    - Manual invalidation support
    - Thread-safe operations
    - Metrics tracking
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 300s = 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

        logger.info(f"Initialized upstream tool cache with TTL={ttl_seconds}s")

    async def get(self, server_id: str) -> Optional[list[dict[str, Any]]]:
        """Get cached tools for a server if not expired.

        Args:
            server_id: Server ID to look up

        Returns:
            Cached tools list if valid, None if expired or not found
        """
        async with self._lock:
            entry = self._cache.get(server_id)

            if entry is None:
                self._misses += 1
                logger.debug(f"Cache miss for server '{server_id}'")
                return None

            # Check if expired
            age = time.time() - entry.timestamp
            if age >= self.ttl_seconds:
                self._misses += 1
                logger.debug(f"Cache expired for server '{server_id}' (age: {age:.1f}s)")
                # Clean up expired entry
                del self._cache[server_id]
                return None

            self._hits += 1
            logger.debug(f"Cache hit for server '{server_id}' (age: {age:.1f}s, {len(entry.tools)} tools)")
            return entry.tools

    async def set(self, server_id: str, tools: list[dict[str, Any]], server_name: str = ""):
        """Cache tools for a server.

        Args:
            server_id: Server ID
            tools: List of tool dictionaries
            server_name: Human-readable server name for logging
        """
        async with self._lock:
            entry = CacheEntry(
                tools=tools,
                timestamp=time.time(),
                server_name=server_name or server_id
            )
            self._cache[server_id] = entry
            logger.debug(f"Cached {len(tools)} tools for server '{server_name or server_id}'")

    async def invalidate(self, server_id: Optional[str] = None):
        """Invalidate cache entries.

        Args:
            server_id: Specific server to invalidate, or None to clear all
        """
        async with self._lock:
            if server_id is None:
                # Clear all entries
                count = len(self._cache)
                self._cache.clear()
                self._invalidations += count
                logger.info(f"Invalidated all cache entries ({count} servers)")
            else:
                # Clear specific server
                if server_id in self._cache:
                    del self._cache[server_id]
                    self._invalidations += 1
                    logger.info(f"Invalidated cache for server '{server_id}'")

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "invalidations": self._invalidations,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "cached_servers": len(self._cache),
                "cached_servers_list": [
                    {
                        "server_id": server_id,
                        "server_name": entry.server_name,
                        "tool_count": len(entry.tools),
                        "age_seconds": round(time.time() - entry.timestamp, 1),
                        "ttl_remaining": round(self.ttl_seconds - (time.time() - entry.timestamp), 1)
                    }
                    for server_id, entry in self._cache.items()
                ],
                "ttl_seconds": self.ttl_seconds
            }

    async def cleanup_expired(self):
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            now = time.time()
            expired_servers = [
                server_id
                for server_id, entry in self._cache.items()
                if (now - entry.timestamp) >= self.ttl_seconds
            ]

            for server_id in expired_servers:
                del self._cache[server_id]

            if expired_servers:
                logger.debug(f"Cleaned up {len(expired_servers)} expired cache entries")

            return len(expired_servers)
