#!/usr/bin/env python3
"""Test transport type detection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillflow.config_converter import _detect_transport_type


def test_transport_detection():
    """Test various command/args combinations."""

    test_cases = [
        {
            "name": "NPX filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "config": {},
            "expected": "stdio"
        },
        {
            "name": "UV with --directory (screenmonitormcp)",
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "I:\\凌星開發計畫\\凌星\\ScreenMonitorMCP",
                "python",
                "-m",
                "screenmonitormcp_v2.mcp_main"
            ],
            "config": {},
            "expected": "stdio"
        },
        {
            "name": "UV with --directory (windows-driver-input)",
            "command": "uv",
            "args": [
                "--directory",
                "I:\\凌星開發計畫\\凌星\\VYO-MCP\\windows-driver-input-mcp",
                "run",
                "main.py"
            ],
            "config": {},
            "expected": "stdio"
        },
        {
            "name": "HTTP server",
            "command": "python",
            "args": ["-m", "http_server"],
            "config": {},
            "expected": "streamable_http"
        },
        {
            "name": "HTTP+SSE server",
            "command": "python",
            "args": ["-m", "http_sse_server"],
            "config": {},
            "expected": "http_sse"
        },
        {
            "name": "WebSocket server explicit",
            "command": "python",
            "args": ["-m", "websocket_server"],
            "config": {},
            "expected": "websocket"
        },
        {
            "name": "Explicit transport in config",
            "command": "python",
            "args": ["-m", "my_server"],
            "config": {"transport": "websocket"},
            "expected": "websocket"
        }
    ]

    print("=" * 80)
    print("Transport Type Detection Tests")
    print("=" * 80)
    print()

    failed = []
    for test in test_cases:
        detected = _detect_transport_type(test["command"], test["args"], test["config"])
        expected = test["expected"]

        status = "✅" if detected == expected else "❌"
        print(f"{status} {test['name']}")
        print(f"   Command: {test['command']}")
        print(f"   Args: {test['args'][:2]}..." if len(test['args']) > 2 else f"   Args: {test['args']}")
        print(f"   Expected: {expected}, Got: {detected}")
        print()

        if detected != expected:
            failed.append(test['name'])

    print("=" * 80)
    if failed:
        print(f"❌ {len(failed)} tests failed:")
        for name in failed:
            print(f"   - {name}")
        return False
    else:
        print("✅ All tests passed!")
        return True


if __name__ == "__main__":
    success = test_transport_detection()
    sys.exit(0 if success else 1)
