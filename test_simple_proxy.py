#!/usr/bin/env python3
"""Simple test to verify proxy tools are created."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.skillflow.server import SkillFlowServer


async def main():
    """Test if proxy tools are created."""

    print("=" * 70)
    print("Simple Proxy Tools Test")
    print("=" * 70)
    print()

    # Create and initialize server
    print("1. Creating SkillFlowServer...")
    server = SkillFlowServer(data_dir="data")

    print("2. Initializing server...")
    await server.initialize()
    print("   ✓ Server initialized")
    print()

    # List registered servers
    print("3. Checking registered servers...")
    servers = await server.mcp_clients.list_servers()
    print(f"   Found {len(servers)} registered servers:")
    for srv in servers:
        print(f"   - {srv.server_id}: {srv.name} (enabled: {srv.enabled})")
    print()

    # Try to get upstream tools
    print("4. Attempting to fetch upstream tools...")
    print("   (This will show [Skillflow] logs if working)")
    print()

    upstream_tools = await server._get_upstream_tools()

    print()
    print(f"5. Results:")
    print(f"   Total proxy tools created: {len(upstream_tools)}")
    print()

    if upstream_tools:
        print("   Sample proxy tools:")
        for tool in upstream_tools[:10]:
            print(f"   ✓ {tool.name}")
            print(f"     {tool.description}")

        if len(upstream_tools) > 10:
            print(f"   ... and {len(upstream_tools) - 10} more")
    else:
        print("   ⚠️  No proxy tools were created!")
        print()
        print("   Possible reasons:")
        print("   - Upstream servers are not reachable")
        print("   - Connection timeout")
        print("   - Server configuration errors")

    print()
    print("=" * 70)
    print("Test completed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
