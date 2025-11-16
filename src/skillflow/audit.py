"""
Audit logging system for SkillFlow MCP server.

Tracks all user actions, skill executions, tool calls, and system events
for compliance, debugging, and analysis purposes.
"""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .storage import StorageLayer


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Skill operations
    SKILL_CREATED = "skill_created"
    SKILL_UPDATED = "skill_updated"
    SKILL_DELETED = "skill_deleted"
    SKILL_EXECUTED = "skill_executed"
    SKILL_EXECUTION_COMPLETED = "skill_execution_completed"
    SKILL_EXECUTION_FAILED = "skill_execution_failed"
    SKILL_EXECUTION_CANCELLED = "skill_execution_cancelled"

    # Recording operations
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    RECORDING_DELETED = "recording_deleted"

    # Tool operations
    TOOL_CALLED = "tool_called"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"

    # Server operations
    UPSTREAM_SERVER_REGISTERED = "upstream_server_registered"
    UPSTREAM_SERVER_DISCONNECTED = "upstream_server_disconnected"
    UPSTREAM_SERVER_CONNECTION_FAILED = "upstream_server_connection_failed"

    # Resource operations
    RESOURCE_READ = "resource_read"
    PROMPT_RETRIEVED = "prompt_retrieved"

    # System events
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    ERROR_OCCURRED = "error_occurred"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Represents a single audit event."""

    id: str = Field(description="Unique event ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp (UTC)"
    )
    event_type: AuditEventType = Field(description="Type of event")
    severity: AuditEventSeverity = Field(
        default=AuditEventSeverity.INFO,
        description="Event severity"
    )

    # Context
    user_id: Optional[str] = Field(default=None, description="User ID (if applicable)")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    skill_id: Optional[str] = Field(default=None, description="Skill ID")
    run_id: Optional[str] = Field(default=None, description="Execution run ID")
    tool_name: Optional[str] = Field(default=None, description="Tool name")

    # Event details
    message: str = Field(description="Human-readable event message")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event details"
    )

    # Error information (if applicable)
    error_type: Optional[str] = Field(default=None, description="Error type")
    error_message: Optional[str] = Field(default=None, description="Error message")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace")

    # Performance metrics (if applicable)
    duration_ms: Optional[float] = Field(
        default=None,
        description="Operation duration in milliseconds"
    )

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuditLogger:
    """Manages audit logging for the SkillFlow server."""

    def __init__(self, storage: StorageLayer):
        """
        Initialize audit logger.

        Args:
            storage: Storage layer instance
        """
        self.storage = storage
        self.audit_dir = Path(storage.data_dir) / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # In-memory event buffer for real-time monitoring
        self.recent_events: list[AuditEvent] = []
        self.max_recent_events = 1000

    def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditEventSeverity = AuditEventSeverity.INFO,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        run_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            severity: Event severity level
            user_id: User ID (if applicable)
            session_id: Session ID
            skill_id: Skill ID
            run_id: Execution run ID
            tool_name: Tool name
            details: Additional event details
            error_type: Error type (if applicable)
            error_message: Error message (if applicable)
            stack_trace: Stack trace (if applicable)
            duration_ms: Operation duration in milliseconds

        Returns:
            Created audit event
        """
        import uuid

        event = AuditEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            skill_id=skill_id,
            run_id=run_id,
            tool_name=tool_name,
            message=message,
            details=details or {},
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            duration_ms=duration_ms,
        )

        # Save to storage
        self._save_event(event)

        # Add to recent events buffer
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

        return event

    def _save_event(self, event: AuditEvent) -> None:
        """
        Save audit event to storage.

        Events are organized by date for efficient querying and retention.

        Args:
            event: Audit event to save
        """
        # Organize by year/month/day for efficient querying
        date_str = event.timestamp.strftime("%Y/%m/%d")
        date_dir = self.audit_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # Save event to dated file
        event_file = date_dir / f"{event.id}.json"
        event_file.write_text(event.model_dump_json(indent=2))

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """
        Retrieve a specific audit event by ID.

        Args:
            event_id: Event ID

        Returns:
            Audit event if found, None otherwise
        """
        # Search in recent events first (fast path)
        for event in self.recent_events:
            if event.id == event_id:
                return event

        # Search in storage (slower)
        for event_file in self.audit_dir.rglob(f"{event_id}.json"):
            return AuditEvent.model_validate_json(event_file.read_text())

        return None

    def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditEventSeverity] = None,
        skill_id: Optional[str] = None,
        run_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """
        Query audit events with filters.

        Args:
            event_type: Filter by event type
            severity: Filter by severity
            skill_id: Filter by skill ID
            run_id: Filter by run ID
            session_id: Filter by session ID
            user_id: Filter by user ID
            start_time: Filter by start time (UTC)
            end_time: Filter by end time (UTC)
            limit: Maximum number of events to return

        Returns:
            List of matching audit events (newest first)
        """
        events: list[AuditEvent] = []

        # Determine which files to check based on time range
        if start_time and end_time:
            # Generate date range
            current = start_time.date()
            end = end_time.date()
            date_paths = []
            while current <= end:
                date_str = current.strftime("%Y/%m/%d")
                date_dir = self.audit_dir / date_str
                if date_dir.exists():
                    date_paths.append(date_dir)
                current = current.replace(day=current.day + 1)
        else:
            # Check all event files
            date_paths = [self.audit_dir]

        # Load and filter events
        for date_path in date_paths:
            for event_file in date_path.rglob("*.json"):
                try:
                    event = AuditEvent.model_validate_json(event_file.read_text())

                    # Apply filters
                    if event_type and event.event_type != event_type:
                        continue
                    if severity and event.severity != severity:
                        continue
                    if skill_id and event.skill_id != skill_id:
                        continue
                    if run_id and event.run_id != run_id:
                        continue
                    if session_id and event.session_id != session_id:
                        continue
                    if user_id and event.user_id != user_id:
                        continue
                    if start_time and event.timestamp < start_time:
                        continue
                    if end_time and event.timestamp > end_time:
                        continue

                    events.append(event)

                    if len(events) >= limit:
                        break
                except Exception:
                    # Skip corrupted event files
                    continue

            if len(events) >= limit:
                break

        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        return events[:limit]

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditEventSeverity] = None,
    ) -> list[AuditEvent]:
        """
        Get recent events from the in-memory buffer.

        This is much faster than querying storage, suitable for real-time monitoring.

        Args:
            limit: Maximum number of events
            event_type: Filter by event type
            severity: Filter by severity

        Returns:
            List of recent events (newest first)
        """
        filtered = self.recent_events

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        # Return newest first
        return list(reversed(filtered[-limit:]))

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Get audit statistics for a time range.

        Args:
            start_time: Start time (UTC)
            end_time: End time (UTC)

        Returns:
            Statistics dictionary with event counts, severity distribution, etc.
        """
        events = self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000  # Reasonable limit for statistics
        )

        # Count by event type
        event_type_counts: dict[str, int] = {}
        for event in events:
            event_type_counts[event.event_type] = \
                event_type_counts.get(event.event_type, 0) + 1

        # Count by severity
        severity_counts: dict[str, int] = {}
        for event in events:
            severity_counts[event.severity] = \
                severity_counts.get(event.severity, 0) + 1

        # Calculate error rate
        total_executions = (
            event_type_counts.get(AuditEventType.SKILL_EXECUTION_COMPLETED, 0) +
            event_type_counts.get(AuditEventType.SKILL_EXECUTION_FAILED, 0)
        )
        error_rate = 0.0
        if total_executions > 0:
            failed = event_type_counts.get(AuditEventType.SKILL_EXECUTION_FAILED, 0)
            error_rate = (failed / total_executions) * 100

        return {
            "total_events": len(events),
            "event_type_counts": event_type_counts,
            "severity_counts": severity_counts,
            "error_rate_percent": error_rate,
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            }
        }
