"""File watching system for hot-reload of skills.

This module monitors the skills directory for changes and triggers
automatic cache invalidation and reload.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional
import time

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches skill directory for changes and triggers callbacks.

    Uses a polling-based approach for cross-platform compatibility.
    For production, consider using watchdog library for inotify/FSEvents.
    """

    def __init__(
        self,
        watch_dir: Path,
        on_skill_changed: Optional[Callable[[str], None]] = None,
        on_skill_created: Optional[Callable[[str], None]] = None,
        on_skill_deleted: Optional[Callable[[str], None]] = None,
        poll_interval: float = 2.0
    ):
        """Initialize file watcher.

        Args:
            watch_dir: Directory to watch (skills directory)
            on_skill_changed: Callback when skill is modified
            on_skill_created: Callback when skill is created
            on_skill_deleted: Callback when skill is deleted
            poll_interval: Polling interval in seconds (default: 2s)
        """
        self.watch_dir = Path(watch_dir)
        self.on_skill_changed = on_skill_changed
        self.on_skill_created = on_skill_created
        self.on_skill_deleted = on_skill_deleted
        self.poll_interval = poll_interval

        # Track file states
        self._file_mtimes: dict[Path, float] = {}
        self._skill_dirs: set[str] = set()

        # Control
        self._running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(f"Initialized file watcher for {watch_dir} (poll interval: {poll_interval}s)")

    def _scan_directory(self) -> dict[str, dict[str, float]]:
        """Scan skills directory and return skill states.

        Returns:
            Dict mapping skill_id to dict of {filename: mtime}
        """
        skills = {}

        if not self.watch_dir.exists():
            return skills

        for skill_dir in self.watch_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_id = skill_dir.name
            files = {}

            # Track meta.json and all version files
            for file_path in skill_dir.iterdir():
                if file_path.is_file() and (file_path.name == "meta.json" or file_path.name.startswith("v")):
                    try:
                        files[file_path.name] = file_path.stat().st_mtime
                    except OSError:
                        pass

            if files:  # Only include if has files
                skills[skill_id] = files

        return skills

    async def _check_for_changes(self):
        """Check for file changes and trigger callbacks."""
        current_state = self._scan_directory()
        current_skill_ids = set(current_state.keys())

        # Detect new skills (created)
        new_skills = current_skill_ids - self._skill_dirs
        for skill_id in new_skills:
            logger.info(f"Detected new skill: {skill_id}")
            if self.on_skill_created:
                try:
                    await asyncio.to_thread(self.on_skill_created, skill_id)
                except Exception as e:
                    logger.error(f"Error in on_skill_created callback for {skill_id}: {e}")

        # Detect deleted skills
        deleted_skills = self._skill_dirs - current_skill_ids
        for skill_id in deleted_skills:
            logger.info(f"Detected deleted skill: {skill_id}")
            if self.on_skill_deleted:
                try:
                    await asyncio.to_thread(self.on_skill_deleted, skill_id)
                except Exception as e:
                    logger.error(f"Error in on_skill_deleted callback for {skill_id}: {e}")

        # Detect modified skills
        for skill_id in current_skill_ids & self._skill_dirs:
            current_files = current_state[skill_id]

            # Get previous state from _file_mtimes
            skill_dir = self.watch_dir / skill_id
            changed = False

            for filename, mtime in current_files.items():
                file_path = skill_dir / filename
                prev_mtime = self._file_mtimes.get(file_path)

                if prev_mtime is None or mtime != prev_mtime:
                    changed = True
                    break

            if changed:
                logger.info(f"Detected modified skill: {skill_id}")
                if self.on_skill_changed:
                    try:
                        await asyncio.to_thread(self.on_skill_changed, skill_id)
                    except Exception as e:
                        logger.error(f"Error in on_skill_changed callback for {skill_id}: {e}")

        # Update state
        self._skill_dirs = current_skill_ids
        self._file_mtimes.clear()
        for skill_id, files in current_state.items():
            skill_dir = self.watch_dir / skill_id
            for filename, mtime in files.items():
                file_path = skill_dir / filename
                self._file_mtimes[file_path] = mtime

    async def _watch_loop(self):
        """Main watching loop."""
        logger.info("File watcher started")

        # Initial scan
        self._scan_directory()
        current_state = self._scan_directory()
        self._skill_dirs = set(current_state.keys())
        for skill_id, files in current_state.items():
            skill_dir = self.watch_dir / skill_id
            for filename, mtime in files.items():
                file_path = skill_dir / filename
                self._file_mtimes[file_path] = mtime

        while self._running:
            try:
                await self._check_for_changes()
            except Exception as e:
                logger.error(f"Error in file watcher loop: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

        logger.info("File watcher stopped")

    async def start(self):
        """Start watching for file changes."""
        if self._running:
            logger.warning("File watcher already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("File watcher started")

    async def stop(self):
        """Stop watching for file changes."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("File watcher stopped")

    async def trigger_manual_scan(self):
        """Manually trigger a directory scan.

        Useful for forcing an immediate check without waiting for poll interval.
        """
        if self._running:
            await self._check_for_changes()
            logger.info("Manual scan triggered")


class WatchdogFileWatcher:
    """Alternative implementation using watchdog library for better performance.

    This provides real-time file system events instead of polling.
    Requires: pip install watchdog
    """

    def __init__(
        self,
        watch_dir: Path,
        on_skill_changed: Optional[Callable[[str], None]] = None,
        on_skill_created: Optional[Callable[[str], None]] = None,
        on_skill_deleted: Optional[Callable[[str], None]] = None,
    ):
        """Initialize watchdog-based file watcher.

        Args:
            watch_dir: Directory to watch (skills directory)
            on_skill_changed: Callback when skill is modified
            on_skill_created: Callback when skill is created
            on_skill_deleted: Callback when skill is deleted
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent
        except ImportError:
            raise ImportError(
                "watchdog library not installed. "
                "Install it with: pip install watchdog"
            )

        self.watch_dir = Path(watch_dir)
        self.on_skill_changed = on_skill_changed
        self.on_skill_created = on_skill_created
        self.on_skill_deleted = on_skill_deleted

        # Debounce rapid events (e.g., editor save might trigger multiple events)
        self._debounce_delay = 0.5  # 500ms
        self._pending_events: dict[str, float] = {}
        self._event_task: Optional[asyncio.Task] = None

        # Watchdog components
        self._observer = Observer()
        self._handler = self._create_handler()

        logger.info(f"Initialized watchdog file watcher for {watch_dir}")

    def _create_handler(self):
        """Create watchdog event handler."""
        from watchdog.events import FileSystemEventHandler

        watcher = self

        class SkillEventHandler(FileSystemEventHandler):
            """Handle file system events for skills."""

            def _extract_skill_id(self, path: str) -> Optional[str]:
                """Extract skill ID from file path."""
                path_obj = Path(path)
                try:
                    # Check if path is inside skills directory
                    rel_path = path_obj.relative_to(watcher.watch_dir)
                    # First component should be skill_id
                    parts = rel_path.parts
                    if len(parts) >= 1:
                        return parts[0]
                except ValueError:
                    return None
                return None

            def _schedule_callback(self, skill_id: str, event_type: str):
                """Schedule callback with debouncing."""
                if not skill_id:
                    return

                current_time = time.time()
                watcher._pending_events[f"{skill_id}:{event_type}"] = current_time

                # Start processing task if not running
                if watcher._event_task is None or watcher._event_task.done():
                    watcher._event_task = asyncio.create_task(watcher._process_pending_events())

            def on_created(self, event):
                """Handle file/directory creation."""
                if event.is_directory:
                    # New skill directory
                    skill_id = Path(event.src_path).name
                    if skill_id:
                        self._schedule_callback(skill_id, "created")
                else:
                    # File created (might be new version or meta.json)
                    skill_id = self._extract_skill_id(event.src_path)
                    if skill_id and (event.src_path.endswith("meta.json") or "/v" in event.src_path):
                        self._schedule_callback(skill_id, "changed")

            def on_modified(self, event):
                """Handle file modification."""
                if not event.is_directory:
                    skill_id = self._extract_skill_id(event.src_path)
                    if skill_id and (event.src_path.endswith("meta.json") or "/v" in event.src_path):
                        self._schedule_callback(skill_id, "changed")

            def on_deleted(self, event):
                """Handle file/directory deletion."""
                if event.is_directory:
                    # Skill directory deleted
                    skill_id = Path(event.src_path).name
                    if skill_id:
                        self._schedule_callback(skill_id, "deleted")

        return SkillEventHandler()

    async def _process_pending_events(self):
        """Process pending events after debounce delay."""
        await asyncio.sleep(self._debounce_delay)

        current_time = time.time()
        events_to_process = []

        # Find events that have aged beyond debounce delay
        for event_key, event_time in list(self._pending_events.items()):
            if current_time - event_time >= self._debounce_delay:
                events_to_process.append(event_key)
                del self._pending_events[event_key]

        # Process events
        for event_key in events_to_process:
            skill_id, event_type = event_key.split(":", 1)

            try:
                if event_type == "created" and self.on_skill_created:
                    await asyncio.to_thread(self.on_skill_created, skill_id)
                    logger.info(f"Processed skill created event: {skill_id}")
                elif event_type == "changed" and self.on_skill_changed:
                    await asyncio.to_thread(self.on_skill_changed, skill_id)
                    logger.info(f"Processed skill changed event: {skill_id}")
                elif event_type == "deleted" and self.on_skill_deleted:
                    await asyncio.to_thread(self.on_skill_deleted, skill_id)
                    logger.info(f"Processed skill deleted event: {skill_id}")
            except Exception as e:
                logger.error(f"Error processing event {event_key}: {e}", exc_info=True)

    async def start(self):
        """Start watching for file changes."""
        self._observer.schedule(self._handler, str(self.watch_dir), recursive=True)
        self._observer.start()
        logger.info("Watchdog file watcher started")

    async def stop(self):
        """Stop watching for file changes."""
        self._observer.stop()
        self._observer.join()

        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass

        logger.info("Watchdog file watcher stopped")
