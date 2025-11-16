#!/usr/bin/env python3
"""Quick test to verify windows-driver-input server can start."""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.skillflow.mcp_clients import MCPClientManager
from src.skillflow.storage import StorageLayer
from src.skillflow.schemas import ServerConfig, TransportType


async def test_connection():
    """Test connection to windows-driver-input server."""

    print("=" * 70)
    print("Windows Driver Input Connection Test")
    print("=" * 70)
    print()

    # Initialize storage and client manager
    storage = StorageLayer("data")
    await storage.initialize()

    client_manager = MCPClientManager(storage)
    await client_manager.initialize()

    # Get server config
    registry = await storage.load_registry()
    server_config = registry.servers.get("windows-driver-input")

    if not server_config:
        print("❌ windows-driver-input not found in registry")
        return

    print(f"✓ Found server config:")
    print(f"  ID: {server_config.server_id}")
    print(f"  Name: {server_config.name}")
    print(f"  Command: {server_config.config.get('command')}")
    print(f"  Args: {server_config.config.get('args')}")
    print()

    print("Attempting to connect (30 second timeout)...")
    print("This may take a while if the server is slow to start...")
    print()

    start_time = time.time()

    try:
        # Try to list tools with 30 second timeout
        tools = await asyncio.wait_for(
            client_manager.list_tools("windows-driver-input"),
            timeout=30.0
        )

        elapsed = time.time() - start_time

        print()
        print(f"✅ SUCCESS! Connected in {elapsed:.1f} seconds")
        print(f"   Found {len(tools)} tools:")
        print()

        for i, tool in enumerate(tools[:10], 1):
            print(f"   {i}. {tool['name']}")
            desc = tool.get('description', '')
            if desc:
                print(f"      {desc[:60]}...")

        if len(tools) > 10:
            print(f"   ... and {len(tools) - 10} more")

        print()
        print("=" * 70)
        print("✅ Server is working! Proxy tools should now be available.")
        print("=" * 70)

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print()
        print(f"❌ TIMEOUT after {elapsed:.1f} seconds")
        print()
        print("Possible issues:")
        print("1. Server is taking too long to start (>30 seconds)")
        print("2. Path or command is incorrect")
        print("3. Environment variables are missing or wrong")
        print()
        print("Try running the server manually:")
        print(f"   {server_config.config.get('command')} {' '.join(server_config.config.get('args', []))}")

    except Exception as e:
        elapsed = time.time() - start_time
        print()
        print(f"❌ ERROR after {elapsed:.1f} seconds:")
        print(f"   {type(e).__name__}: {e}")
        print()

        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

    finally:
        # Clean up
        await client_manager.close_all()


if __name__ == "__main__":
    asyncio.run(test_connection())
