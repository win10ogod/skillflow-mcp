"""Configuration format converter for MCP server configs.

Converts between standard Claude Code/Claude Desktop MCP configuration format
and SkillFlow's internal server registry format.
"""

from typing import Any, Optional

from .schemas import ServerConfig, ServerRegistry, TransportType


def detect_config_format(data: dict[str, Any]) -> str:
    """Detect configuration file format.

    Args:
        data: Configuration data

    Returns:
        Format type: 'claude_code', 'skillflow', or 'unknown'
    """
    if "mcpServers" in data:
        return "claude_code"
    elif "servers" in data:
        # Check if it's SkillFlow format (has server_id, name, transport)
        servers = data.get("servers", {})
        if servers:
            first_server = next(iter(servers.values()), {})
            if "server_id" in first_server and "transport" in first_server:
                return "skillflow"
            # Otherwise it might be Claude Code format nested under "servers"
            if "command" in first_server and "args" in first_server:
                return "claude_code_nested"
    return "unknown"


def convert_claude_code_to_skillflow(
    claude_config: dict[str, Any],
    default_transport: str = "stdio"
) -> ServerRegistry:
    """Convert Claude Code MCP configuration to SkillFlow format.

    Supports multiple input formats:
    1. Standard Claude Code format with "mcpServers" key
    2. Nested format with "servers" key containing Claude Code-style configs
    3. Mixed format with some servers in each style

    Args:
        claude_config: Claude Code/Claude Desktop MCP configuration
        default_transport: Default transport type for servers (default: stdio)

    Returns:
        ServerRegistry in SkillFlow internal format

    Example input (Claude Code standard):
        {
          "mcpServers": {
            "filesystem": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
              "env": {"DEBUG": "true"}
            }
          }
        }

    Example input (nested under servers):
        {
          "servers": {
            "filesystem": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
              "env": {"DEBUG": "true"}
            }
          }
        }

    Example output (SkillFlow format):
        {
          "servers": {
            "filesystem": {
              "server_id": "filesystem",
              "name": "filesystem",
              "transport": "stdio",
              "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"DEBUG": "true"}
              },
              "enabled": true,
              "metadata": {}
            }
          }
        }
    """
    registry = ServerRegistry()

    # Detect which key to use
    servers_key = None
    if "mcpServers" in claude_config:
        servers_key = "mcpServers"
    elif "servers" in claude_config:
        servers_key = "servers"
    else:
        return registry  # Empty registry

    servers = claude_config.get(servers_key, {})

    for server_id, server_config in servers.items():
        # Check if this is already in SkillFlow format
        if "server_id" in server_config and "transport" in server_config:
            # Already in SkillFlow format, use directly
            registry.servers[server_id] = ServerConfig(**server_config)
            continue

        # Convert from Claude Code format
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env")

        if not command:
            # Skip servers without command (log to stderr, not stdout)
            import logging
            logging.getLogger(__name__).warning(f"Server '{server_id}' has no command, skipping")
            continue

        # Detect transport type from command/args
        transport = _detect_transport_type(command, args, server_config)
        if not transport:
            transport = default_transport

        # Extract optional fields
        name = server_config.get("name", server_id)
        enabled = server_config.get("enabled", True)
        metadata = server_config.get("metadata", {})

        # Build internal config
        internal_config = {
            "command": command,
            "args": args,
        }

        # Only add env if it's not None/null
        if env is not None:
            internal_config["env"] = env

        # Create ServerConfig
        server = ServerConfig(
            server_id=server_id,
            name=name,
            transport=TransportType(transport),
            config=internal_config,
            enabled=enabled,
            metadata=metadata,
        )

        registry.servers[server_id] = server

    return registry


