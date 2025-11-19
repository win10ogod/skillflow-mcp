"""JSON-based storage layer for SkillFlow."""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles
from filelock import FileLock
from pydantic import BaseModel

from .schemas import (
    RecordingSession,
    ServerRegistry,
    Skill,
    SkillMeta,
    NodeExecution,
)
from .skill_cache import SkillCache

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class SkillNotFoundError(StorageError):
    """Skill not found in storage."""
    pass


class SessionNotFoundError(StorageError):
    """Recording session not found in storage."""
    pass


class StorageLayer:
    """JSON-based storage for skills, sessions, and runs."""

    def __init__(self, data_dir: str | Path = "data", enable_cache: bool = True, cache_ttl: int = 300):
        """Initialize storage layer.

        Args:
            data_dir: Root directory for data storage
            enable_cache: Enable skill caching for performance (default: True)
            cache_ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.data_dir = Path(data_dir)
        self.skills_dir = self.data_dir / "skills"
        self.sessions_dir = self.data_dir / "sessions"
        self.runs_dir = self.data_dir / "runs"
        self.registry_dir = self.data_dir / "registry"

        # In-memory index for fast lookups (metadata only)
        self._skill_index: dict[str, SkillMeta] = {}
        self._index_lock = asyncio.Lock()

        # Skill cache for performance (full skill objects)
        self._cache_enabled = enable_cache
        self._skill_cache = SkillCache(ttl_seconds=cache_ttl) if enable_cache else None

        # Ensure directories exist
        for dir_path in [self.skills_dir, self.sessions_dir, self.runs_dir, self.registry_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize storage and load indexes."""
        await self._rebuild_skill_index()

    # ========== Skill Storage ==========

    async def _rebuild_skill_index(self):
        """Rebuild the in-memory skill index from disk."""
        async with self._index_lock:
            self._skill_index.clear()

            for skill_dir in self.skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                meta_path = skill_dir / "meta.json"
                if not meta_path.exists():
                    continue

                try:
                    async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                        content = await f.read()
                        meta_data = json.loads(content)
                        skill_meta = SkillMeta(**meta_data)
                        self._skill_index[skill_meta.id] = skill_meta
                except Exception as e:
                    print(f"Error loading skill meta {meta_path}: {e}")

    def _get_skill_dir(self, skill_id: str) -> Path:
        """Get directory path for a skill."""
        return self.skills_dir / skill_id

    def _get_skill_version_path(self, skill_id: str, version: int) -> Path:
        """Get file path for a specific skill version."""
        return self._get_skill_dir(skill_id) / f"v{version:04d}.json"

    def _get_skill_meta_path(self, skill_id: str) -> Path:
        """Get file path for skill metadata."""
        return self._get_skill_dir(skill_id) / "meta.json"

    async def save_skill(self, skill: Skill) -> None:
        """Save a skill to storage.

        Args:
            skill: The skill to save
        """
        skill_dir = self._get_skill_dir(skill.id)
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Save skill version
        version_path = self._get_skill_version_path(skill.id, skill.version)
        await self._atomic_write_json(version_path, skill.model_dump(mode="json"))

        # Update metadata
        meta = SkillMeta(
            id=skill.id,
            name=skill.name,
            version=skill.version,
            description=skill.description,
            tags=skill.tags,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
            author=skill.author,
        )
        meta_path = self._get_skill_meta_path(skill.id)
        await self._atomic_write_json(meta_path, meta.model_dump(mode="json"))

        # Update index
        async with self._index_lock:
            self._skill_index[skill.id] = meta

    async def load_skill(self, skill_id: str, version: Optional[int] = None) -> Skill:
        """Load a skill from storage with caching.

        Args:
            skill_id: ID of the skill to load
            version: Specific version to load (None for latest)

        Returns:
            The loaded skill

        Raises:
            SkillNotFoundError: If skill is not found
        """
        skill_dir = self._get_skill_dir(skill_id)
        if not skill_dir.exists():
            raise SkillNotFoundError(f"Skill {skill_id} not found")

        if version is None:
            # Load latest version from meta
            meta_path = self._get_skill_meta_path(skill_id)
            if not meta_path.exists():
                raise SkillNotFoundError(f"Skill {skill_id} meta not found")

            async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                content = await f.read()
                meta = json.loads(content)
                version = meta["version"]

        # Try cache first (only for latest version)
        if self._cache_enabled and self._skill_cache and version is not None:
            cached_skill = await self._skill_cache.get_skill(skill_id, skill_dir)
            if cached_skill and cached_skill.version == version:
                return cached_skill

        # Cache miss - load from disk
        version_path = self._get_skill_version_path(skill_id, version)
        if not version_path.exists():
            raise SkillNotFoundError(f"Skill {skill_id} version {version} not found")

        async with aiofiles.open(version_path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            skill = Skill(**data)

        # Cache the skill (only latest version)
        if self._cache_enabled and self._skill_cache:
            await self._skill_cache.set_skill(skill, skill_dir)

        return skill

    async def list_skills(self) -> list[SkillMeta]:
        """List all skills.

        Returns:
            List of skill metadata
        """
        async with self._index_lock:
            return list(self._skill_index.values())

    async def delete_skill(self, skill_id: str, hard: bool = False) -> None:
        """Delete a skill.

        Args:
            skill_id: ID of skill to delete
            hard: If True, physically delete files; otherwise just remove from index
        """
        if hard:
            skill_dir = self._get_skill_dir(skill_id)
            if skill_dir.exists():
                import shutil
                shutil.rmtree(skill_dir)

        async with self._index_lock:
            self._skill_index.pop(skill_id, None)

        # Invalidate cache
        if self._cache_enabled and self._skill_cache:
            await self._skill_cache.invalidate_skill(skill_id)

    async def invalidate_skill_cache(self, skill_id: Optional[str] = None):
        """Manually invalidate skill cache.

        Args:
            skill_id: Specific skill to invalidate, or None to invalidate all
        """
        if self._cache_enabled and self._skill_cache:
            if skill_id:
                await self._skill_cache.invalidate_skill(skill_id)
            else:
                await self._skill_cache.invalidate_all()

    async def get_cache_stats(self) -> Optional[dict]:
        """Get cache statistics.

        Returns:
            Cache statistics dict, or None if caching disabled
        """
        if self._cache_enabled and self._skill_cache:
            return await self._skill_cache.get_stats()
        return None

    async def get_skill_meta(self, skill_id: str) -> Optional[SkillMeta]:
        """Get skill metadata from index.

        Args:
            skill_id: ID of the skill

        Returns:
            Skill metadata or None if not found
        """
        async with self._index_lock:
            return self._skill_index.get(skill_id)

    # ========== Recording Session Storage ==========

    def _get_session_path(self, session_id: str) -> Path:
        """Get file path for a recording session."""
        return self.sessions_dir / f"{session_id}.json"

    async def save_session(self, session: RecordingSession) -> None:
        """Save a recording session.

        Args:
            session: The recording session to save
        """
        session_path = self._get_session_path(session.id)
        await self._atomic_write_json(session_path, session.model_dump(mode="json"))

    async def load_session(self, session_id: str) -> RecordingSession:
        """Load a recording session.

        Args:
            session_id: ID of the session to load

        Returns:
            The loaded recording session

        Raises:
            SessionNotFoundError: If session is not found
        """
        session_path = self._get_session_path(session_id)
        if not session_path.exists():
            raise SessionNotFoundError(f"Session {session_id} not found")

        async with aiofiles.open(session_path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return RecordingSession(**data)

    async def list_sessions(self) -> list[str]:
        """List all recording session IDs.

        Returns:
            List of session IDs
        """
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            sessions.append(session_file.stem)
        return sorted(sessions)

    # ========== Run Log Storage ==========

    def _get_run_log_path(self, run_id: str) -> Path:
        """Get file path for a run log."""
        # Organize by date for better organization
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        date_dir = self.runs_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / f"{run_id}.jsonl"

    async def append_run_log(self, run_id: str, execution: NodeExecution) -> None:
        """Append a node execution to a run log.

        Args:
            run_id: ID of the run
            execution: Node execution to log
        """
        log_path = self._get_run_log_path(run_id)

        # Use file lock for concurrent writes
        lock_path = str(log_path) + ".lock"
        lock = FileLock(lock_path, timeout=10)

        with lock:
            async with aiofiles.open(log_path, "a", encoding="utf-8") as f:
                line = json.dumps(execution.model_dump(mode="json")) + "\n"
                await f.write(line)

    async def load_run_log(self, run_id: str) -> list[NodeExecution]:
        """Load all node executions for a run.

        Args:
            run_id: ID of the run

        Returns:
            List of node executions
        """
        # Search for run log in date directories
        for date_dir in self.runs_dir.iterdir():
            if not date_dir.is_dir():
                continue

            log_path = date_dir / f"{run_id}.jsonl"
            if log_path.exists():
                executions = []
                async with aiofiles.open(log_path, "r", encoding="utf-8") as f:
                    async for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            executions.append(NodeExecution(**data))
                return executions

        return []

    # ========== Server Registry Storage ==========

    def _get_registry_path(self) -> Path:
        """Get file path for server registry."""
        return self.registry_dir / "servers.json"

    async def save_registry(self, registry: ServerRegistry) -> None:
        """Save server registry.

        Args:
            registry: The server registry to save
        """
        registry_path = self._get_registry_path()
        await self._atomic_write_json(registry_path, registry.model_dump(mode="json"))

    async def load_registry(self) -> ServerRegistry:
        """Load server registry with auto-normalization.

        Returns:
            The server registry

        Notes:
            - Uses ConfigConverter to handle both mcpServers and servers formats
            - Automatically normalizes incomplete configurations
            - Returns empty registry if file doesn't exist or parsing fails
        """
        registry_path = self._get_registry_path()
        if not registry_path.exists():
            logger.info(f"Registry file does not exist: {registry_path}")
            return ServerRegistry()

        try:
            async with aiofiles.open(registry_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                logger.debug(f"Loaded registry JSON with {len(data.get('servers', data.get('mcpServers', {})))} servers")

                # Import ConfigConverter for normalization
                from .config_utils import ConfigConverter

                # Use ConfigConverter to handle normalization and validation
                registry = ConfigConverter.from_claude_code(data)
                logger.info(f"Successfully loaded and normalized registry with {len(registry.servers)} servers")
                return registry

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse registry JSON: {e}")
            return ServerRegistry()
        except ValueError as e:
            logger.error(f"Invalid registry configuration: {e}")
            return ServerRegistry()
        except Exception as e:
            logger.error(f"Failed to load registry: {e}", exc_info=True)
            return ServerRegistry()

    # ========== Helper Methods ==========

    async def _atomic_write_json(self, path: Path, data: Any) -> None:
        """Atomically write JSON data to a file.

        Args:
            path: Target file path
            data: Data to write (will be JSON serialized)
        """
        tmp_path = path.with_suffix(".tmp")

        # Write to temp file
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            await f.write(content)

        # Atomic rename
        os.replace(tmp_path, path)
