#!/usr/bin/env python3
"""Test script for context7 integration with SkillFlow."""

import asyncio
import json
from datetime import datetime

from src.skillflow.storage import StorageLayer
from src.skillflow.skills import SkillManager
from src.skillflow.schemas import (
    Skill,
    SkillAuthor,
    SkillGraph,
    SkillNode,
    SkillEdge,
    NodeKind,
    Concurrency,
    ConcurrencyMode,
)


async def create_context7_skill():
    """Create a test skill that uses context7 MCP tools."""

    storage = StorageLayer("data")
    await storage.initialize()

    skill_manager = SkillManager(storage)

    # Create the skill
    skill = Skill(
        id="fetch_library_docs",
        name="獲取庫文檔",
        version=1,
        description="使用 context7 獲取任意 JavaScript 庫的文檔",
        tags=["context7", "documentation", "test"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        author=SkillAuthor(
            workspace_id="default",
            client_id="test-script"
        ),
        inputs_schema={
            "type": "object",
            "properties": {
                "library_name": {
                    "type": "string",
                    "description": "要查詢的庫名稱（例如：react, vue, svelte）"
                },
                "topic": {
                    "type": "string",
                    "description": "要查詢的主題（可選）"
                }
            },
            "required": ["library_name"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "library_info": {
                    "type": "object",
                    "description": "庫的基本信息"
                },
                "documentation": {
                    "type": "string",
                    "description": "文檔內容"
                }
            }
        },
        graph=SkillGraph(
            nodes=[
                SkillNode(
                    id="resolve_library",
                    kind=NodeKind.TOOL_CALL,
                    server=None,  # Will use mcp__context7 prefix
                    tool="mcp__context7__resolve-library-id",
                    args_template={
                        "libraryName": "$inputs.library_name"
                    },
                    export_outputs={
                        "library_id": "$.library_id",
                        "library_info": "$"
                    }
                ),
                SkillNode(
                    id="get_docs",
                    kind=NodeKind.TOOL_CALL,
                    server=None,
                    tool="mcp__context7__get-library-docs",
                    args_template={
                        "context7CompatibleLibraryID": "@resolve_library.outputs.library_id",
                        "topic": "$inputs.topic",
                        "tokens": 3000
                    },
                    export_outputs={
                        "documentation": "$"
                    },
                    depends_on=["resolve_library"]
                )
            ],
            edges=[
                SkillEdge(
                    from_node="resolve_library",
                    to_node="get_docs"
                )
            ],
            concurrency=Concurrency(mode=ConcurrencyMode.SEQUENTIAL)
        )
    )

    # Save the skill
    await storage.save_skill(skill)

    print(f"✅ Created skill: {skill.id}")
    print(f"   Version: {skill.version}")
    print(f"   Description: {skill.description}")
    print(f"\n📝 Skill saved to: data/skills/{skill.id}/v{skill.version:04d}.json")

    # Print usage
    print(f"\n🚀 Usage example:")
    print(f'   skill__fetch_library_docs(library_name="react", topic="hooks")')

    return skill


async def main():
    """Main function."""
    print("=" * 60)
    print("SkillFlow + Context7 Integration Test")
    print("=" * 60)
    print()

    skill = await create_context7_skill()

    print()
    print("=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Restart your MCP client to load the new skill")
    print("2. Call the skill with: skill__fetch_library_docs")
    print("3. Example: Get React hooks documentation")
    print()


if __name__ == "__main__":
    asyncio.run(main())
