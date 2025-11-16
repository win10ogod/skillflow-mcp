"""Skill management module."""

from datetime import datetime
from typing import Optional

from .schemas import (
    Skill,
    SkillAuthor,
    SkillDraft,
    SkillFilter,
    SkillMeta,
)
from .storage import SkillNotFoundError, StorageLayer


class SkillManager:
    """Manages skill CRUD operations and versioning."""

    def __init__(self, storage: StorageLayer):
        """Initialize skill manager.

        Args:
            storage: Storage layer instance
        """
        self.storage = storage

    async def list_skills(self, filters: Optional[SkillFilter] = None) -> list[SkillMeta]:
        """List skills with optional filtering.

        Args:
            filters: Optional filter criteria

        Returns:
            List of skill metadata matching filters
        """
        all_skills = await self.storage.list_skills()

        if filters is None:
            return all_skills

        # Apply filters
        filtered = all_skills

        # Query filter (fuzzy match on name or description)
        if filters.query:
            query_lower = filters.query.lower()
            filtered = [
                s for s in filtered
                if query_lower in s.name.lower() or query_lower in s.description.lower()
            ]

        # Tags filter (must have all specified tags)
        if filters.tags:
            filtered = [
                s for s in filtered
                if all(tag in s.tags for tag in filters.tags)
            ]

        # Author filter
        if filters.author_id:
            filtered = [
                s for s in filtered
                if s.author.client_id == filters.author_id
            ]

        # Date range filters
        if filters.created_after:
            filtered = [s for s in filtered if s.created_at >= filters.created_after]

        if filters.created_before:
            filtered = [s for s in filtered if s.created_at <= filters.created_before]

        return filtered

    async def get_skill(self, skill_id: str, version: Optional[int] = None) -> Skill:
        """Get a specific skill.

        Args:
            skill_id: ID of the skill
            version: Specific version (None for latest)

        Returns:
            The skill

        Raises:
            SkillNotFoundError: If skill not found
        """
        return await self.storage.load_skill(skill_id, version)

    async def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        author: SkillAuthor,
        draft: SkillDraft,
    ) -> Skill:
        """Create a new skill.

        Args:
            skill_id: Unique ID for the skill
            name: Skill name
            description: Skill description
            author: Author information
            draft: Skill draft with graph and schemas

        Returns:
            The created skill
        """
        now = datetime.utcnow()

        # Prepare metadata - include source_session_id if available
        metadata = {}
        if draft.source_session_id:
            metadata["source_session_id"] = draft.source_session_id

        skill = Skill(
            id=skill_id,
            name=name,
            version=1,
            description=description,
            tags=draft.tags,
            created_at=now,
            updated_at=now,
            author=author,
            inputs_schema=draft.inputs_schema,
            output_schema=draft.output_schema,
            graph=draft.graph,
            metadata=metadata,
        )

        await self.storage.save_skill(skill)
        return skill

    async def update_skill(
        self,
        skill_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        draft: Optional[SkillDraft] = None,
    ) -> Skill:
        """Update an existing skill (creates new version).

        Args:
            skill_id: ID of skill to update
            name: New name (optional)
            description: New description (optional)
            tags: New tags (optional)
            draft: New skill draft (optional)

        Returns:
            The updated skill with incremented version

        Raises:
            SkillNotFoundError: If skill not found
        """
        # Load current skill
        current = await self.storage.load_skill(skill_id)

        # Create new version
        now = datetime.utcnow()
        updated = Skill(
            id=skill_id,
            name=name if name is not None else current.name,
            version=current.version + 1,
            description=description if description is not None else current.description,
            tags=tags if tags is not None else current.tags,
            created_at=current.created_at,
            updated_at=now,
            author=current.author,
            inputs_schema=draft.inputs_schema if draft else current.inputs_schema,
            output_schema=draft.output_schema if draft else current.output_schema,
            graph=draft.graph if draft else current.graph,
        )

        await self.storage.save_skill(updated)
        return updated

    async def delete_skill(self, skill_id: str, hard: bool = False) -> None:
        """Delete a skill.

        Args:
            skill_id: ID of skill to delete
            hard: If True, physically delete files
        """
        await self.storage.delete_skill(skill_id, hard)

    async def skill_exists(self, skill_id: str) -> bool:
        """Check if a skill exists.

        Args:
            skill_id: ID of the skill

        Returns:
            True if skill exists
        """
        meta = await self.storage.get_skill_meta(skill_id)
        return meta is not None

    def export_as_mcp_tool(self, skill: Skill) -> dict:
        """Export a skill as an MCP tool descriptor.

        Args:
            skill: The skill to export

        Returns:
            MCP tool descriptor (JSON Schema format)
        """
        return {
            "name": f"skill__{skill.id}",
            "description": f"{skill.description}\n\n[Skill v{skill.version}]",
            "inputSchema": skill.inputs_schema,
        }

    async def list_as_mcp_tools(self) -> list[dict]:
        """List all skills as MCP tool descriptors.

        Returns:
            List of MCP tool descriptors
        """
        skills = await self.list_skills()
        tools = []

        for skill_meta in skills:
            try:
                skill = await self.get_skill(skill_meta.id)
                tools.append(self.export_as_mcp_tool(skill))
            except SkillNotFoundError:
                # Skip if skill version not found
                continue

        return tools
