#!/usr/bin/env python3
"""Test tool naming strategy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillflow.tool_naming import ToolNamingStrategy, generate_proxy_tool_name, parse_proxy_tool_name


def test_tool_naming():
    """Test various naming scenarios."""

    print("=" * 70)
    print("Tool Naming Strategy Tests")
    print("=" * 70)
    print()

    test_cases = [
        # (server_id, tool_name, expected_max_length)
        ("windows-driver-input", "Move_Tool", 47),
        ("windows-driver-input", "Input-RateLimiter-Config", 47),
        ("windows-driver-input", "Desktop_Info", 47),
        ("very-long-server-name-that-exceeds-limits", "Very_Long_Tool_Name", 47),
        ("short", "tool", 47),
        ("filesystem", "read_file", 47),
        ("puppeteer", "navigate_to_url", 47),
    ]

    # Add note about client prefix
    print("NOTE: Max length set to 47 to account for Fount's 13-char prefix")
    print("      (mcp_skillflow_) which brings total to 60 chars max.")
    print()

    strategy = ToolNamingStrategy(ToolNamingStrategy.FORMAT_COMPACT)

    print("Test Cases:")
    print()

    for server_id, tool_name, max_len in test_cases:
        proxy_name = strategy.generate_proxy_tool_name(server_id, tool_name, max_len)
        length = len(proxy_name)
        status = "✅" if length <= max_len else "❌"

        print(f"{status} Server: {server_id}")
        print(f"   Tool: {tool_name}")
        print(f"   Proxy: {proxy_name}")
        print(f"   Length: {length}/{max_len}")

        # Test parsing
        parsed_server, parsed_tool = parse_proxy_tool_name(proxy_name)
        print(f"   Parsed: server={parsed_server}, tool={parsed_tool}")

        if parsed_tool != tool_name:
            print(f"   ⚠️  WARNING: Tool name mismatch!")

        print()

    # Test edge cases
    print("=" * 70)
    print("Edge Cases:")
    print("=" * 70)
    print()

    # Very long tool name
    long_tool = "This_Is_A_Very_Long_Tool_Name_That_Might_Cause_Issues"
    proxy = strategy.generate_proxy_tool_name("server", long_tool, 60)
    print(f"Long tool name:")
    print(f"  Original: {long_tool} (len={len(long_tool)})")
    print(f"  Proxy: {proxy} (len={len(proxy)})")
    print()

    # Test legacy format support
    legacy_strategy = ToolNamingStrategy(ToolNamingStrategy.FORMAT_LEGACY)
    legacy_name = legacy_strategy.generate_proxy_tool_name("windows-driver-input", "Move_Tool")
    print(f"Legacy format:")
    print(f"  {legacy_name} (len={len(legacy_name)})")

    # Parse legacy format
    parsed = parse_proxy_tool_name(legacy_name)
    print(f"  Parsed: {parsed}")
    print()

    # Test using default function
    print("=" * 70)
    print("Default Function Tests:")
    print("=" * 70)
    print()

    default_proxy = generate_proxy_tool_name("windows-driver-input", "Input-RateLimiter-Config")
    print(f"Default: {default_proxy} (len={len(default_proxy)})")

    parsed_server, parsed_tool = parse_proxy_tool_name(default_proxy)
    print(f"Parsed: server={parsed_server}, tool={parsed_tool}")
    print()

    # Summary
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print()
    print("Naming formats:")
    print("  - Compact: up_<server_id>_<tool_name>")
    print("  - Hash:    up_<hash>_<tool_name> (when compact exceeds 60 chars)")
    print("  - Legacy:  upstream__<server_id>__<tool_name> (deprecated)")
    print()
    print("All tests completed!")


if __name__ == "__main__":
    test_tool_naming()
