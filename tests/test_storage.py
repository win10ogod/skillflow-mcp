"""Tests for storage layer."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.skillflow.schemas import (
    Skill,
    SkillAuthor,
    SkillGraph,
    SkillNode,
    NodeKind,
    Concurrency,
    RecordingSession,
)
from src.skillflow.storage import StorageLayer


@pytest.fixture
async def storage():
    """Create a temporary storage instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageLayer(tmpdir)
        await storage.initialize()
        yield storage


@pytest.mark.asyncio
async def test_save_and_load_skill(storage):
    """Test saving and loading a skill."""
    skill = Skill(
        id="test_skill",
        name="Test Skill",
        version=1,
        description="A test skill",
        tags=["test"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        author=SkillAuthor(workspace_id="test", client_id="test"),
        inputs_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {}},
        graph=SkillGraph(
            nodes=[
                SkillNode(
                    id="step1",
                    kind=NodeKind.TOOL_CALL,
                    server="test",
                    tool="test_tool",
                    args_template={},
                )
            ],
            edges=[],
            concurrency=Concurrency(),
        ),
    )

    await storage.save_skill(skill)
    loaded = await storage.load_skill("test_skill")

    assert loaded.id == skill.id
    assert loaded.name == skill.name
    assert loaded.version == skill.version


@pytest.mark.asyncio
async def test_list_skills(storage):
    """Test listing skills."""
    for i in range(3):
        skill = Skill(
            id=f"skill_{i}",
            name=f"Skill {i}",
            version=1,
            description=f"Description {i}",
            tags=["test"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            author=SkillAuthor(workspace_id="test", client_id="test"),
            inputs_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            graph=SkillGraph(nodes=[], edges=[], concurrency=Concurrency()),
        )
        await storage.save_skill(skill)

    skills = await storage.list_skills()
    assert len(skills) == 3


@pytest.mark.asyncio
async def test_save_and_load_session(storage):
    """Test saving and loading a recording session."""
    session = RecordingSession(
        id="test_session",
        started_at=datetime.utcnow(),
        client_id="test",
        logs=[],
    )

    await storage.save_session(session)
    loaded = await storage.load_session("test_session")

    assert loaded.id == session.id
    assert loaded.client_id == session.client_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
