#!/usr/bin/env python3
"""Test Claude Code format conversion with actual user config."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skillflow.config_converter import (
    detect_config_format,
    convert_claude_code_to_skillflow,
)


async def test_user_config():
    """Test user's actual Claude Code configuration."""

    # User's actual configuration
    user_config = {
        "mcpServers": {
            "screenmonitormcp-v2": {
                "command": "uv",
                "args": [
                    "run",
                    "--directory",
                    "I:\\凌星開發計畫\\凌星\\ScreenMonitorMCP",
                    "python",
                    "-m",
                    "screenmonitormcp_v2.mcp_main"
                ],
                "env": {
                    "LOG_LEVEL": "INFO"
                }
            },
            "windows-driver-input": {
                "command": "uv",
                "args": [
                    "--directory",
                    "I:\\凌星開發計畫\\凌星\\VYO-MCP\\windows-driver-input-mcp",
                    "run",
                    "main.py"
                ],
                "env": {
                    "WINDOWS_MCP_INPUT_BACKEND": "ibsim-dll",
                    "WINDOWS_MCP_INPUT_DRIVER": "AnyDriver",
                    "WINDOWS_MCP_RATE_MOVE_HZ": "120",
                    "WINDOWS_MCP_RATE_MAX_DELTA": "60",
                    "WINDOWS_MCP_RATE_SMOOTH": "0.0",
                    "WINDOWS_MCP_RATE_CPS": "8.0",
                    "WINDOWS_MCP_RATE_KPS": "12.0",
                    "WINDOWS_INPUT_LOG_LEVEL": "INFO"
                }
            }
        }
    }

    print("=" * 80)
    print("Testing User's Claude Code Configuration")
    print("=" * 80)
    print()

    # Test format detection
    print("1. Format Detection")
    print("-" * 80)
    format_type = detect_config_format(user_config)
    print(f"Detected format: {format_type}")

    if format_type != "claude_code":
        print(f"❌ ERROR: Expected 'claude_code', got '{format_type}'")
        return False

    print("✅ Format correctly detected as 'claude_code'")
    print()

    # Test conversion
    print("2. Conversion to SkillFlow Format")
    print("-" * 80)
    try:
        registry = convert_claude_code_to_skillflow(user_config)
        print(f"✅ Conversion successful")
        print(f"   Servers converted: {len(registry.servers)}")
        print()

        # Display converted servers
        print("Converted servers:")
        for server_id, server in registry.servers.items():
            print(f"\n  Server: {server_id}")
            print(f"    Name: {server.name}")
            print(f"    Transport: {server.transport.value}")
            print(f"    Command: {server.config.get('command')}")
            print(f"    Args: {server.config.get('args')}")
            print(f"    Env vars: {len(server.config.get('env', {}))} variables")
            print(f"    Enabled: {server.enabled}")

        print()

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test serialization
    print("\n3. Serialization Test")
    print("-" * 80)
    try:
        serialized = registry.model_dump(mode="json")
        print("✅ Serialization successful")
        print()

        # Show JSON structure
        print("JSON structure preview:")
        print(json.dumps(serialized, indent=2, ensure_ascii=False)[:500] + "...")
        print()

    except Exception as e:
        print(f"❌ Serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test deserialization
    print("\n4. Deserialization Test")
    print("-" * 80)
    try:
        from skillflow.schemas import ServerRegistry
        registry2 = ServerRegistry(**serialized)
        print("✅ Deserialization successful")
        print(f"   Servers: {len(registry2.servers)}")
        print()

    except Exception as e:
        print(f"❌ Deserialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test actual storage save/load cycle
    print("\n5. Storage Save/Load Cycle")
    print("-" * 80)
    try:
        from skillflow.storage import StorageLayer

        # Create temporary storage
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageLayer(data_dir=tmpdir)
            await storage.initialize()

            # Save
            await storage.save_registry(registry)
            print("✅ Registry saved successfully")

            # Load back
            loaded_registry = await storage.load_registry()
            print(f"✅ Registry loaded successfully")
            print(f"   Servers loaded: {len(loaded_registry.servers)}")

            # Verify
            if len(loaded_registry.servers) != len(registry.servers):
                print(f"❌ Server count mismatch!")
                return False

            for server_id in registry.servers:
                if server_id not in loaded_registry.servers:
                    print(f"❌ Server {server_id} missing after load!")
                    return False

            print("✅ All servers preserved after save/load cycle")
            print()

    except Exception as e:
        print(f"❌ Storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("Your Claude Code configuration is fully compatible!")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_user_config())
    sys.exit(0 if success else 1)
