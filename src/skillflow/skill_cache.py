"""High-performance skill caching system with hot-reload support.

This module provides multi-layer caching to dramatically improve skill loading
and tool listing performance.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .schemas import Skill, SkillMeta

logger = logging.getLogger(__name__)


@dataclass
class SkillCacheEntry:
    """Cached skill with metadata."""
    skill: Skill
    timestamp: float
    file_mtime: float  # File modification time for staleness detection


@dataclass
class ToolListCacheEntry:
    """Cached MCP tool list."""
    tools: list[dict[str, Any]]
    timestamp: float
    skill_ids: set[str]  # Track which skills contributed to this list


class SkillCache:
    """High-performance cache for skills and tool lists.

    Features:
    - Full skill object caching (not just metadata)
    - Tool list caching (compiled MCP tools)
    - TTL-based expiration (default: 5 minutes)
    - File modification time tracking for staleness detection
    - Incremental invalidation (single skill or full cache)
    - Thread-safe async operations
    - Detailed statistics tracking
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize skill cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 300s = 5 minutes)
        """
        self.ttl_seconds = ttl_seconds

        # Full skill object cache
        self._skill_cache: dict[str, SkillCacheEntry] = {}
        self._skill_lock = asyncio.Lock()

        # Compiled tool list cache (for list_tools() performance)
        self._tool_list_cache: Optional[ToolListCacheEntry] = None
        self._tool_list_lock = asyncio.Lock()

        # Statistics
        self._skill_hits = 0
        self._skill_misses = 0
        self._tool_list_hits = 0
        self._tool_list_misses = 0
        self._invalidations = 0

        logger.info(f"Initialized skill cache with TTL={ttl_seconds}s")

    async def get_skill(self, skill_id: str, skill_dir: Path) -> Optional[Skill]:
        """Get cached skill if valid.

        Args:
            skill_id: Skill ID
            skill_dir: Path to skill directory for staleness check

        Returns:
            Cached Skill object if valid, None if expired/stale/missing
        """
        async with self._skill_lock:
            entry = self._skill_cache.get(skill_id)

            if entry is None:
                self._skill_misses += 1
                logger.debug(f"Cache miss for skill '{skill_id}'")
                return None

            # Check if expired
            age = time.time() - entry.timestamp
            if age >= self.ttl_seconds:
                self._skill_misses += 1
                logger.debug(f"Cache expired for skill '{skill_id}' (age: {age:.1f}s)")
                del self._skill_cache[skill_id]
                return None

            # Check if file modified (staleness detection)
            version_path = skill_dir / f"v{entry.skill.version:04d}.json"
            if version_path.exists():
                current_mtime = version_path.stat().st_mtime
                if current_mtime != entry.file_mtime:
                    self._skill_misses += 1
                    logger.debug(f"Cache stale for skill '{skill_id}' (file modified)")
                    del self._skill_cache[skill_id]
                    return None

            self._skill_hits += 1
            logger.debug(f"Cache hit for skill '{skill_id}' (age: {age:.1f}s)")
            return entry.skill

    async def set_skill(self, skill: Skill, skill_dir: Path):
        """Cache a skill object.

        Args:
            skill: Skill object to cache
            skill_dir: Path to skill directory
        """
        async with self._skill_lock:
            version_path = skill_dir / f"v{skill.version:04d}.json"
            file_mtime = version_path.stat().st_mtime if version_path.exists() else time.time()

            entry = SkillCacheEntry(
                skill=skill,
                timestamp=time.time(),
                file_mtime=file_mtime
            )
            self._skill_cache[skill.id] = entry
            logger.debug(f"Cached skill '{skill.id}' v{skill.version}")

            # Invalidate tool list cache since skill data changed
            await self._invalidate_tool_list_cache()

    async def get_tool_list(self) -> Optional[list[dict[str, Any]]]:
        """Get cached tool list.

        Returns:
            Cached tool list if valid, None if expired/missing
        """
        async with self._tool_list_lock:
            if self._tool_list_cache is None:
                self._tool_list_misses += 1
                logger.debug("Tool list cache miss")
                return None

            age = time.time() - self._tool_list_cache.timestamp
            if age >= self.ttl_seconds:
                self._tool_list_misses += 1
                logger.debug(f"Tool list cache expired (age: {age:.1f}s)")
                self._tool_list_cache = None
                return None

            self._tool_list_hits += 1
            logger.debug(f"Tool list cache hit ({len(self._tool_list_cache.tools)} tools, age: {age:.1f}s)")
            return self._tool_list_cache.tools

    async def set_tool_list(self, tools: list[dict[str, Any]], skill_ids: set[str]):
        """Cache compiled tool list.

        Args:
            tools: List of MCP tool dictionaries
            skill_ids: Set of skill IDs that contributed to this list
        """
        async with self._tool_list_lock:
            self._tool_list_cache = ToolListCacheEntry(
                tools=tools,
                timestamp=time.time(),
                skill_ids=skill_ids
            )
            logger.debug(f"Cached tool list ({len(tools)} tools from {len(skill_ids)} skills)")

    async def _invalidate_tool_list_cache(self):
        """Invalidate tool list cache (internal, already locked)."""
        if self._tool_list_cache is not None:
            self._tool_list_cache = None
            logger.debug("Invalidated tool list cache")

    async def invalidate_skill(self, skill_id: str):
        """Invalidate cache for a specific skill.

        Args:
            skill_id: Skill ID to invalidate
        """
        async with self._skill_lock:
            if skill_id in self._skill_cache:
                del self._skill_cache[skill_id]
                self._invalidations += 1
                logger.info(f"Invalidated cache for skill '{skill_id}'")

        # Also invalidate tool list since skill changed
        async with self._tool_list_lock:
            if self._tool_list_cache and skill_id in self._tool_list_cache.skill_ids:
                await self._invalidate_tool_list_cache()

    async def invalidate_all(self):
        """Invalidate all caches."""
        async with self._skill_lock:
            count = len(self._skill_cache)
            self._skill_cache.clear()
            self._invalidations += count
            logger.info(f"Invalidated all skill caches ({count} skills)")

        async with self._tool_list_lock:
            await self._invalidate_tool_list_cache()

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        async with self._skill_lock:
            skill_total = self._skill_hits + self._skill_misses
            skill_hit_rate = (self._skill_hits / skill_total * 100) if skill_total > 0 else 0

            cached_skills = [
                {
                    "skill_id": skill_id,
                    "version": entry.skill.version,
                    "age_seconds": round(time.time() - entry.timestamp, 1),
                    "ttl_remaining": round(self.ttl_seconds - (time.time() - entry.timestamp), 1)
                }
                for skill_id, entry in self._skill_cache.items()
            ]

        async with self._tool_list_lock:
            tool_list_total = self._tool_list_hits + self._tool_list_misses
            tool_list_hit_rate = (self._tool_list_hits / tool_list_total * 100) if tool_list_total > 0 else 0

            tool_list_info = None
            if self._tool_list_cache:
                age = time.time() - self._tool_list_cache.timestamp
                tool_list_info = {
                    "tool_count": len(self._tool_list_cache.tools),
                    "skill_count": len(self._tool_list_cache.skill_ids),
                    "age_seconds": round(age, 1),
                    "ttl_remaining": round(self.ttl_seconds - age, 1)
                }

        return {
            "skill_cache": {
                "hits": self._skill_hits,
                "misses": self._skill_misses,
                "total_requests": skill_total,
                "hit_rate_percent": round(skill_hit_rate, 2),
                "cached_count": len(self._skill_cache),
                "cached_skills": cached_skills
            },
            "tool_list_cache": {
                "hits": self._tool_list_hits,
                "misses": self._tool_list_misses,
                "total_requests": tool_list_total,
                "hit_rate_percent": round(tool_list_hit_rate, 2),
                "current_cache": tool_list_info
            },
            "invalidations": self._invalidations,
            "ttl_seconds": self.ttl_seconds
        }

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0

        async with self._skill_lock:
            expired_skills = [
                skill_id
                for skill_id, entry in self._skill_cache.items()
                if (now - entry.timestamp) >= self.ttl_seconds
            ]

            for skill_id in expired_skills:
                del self._skill_cache[skill_id]
                removed += 1

            if expired_skills:
                logger.debug(f"Cleaned up {removed} expired skill cache entries")

        async with self._tool_list_lock:
            if self._tool_list_cache:
                age = now - self._tool_list_cache.timestamp
                if age >= self.ttl_seconds:
                    await self._invalidate_tool_list_cache()

        return removed
