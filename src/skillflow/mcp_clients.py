"""MCP client management for connecting to upstream servers.

Now using native MCP client implementation for better control and reliability.
"""

import logging
from typing import Any, Optional

from .native_mcp_client import NativeMCPClient, MCPClientError
from .schemas import ServerConfig, ServerRegistry, TransportType
from .storage import StorageLayer

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Manages connections to upstream MCP servers using native implementation."""

    def __init__(self, storage: StorageLayer):
        """Initialize MCP client manager.

        Args:
            storage: Storage layer for server registry
        """
        self.storage = storage
        self._clients: dict[str, NativeMCPClient] = {}
        self._registry: Optional[ServerRegistry] = None

    async def initialize(self):
        """Initialize client manager and load registry."""
        self._registry = await self.storage.load_registry()
        logger.info(f"Loaded registry with {len(self._registry.servers)} servers")

        # Note: We don't auto-connect to servers during initialization to avoid
        # timeout issues. Servers will be connected lazily when first used.

    async def connect_server(self, server_id: str) -> NativeMCPClient:
        """Connect to an upstream MCP server.

        Args:
            server_id: ID of the server to connect

        Returns:
            Native MCP client

        Raises:
            ValueError: If server not found in registry
            MCPClientError: If connection fails
        """
        if not self._registry:
            self._registry = await self.storage.load_registry()

        config = self._registry.servers.get(server_id)
        if not config:
            raise ValueError(f"Server {server_id} not found in registry")

        # Check if already connected
        if server_id in self._clients:
            client = self._clients[server_id]
            if client.status == "connected":
                return client
            else:
                # Client exists but not connected, clean up and reconnect
                logger.warning(f"Client {server_id} exists but not connected (status: {client.status}), reconnecting...")
                await self.disconnect_server(server_id)

        # Create client based on transport type
        if config.transport == TransportType.STDIO:
            client = await self._connect_stdio(config)
        elif config.transport == TransportType.HTTP_SSE:
            client = await self._connect_http_sse(config)
        else:
            raise ValueError(f"Unsupported transport: {config.transport}")

        self._clients[server_id] = client
        return client

    async def _connect_stdio(self, config: ServerConfig) -> NativeMCPClient:
        """Connect to a stdio-based MCP server.

        Args:
            config: Server configuration

        Returns:
            Native MCP client
        """
        command = config.config.get("command")
        args = config.config.get("args", [])
        env = config.config.get("env")

        if not command:
            raise ValueError("stdio transport requires 'command' in config")

        # Create native client
        client = NativeMCPClient(
            server_id=config.server_id,
            command=command,
            args=args,
            env=env,
            timeout=60.0,  # 60 second default timeout
            client_name="skillflow",
            client_version="0.1.0",
        )

        # Start and initialize
        await client.start()

        return client

    async def _connect_http_sse(self, config: ServerConfig) -> NativeMCPClient:
        """Connect to an HTTP+SSE based MCP server.

        Args:
            config: Server configuration

        Returns:
            Native MCP client
        """
        # This would use httpx-based client
        # For now, raise not implemented
        raise NotImplementedError("HTTP+SSE transport not yet implemented")

    async def disconnect_server(self, server_id: str):
        """Disconnect from an upstream server.

        Args:
            server_id: ID of the server to disconnect
        """
        client = self._clients.pop(server_id, None)

        if client:
            try:
                await client.stop()
                logger.info(f"Disconnected from {server_id}")
            except Exception as e:
                logger.error(f"Error disconnecting from {server_id}: {e}")

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

        client = self._clients.get(server_id)
        if not client or client.status != "connected":
            # Try to connect
            client = await self.connect_server(server_id)

        # Call tool
        result = await client.call_tool(tool_name, arguments)

        # Native client returns dict directly from MCP protocol
        # Format: {'content': [...], 'isError': bool}
        return result

    async def list_tools(self, server_id: str) -> list[dict]:
        """List available tools from a server.

        Args:
            server_id: ID of the server

        Returns:
            List of tool descriptors
        """
        client = self._clients.get(server_id)
        if not client or client.status != "connected":
            client = await self.connect_server(server_id)

        # Native client stores tools after initialization
        return client.tools

    async def list_prompts(self, server_id: str) -> list[dict]:
        """List available prompts from a server.

        Args:
            server_id: ID of the server

        Returns:
            List of prompt descriptors
        """
        client = self._clients.get(server_id)
        if not client or client.status != "connected":
            client = await self.connect_server(server_id)

        return client.prompts

    async def get_prompt(
        self,
        server_id: str,
        prompt_name: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """Get a prompt from a server.

        Args:
            server_id: ID of the server
            prompt_name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result
        """
        client = self._clients.get(server_id)
        if not client or client.status != "connected":
            client = await self.connect_server(server_id)

        return await client.get_prompt(prompt_name, arguments)

    async def list_resources(self, server_id: str) -> list[dict]:
        """List available resources from a server.

        Args:
            server_id: ID of the server

        Returns:
            List of resource descriptors
        """
        client = self._clients.get(server_id)
        if not client or client.status != "connected":
            client = await self.connect_server(server_id)

        return client.resources

    async def read_resource(self, server_id: str, uri: str) -> dict:
        """Read a resource from a server.

        Args:
            server_id: ID of the server
            uri: Resource URI

        Returns:
            Resource content
        """
        client = self._clients.get(server_id)
        if not client or client.status != "connected":
            client = await self.connect_server(server_id)

        return await client.read_resource(uri)

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
        logger.info(f"Registered server: {server_id}")

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
        logger.info(f"Unregistered server: {server_id}")

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
        logger.info(f"Closing {len(self._clients)} client connections")
        for server_id in list(self._clients.keys()):
            await self.disconnect_server(server_id)
