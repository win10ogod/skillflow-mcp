#!/usr/bin/env python3
"""示例：如何以編程方式添加 MCP server 到 SkillFlow."""

import asyncio
import json

from src.skillflow.storage import StorageLayer
from src.skillflow.schemas import ServerConfig, ServerRegistry, TransportType


async def add_filesystem_server():
    """添加 Filesystem MCP server."""

    storage = StorageLayer("data")
    await storage.initialize()

    # 加載或創建註冊表
    registry = await storage.load_registry()

    # 配置 Filesystem server
    filesystem_config = ServerConfig(
        server_id="filesystem",
        name="File System Tools",
        transport=TransportType.STDIO,
        config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": None
        },
        enabled=True,
        metadata={
            "description": "提供檔案系統操作工具",
            "tools": ["read_file", "write_file", "list_directory", "search_files"]
        }
    )

    # 添加到註冊表
    registry.servers["filesystem"] = filesystem_config

    # 保存
    await storage.save_registry(registry)

    print(f"✅ 已添加 server: {filesystem_config.name}")
    print(f"   ID: {filesystem_config.server_id}")
    print(f"   Transport: {filesystem_config.transport.value}")
    print(f"   Command: {filesystem_config.config['command']}")

    return filesystem_config


async def add_puppeteer_server():
    """添加 Puppeteer (Browser) MCP server."""

    storage = StorageLayer("data")
    registry = await storage.load_registry()

    puppeteer_config = ServerConfig(
        server_id="puppeteer",
        name="Browser Automation",
        transport=TransportType.STDIO,
        config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            "env": None
        },
        enabled=True,
        metadata={
            "description": "使用 Puppeteer 進行瀏覽器自動化",
            "tools": ["puppeteer_navigate", "puppeteer_screenshot", "puppeteer_click"]
        }
    )

    registry.servers["puppeteer"] = puppeteer_config
    await storage.save_registry(registry)

    print(f"✅ 已添加 server: {puppeteer_config.name}")

    return puppeteer_config


async def add_brave_search_server(api_key: str):
    """添加 Brave Search MCP server.

    Args:
        api_key: Brave Search API key
    """

    storage = StorageLayer("data")
    registry = await storage.load_registry()

    brave_config = ServerConfig(
        server_id="brave-search",
        name="Brave Search API",
        transport=TransportType.STDIO,
        config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {
                "BRAVE_API_KEY": api_key
            }
        },
        enabled=True,
        metadata={
            "description": "Brave Search API 整合",
            "requires_api_key": True
        }
    )

    registry.servers["brave-search"] = brave_config
    await storage.save_registry(registry)

    print(f"✅ 已添加 server: {brave_config.name}")
    print(f"   ⚠️  API Key 已設置（請確保有效）")

    return brave_config


async def add_custom_python_server(module_name: str):
    """添加自定義 Python MCP server.

    Args:
        module_name: Python 模組名稱（例如 "my_mcp_server"）
    """

    storage = StorageLayer("data")
    registry = await storage.load_registry()

    server_id = module_name.replace("_", "-")

    custom_config = ServerConfig(
        server_id=server_id,
        name=f"Custom: {module_name}",
        transport=TransportType.STDIO,
        config={
            "command": "python",
            "args": ["-m", module_name],
            "env": None
        },
        enabled=True,
        metadata={
            "description": f"自定義 Python MCP server: {module_name}",
            "type": "custom"
        }
    )

    registry.servers[server_id] = custom_config
    await storage.save_registry(registry)

    print(f"✅ 已添加 server: {custom_config.name}")
    print(f"   Module: {module_name}")

    return custom_config


async def list_registered_servers():
    """列出所有已註冊的 server."""

    storage = StorageLayer("data")
    registry = await storage.load_registry()

    if not registry.servers:
        print("ℹ️  沒有已註冊的 server")
        return

    print(f"\n📋 已註冊的 MCP Servers ({len(registry.servers)}):")
    print("=" * 60)

    for server_id, config in registry.servers.items():
        status = "✅ 啟用" if config.enabled else "❌ 禁用"
        print(f"\n{status} {config.name}")
        print(f"   ID: {server_id}")
        print(f"   Transport: {config.transport.value}")
        print(f"   Command: {config.config.get('command')} {' '.join(config.config.get('args', []))}")
        if config.metadata.get('description'):
            print(f"   描述: {config.metadata['description']}")


async def remove_server(server_id: str):
    """移除一個 server.

    Args:
        server_id: 要移除的 server ID
    """

    storage = StorageLayer("data")
    registry = await storage.load_registry()

    if server_id in registry.servers:
        removed = registry.servers.pop(server_id)
        await storage.save_registry(registry)
        print(f"✅ 已移除 server: {removed.name} ({server_id})")
    else:
        print(f"❌ Server {server_id} 不存在")


async def main():
    """主函數 - 展示各種操作."""

    print("=" * 60)
    print("SkillFlow - 添加 MCP Server 示例")
    print("=" * 60)
    print()

    # 示例 1: 添加 Filesystem server
    print("示例 1: 添加 Filesystem Server")
    print("-" * 60)
    await add_filesystem_server()
    print()

    # 示例 2: 添加 Puppeteer server
    print("示例 2: 添加 Puppeteer Server")
    print("-" * 60)
    await add_puppeteer_server()
    print()

    # 示例 3: 添加自定義 Python server（註釋掉，因為可能不存在）
    # print("示例 3: 添加自定義 Python Server")
    # print("-" * 60)
    # await add_custom_python_server("my_custom_mcp")
    # print()

    # 示例 4: 列出所有 server
    print("示例 4: 列出所有已註冊的 Server")
    print("-" * 60)
    await list_registered_servers()
    print()

    # 示例 5: 查看註冊表文件
    print("示例 5: 註冊表文件位置")
    print("-" * 60)
    print("📁 註冊表文件: data/registry/servers.json")
    print()

    # 讀取並顯示 JSON
    storage = StorageLayer("data")
    registry = await storage.load_registry()
    print("📄 當前註冊表內容:")
    print(json.dumps(registry.model_dump(mode="json"), indent=2, ensure_ascii=False))
    print()

    print("=" * 60)
    print("✅ 示例完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 檢查 data/registry/servers.json")
    print("2. 重啟 SkillFlow 以加載新 server")
    print("3. 使用 list_upstream_servers 工具驗證")
    print("4. 在技能中使用這些 server")
    print()


if __name__ == "__main__":
    asyncio.run(main())
