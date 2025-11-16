"""Recording session management module."""

import asyncio
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .schemas import (
    ConcurrencyMode,
    ExposeParamSpec,
    RecordingContext,
    RecordingSession,
    SkillDraft,
    SkillGraph,
    SkillNode,
    SkillEdge,
    StepSelection,
    ToolCallLog,
    ToolCallStatus,
    NodeKind,
    Concurrency,
)
from .storage import SessionNotFoundError, StorageLayer


class RecordingManager:
    """Manages recording sessions and skill draft generation."""

    def __init__(self, storage: StorageLayer):
        """Initialize recording manager.

        Args:
            storage: Storage layer instance
        """
        self.storage = storage
        self._active_sessions: dict[str, RecordingSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}

    async def start_session(
        self,
        context: RecordingContext,
        session_name: Optional[str] = None,
    ) -> str:
        """Start a new recording session.

        Args:
            context: Recording context with client info
            session_name: Optional human-readable name

        Returns:
            Session ID
        """
        session_id = f"session_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}_{uuid4().hex[:8]}"

        session = RecordingSession(
            id=session_id,
            started_at=datetime.utcnow(),
            client_id=context.client_id,
            workspace_id=context.workspace_id,
            metadata=context.metadata,
        )

        if session_name:
            session.metadata["name"] = session_name

        self._active_sessions[session_id] = session
        self._session_locks[session_id] = asyncio.Lock()

        return session_id

    async def stop_session(self, session_id: str) -> RecordingSession:
        """Stop a recording session and persist it.

        Args:
            session_id: ID of the session to stop

        Returns:
            The completed recording session

        Raises:
            SessionNotFoundError: If session not found
        """
        if session_id not in self._active_sessions:
            raise SessionNotFoundError(f"Active session {session_id} not found")

        async with self._session_locks[session_id]:
            session = self._active_sessions[session_id]
            session.ended_at = datetime.utcnow()

            # Persist to storage
            await self.storage.save_session(session)

            # Clean up
            del self._active_sessions[session_id]
            del self._session_locks[session_id]

        return session

    async def record_tool_call(
        self,
        session_id: str,
        server: str,
        tool: str,
        args: dict[str, Any],
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: float = 0,
        status: ToolCallStatus = ToolCallStatus.SUCCESS,
    ) -> None:
        """Record a tool call in an active session.

        Args:
            session_id: ID of the recording session
            server: Name of the MCP server
            tool: Name of the tool
            args: Tool arguments
            result: Tool result (optional)
            error: Error message if failed (optional)
            duration_ms: Execution duration in milliseconds
            status: Execution status
        """
        if session_id not in self._active_sessions:
            # Session not active, skip recording
            return

        async with self._session_locks[session_id]:
            session = self._active_sessions[session_id]

            log = ToolCallLog(
                index=len(session.logs) + 1,
                timestamp=datetime.utcnow(),
                server=server,
                tool=tool,
                args=args,
                result_summary=result or {},
                error=error,
                duration_ms=duration_ms,
                status=status,
            )

            session.logs.append(log)

    async def get_active_session(self, session_id: str) -> Optional[RecordingSession]:
        """Get an active recording session.

        Args:
            session_id: ID of the session

        Returns:
            The recording session or None if not active
        """
        return self._active_sessions.get(session_id)

    async def list_active_sessions(self) -> list[str]:
        """List all active session IDs.

        Returns:
            List of active session IDs
        """
        return list(self._active_sessions.keys())

    async def to_skill_draft(
        self,
        session_id: str,
        skill_id: str,
        name: str,
        description: str,
        selection: Optional[StepSelection] = None,
        expose_params: Optional[list[ExposeParamSpec]] = None,
        tags: Optional[list[str]] = None,
    ) -> SkillDraft:
        """Generate a skill draft from a recording session.

        Args:
            session_id: ID of the recording session
            skill_id: ID for the new skill
            name: Name for the skill
            description: Description for the skill
            selection: Step selection (None for all steps)
            expose_params: Parameters to expose as skill inputs
            tags: Tags for the skill

        Returns:
            A skill draft

        Raises:
            SessionNotFoundError: If session not found
        """
        # Load session from storage
        session = await self.storage.load_session(session_id)

        # Select logs
        selected_logs = self._select_logs(session, selection)

        # Generate graph nodes
        nodes = []
        for i, log in enumerate(selected_logs):
            node = SkillNode(
                id=f"step_{i + 1}",
                kind=NodeKind.TOOL_CALL,
                server=log.server,
                tool=log.tool,
                args_template=log.args,  # Will be templated later
                export_outputs={},  # Will be populated if needed
            )
            nodes.append(node)

        # Generate linear edges (sequential execution)
        edges = []
        for i in range(len(nodes) - 1):
            edge = SkillEdge(
                from_node=nodes[i].id,
                to_node=nodes[i + 1].id,
            )
            edges.append(edge)

        # Apply parameter templating
        inputs_schema = self._build_inputs_schema(expose_params or [])
        self._apply_param_templates(nodes, expose_params or [])

        # Build graph
        graph = SkillGraph(
            nodes=nodes,
            edges=edges,
            concurrency=Concurrency(
                mode=ConcurrencyMode.SEQUENTIAL,
            ),
        )

        # Basic output schema (can be customized later)
        output_schema = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
            },
        }

        return SkillDraft(
            skill_id=skill_id,
            name=name,
            description=description,
            tags=tags or [],
            graph=graph,
            inputs_schema=inputs_schema,
            output_schema=output_schema,
            source_session_id=session_id,
        )

    def _select_logs(
        self,
        session: RecordingSession,
        selection: Optional[StepSelection],
    ) -> list[ToolCallLog]:
        """Select logs based on selection criteria.

        Args:
            session: The recording session
            selection: Selection criteria

        Returns:
            Selected tool call logs
        """
        if selection is None:
            return session.logs

        logs = session.logs

        # Filter by indices
        if selection.indices is not None:
            return [logs[i - 1] for i in selection.indices if 1 <= i <= len(logs)]

        # Filter by range
        start = (selection.start_index or 1) - 1
        end = selection.end_index or len(logs)
        return logs[start:end]

    def _build_inputs_schema(self, expose_params: list[ExposeParamSpec]) -> dict[str, Any]:
        """Build JSON Schema for skill inputs.

        Args:
            expose_params: Parameters to expose

        Returns:
            JSON Schema for inputs
        """
        if not expose_params:
            return {
                "type": "object",
                "properties": {},
                "required": [],
            }

        properties = {}
        required = []

        for param in expose_params:
            properties[param.name] = param.schema_
            # Simple heuristic: if schema doesn't allow null, it's required
            if param.schema_.get("type") != "null" and "null" not in param.schema_.get("type", []):
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def _apply_param_templates(
        self,
        nodes: list[SkillNode],
        expose_params: list[ExposeParamSpec],
    ) -> None:
        """Apply parameter templates to node args.

        This replaces specific arg values with template references like $inputs.param_name.

        Args:
            nodes: Skill nodes to template
            expose_params: Parameters being exposed
        """
        for param in expose_params:
            # Parse source path (e.g., "logs[2].args.text")
            # For simplicity, we'll use a basic implementation
            # In production, use a proper JSONPath library

            if not param.source_path.startswith("logs["):
                continue

            try:
                # Extract index: logs[N].args.field
                parts = param.source_path.split("]", 1)
                index_str = parts[0].replace("logs[", "")
                log_index = int(index_str)

                if "." not in parts[1]:
                    continue

                # Extract field path: .args.field -> ["args", "field"]
                field_path = parts[1].lstrip(".").split(".")

                if log_index <= 0 or log_index > len(nodes):
                    continue

                # Replace in corresponding node
                node = nodes[log_index - 1]
                if field_path[0] == "args" and len(field_path) > 1:
                    arg_name = field_path[1]
                    # Replace value with template
                    node.args_template[arg_name] = f"$inputs.{param.name}"

            except (ValueError, IndexError, KeyError):
                # Skip invalid paths
                continue
