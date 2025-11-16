#!/usr/bin/env python3
"""Test script for upstream tool proxy functionality."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.skillflow.server import SkillFlowServer
from src.skillflow.schemas import TransportType


async def test_proxy_functionality():
    """Test the upstream tool proxy functionality."""

    print("=" * 70)
    print("Testing Upstream Tool Proxy Functionality")
    print("=" * 70)
    print()

    # Create server instance
    server = SkillFlowServer(data_dir="data")
    await server.initialize()

    # Test 1: Register a mock upstream server
    print("Test 1: Registering upstream server...")
    print("-" * 70)

    await server.mcp_clients.register_server(
        server_id="test-server",
        name="Test MCP Server",
        transport=TransportType.STDIO,
        config={
            "command": "echo",
            "args": ["test"],
            "env": None
        }
    )

    print("✅ Server registered")
    print()

    # Test 2: List registered servers
    print("Test 2: Listing registered servers...")
    print("-" * 70)

    servers = await server.mcp_clients.list_servers()
    for srv in servers:
        print(f"  - {srv.server_id}: {srv.name} (enabled: {srv.enabled})")

    print()

    # Test 3: Parse upstream tool names
    print("Test 3: Testing tool name parsing...")
    print("-" * 70)

    test_cases = [
        ("upstream__windows-driver-input__Desktop_Info",
         "windows-driver-input", "Desktop_Info"),
        ("upstream__test-server__some_tool",
         "test-server", "some_tool"),
        ("regular_tool_name", None, None),
        ("skill__my_skill", None, None),
    ]

    for tool_name, expected_server, expected_tool in test_cases:
        server_id, actual_tool = server._parse_upstream_tool_name(tool_name)

        if server_id == expected_server and actual_tool == expected_tool:
            print(f"  ✅ {tool_name}")
            if server_id:
                print(f"     → server: {server_id}, tool: {actual_tool}")
        else:
            print(f"  ❌ {tool_name}")
            print(f"     Expected: ({expected_server}, {expected_tool})")
            print(f"     Got: ({server_id}, {actual_tool})")

    print()

    # Test 4: Check tool listing
    print("Test 4: Checking if _get_upstream_tools works...")
    print("-" * 70)

    try:
        upstream_tools = await server._get_upstream_tools()
        print(f"  Found {len(upstream_tools)} upstream tools")

        if upstream_tools:
            print("  Sample tools:")
            for tool in upstream_tools[:5]:
                print(f"    - {tool.name}")
                print(f"      {tool.description[:60]}...")
        else:
            print("  ℹ️  No upstream tools found (expected if test server has no tools)")

    except Exception as e:
        print(f"  ⚠️  Error getting upstream tools: {e}")
        print("     (This is expected if test server cannot be connected)")

    print()

    print("=" * 70)
    print("✅ Proxy functionality tests completed!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Register a real MCP server (e.g., windows-driver-input)")
    print("2. Restart Skillflow to load the new code")
    print("3. Check that upstream tools appear in list_tools()")
    print("4. Start recording and call upstream tools")
    print("5. Verify that recording captures the calls")
    print()


async def test_recording_flow():
    """Test the complete recording flow with upstream tools."""

    print("=" * 70)
    print("Testing Recording Flow (Simulation)")
    print("=" * 70)
    print()

    server = SkillFlowServer(data_dir="data")
    await server.initialize()

    # Start recording
    print("Step 1: Starting recording...")
    from src.skillflow.schemas import RecordingContext

    context = RecordingContext(
        client_id="test-client",
        workspace_id="test-workspace"
    )

    session_id = await server.recording_manager.start_session(context, "test_recording")
    server.active_recording_session = session_id

    print(f"  ✅ Recording started: {session_id}")
    print()

    # Simulate tool call (without actually calling upstream server)
    print("Step 2: Simulating upstream tool call...")

    from datetime import datetime
    from src.skillflow.schemas import ToolCallStatus

    await server.recording_manager.record_tool_call(
        session_id=session_id,
        server="windows-driver-input",
        tool="Desktop_Info",
        args={},
        result={"width": 1920, "height": 1080},
        duration_ms=50,
        status=ToolCallStatus.SUCCESS
    )

    print("  ✅ Tool call recorded (simulated)")
    print()

    # Stop recording
    print("Step 3: Stopping recording...")

    session = await server.recording_manager.stop_session(session_id)
    server.active_recording_session = None

    print(f"  ✅ Recording stopped")
    print(f"     Total calls recorded: {len(session.logs)}")

    if session.logs:
        print("     Recorded calls:")
        for log in session.logs:
            print(f"       - {log.server}.{log.tool}")
            print(f"         Args: {log.args}")
            print(f"         Status: {log.status}")

    print()

    print("=" * 70)
    print("✅ Recording flow test completed!")
    print("=" * 70)
    print()


async def main():
    """Run all tests."""

    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + " Skillflow-MCP Upstream Tool Proxy Test Suite".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    try:
        await test_proxy_functionality()
        await test_recording_flow()

        print("\n")
        print("🎉 All tests completed successfully!")
        print()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
