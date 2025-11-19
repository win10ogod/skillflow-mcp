#!/usr/bin/env python3
"""
Test script for MCP configuration format converter.

This script verifies that SkillFlow can correctly read and convert
Claude Code/Claude Desktop MCP configuration formats.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillflow.config_converter import (
    detect_config_format,
    convert_claude_code_to_skillflow,
    convert_skillflow_to_claude_code,
)
from skillflow.schemas import ServerRegistry


def print_section(title: str):
    """Print a section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_subsection(title: str):
    """Print a subsection header."""
    print()
    print(f"--- {title} ---")
    print()


async def test_format_detection():
    """Test configuration format detection."""
    print_section("Test 1: Format Detection")

    # Test Claude Code format
    claude_code_config = {
        "mcpServers": {
            "test": {
                "command": "test",
                "args": []
            }
        }
    }
    format_type = detect_config_format(claude_code_config)
    print(f"✅ Claude Code format detected: {format_type}")
    assert format_type == "claude_code", f"Expected 'claude_code', got '{format_type}'"

    # Test SkillFlow format
    skillflow_config = {
        "servers": {
            "test": {
                "server_id": "test",
                "name": "Test",
                "transport": "stdio",
                "config": {"command": "test", "args": []},
                "enabled": True,
                "metadata": {}
            }
        }
    }
    format_type = detect_config_format(skillflow_config)
    print(f"✅ SkillFlow format detected: {format_type}")
    assert format_type == "skillflow", f"Expected 'skillflow', got '{format_type}'"

    # Test nested Claude Code format
    nested_config = {
        "servers": {
            "test": {
                "command": "test",
                "args": []
            }
        }
    }
    format_type = detect_config_format(nested_config)
    print(f"✅ Nested Claude Code format detected: {format_type}")
    assert format_type == "claude_code_nested", f"Expected 'claude_code_nested', got '{format_type}'"

    print()
    print("🎉 All format detection tests passed!")


async def test_claude_code_conversion():
    """Test Claude Code to SkillFlow conversion."""
    print_section("Test 2: Claude Code to SkillFlow Conversion")

    # Test standard Claude Code format
    print_subsection("Standard Claude Code Format")
    claude_config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"DEBUG": "true"}
            },
            "puppeteer": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
            }
        }
    }

    print("Input (Claude Code format):")
    print(json.dumps(claude_config, indent=2))

    registry = convert_claude_code_to_skillflow(claude_config)

    print()
    print("Output (SkillFlow format):")
    print(json.dumps(registry.model_dump(), indent=2))

    # Verify conversion
    assert "filesystem" in registry.servers
    assert "puppeteer" in registry.servers

    fs_server = registry.servers["filesystem"]
    assert fs_server.server_id == "filesystem"
    assert fs_server.name == "filesystem"
    assert fs_server.transport.value == "stdio"
    assert fs_server.config["command"] == "npx"
    assert fs_server.config["args"] == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    assert fs_server.config["env"] == {"DEBUG": "true"}
    assert fs_server.enabled is True

    print()
    print("✅ Conversion verified!")

    # Test nested format
    print_subsection("Nested Claude Code Format")
    nested_config = {
        "servers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "test"}
            }
        }
    }

    print("Input (Nested format):")
    print(json.dumps(nested_config, indent=2))

    registry = convert_claude_code_to_skillflow(nested_config)

    print()
    print("Output (SkillFlow format):")
    print(json.dumps(registry.model_dump(), indent=2))

    assert "github" in registry.servers
    gh_server = registry.servers["github"]
    assert gh_server.config["env"] == {"GITHUB_TOKEN": "test"}

    print()
    print("✅ Nested format conversion verified!")

    print()
    print("🎉 All Claude Code conversion tests passed!")


