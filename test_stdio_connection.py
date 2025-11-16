#!/usr/bin/env python3
"""Detailed stdio connection test to diagnose where the connection hangs."""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_stdio_connection():
    """Test stdio connection step by step."""

    print("=" * 70)
    print("Detailed stdio Connection Test")
    print("=" * 70)
    print()

    # Server configuration
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "--directory",
            "I:\\凌星開發計畫\\凌星OS\\input_driver_server",
            "run",
            "main.py"
        ],
        env={
            "WINDOWS_INPUT_LOG_LEVEL": "INFO",
            "WINDOWS_MCP_INPUT_BACKEND": "ibsim-dll",
            "WINDOWS_MCP_INPUT_DRIVER": "SendInput",
            "WINDOWS_MCP_RATE_CPS": "8.0",
            "WINDOWS_MCP_RATE_KPS": "12.0",
            "WINDOWS_MCP_RATE_MAX_DELTA": "60",
            "WINDOWS_MCP_RATE_MOVE_HZ": "60",
            "WINDOWS_MCP_RATE_SMOOTH": "0.0"
        }
    )

    print("Server configuration:")
    print(f"  Command: {server_params.command}")
    print(f"  Args: {server_params.args}")
    print(f"  Env vars: {len(server_params.env)} variables")
    print()

    context = None
    session = None

    try:
        # Step 1: Create context
        print("Step 1: Creating stdio context...")
        start_time = time.time()
        context = stdio_client(server_params)
        elapsed = time.time() - start_time
        print(f"  ✓ Context created in {elapsed:.2f}s")
        print()

        # Step 2: Enter context (starts subprocess)
        print("Step 2: Starting subprocess...")
        start_time = time.time()
        try:
            read, write = await asyncio.wait_for(
                context.__aenter__(),
                timeout=10.0
            )
            elapsed = time.time() - start_time
            print(f"  ✓ Subprocess started in {elapsed:.2f}s")
            print(f"  Read stream: {type(read).__name__}")
            print(f"  Write stream: {type(write).__name__}")
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"  ❌ TIMEOUT after {elapsed:.2f}s during subprocess start")
            print()
            print("This suggests the subprocess itself is failing to start.")
            return
        print()

        # Step 3: Create session
        print("Step 3: Creating ClientSession...")
        start_time = time.time()
        session = ClientSession(read, write)
        elapsed = time.time() - start_time
        print(f"  ✓ Session created in {elapsed:.2f}s")
        print()

        # Step 4: Initialize session (MCP handshake)
        print("Step 4: Initializing session (MCP handshake)...")
        print("  This sends 'initialize' request to the server...")
        start_time = time.time()
        try:
            await asyncio.wait_for(
                session.initialize(),
                timeout=30.0
            )
            elapsed = time.time() - start_time
            print(f"  ✓ Session initialized in {elapsed:.2f}s")
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"  ❌ TIMEOUT after {elapsed:.2f}s during session.initialize()")
            print()
            print("This suggests:")
            print("  - Server process started but didn't respond to 'initialize'")
            print("  - MCP protocol handshake is failing")
            print("  - Server might be stuck or not implementing MCP correctly")
            return
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ ERROR after {elapsed:.2f}s: {type(e).__name__}: {e}")
            import traceback
            print()
            print("Traceback:")
            print(traceback.format_exc())
            return
        print()

        # Step 5: List tools
        print("Step 5: Listing tools...")
        start_time = time.time()
        try:
            tools_result = await asyncio.wait_for(
                session.list_tools(),
                timeout=10.0
            )
            elapsed = time.time() - start_time
            print(f"  ✓ Got tools list in {elapsed:.2f}s")
            print(f"  Found {len(tools_result.tools)} tools")
            print()

            for i, tool in enumerate(tools_result.tools[:5], 1):
                print(f"  {i}. {tool.name}")
                if tool.description:
                    print(f"     {tool.description[:60]}...")

            if len(tools_result.tools) > 5:
                print(f"  ... and {len(tools_result.tools) - 5} more")

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"  ❌ TIMEOUT after {elapsed:.2f}s during list_tools()")
            return
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ ERROR after {elapsed:.2f}s: {type(e).__name__}: {e}")
            return

        print()
        print("=" * 70)
        print("✅ ALL STEPS SUCCEEDED!")
        print("=" * 70)

    except Exception as e:
        print()
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        print()
        print("Traceback:")
        print(traceback.format_exc())

    finally:
        # Cleanup
        print()
        print("Cleaning up...")
        if context:
            try:
                await context.__aexit__(None, None, None)
                print("  ✓ Context cleaned up")
            except Exception as e:
                print(f"  ⚠️  Error during cleanup: {e}")


if __name__ == "__main__":
    asyncio.run(test_stdio_connection())
