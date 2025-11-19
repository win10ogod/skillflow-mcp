# Bug Fixes and Enhancements

## Date: 2025-11-19

### Fixed: Support for Standard Claude Code MCP Configuration Format

**Issue:** The system did not support the standard Claude Code `mcpServers` configuration format.

**Solution:** Updated `ConfigConverter.from_claude_code()` to accept both:
- Standard Claude Code format with `mcpServers` key
- SkillFlow internal format with `servers` key

**Example Usage:**

You can now import configurations in the standard Claude Code format:

```json
{
  "mcpServers": {
    "screenmonitormcp-v2": {
      "command": "uv",
      "args": ["run", "--directory", "...", "python", "-m", "..."],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Use the `import_claude_code_config` tool to import:

```python
# Via MCP tool call
{
  "name": "import_claude_code_config",
  "arguments": {
    "config_json": "{\"mcpServers\": {...}}",
    "merge": true,
    "overwrite": false
  }
}
```

### Enhanced: StepSelection Support in Skill Creation

**Issue:** `StepSelection` was defined in schemas but not exposed in the API, preventing users from selecting specific steps when creating skills from recording sessions.

**Solution:** Exposed step selection parameters in the `create_skill_from_session` tool.

**New Parameters:**

- `step_indices` (array of integers): Select specific steps by index (1-indexed)
  - Example: `[1, 3, 5]` - Include only steps 1, 3, and 5

- `start_index` (integer): Start of step range (1-indexed, inclusive)
- `end_index` (integer): End of step range (1-indexed, inclusive)
  - Example: `start_index: 2, end_index: 5` - Include steps 2, 3, 4, 5

**Example Usage:**

```python
# Create skill with specific steps only
{
  "name": "create_skill_from_session",
  "arguments": {
    "session_id": "session_abc123",
    "skill_id": "my_skill",
    "name": "My Skill",
    "description": "Skill with selected steps",
    "step_indices": [1, 3, 5]  # Only include steps 1, 3, and 5
  }
}

# Create skill with step range
{
  "name": "create_skill_from_session",
  "arguments": {
    "session_id": "session_abc123",
    "skill_id": "my_skill_range",
    "name": "My Skill Range",
    "description": "Skill with step range",
    "start_index": 2,  # Start from step 2
    "end_index": 5     # End at step 5
  }
}
```

### Files Modified:

1. **src/skillflow/config_utils.py**
   - Updated `ConfigConverter.from_claude_code()` to handle both `mcpServers` and `servers` keys
   - Added normalization logic to convert `mcpServers` to internal format

2. **src/skillflow/server.py**
   - Added `step_indices`, `start_index`, and `end_index` parameters to `create_skill_from_session` tool schema
   - Updated tool handler to create `StepSelection` object from parameters
   - Passed `selection` parameter to `to_skill_draft()` method

### Benefits:

1. **Full Claude Code Compatibility**: Users can now import MCP server configurations directly from Claude Code format without manual conversion

2. **Flexible Skill Creation**: Users can create skills from specific steps in a recording session, enabling:
   - Removal of unwanted steps
   - Creation of multiple skills from different parts of the same session
   - Better control over skill composition

3. **Backward Compatibility**: All existing functionality continues to work unchanged
   - If step selection parameters are omitted, all steps are included (default behavior)
   - Internal `servers` format still supported
