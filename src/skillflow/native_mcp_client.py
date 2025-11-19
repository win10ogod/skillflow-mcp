"""Native MCP client implementation.

Direct implementation of MCP protocol over stdio without relying on the
official mcp SDK. This provides better control, debugging, and reliability.

Inspired by the Node.js MCP client implementation.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Connection-related errors."""
    pass


class MCPTimeoutError(MCPClientError):
    """Request timeout errors."""
    pass


class MCPProtocolError(MCPClientError):
    """Protocol-level errors."""
    pass


class NativeMCPClient:
    """Native MCP client with direct stdio control.

    This implementation provides:
    - Direct subprocess management
    - Streaming JSON-RPC message parsing
    - Bidirectional communication (client ↔ server)
    - Request/response matching with timeouts
    - Server request handling (roots/list, sampling/createMessage)
    - Detailed logging and error handling
    """

    def __init__(
        self,
        server_id: str,
        command: str,
        args: list[str],
        env: Optional[dict[str, str]] = None,
        timeout: float = 60.0,
        client_name: str = "skillflow",
        client_version: str = "0.1.0",
    ):
        """Initialize native MCP client.

        Args:
            server_id: Unique identifier for this server
            command: Command to execute
            args: Command arguments
            env: Environment variables
            timeout: Default timeout for requests (seconds)
            client_name: Client name for MCP handshake
            client_version: Client version for MCP handshake
        """
        self.server_id = server_id
        self.command = command
        self.args = args
        self.env = env
        self.timeout = timeout
        self.client_name = client_name
        self.client_version = client_version

        # Process and communication
        self.process: Optional[subprocess.Popen] = None
        self._message_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None

        # MCP state
        self.status = "init"
        self.capabilities: Optional[dict] = None
        self.server_info: Optional[dict] = None
        self.tools: list[dict] = []
        self.prompts: list[dict] = []
        self.resources: list[dict] = []
        self.resource_templates: list[dict] = []

        # Server request handlers
        self._roots: list[str] = []
        self._sampling_handler: Optional[Callable] = None

    async def start(self) -> None:
        """Start the MCP server process and initialize connection."""
        if self.process:
            logger.warning(f"[{self.server_id}] Process already started")
            return

        logger.info(f"[{self.server_id}] Starting subprocess: {self.command} {' '.join(self.args)}")

        try:
            # Build environment
            full_env = dict(os.environ) if hasattr(os, 'environ') else {}
            if self.env:
                full_env.update(self.env)

            # Start subprocess
            start_time = asyncio.get_event_loop().time()
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                bufsize=0,  # Unbuffered
            )
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"[{self.server_id}] Subprocess started in {elapsed:.2f}s (PID: {self.process.pid})")

            # Start reading stdout and stderr
            self._read_task = asyncio.create_task(self._read_loop())
            self._stderr_task = asyncio.create_task(self._stderr_loop())

            # Initialize MCP connection
            await self._initialize()

            self.status = "connected"
            logger.info(f"[{self.server_id}] Connected and initialized")

        except Exception as e:
            logger.error(f"[{self.server_id}] Failed to start: {e}")
            await self.stop()
            raise MCPConnectionError(f"Failed to start {self.server_id}: {e}") from e

    async def _read_loop(self) -> None:
        """Read and parse messages from stdout."""
        if not self.process or not self.process.stdout:
            return

        buffer = ""
        try:
            while True:
                # Read data (blocking in executor to not block event loop)
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.process.stdout.read,
                    4096,
                )

                if not chunk:
                    logger.warning(f"[{self.server_id}] stdout closed")
                    break

                # Decode and buffer
                buffer += chunk.decode('utf-8', errors='replace')

                # Parse complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        message = json.loads(line)
                        await self._handle_message(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"[{self.server_id}] Failed to parse JSON: {line[:100]}... Error: {e}")
                    except Exception as e:
                        logger.error(f"[{self.server_id}] Error handling message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"[{self.server_id}] Read loop error: {e}", exc_info=True)
        finally:
            logger.info(f"[{self.server_id}] Read loop ended")

    async def _stderr_loop(self) -> None:
        """Read and log stderr output."""
        if not self.process or not self.process.stderr:
            return

        try:
            while True:
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.process.stderr.read,
                    4096,
                )

                if not chunk:
                    break

                text = chunk.decode('utf-8', errors='replace').strip()
                if text:
                    logger.warning(f"[{self.server_id}] stderr: {text}")

        except Exception as e:
            logger.error(f"[{self.server_id}] stderr loop error: {e}")
        finally:
            logger.info(f"[{self.server_id}] stderr loop ended")

    async def _handle_message(self, message: dict) -> None:
        """Handle incoming message from server.

        Args:
            message: JSON-RPC message
        """
        # Response to our request
        if 'id' in message and message['id'] in self._pending_requests:
            future = self._pending_requests.pop(message['id'])

            if 'error' in message:
                error = message['error']
                error_msg = f"[{error.get('code', -1)}] {error.get('message', 'Unknown error')}"
                future.set_exception(MCPProtocolError(error_msg))
            else:
                future.set_result(message.get('result'))

            return

        # Request from server
        if 'method' in message and 'id' in message:
            request_id = message['id']

            # Validate request ID - must not be None/null
            # According to JSONRPC 2.0, id can be string/number/null, but MCP requires valid id
            if request_id is None:
                logger.error(
                    f"[{self.server_id}] Received request with id=null for method '{message['method']}'. "
                    f"This is invalid for MCP protocol. Ignoring request."
                )
                # Send error response with a generated ID to inform the server
                await self._send_error_response(
                    0,  # Use 0 as fallback ID
                    -32600,  # Invalid Request error code
                    "Request ID cannot be null in MCP protocol"
                )
                return

            await self._handle_server_request(
                message['method'],
                message.get('params', {}),
                request_id,
            )
            return

        # Notification from server
        if 'method' in message and 'id' not in message:
            await self._handle_notification(
                message['method'],
                message.get('params', {}),
            )
            return

        logger.warning(f"[{self.server_id}] Unknown message type: {message}")

    async def _handle_notification(self, method: str, params: dict) -> None:
        """Handle notification from server.

        Args:
            method: Notification method
            params: Notification parameters
        """
        if method == 'notifications/message':
            level = params.get('level', 'info')
            data = params.get('data', '')
            logger_name = params.get('logger', '')
            prefix = f"[{logger_name}] " if logger_name else ""
            logger.info(f"[{self.server_id}] {level.upper()} {prefix}{data}")
        else:
            logger.debug(f"[{self.server_id}] Notification: {method} {params}")

    async def _handle_server_request(self, method: str, params: dict, request_id: int) -> None:
        """Handle request from server.

        Args:
            method: Request method
            params: Request parameters
            request_id: Request ID
        """
        try:
            result = None

            if method == 'roots/list':
                # Return client roots
                result = {
                    'roots': [
                        {
                            'uri': root if root.startswith('file://') else f"file://{root}",
                            'name': root.split('/')[-1] or root,
                        }
                        for root in self._roots
                    ]
                }

            elif method == 'sampling/createMessage':
                # Handle sampling request
                if not self._sampling_handler:
                    raise MCPProtocolError("Sampling not supported - no handler configured")

                sampling_result = await self._sampling_handler(params)

                result = {
                    'role': 'assistant',
                    'content': {
                        'type': 'text',
                        'text': sampling_result,
                    }
                }

            else:
                raise MCPProtocolError(f"Unknown server request method: {method}")

            # Send success response
            await self._send_response(request_id, result)

        except Exception as e:
            logger.error(f"[{self.server_id}] Error handling server request {method}: {e}")
            await self._send_error_response(request_id, -32603, str(e))

    async def _send_request(self, method: str, params: Optional[dict] = None) -> Any:
        """Send request to server and wait for response.

        Args:
            method: Request method
            params: Request parameters

        Returns:
            Response result

        Raises:
            MCPTimeoutError: If request times out
            MCPProtocolError: If server returns error
        """
        if not self.process or not self.process.stdin:
            raise MCPConnectionError(f"Process not started for {self.server_id}")

        msg_id = self._message_id
        self._message_id += 1

        request = {
            'jsonrpc': '2.0',
            'id': msg_id,
            'method': method,
            'params': params or {},
        }

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[msg_id] = future

        # Send request
        request_text = json.dumps(request) + '\n'
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.process.stdin.write,
                request_text.encode('utf-8'),
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.process.stdin.flush,
            )
        except Exception as e:
            self._pending_requests.pop(msg_id, None)
            raise MCPConnectionError(f"Failed to send request: {e}") from e

        # Wait for response with timeout
        try:
            result = await asyncio.wait_for(future, timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(msg_id, None)
            raise MCPTimeoutError(f"Request timeout: {method}") from None

    async def _send_notification(self, method: str, params: Optional[dict] = None) -> None:
        """Send notification to server (no response expected).

        Args:
            method: Notification method
            params: Notification parameters
        """
        if not self.process or not self.process.stdin:
            return

        # Notification MUST NOT have an 'id' field according to JSONRPC 2.0
        notification = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or {},
        }

        # Explicitly ensure no 'id' field is present (defensive programming)
        if 'id' in notification:
            logger.error(
                f"[{self.server_id}] Notification for '{method}' incorrectly contains 'id' field. "
                f"Removing it to comply with JSONRPC 2.0."
            )
            del notification['id']

        notification_text = json.dumps(notification) + '\n'
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.process.stdin.write,
            notification_text.encode('utf-8'),
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.process.stdin.flush,
        )

    async def _send_response(self, request_id: int, result: Any) -> None:
        """Send response to server request.

        Args:
            request_id: Request ID
            result: Response result
        """
        if not self.process or not self.process.stdin:
            return

        # Validate request_id - must not be None
        if request_id is None:
            logger.error(
                f"[{self.server_id}] Attempted to send response with id=None. "
                f"This is invalid for MCP protocol. Response will not be sent."
            )
            return

        response = {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result,
        }

        response_text = json.dumps(response) + '\n'
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.process.stdin.write,
            response_text.encode('utf-8'),
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.process.stdin.flush,
        )

    async def _send_error_response(self, request_id: int, code: int, message: str) -> None:
        """Send error response to server request.

        Args:
            request_id: Request ID
            code: Error code
            message: Error message
        """
        if not self.process or not self.process.stdin:
            return

        # Validate request_id - must not be None
        if request_id is None:
            logger.error(
                f"[{self.server_id}] Attempted to send error response with id=None. "
                f"Error was: [{code}] {message}. Response will not be sent."
            )
            return

        response = {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': code,
                'message': message,
            },
        }

        response_text = json.dumps(response) + '\n'
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.process.stdin.write,
            response_text.encode('utf-8'),
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.process.stdin.flush,
        )

    async def _initialize(self) -> None:
        """Initialize MCP connection."""
        logger.info(f"[{self.server_id}] Sending initialize request")

        # Send initialize request
        result = await self._send_request('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'roots': {'listChanged': True},
                'sampling': {},
            },
            'clientInfo': {
                'name': self.client_name,
                'version': self.client_version,
            },
        })

        self.capabilities = result.get('capabilities', {})
        self.server_info = result.get('serverInfo', {})

        logger.info(f"[{self.server_id}] Server info: {self.server_info}")
        logger.info(f"[{self.server_id}] Capabilities: {list(self.capabilities.keys())}")

        # Send initialized notification
        await self._send_notification('notifications/initialized')

        # Fetch available resources
        if self.capabilities.get('tools'):
            try:
                tools_result = await self._send_request('tools/list')
                self.tools = tools_result.get('tools', [])
                logger.info(f"[{self.server_id}] Found {len(self.tools)} tools")
            except Exception as e:
                logger.warning(f"[{self.server_id}] Failed to fetch tools: {e}")

        if self.capabilities.get('prompts'):
            try:
                prompts_result = await self._send_request('prompts/list')
                self.prompts = prompts_result.get('prompts', [])
                logger.info(f"[{self.server_id}] Found {len(self.prompts)} prompts")
            except Exception as e:
                logger.warning(f"[{self.server_id}] Failed to fetch prompts: {e}")

        if self.capabilities.get('resources'):
            try:
                resources_result = await self._send_request('resources/list')
                self.resources = resources_result.get('resources', [])
                logger.info(f"[{self.server_id}] Found {len(self.resources)} resources")
            except Exception as e:
                logger.warning(f"[{self.server_id}] Failed to fetch resources: {e}")

            try:
                templates_result = await self._send_request('resources/templates/list')
                self.resource_templates = templates_result.get('resourceTemplates', [])
                logger.info(f"[{self.server_id}] Found {len(self.resource_templates)} resource templates")
            except Exception as e:
                logger.debug(f"[{self.server_id}] Resource templates not supported: {e}")

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the server.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        result = await self._send_request('tools/call', {
            'name': tool_name,
            'arguments': arguments,
        })
        return result

    async def get_prompt(self, prompt_name: str, arguments: Optional[dict] = None) -> dict:
        """Get a prompt from the server.

        Args:
            prompt_name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result
        """
        result = await self._send_request('prompts/get', {
            'name': prompt_name,
            'arguments': arguments or {},
        })
        return result

    async def read_resource(self, uri: str) -> dict:
        """Read a resource from the server.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        result = await self._send_request('resources/read', {
            'uri': uri,
        })
        return result

    def set_roots(self, roots: list[str]) -> None:
        """Set client roots.

        Args:
            roots: List of root paths
        """
        self._roots = roots

    def set_sampling_handler(self, handler: Callable) -> None:
        """Set sampling handler.

        Args:
            handler: Async function that handles sampling requests
        """
        self._sampling_handler = handler

    async def stop(self) -> None:
        """Stop the MCP client and cleanup resources."""
        logger.info(f"[{self.server_id}] Stopping...")

        # Cancel tasks
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        # Reject pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(MCPConnectionError("Client stopped"))
        self._pending_requests.clear()

        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, self.process.wait),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"[{self.server_id}] Process did not terminate, killing...")
                    self.process.kill()
                    await asyncio.get_event_loop().run_in_executor(None, self.process.wait)
            except Exception as e:
                logger.error(f"[{self.server_id}] Error stopping process: {e}")

            self.process = None

        self.status = "stopped"
        logger.info(f"[{self.server_id}] Stopped")


# Import os for environment variables
import os