def convert_skillflow_to_claude_code(
    skillflow_registry: ServerRegistry,
    include_metadata: bool = False
) -> dict[str, Any]:
    """Convert SkillFlow ServerRegistry to Claude Code MCP configuration.

    Args:
        skillflow_registry: SkillFlow server registry
        include_metadata: Include SkillFlow-specific metadata (default: False)

    Returns:
        Claude Code MCP configuration

    Example input (SkillFlow format):
        {
          "servers": {
            "filesystem": {
              "server_id": "filesystem",
              "name": "File System",
              "transport": "stdio",
              "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"DEBUG": "true"}
              },
              "enabled": true,
              "metadata": {"version": "1.0"}
            }
          }
        }

    Example output (Claude Code format):
        {
          "mcpServers": {
            "filesystem": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
              "env": {"DEBUG": "true"}
            }
          }
        }
    """
    claude_config = {"mcpServers": {}}

    for server_id, server in skillflow_registry.servers.items():
        # Skip disabled servers
        if not server.enabled:
            continue

        # Extract command, args, env from config
        command = server.config.get("command")
        args = server.config.get("args", [])
        env = server.config.get("env")

        if not command:
            continue

        server_config = {
            "command": command,
            "args": args,
        }

        # Only include env if it's not None
        if env is not None:
            server_config["env"] = env

        # Optionally include SkillFlow-specific fields
        if include_metadata:
            if server.name != server_id:
                server_config["name"] = server.name
            if server.metadata:
                server_config["metadata"] = server.metadata

        claude_config["mcpServers"][server_id] = server_config

    return claude_config


def _detect_transport_type(
    command: str,
    args: list[str],
    config: dict[str, Any]
) -> Optional[str]:
    """Detect transport type from command/args/config.

    Args:
        command: Command to run
        args: Command arguments
        config: Full configuration

    Returns:
        Transport type or None if cannot detect
    """
    # Check if explicitly specified
    if "transport" in config:
        return config["transport"]

    # Detect from command/args
    # Only check command and module names, not file paths to avoid false positives
    all_parts = [command] + args

    # Check for HTTP/SSE indicators
    # Look for http in command or module names (e.g., "http-server", "mcp-http")
    for part in all_parts:
        part_lower = part.lower()
        # Skip file paths (contain \ or / or :)
        if '\\' in part or '/' in part or ':' in part:
            continue

        if "http" in part_lower:
            if "sse" in part_lower:
                return "http_sse"
            return "streamable_http"

    # Check for WebSocket indicators
    # Only match explicit websocket keywords, not substrings in paths
    for part in all_parts:
        part_lower = part.lower()
        # Skip file paths
        if '\\' in part or '/' in part or ':' in part:
            continue

        # Only match if "websocket" or "ws" as a whole word/module name
        if part_lower == "websocket" or part_lower == "ws" or \
           part_lower.startswith("websocket-") or part_lower.startswith("ws-") or \
           "-websocket" in part_lower or "-ws-" in part_lower or \
           "websocket_" in part_lower or "ws_" in part_lower:
            return "websocket"

    # Default to stdio
    return "stdio"


def merge_server_registries(
    base: ServerRegistry,
    override: ServerRegistry,
    merge_strategy: str = "override"
) -> ServerRegistry:
    """Merge two server registries.

    Args:
        base: Base registry
        override: Override registry
        merge_strategy: How to merge conflicts:
            - "override": Override servers replace base servers (default)
            - "merge": Merge server configs, override takes precedence
            - "skip": Skip servers that exist in base

    Returns:
        Merged registry
    """
    merged = ServerRegistry()

    # Add base servers
    for server_id, server in base.servers.items():
        merged.servers[server_id] = server.model_copy(deep=True)

    # Add/merge override servers
    for server_id, server in override.servers.items():
        if server_id not in merged.servers:
            # New server, add it
            merged.servers[server_id] = server.model_copy(deep=True)
        else:
            # Conflict, apply strategy
            if merge_strategy == "override":
                merged.servers[server_id] = server.model_copy(deep=True)
            elif merge_strategy == "merge":
                # Merge configs
                base_server = merged.servers[server_id]
                base_server.name = server.name
                base_server.transport = server.transport
                base_server.enabled = server.enabled
                # Merge config dicts
                base_server.config.update(server.config)
                # Merge metadata
                base_server.metadata.update(server.metadata)
            elif merge_strategy == "skip":
                # Keep base server
                pass

    return merged
