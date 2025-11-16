"""SkillFlow MCP Server implementation."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from .engine import ExecutionEngine
from .mcp_clients import MCPClientManager
from .recording import RecordingManager
from .schemas import (
    ExposeParamSpec,
    RecordingContext,
    SkillAuthor,
    SkillFilter,
    StepSelection,
    ToolCallStatus,
    TransportType,
)
from .skills import SkillManager
from .storage import StorageLayer


class SkillFlowServer:
    """Main SkillFlow MCP Server."""

    def __init__(self, data_dir: str | Path = "data"):
        """Initialize SkillFlow server.

        Args:
            data_dir: Directory for data storage
        """
        self.server = Server("skillflow")
        self.storage = StorageLayer(data_dir)
        self.skill_manager = SkillManager(self.storage)
        self.recording_manager = RecordingManager(self.storage)
        self.mcp_clients = MCPClientManager(self.storage)

        # Initialize execution engine with tool executor
        self.engine = ExecutionEngine(
            storage=self.storage,
            tool_executor=self._execute_tool,
        )

        # Track active recording session
        self.active_recording_session: Optional[str] = None

        # Register tools
        self._register_tools()
        self._setup_list_tools()

    async def initialize(self):
        """Initialize server and load data."""
        await self.storage.initialize()
        await self.mcp_clients.initialize()

        # Register dynamic skill tools
        await self._register_skill_tools()

    async def _execute_tool(
        self,
        server_id: Optional[str],
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool (used by execution engine).

        Args:
            server_id: Server ID (None for local)
            tool_name: Tool name
            args: Tool arguments

        Returns:
            Tool result
        """
        # Record if in recording mode
        if self.active_recording_session:
            start_time = datetime.utcnow()

        try:
            # Execute via MCP client
            result = await self.mcp_clients.call_tool(server_id, tool_name, args)

            # Record success
            if self.active_recording_session:
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self.recording_manager.record_tool_call(
                    session_id=self.active_recording_session,
                    server=server_id or "local",
                    tool=tool_name,
                    args=args,
                    result=result,
                    duration_ms=duration,
                    status=ToolCallStatus.SUCCESS,
                )

            return result

        except Exception as e:
            # Record error
            if self.active_recording_session:
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self.recording_manager.record_tool_call(
                    session_id=self.active_recording_session,
                    server=server_id or "local",
                    tool=tool_name,
                    args=args,
                    error=str(e),
                    duration_ms=duration,
                    status=ToolCallStatus.ERROR,
                )
            raise

    def _register_tools(self):
        """Register all management tools."""

        @self.server.call_tool()
        async def handle_tool_call(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle all tool calls dispatched by name."""

            # ========== Upstream Server Tools (Proxied) ==========
            server_id, actual_tool_name = self._parse_upstream_tool_name(tool_name)
            if server_id and actual_tool_name:
                # This is a proxied upstream tool call
                try:
                    result = await self._execute_tool(server_id, actual_tool_name, arguments)

                    # Format result
                    import json
                    if isinstance(result, dict):
                        content = result.get("content", [])
                        if isinstance(content, list):
                            return [TextContent(type="text", text=str(item)) for item in content]
                        else:
                            return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    else:
                        return [TextContent(type="text", text=str(result))]

                except Exception as e:
                    return [TextContent(type="text", text=f"Error calling upstream tool: {str(e)}")]

            # ========== Recording Tools ==========
            if tool_name == "start_recording":
                session_name = arguments.get("session_name")

                context = RecordingContext(
                    client_id="default-client",
                    workspace_id="default",
                )

                session_id = await self.recording_manager.start_session(context, session_name)
                self.active_recording_session = session_id

                return [
                    TextContent(
                        type="text",
                        text=f"Recording started. Session ID: {session_id}",
                    )
                ]

            if tool_name == "stop_recording":
                if not self.active_recording_session:
                    return [TextContent(type="text", text="No active recording session")]

                session = await self.recording_manager.stop_session(self.active_recording_session)
                session_id = self.active_recording_session
                self.active_recording_session = None

                return [
                    TextContent(
                        type="text",
                        text=f"Recording stopped. Session ID: {session_id}, Total calls: {len(session.logs)}",
                    )
                ]

            if tool_name == "list_recording_sessions":
                sessions = await self.storage.list_sessions()
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(sessions)} recording sessions:\n" + "\n".join(sessions),
                    )
                ]

            # ========== Skill Management Tools ==========
            if tool_name == "create_skill_from_session":
                session_id = arguments["session_id"]
                skill_id = arguments["skill_id"]
                name = arguments["name"]
                description = arguments["description"]
                tags = arguments.get("tags") or []
                expose_params = arguments.get("expose_params") or []

                params = []
                for p in expose_params:
                    params.append(
                        ExposeParamSpec(
                            name=p["name"],
                            description=p["description"],
                            schema=p["schema"],
                            source_path=p["source_path"],
                        )
                    )

                draft = await self.recording_manager.to_skill_draft(
                    session_id=session_id,
                    skill_id=skill_id,
                    name=name,
                    description=description,
                    expose_params=params,
                    tags=tags,
                )

                author = SkillAuthor(
                    workspace_id="default",
                    client_id="default-client",
                )

                skill = await self.skill_manager.create_skill(
                    skill_id=skill_id,
                    name=name,
                    description=description,
                    author=author,
                    draft=draft,
                )

                await self._register_skill_tools()

                return [
                    TextContent(
                        type="text",
                        text=f"Skill created: {skill.id} (v{skill.version})",
                    )
                ]

            if tool_name == "list_skills":
                query = arguments.get("query")
                tags = arguments.get("tags") or []

                filters = SkillFilter(query=query, tags=tags)
                skills = await self.skill_manager.list_skills(filters)

                if not skills:
                    return [TextContent(type="text", text="No skills found")]

                lines = [f"Found {len(skills)} skills:\n"]
                for skill in skills:
                    lines.append(f"- {skill.id} (v{skill.version}): {skill.name}")
                    lines.append(f"  {skill.description}")
                    if skill.tags:
                        lines.append(f"  Tags: {', '.join(skill.tags)}")

                return [TextContent(type="text", text="\n".join(lines))]

            if tool_name == "get_skill":
                skill_id = arguments["skill_id"]
                version = arguments.get("version")

                skill = await self.skill_manager.get_skill(skill_id, version)

                import json

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(skill.model_dump(mode="json"), indent=2),
                    )
                ]

            if tool_name == "delete_skill":
                skill_id = arguments["skill_id"]
                hard = arguments.get("hard", False)

                await self.skill_manager.delete_skill(skill_id, hard)
                await self._register_skill_tools()

                return [
                    TextContent(
                        type="text",
                        text=f"Skill {skill_id} deleted",
                    )
                ]

            # ========== Execution Tools ==========
            if tool_name == "get_run_status":
                run_id = arguments["run_id"]

                status = await self.engine.get_run_status(run_id)

                if not status:
                    return [TextContent(type="text", text=f"Run {run_id} not found")]

                import json

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(status.model_dump(mode="json"), indent=2),
                    )
                ]

            if tool_name == "cancel_run":
                run_id = arguments["run_id"]

                success = await self.engine.cancel_run(run_id)

                if success:
                    return [TextContent(type="text", text=f"Run {run_id} cancelled")]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Run {run_id} not found or already completed",
                        )
                    ]

            # ========== Server Registry Tools ==========
            if tool_name == "register_upstream_server":
                server_id = arguments["server_id"]
                name = arguments["name"]
                transport = arguments["transport"]
                config = arguments["config"]

                transport_type = TransportType(transport)

                await self.mcp_clients.register_server(
                    server_id=server_id,
                    name=name,
                    transport=transport_type,
                    config=config,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Server {server_id} registered",
                    )
                ]

            if tool_name == "list_upstream_servers":
                servers = await self.mcp_clients.list_servers()

                if not servers:
                    return [TextContent(type="text", text="No servers registered")]

                lines = [f"Registered servers ({len(servers)}):\n"]
                for server in servers:
                    status = "enabled" if server.enabled else "disabled"
                    lines.append(
                        f"- {server.server_id}: {server.name} ({server.transport.value}) [{status}]",
                    )

                return [TextContent(type="text", text="\n".join(lines))]

            if tool_name == "debug_upstream_tools":
                """Debug tool to check upstream tool proxy status."""
                import json
                import traceback

                debug_info = {
                    "registered_servers": [],
                    "connection_tests": {},
                    "proxy_tools": [],
                    "errors": []
                }

                try:
                    # Get registered servers
                    servers = await self.mcp_clients.list_servers()
                    for server in servers:
                        debug_info["registered_servers"].append({
                            "id": server.server_id,
                            "name": server.name,
                            "enabled": server.enabled,
                            "transport": server.transport.value,
                            "command": server.config.get("command", "N/A")
                        })

                        # Test connection to each server
                        if server.enabled:
                            try:
                                print(f"[Debug] Testing connection to {server.server_id}...")

                                try:
                                    tools = await asyncio.wait_for(
                                        self.mcp_clients.list_tools(server.server_id),
                                        timeout=30.0
                                    )

                                    debug_info["connection_tests"][server.server_id] = {
                                        "status": "success",
                                        "tools_count": len(tools),
                                        "sample_tools": [t["name"] for t in tools[:3]]
                                    }

                                except asyncio.TimeoutError:
                                    # Clean up partial connection to avoid resource leak
                                    print(f"[Debug] Timeout on {server.server_id}, cleaning up...")
                                    await self.mcp_clients.disconnect_server(server.server_id)

                                    debug_info["connection_tests"][server.server_id] = {
                                        "status": "timeout",
                                        "error": "Connection timed out after 30 seconds (cleaned up)"
                                    }

                            except Exception as e:
                                debug_info["connection_tests"][server.server_id] = {
                                    "status": "error",
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "traceback": traceback.format_exc()
                                }

                    # Try to get upstream tools
                    upstream_tools = await self._get_upstream_tools()
                    for tool in upstream_tools:
                        debug_info["proxy_tools"].append({
                            "name": tool.name,
                            "description": tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
                        })

                except Exception as e:
                    debug_info["errors"].append({
                        "error": str(e),
                        "type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    })

                return [TextContent(
                    type="text",
                    text=f"Debug Info:\n{json.dumps(debug_info, indent=2, ensure_ascii=False)}"
                )]

            # Unknown tool name
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {tool_name}",
                )
            ]

    async def _register_skill_tools(self):
        """Dynamically register tools for all skills."""
        skills = await self.skill_manager.list_skills()

        for skill_meta in skills:
            try:
                skill = await self.skill_manager.get_skill(skill_meta.id)

                # Create tool descriptor
                tool_name = f"skill__{skill.id}"

                # Define tool handler
                async def skill_handler(**inputs) -> list[TextContent]:
                    """Execute the skill."""
                    # Capture skill in closure
                    current_skill = skill

                    result = await self.engine.run_skill(current_skill, inputs)

                    import json
                    return [TextContent(
                        type="text",
                        text=json.dumps(result.model_dump(mode="json"), indent=2),
                    )]

                # Register tool
                # Note: This is a simplified approach; in production, use proper dynamic registration
                # For now, we'll rely on list_tools to expose skills

            except Exception as e:
                print(f"Error registering skill {skill_meta.id}: {e}")

    async def _get_upstream_tools(self) -> list[Tool]:
        """Get all tools from upstream servers and create proxy tools.

        Returns:
            List of proxy tools with prefixed names
        """
        upstream_tools = []
        errors = []  # Track errors for debugging

        try:
            servers = await self.mcp_clients.list_servers()

            for server_config in servers:
                if not server_config.enabled:
                    continue

                try:
                    # Try to get tools from this server with timeout
                    # Use asyncio.wait_for to prevent hanging on slow/unresponsive servers
                    print(f"[Skillflow] Fetching tools from {server_config.server_id}...")

                    try:
                        tools = await asyncio.wait_for(
                            self.mcp_clients.list_tools(server_config.server_id),
                            timeout=30.0  # Increased to 30 seconds for slow Windows servers
                        )
                    except asyncio.TimeoutError:
                        # CRITICAL: Clean up partial connection on timeout to avoid resource leak
                        error_msg = f"Timeout connecting to {server_config.server_id}"
                        print(f"[Skillflow] {error_msg} - cleaning up partial connection...")

                        # Disconnect to clean up any partial connections and kill orphaned processes
                        await self.mcp_clients.disconnect_server(server_config.server_id)

                        errors.append(error_msg)
                        continue  # Skip to next server

                    print(f"[Skillflow] Found {len(tools)} tools from {server_config.server_id}")

                    # Create proxy tools with prefixed names
                    for tool_dict in tools:
                        proxy_tool_name = f"upstream__{server_config.server_id}__{tool_dict['name']}"

                        # Add server info to description
                        description = tool_dict.get('description', '')
                        enhanced_description = f"[{server_config.name}] {description}"

                        proxy_tool = Tool(
                            name=proxy_tool_name,
                            description=enhanced_description,
                            inputSchema=tool_dict.get('inputSchema', {"type": "object", "properties": {}}),
                        )
                        upstream_tools.append(proxy_tool)

                except Exception as e:
                    error_msg = f"Error from {server_config.server_id}: {str(e)}"
                    print(f"[Skillflow] {error_msg}")
                    errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to get upstream tools: {str(e)}"
            print(f"[Skillflow] {error_msg}")
            errors.append(error_msg)

        if errors:
            print(f"[Skillflow] Encountered {len(errors)} errors while fetching upstream tools")

        print(f"[Skillflow] Total proxy tools created: {len(upstream_tools)}")

        return upstream_tools

    def _parse_upstream_tool_name(self, tool_name: str) -> tuple[Optional[str], Optional[str]]:
        """Parse upstream tool name to extract server_id and actual tool name.

        Args:
            tool_name: Tool name in format "upstream__<server_id>__<tool_name>"

        Returns:
            Tuple of (server_id, actual_tool_name) or (None, None) if not an upstream tool
        """
        if not tool_name.startswith("upstream__"):
            return None, None

        parts = tool_name.split("__", 2)
        if len(parts) != 3:
            return None, None

        return parts[1], parts[2]

    def _setup_list_tools(self):
        """Setup the list_tools handler."""
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools including skills and upstream server tools."""
            # Get base tools (recording, management, etc.)
            base_tools = [
                Tool(
                    name="start_recording",
                    description="Start recording tool calls into a session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_name": {
                                "type": "string",
                                "description": "Optional name for the session",
                            },
                        },
                    },
                ),
                Tool(
                    name="stop_recording",
                    description="Stop the active recording session",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="list_recording_sessions",
                    description="List all recording sessions",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="create_skill_from_session",
                    description="Create a skill from a recording session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "skill_id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "expose_params": {
                                "type": "array",
                                "items": {"type": "object"},
                            },
                        },
                        "required": ["session_id", "skill_id", "name", "description"],
                    },
                ),
                Tool(
                    name="list_skills",
                    description="List all skills",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                ),
                Tool(
                    name="get_skill",
                    description="Get detailed skill information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "skill_id": {"type": "string"},
                            "version": {"type": "integer"},
                        },
                        "required": ["skill_id"],
                    },
                ),
                Tool(
                    name="delete_skill",
                    description="Delete a skill",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "skill_id": {"type": "string"},
                            "hard": {"type": "boolean"},
                        },
                        "required": ["skill_id"],
                    },
                ),
                Tool(
                    name="get_run_status",
                    description="Get status of a skill run",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "run_id": {"type": "string"},
                        },
                        "required": ["run_id"],
                    },
                ),
                Tool(
                    name="cancel_run",
                    description="Cancel an active skill run",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "run_id": {"type": "string"},
                        },
                        "required": ["run_id"],
                    },
                ),
                Tool(
                    name="register_upstream_server",
                    description="Register an upstream MCP server",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "server_id": {"type": "string"},
                            "name": {"type": "string"},
                            "transport": {"type": "string"},
                            "config": {"type": "object"},
                        },
                        "required": ["server_id", "name", "transport", "config"],
                    },
                ),
                Tool(
                    name="list_upstream_servers",
                    description="List all registered upstream servers",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="debug_upstream_tools",
                    description="Debug tool to check if upstream tools are being proxied correctly",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

            # Add skill tools
            skill_tools_data = await self.skill_manager.list_as_mcp_tools()
            skill_tools = [
                Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"],
                )
                for t in skill_tools_data
            ]

            # Add upstream server tools (proxied)
            upstream_tools = await self._get_upstream_tools()

            return base_tools + skill_tools + upstream_tools

    def run(self):
        """Run the MCP server."""
        import sys
        from mcp.server.stdio import stdio_server

        async def main():
            await self.initialize()
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )

        asyncio.run(main())


def main():
    """Main entry point."""
    server = SkillFlowServer()
    server.run()


if __name__ == "__main__":
    main()
