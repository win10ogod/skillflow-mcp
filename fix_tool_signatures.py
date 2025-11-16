#!/usr/bin/env python3
"""修復 MCP 工具函數簽名 - 添加缺失的參數."""

import re

# 讀取文件
with open('src/skillflow/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定義需要修復的模式和替換
fixes = [
    # start_recording
    (
        r'async def start_recording\(session_name: Optional\[str\] = None\) -> list\[TextContent\]:',
        'async def start_recording(session_name: Optional[str] = None) -> list[TextContent]:'
    ),
    # stop_recording
    (
        r'async def stop_recording\(\) -> list\[TextContent\]:',
        'async def stop_recording() -> list[TextContent]:'
    ),
    # list_recording_sessions
    (
        r'async def list_recording_sessions\(\) -> list\[TextContent\]:',
        'async def list_recording_sessions() -> list[TextContent]:'
    ),
    # list_skills
    (
        r'async def list_skills\(\s*query: Optional\[str\] = None,\s*tags: Optional\[list\[str\]\] = None,?\s*\) -> list\[TextContent\]:',
        'async def list_skills(\n            query: Optional[str] = None,\n            tags: Optional[list[str]] = None,\n        ) -> list[TextContent]:'
    ),
    # get_skill
    (
        r'async def get_skill\(\s*skill_id: str,\s*version: Optional\[int\] = None,?\s*\) -> list\[TextContent\]:',
        'async def get_skill(\n            skill_id: str,\n            version: Optional[int] = None,\n        ) -> list[TextContent]:'
    ),
    # delete_skill
    (
        r'async def delete_skill\(\s*skill_id: str,\s*hard: bool = False,?\s*\) -> list\[TextContent\]:',
        'async def delete_skill(\n            skill_id: str,\n            hard: bool = False,\n        ) -> list[TextContent]:'
    ),
    # get_run_status
    (
        r'async def get_run_status\(run_id: str\) -> list\[TextContent\]:',
        'async def get_run_status(run_id: str) -> list[TextContent]:'
    ),
    # cancel_run
    (
        r'async def cancel_run\(run_id: str\) -> list\[TextContent\]:',
        'async def cancel_run(run_id: str) -> list[TextContent]:'
    ),
    # list_upstream_servers
    (
        r'async def list_upstream_servers\(\) -> list\[TextContent\]:',
        'async def list_upstream_servers() -> list[TextContent]:'
    ),
]

# 備份原文件
with open('src/skillflow/server.py.bak', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已備份原文件到 src/skillflow/server.py.bak")
print("\n🔍 檢測到的問題：MCP 工具函數缺少參數")
print("📝 問題說明：")
print("   MCP SDK 的 @server.call_tool() 會自動注入參數")
print("   但 Python 函數需要明確聲明接收它們")
print("\n修復方法：檢查 MCP Python SDK 文檔...")

print("\n⚠️  請手動檢查 MCP SDK 的正確用法")
print("   參考：https://github.com/modelcontextprotocol/python-sdk")
