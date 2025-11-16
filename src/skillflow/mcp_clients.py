"""MCP client management for connecting to upstream servers."""

import asyncio
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .schemas import ServerConfig, ServerRegistry, TransportType
from .storage import StorageLayer


class MCPClientManager:
    """Manages connections to upstream MCP servers."""

    def __init__(self, storage: StorageLayer):
        """Initialize MCP client manager.

        Args:
            storage: Storage layer for server registry
        """
        self.storage = storage
        self._clients: dict[str, ClientSession] = {}
        self._registry: Optional[ServerRegistry] = None

    async def initialize(self):
        """Initialize client manager and load registry."""
        self._registry = await self.storage.load_registry()

        # Auto-connect to enabled servers
        for server_id, config in self._registry.servers.items():
            if config.enabled:
                try:
                    await self.connect_server(server_id)
                except Exception as e:
                    print(f"Failed to connect to {server_id}: {e}")

    async def connect_server(self, server_id: str) -> ClientSession:
        """Connect to an upstream MCP server.

        Args:
            server_id: ID of the server to connect

        Returns:
            Client session

        Raises:
            ValueError: If server not found in registry
        """
        if not self._registry:
            self._registry = await self.storage.load_registry()

        config = self._registry.servers.get(server_id)
        if not config:
            raise ValueError(f"Server {server_id} not found in registry")

        # Check if already connected
        if server_id in self._clients:
            return self._clients[server_id]

        # Create client based on transport type
        if config.transport == TransportType.STDIO:
            session = await self._connect_stdio(config)
        elif config.transport == TransportType.HTTP_SSE:
            session = await self._connect_http_sse(config)
        else:
            raise ValueError(f"Unsupported transport: {config.transport}")

        self._clients[server_id] = session
        return session

    async def _connect_stdio(self, config: ServerConfig) -> ClientSession:
        """Connect to a stdio-based MCP server.

        Args:
            config: Server configuration

        Returns:
            Client session
        """
        command = config.config.get("command")
        args = config.config.get("args", [])
        env = config.config.get("env")

        if not command:
            raise ValueError("stdio transport requires 'command' in config")

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        # Create stdio client (stdio_client is an async context manager)
        streams = stdio_client(server_params)
        read, write = await streams.__aenter__()

        session = ClientSession(read, write)
        await session.initialize()

        return session

    async def _connect_http_sse(self, config: ServerConfig) -> ClientSession:
        """Connect to an HTTP+SSE based MCP server.

        Args:
            config: Server configuration

        Returns:
            Client session
        """
        # This would use httpx-based client
        # For now, raise not implemented
        raise NotImplementedError("HTTP+SSE transport not yet implemented")

    async def disconnect_server(self, server_id: str):
        """Disconnect from an upstream server.

        Args:
            server_id: ID of the server to disconnect
        """
        session = self._clients.pop(server_id, None)
        if session:
            # Clean up session
            pass

    async def call_tool(
        self,
        server_id: Optional[str],
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a tool on an upstream server.

        Args:
            server_id: ID of the server (None for local tools)
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            ValueError: If server not connected
        """
        if server_id is None:
            # Local tool execution would be handled separately
            raise ValueError("Local tool execution not implemented")

        session = self._clients.get(server_id)
        if not session:
            # Try to connect
            session = await self.connect_server(server_id)

        # Call tool
        result = await session.call_tool(tool_name, arguments)

        # Extract result content
        if hasattr(result, 'content') and result.content:
            # MCP returns CallToolResult with content array
            content_items = []
            for item in result.content:
                if hasattr(item, 'text'):
                    content_items.append(item.text)
                elif hasattr(item, 'data'):
                    content_items.append(item.data)

            return {
                "content": content_items,
                "isError": getattr(result, 'isError', False),
            }

        return {"content": [str(result)]}

    async def list_tools(self, server_id: str) -> list[dict]:
        """List available tools from a server.

        Args:
            server_id: ID of the server

        Returns:
            List of tool descriptors
        """
        session = self._clients.get(server_id)
        if not session:
            session = await self.connect_server(server_id)

        tools_result = await session.list_tools()

        # Convert to dict format
        tools = []
        for tool in tools_result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            })

        return tools

    async def register_server(
        self,
        server_id: str,
        name: str,
        transport: TransportType,
        config: dict[str, Any],
    ) -> None:
        """Register a new upstream server.

        Args:
            server_id: Unique server identifier
            name: Human-readable name
            transport: Transport type
            config: Transport-specific configuration
        """
        if not self._registry:
            self._registry = await self.storage.load_registry()

        server_config = ServerConfig(
            server_id=server_id,
            name=name,
            transport=transport,
            config=config,
            enabled=True,
        )

        self._registry.servers[server_id] = server_config
        await self.storage.save_registry(self._registry)

    async def unregister_server(self, server_id: str) -> None:
        """Unregister a server.

        Args:
            server_id: Server to unregister
        """
        if not self._registry:
            self._registry = await self.storage.load_registry()

        # Disconnect if connected
        await self.disconnect_server(server_id)

        # Remove from registry
        self._registry.servers.pop(server_id, None)
        await self.storage.save_registry(self._registry)

    async def list_servers(self) -> list[ServerConfig]:
        """List all registered servers.

        Returns:
            List of server configurations
        """
        if not self._registry:
            self._registry = await self.storage.load_registry()

        return list(self._registry.servers.values())

    async def close_all(self):
        """Close all client connections."""
        for server_id in list(self._clients.keys()):
            await self.disconnect_server(server_id)
