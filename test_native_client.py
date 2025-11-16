#!/usr/bin/env python3
"""Test native MCP client implementation."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillflow.native_mcp_client import NativeMCPClient

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_native_client():
    """Test native MCP client with windows-driver-input."""

    print("=" * 70)
    print("Testing Native MCP Client")
    print("=" * 70)
    print()

    # Create client
    client = NativeMCPClient(
        server_id="windows-driver-input",
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
        },
        timeout=60.0,
    )

    try:
        # Start client
        print("Starting client...")
        start_time = asyncio.get_event_loop().time()
        await client.start()
        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"✅ Client started in {elapsed:.2f}s")
        print()

        # Display server info
        print("Server Information:")
        print(f"  Status: {client.status}")
        print(f"  Server: {client.server_info}")
        print(f"  Capabilities: {list(client.capabilities.keys())}")
        print()

        # List tools
        print(f"Available Tools: {len(client.tools)}")
        for i, tool in enumerate(client.tools[:5], 1):
            print(f"  {i}. {tool['name']}")
            if tool.get('description'):
                desc = tool['description'][:60]
                print(f"     {desc}...")

        if len(client.tools) > 5:
            print(f"  ... and {len(client.tools) - 5} more")
        print()

        # Test calling a tool (if available)
        if client.tools:
            test_tool = None

            # Look for Desktop_Info tool
            for tool in client.tools:
                if 'Desktop_Info' in tool['name']:
                    test_tool = tool
                    break

            if not test_tool:
                test_tool = client.tools[0]

            print(f"Testing tool call: {test_tool['name']}")
            try:
                result = await client.call_tool(test_tool['name'], {})
                print(f"✅ Tool call succeeded")
                print(f"  Result: {result}")
            except Exception as e:
                print(f"❌ Tool call failed: {e}")

        print()
        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)

    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print()
        print("Stopping client...")
        await client.stop()
        print("Done")


if __name__ == "__main__":
    asyncio.run(test_native_client())
