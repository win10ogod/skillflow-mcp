"""HTTP+SSE transport client for MCP protocol."""

import asyncio
import json
import logging
from typing import Any, Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class HTTPSSEClientError(Exception):
    """Error in HTTP+SSE client operations."""
    pass


class HTTPSSEClient:
    """MCP client using HTTP+SSE transport."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize HTTP+SSE client.

        Args:
            base_url: Base URL of the MCP server (e.g., "http://localhost:3000")
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        if not AIOHTTP_AVAILABLE:
            raise HTTPSSEClientError(
                "HTTP+SSE transport requires aiohttp package. "
                "Install with: pip install aiohttp"
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.event_handlers: dict[str, Any] = {}
        self._message_id_counter = 0
        self._pending_requests: dict[int, asyncio.Future] = {}

    async def connect(self) -> dict[str, Any]:
        """Connect to the MCP server and initialize.

        Returns:
            Server information from initialization

        Raises:
            HTTPSSEClientError: If connection or initialization fails
        """
        if self.session is not None:
            raise HTTPSSEClientError("Client already connected")

        # Create aiohttp session
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )

        try:
            # Send initialize request
            init_result = await self._post_request("/mcp/v1/initialize", {
                "protocolVersion": "1.0",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "clientInfo": {
                    "name": "skillflow",
                    "version": "0.1.0",
                },
            })

            # Start SSE connection for server-initiated messages
            self.sse_task = asyncio.create_task(self._sse_connection())

            logger.info(f"Connected to HTTP+SSE server at {self.base_url}")
            return init_result

        except Exception as e:
            await self.close()
            raise HTTPSSEClientError(f"Failed to connect: {str(e)}") from e

    async def _post_request(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Send POST request to server.

        Args:
            endpoint: API endpoint path
            data: Request payload

        Returns:
            Response data

        Raises:
            HTTPSSEClientError: If request fails
        """
        if self.session is None:
            raise HTTPSSEClientError("Client not connected")

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            raise HTTPSSEClientError(f"HTTP request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise HTTPSSEClientError(f"Invalid JSON response: {str(e)}") from e

    async def _sse_connection(self):
        """Maintain SSE connection for server-initiated messages."""
        if self.session is None:
            return

        url = f"{self.base_url}/mcp/v1/sse"

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()

                async for line in response.content:
                    line = line.decode("utf-8").strip()

                    # Parse SSE events
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)
                            await self._handle_sse_event(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid SSE data: {data_str}")

        except asyncio.CancelledError:
            logger.debug("SSE connection cancelled")
        except Exception as e:
            logger.error(f"SSE connection error: {str(e)}")

    async def _handle_sse_event(self, event: dict[str, Any]):
        """Handle incoming SSE event.

        Args:
            event: Event data from server
        """
        # Handle server notifications and requests
        if "method" in event:
            # Server-initiated request
            method = event["method"]
            params = event.get("params", {})
            message_id = event.get("id")

            # Call registered handler
            if method in self.event_handlers:
                try:
                    result = await self.event_handlers[method](params)
                    # Send response back to server if ID present
                    if message_id is not None:
                        await self._post_request("/mcp/v1/response", {
                            "id": message_id,
                            "result": result,
                        })
                except Exception as e:
                    if message_id is not None:
                        await self._post_request("/mcp/v1/response", {
                            "id": message_id,
                            "error": {"code": -32603, "message": str(e)},
                        })

        # Handle responses to our requests
        elif "id" in event:
            message_id = event["id"]
            if message_id in self._pending_requests:
                future = self._pending_requests.pop(message_id)
                if "error" in event:
                    future.set_exception(HTTPSSEClientError(event["error"].get("message", "Unknown error")))
                else:
                    future.set_result(event.get("result"))

    def on(self, method: str, handler):
        """Register handler for server-initiated requests.

        Args:
            method: Method name to handle
            handler: Async function to handle the request
        """
        self.event_handlers[method] = handler

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Call a tool on the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result content

        Raises:
            HTTPSSEClientError: If tool call fails
        """
        result = await self._post_request("/mcp/v1/tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        return result.get("content", [])

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools.

        Returns:
            List of tool descriptions

        Raises:
            HTTPSSEClientError: If request fails
        """
        result = await self._post_request("/mcp/v1/tools/list", {})
        return result.get("tools", [])

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources.

        Returns:
            List of resource descriptions

        Raises:
            HTTPSSEClientError: If request fails
        """
        result = await self._post_request("/mcp/v1/resources/list", {})
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            HTTPSSEClientError: If request fails
        """
        return await self._post_request("/mcp/v1/resources/read", {
            "uri": uri,
        })

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List available prompts.

        Returns:
            List of prompt descriptions

        Raises:
            HTTPSSEClientError: If request fails
        """
        result = await self._post_request("/mcp/v1/prompts/list", {})
        return result.get("prompts", [])

    async def get_prompt(self, name: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Get a prompt.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt content

        Raises:
            HTTPSSEClientError: If request fails
        """
        return await self._post_request("/mcp/v1/prompts/get", {
            "name": name,
            "arguments": arguments or {},
        })

    async def close(self):
        """Close the client connection."""
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
            self.sse_task = None

        if self.session:
            await self.session.close()
            self.session = None

        logger.info("HTTP+SSE client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
