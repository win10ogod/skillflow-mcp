"""SkillFlow MCP Server implementation."""

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, AudioContent, EmbeddedResource

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
from .tool_naming import generate_proxy_tool_name, parse_proxy_tool_name


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

        # Mapping from hash to server_id for proxy tools
        # When using compact hash format (up_<hash>_toolname), we need to resolve hash back to server_id
        self._hash_to_server_id: dict[str, str] = {}

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

            # ========== Skill Tools (Dynamic) ==========
            if tool_name.startswith("skill__"):
                # Extract skill ID from tool name
                skill_id = tool_name[7:]  # Remove "skill__" prefix

                try:
                    # Load and execute the skill
                    skill = await self.skill_manager.get_skill(skill_id)
                    result = await self.engine.run_skill(skill, arguments)

                    import json
                    return [TextContent(
                        type="text",
                        text=json.dumps(result.model_dump(mode="json"), indent=2),
                    )]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error executing skill '{skill_id}': {str(e)}",
                    )]

            # ========== Upstream Server Tools (Proxied) ==========
            server_id, actual_tool_name = self._parse_upstream_tool_name(tool_name)
            if server_id and actual_tool_name:
                # This is a proxied upstream tool call
                try:
                    result = await self._execute_tool(server_id, actual_tool_name, arguments)

                    # Convert upstream MCP result to Content objects
                    # MCP protocol returns: {'content': [...], 'isError': bool}
                    # Support all MCP content types: text, image, audio, resource
                    import json
                    if isinstance(result, dict):
                        content = result.get("content", [])
                        if isinstance(content, list) and len(content) > 0:
                            # Convert each content item to appropriate Content type
                            converted_content = []
                            for item in content:
                                if isinstance(item, dict):
                                    content_type = item.get("type", "text")

                                    if content_type == "text":
                                        # TextContent: text messages
                                        converted_content.append(TextContent(
                                            type="text",
                                            text=item.get("text", str(item)),
                                        ))
                                    elif content_type == "image":
                                        # ImageContent: images (screenshots, charts, etc.)
                                        converted_content.append(ImageContent(
                                            type="image",
                                            data=item.get("data", ""),
                                            mimeType=item.get("mimeType", "image/png"),
                                        ))
                                    elif content_type == "audio":
                                        # AudioContent: audio files (recordings, TTS, etc.)
                                        converted_content.append(AudioContent(
                                            type="audio",
                                            data=item.get("data", ""),
                                            mimeType=item.get("mimeType", "audio/wav"),
                                        ))
                                    elif content_type == "resource":
                                        # EmbeddedResource: embedded resources (files, data, etc.)
                                        converted_content.append(EmbeddedResource(
                                            type="resource",
                                            resource=item.get("resource", {}),
                                        ))
                                    else:
                                        # Unknown type: convert to text for safety
                                        # This ensures forward compatibility with future content types
                                        converted_content.append(TextContent(
                                            type="text",
                                            text=json.dumps(item, indent=2, ensure_ascii=False),
                                        ))
                                else:
                                    # Not a dict: convert to text
                                    converted_content.append(TextContent(
                                        type="text",
                                        text=str(item),
                                    ))

                            return converted_content
                        else:
                            # No content or empty: return formatted result
                            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
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

                # Note: MCP servers cannot proactively notify clients of tool list changes
                # Some clients (like Fount) cache the tool list and need manual refresh
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"✅ Skill created: {skill.id} (v{skill.version})\n"
                            f"Tool name: skill__{skill.id}\n\n"
                            f"⚠️ Note: If the tool doesn't appear in your client, try:\n"
                            f"  1. Refresh the client's tool list\n"
                            f"  2. Or call it directly: skill__{skill.id}\n"
                            f"  3. Or restart the client if refresh doesn't work"
                        ),
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
                                # CRITICAL: Clean up connection on ANY error to prevent process leak
                                print(f"[Debug] Error on {server.server_id}, cleaning up...")
                                try:
                                    await self.mcp_clients.disconnect_server(server.server_id)
                                except:
                                    pass  # Ignore cleanup errors

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

            if tool_name == "debug_skill_tools":
                """Debug tool to check skill tool registration status."""
                import json

                debug_info = {
                    "skills": [],
                    "skill_tools": [],
                    "total_skills": 0,
                }

                try:
                    # Get all skills
                    skills = await self.skill_manager.list_skills()
                    debug_info["total_skills"] = len(skills)

                    for skill_meta in skills:
                        try:
                            skill = await self.skill_manager.get_skill(skill_meta.id)
                            debug_info["skills"].append({
                                "id": skill.id,
                                "name": skill.name,
                                "version": skill.version,
                                "description": skill.description,
                                "tool_name": f"skill__{skill.id}",
                            })
                        except Exception as e:
                            debug_info["skills"].append({
                                "id": skill_meta.id,
                                "error": str(e),
                            })

                    # Get skill tools as they would appear in list_tools
                    skill_tools_data = await self.skill_manager.list_as_mcp_tools()
                    debug_info["skill_tools"] = [
                        {
                            "name": t["name"],
                            "description": t.get("description", "")[:60] + "...",
                        }
                        for t in skill_tools_data
                    ]

                except Exception as e:
                    debug_info["error"] = str(e)
                    import traceback
                    debug_info["traceback"] = traceback.format_exc()

                return [TextContent(
                    type="text",
                    text=f"Skill Tools Debug Info:\n{json.dumps(debug_info, indent=2, ensure_ascii=False)}"
                )]

            if tool_name == "debug_skill_definition":
                """Debug tool to inspect skill definition and compare with source recording."""
                import json

                skill_id = arguments["skill_id"]

                debug_info = {
                    "skill_id": skill_id,
                    "found": False,
                    "skill": {},
                    "nodes": [],
                    "source_session": {},
                }

                try:
                    # Load skill
                    skill = await self.skill_manager.get_skill(skill_id)

                    if skill:
                        debug_info["found"] = True

                        # Check metadata for source_session_id
                        source_session_id = skill.metadata.get("source_session_id")

                        debug_info["skill"] = {
                            "id": skill.id,
                            "name": skill.name,
                            "version": skill.version,
                            "description": skill.description,
                            "tags": skill.tags,
                            "metadata": skill.metadata,
                            "source_session_id": source_session_id,
                        }

                        # Inspect each node in the graph
                        if skill.graph:
                            for node in skill.graph.nodes:
                                node_detail = {
                                    "id": node.id,
                                    "kind": node.kind,
                                    "server": node.server,
                                    "tool": node.tool,
                                    "args_template": node.args_template,
                                    "args_json": json.dumps(node.args_template, ensure_ascii=False),
                                    "args_repr": repr(node.args_template),
                                }

                                # For text arguments, show detailed character analysis
                                for key, value in node.args_template.items():
                                    if isinstance(value, str) and len(value) > 0 and not value.startswith("$") and not value.startswith("@"):
                                        node_detail[f"arg_{key}_length"] = len(value)
                                        node_detail[f"arg_{key}_chars"] = [c for c in value]
                                        node_detail[f"arg_{key}_bytes"] = value.encode('utf-8').hex()

                                debug_info["nodes"].append(node_detail)

                except Exception as e:
                    debug_info["error"] = str(e)
                    import traceback
                    debug_info["traceback"] = traceback.format_exc()

                return [TextContent(
                    type="text",
                    text=f"Skill Definition Debug Info:\n{json.dumps(debug_info, indent=2, ensure_ascii=False)}"
                )]

            if tool_name == "debug_skill_execution":
                """Debug tool to trace skill execution and diagnose parameter corruption."""
                import json

                run_id = arguments["run_id"]

                debug_info = {
                    "run_id": run_id,
                    "found": False,
                    "executions": [],
                }

                try:
                    # Load execution log
                    executions = await self.storage.load_run_log(run_id)

                    if executions:
                        debug_info["found"] = True
                        debug_info["total_executions"] = len(executions)

                        # Inspect each node execution
                        for execution in executions:
                            exec_detail = {
                                "node_id": execution.node_id,
                                "server": execution.server,
                                "tool": execution.tool,
                                "status": execution.status,
                                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                                "ended_at": execution.ended_at.isoformat() if execution.ended_at else None,
                                "args_resolved": execution.args_resolved,
                                "args_resolved_json": json.dumps(execution.args_resolved, ensure_ascii=False),
                                "args_resolved_repr": repr(execution.args_resolved),
                                "output": execution.output,
                                "error": execution.error,
                            }

                            # For text arguments in resolved args, show detailed character analysis
                            for key, value in execution.args_resolved.items():
                                if isinstance(value, str) and len(value) > 0:
                                    exec_detail[f"resolved_{key}_length"] = len(value)
                                    exec_detail[f"resolved_{key}_chars"] = [c for c in value]
                                    exec_detail[f"resolved_{key}_bytes"] = value.encode('utf-8').hex()

                            debug_info["executions"].append(exec_detail)
                    else:
                        debug_info["message"] = "No execution log found for this run_id"

                except Exception as e:
                    debug_info["error"] = str(e)
                    import traceback
                    debug_info["traceback"] = traceback.format_exc()

                return [TextContent(
                    type="text",
                    text=f"Skill Execution Debug Info:\n{json.dumps(debug_info, indent=2, ensure_ascii=False)}"
                )]

            if tool_name == "debug_recording_session":
                """Debug tool to inspect recording session details and diagnose text scrambling issues."""
                import json

                session_id = arguments["session_id"]

                debug_info = {
                    "session_id": session_id,
                    "found": False,
                    "logs": [],
                    "summary": {},
                }

                try:
                    # Try to load from active sessions first
                    session = await self.recording_manager.get_active_session(session_id)

                    # If not active, try to load from storage
                    if not session:
                        session = await self.storage.load_session(session_id)

                    if session:
                        debug_info["found"] = True
                        debug_info["summary"] = {
                            "started_at": session.started_at.isoformat() if session.started_at else None,
                            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                            "client_id": session.client_id,
                            "workspace_id": session.workspace_id,
                            "total_logs": len(session.logs),
                            "metadata": session.metadata,
                        }

                        # Show each log with detailed argument inspection
                        for log in session.logs:
                            log_detail = {
                                "index": log.index,
                                "timestamp": log.timestamp.isoformat(),
                                "server": log.server,
                                "tool": log.tool,
                                "args": log.args,  # Show exact recorded args
                                "args_json": json.dumps(log.args, ensure_ascii=False),  # Show JSON representation
                                "args_repr": repr(log.args),  # Show Python repr
                                "status": log.status,
                                "duration_ms": log.duration_ms,
                                "error": log.error,
                            }

                            # For text arguments, show detailed character analysis
                            for key, value in log.args.items():
                                if isinstance(value, str) and len(value) > 0:
                                    log_detail[f"arg_{key}_length"] = len(value)
                                    log_detail[f"arg_{key}_chars"] = [c for c in value]
                                    log_detail[f"arg_{key}_bytes"] = value.encode('utf-8').hex()

                            debug_info["logs"].append(log_detail)
                    else:
                        debug_info["error"] = "Session not found"

                except Exception as e:
                    debug_info["error"] = str(e)
                    import traceback
                    debug_info["traceback"] = traceback.format_exc()

                return [TextContent(
                    type="text",
                    text=f"Recording Session Debug Info:\n{json.dumps(debug_info, indent=2, ensure_ascii=False)}"
                )]

            # Unknown tool name
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {tool_name}",
                )
            ]

    async def _register_skill_tools(self):
        """Register skill tools (now handled dynamically in handle_tool_call).

        This method is kept for backward compatibility but no longer performs
        pre-registration. Skill tools are now loaded and executed on-demand,
        allowing new skills to be callable immediately without server restart.
        """
        # Skills are now handled dynamically in handle_tool_call
        # No pre-registration needed
        pass

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

                    # Create proxy tools with compact naming
                    # Max 47 chars to account for Fount's 13-char prefix (mcp_skillflow_)
                    # Total: 13 + 47 = 60 chars
                    for tool_dict in tools:
                        original_tool_name = tool_dict['name']
                        proxy_tool_name = generate_proxy_tool_name(
                            server_config.server_id,
                            original_tool_name,
                            max_length=47  # Reserve space for client prefix
                        )

                        # Store hash mapping if using hash format
                        # Parse to check if it's a hash format (up_<hash>_toolname)
                        server_part, tool_part = parse_proxy_tool_name(proxy_tool_name)
                        if server_part and len(server_part) <= 8 and all(c in '0123456789abcdef' for c in server_part):
                            # It's a hash, store the mapping
                            self._hash_to_server_id[server_part] = server_config.server_id

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
            tool_name: Tool name in format:
                - "up_<server_id>_<tool_name>" (compact)
                - "up_<hash>_<tool_name>" (hash)
                - "upstream__<server_id>__<tool_name>" (legacy, deprecated)

        Returns:
            Tuple of (server_id, actual_tool_name) or (None, None) if not an upstream tool
        """
        server_part, tool_part = parse_proxy_tool_name(tool_name)

        if not server_part or not tool_part:
            return None, None

        # If server_part looks like a hash (4-8 hex chars), resolve to actual server_id
        if len(server_part) <= 8 and all(c in '0123456789abcdef' for c in server_part):
            # It's a hash, look up the actual server_id
            server_id = self._hash_to_server_id.get(server_part)
            if not server_id:
                print(f"[Skillflow] Warning: Hash {server_part} not found in mapping")
                return None, None
            return server_id, tool_part

        # It's a full server_id
        return server_part, tool_part

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
                Tool(
                    name="debug_skill_tools",
                    description="Debug tool to check skill tool registration status",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="debug_skill_definition",
                    description="Debug tool to inspect skill definition and compare with source recording",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "skill_id": {
                                "type": "string",
                                "description": "ID of the skill to inspect",
                            },
                        },
                        "required": ["skill_id"],
                    },
                ),
                Tool(
                    name="debug_skill_execution",
                    description="Debug tool to trace skill execution and diagnose parameter corruption during replay",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "run_id": {
                                "type": "string",
                                "description": "ID of the skill execution run to inspect",
                            },
                        },
                        "required": ["run_id"],
                    },
                ),
                Tool(
                    name="debug_recording_session",
                    description="Debug tool to inspect recording session details and diagnose text scrambling issues",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "ID of the recording session to inspect",
                            },
                        },
                        "required": ["session_id"],
                    },
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

    async def cleanup(self):
        """Clean up resources when server shuts down."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Cleaning up SkillFlow server resources...")

        # Close all upstream client connections
        try:
            await self.mcp_clients.close_all()
            logger.info("All upstream clients closed")
        except Exception as e:
            logger.error(f"Error closing upstream clients: {e}")

    def run(self):
        """Run the MCP server."""
        import sys
        import signal
        import atexit
        from mcp.server.stdio import stdio_server

        # Register cleanup on normal exit
        def sync_cleanup():
            """Synchronous cleanup wrapper for atexit."""
            try:
                # Run cleanup in new event loop if needed
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.cleanup())
                loop.close()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error during cleanup: {e}")

        atexit.register(sync_cleanup)

        async def main():
            try:
                await self.initialize()
                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(
                        read_stream,
                        write_stream,
                        self.server.create_initialization_options(),
                    )
            finally:
                # Ensure cleanup happens even if server crashes
                await self.cleanup()

        # Handle Ctrl+C and termination signals (works on Unix and Windows)
        def signal_handler(sig, frame):
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Received signal {sig}, shutting down gracefully...")
            # Don't call sys.exit here - let the finally block in main() handle cleanup
            raise KeyboardInterrupt()

        signal.signal(signal.SIGINT, signal_handler)
        # SIGTERM only available on Unix
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Server stopped by user")


def main():
    """Main entry point."""
    server = SkillFlowServer()
    server.run()


if __name__ == "__main__":
    main()