async def test_skillflow_conversion():
    """Test SkillFlow to Claude Code conversion."""
    print_section("Test 3: SkillFlow to Claude Code Conversion")

    # Create a SkillFlow registry
    from skillflow.schemas import ServerConfig, TransportType

    registry = ServerRegistry()
    registry.servers["test"] = ServerConfig(
        server_id="test",
        name="Test Server",
        transport=TransportType.STDIO,
        config={
            "command": "python",
            "args": ["-m", "test_server"],
            "env": {"TEST": "true"}
        },
        enabled=True,
        metadata={"version": "1.0"}
    )

    print("Input (SkillFlow format):")
    print(json.dumps(registry.model_dump(), indent=2))

    claude_config = convert_skillflow_to_claude_code(registry)

    print()
    print("Output (Claude Code format):")
    print(json.dumps(claude_config, indent=2))

    # Verify conversion
    assert "mcpServers" in claude_config
    assert "test" in claude_config["mcpServers"]
    test_server = claude_config["mcpServers"]["test"]
    assert test_server["command"] == "python"
    assert test_server["args"] == ["-m", "test_server"]
    assert test_server["env"] == {"TEST": "true"}

    print()
    print("✅ Conversion verified!")

    # Test with metadata inclusion
    print_subsection("With Metadata Inclusion")
    claude_config_with_meta = convert_skillflow_to_claude_code(registry, include_metadata=True)

    print("Output (with metadata):")
    print(json.dumps(claude_config_with_meta, indent=2))

    test_server = claude_config_with_meta["mcpServers"]["test"]
    assert test_server["name"] == "Test Server"
    assert test_server["metadata"] == {"version": "1.0"}

    print()
    print("✅ Metadata inclusion verified!")

    print()
    print("🎉 All SkillFlow conversion tests passed!")


async def test_round_trip():
    """Test round-trip conversion."""
    print_section("Test 4: Round-Trip Conversion")

    original_claude = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"DEBUG": "true"}
            }
        }
    }

    print("Original (Claude Code):")
    print(json.dumps(original_claude, indent=2))

    # Convert to SkillFlow
    registry = convert_claude_code_to_skillflow(original_claude)
    print()
    print("Intermediate (SkillFlow):")
    print(json.dumps(registry.model_dump(), indent=2))

    # Convert back to Claude Code
    result_claude = convert_skillflow_to_claude_code(registry)
    print()
    print("Result (Claude Code):")
    print(json.dumps(result_claude, indent=2))

    # Verify round-trip
    orig_server = original_claude["mcpServers"]["filesystem"]
    result_server = result_claude["mcpServers"]["filesystem"]

    assert orig_server["command"] == result_server["command"]
    assert orig_server["args"] == result_server["args"]
    assert orig_server["env"] == result_server["env"]

    print()
    print("✅ Round-trip verified!")
    print()
    print("🎉 Round-trip conversion test passed!")


async def test_example_files():
    """Test example configuration files."""
    print_section("Test 5: Example Configuration Files")

    examples_dir = Path(__file__).parent / "examples"

    # Test Claude Code format example
    claude_code_path = examples_dir / "upstream_servers_claude_code_format.json"
    if claude_code_path.exists():
        print(f"Testing: {claude_code_path.name}")
        with open(claude_code_path, "r") as f:
            config = json.load(f)

        format_type = detect_config_format(config)
        print(f"  Format detected: {format_type}")

        registry = convert_claude_code_to_skillflow(config)
        print(f"  Servers loaded: {len(registry.servers)}")
        for server_id in registry.servers:
            print(f"    - {server_id}")

        print("  ✅ Successfully loaded and converted")
    else:
        print(f"⚠️  Example file not found: {claude_code_path.name}")

    print()

    # Test mixed format example
    mixed_path = examples_dir / "upstream_servers_mixed_format.json"
    if mixed_path.exists():
        print(f"Testing: {mixed_path.name}")
        with open(mixed_path, "r") as f:
            config = json.load(f)

        format_type = detect_config_format(config)
        print(f"  Format detected: {format_type}")

        registry = convert_claude_code_to_skillflow(config)
        print(f"  Servers loaded: {len(registry.servers)}")
        for server_id, server in registry.servers.items():
            print(f"    - {server_id}: {server.name}")
            if server.metadata:
                print(f"      Metadata: {server.metadata}")

        print("  ✅ Successfully loaded and converted")
    else:
        print(f"⚠️  Example file not found: {mixed_path.name}")

    print()
    print("🎉 Example file tests completed!")


async def main():
    """Run all tests."""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "MCP Configuration Converter Tests" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        await test_format_detection()
        await test_claude_code_conversion()
        await test_skillflow_conversion()
        await test_round_trip()
        await test_example_files()

        print()
        print("=" * 80)
        print("  🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print()

        return 0

    except AssertionError as e:
        print()
        print("=" * 80)
        print("  ❌ TEST FAILED!")
        print("=" * 80)
        print(f"  Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print()
        print("=" * 80)
        print("  ❌ UNEXPECTED ERROR!")
        print("=" * 80)
        print(f"  Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
