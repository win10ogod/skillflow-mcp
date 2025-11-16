"""WebSocket transport client for MCP protocol."""

import asyncio
import json
import logging
from typing import Any, Optional

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class WebSocketClientError(Exception):
    """Error in WebSocket client operations."""
    pass


class WebSocketClient:
    """MCP client using WebSocket transport."""

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        ping_interval: int = 20,
        ping_timeout: int = 10,
    ):
        """Initialize WebSocket client.

        Args:
            url: WebSocket URL (e.g., "ws://localhost:3000/mcp")
            api_key: Optional API key for authentication
            ping_interval: Interval between ping messages in seconds
            ping_timeout: Timeout for ping/pong in seconds
        """
        if not WEBSOCKETS_AVAILABLE:
            raise WebSocketClientError(
                "WebSocket transport requires websockets package. "
                "Install with: pip install websockets"
            )

        self.url = url
        self.api_key = api_key
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.receive_task: Optional[asyncio.Task] = None
        self.event_handlers: dict[str, Any] = {}
        self._message_id_counter = 0
        self._pending_requests: dict[int, asyncio.Future] = {}

    async def connect(self) -> dict[str, Any]:
        """Connect to the WebSocket server and initialize.

        Returns:
            Server information from initialization

        Raises:
            WebSocketClientError: If connection or initialization fails
        """
        if self.websocket is not None:
            raise WebSocketClientError("Client already connected")

        # Prepare headers
        extra_headers = {}
        if self.api_key:
            extra_headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.url,
                extra_headers=extra_headers,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )

            # Start message receiver task
            self.receive_task = asyncio.create_task(self._receive_messages())

            # Send initialize message
            init_result = await self._send_request("initialize", {
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

            logger.info(f"Connected to WebSocket server at {self.url}")
            return init_result

        except Exception as e:
            await self.close()
            raise WebSocketClientError(f"Failed to connect: {str(e)}") from e

    async def _send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Send a request and wait for response.

        Args:
            method: Method name
            params: Request parameters

        Returns:
            Response result

        Raises:
            WebSocketClientError: If request fails
        """
        if self.websocket is None:
            raise WebSocketClientError("Client not connected")

        # Generate message ID
        self._message_id_counter += 1
        message_id = self._message_id_counter

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[message_id] = future

        # Send request
        message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": method,
            "params": params,
        }

        try:
            await self.websocket.send(json.dumps(message))
            # Wait for response
            return await future

        except Exception as e:
            self._pending_requests.pop(message_id, None)
            raise WebSocketClientError(f"Request failed: {str(e)}") from e

    async def _send_notification(self, method: str, params: dict[str, Any]):
        """Send a notification (no response expected).

        Args:
            method: Method name
            params: Notification parameters

        Raises:
            WebSocketClientError: If send fails
        """
        if self.websocket is None:
            raise WebSocketClientError("Client not connected")

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            raise WebSocketClientError(f"Notification failed: {str(e)}") from e

    async def _receive_messages(self):
        """Receive and handle incoming messages."""
        if self.websocket is None:
            return

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")

        except asyncio.CancelledError:
            logger.debug("Message receiver cancelled")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Message receiver error: {str(e)}")

    async def _handle_message(self, message: dict[str, Any]):
        """Handle incoming message.

        Args:
            message: Parsed JSON-RPC message
        """
        # Handle response to our request
        if "id" in message and message["id"] in self._pending_requests:
            message_id = message["id"]
            future = self._pending_requests.pop(message_id)

            if "error" in message:
                error = message["error"]
                future.set_exception(
                    WebSocketClientError(error.get("message", "Unknown error"))
                )
            else:
                future.set_result(message.get("result"))

        # Handle server-initiated request
        elif "method" in message and "id" in message:
            method = message["method"]
            params = message.get("params", {})
            message_id = message["id"]

            # Call registered handler
            if method in self.event_handlers:
                try:
                    result = await self.event_handlers[method](params)
                    # Send response
                    response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": result,
                    }
                    await self.websocket.send(json.dumps(response))

                except Exception as e:
                    # Send error response
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {
                            "code": -32603,
                            "message": str(e),
                        },
                    }
                    await self.websocket.send(json.dumps(error_response))

        # Handle server notification
        elif "method" in message:
            method = message["method"]
            params = message.get("params", {})

            # Call registered handler (no response needed)
            if method in self.event_handlers:
                try:
                    await self.event_handlers[method](params)
                except Exception as e:
                    logger.error(f"Error in notification handler for {method}: {str(e)}")

    def on(self, method: str, handler):
        """Register handler for server-initiated messages.

        Args:
            method: Method name to handle
            handler: Async function to handle the message
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
            WebSocketClientError: If tool call fails
        """
        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        return result.get("content", [])

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools.

        Returns:
            List of tool descriptions

        Raises:
            WebSocketClientError: If request fails
        """
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources.

        Returns:
            List of resource descriptions

        Raises:
            WebSocketClientError: If request fails
        """
        result = await self._send_request("resources/list", {})
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            WebSocketClientError: If request fails
        """
        return await self._send_request("resources/read", {
            "uri": uri,
        })

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List available prompts.

        Returns:
            List of prompt descriptions

        Raises:
            WebSocketClientError: If request fails
        """
        result = await self._send_request("prompts/list", {})
        return result.get("prompts", [])

    async def get_prompt(self, name: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Get a prompt.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt content

        Raises:
            WebSocketClientError: If request fails
        """
        return await self._send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {},
        })

    async def close(self):
        """Close the WebSocket connection."""
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        logger.info("WebSocket client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
