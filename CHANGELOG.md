# Changelog

All notable changes to SkillFlow MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-16

### Added - MVP Release

#### Core Features
- **Recording System**: Record tool call sequences into sessions
  - `start_recording()` and `stop_recording()` tools
  - Session persistence in JSON format
  - Tool call logging with timing and status

- **Skill Management**: Create and manage reusable skills
  - Create skills from recording sessions
  - Skill versioning (automatic version increment)
  - List, get, and delete skills
  - Tag-based filtering and search
  - Skills automatically registered as MCP tools

- **Execution Engine**: Execute skills with DAG support
  - Topological sorting of skill nodes
  - Three concurrency modes:
    - Sequential: Execute nodes in order
    - Phased: Execute phases in parallel
    - Full Parallel: Maximize parallelism with dependency analysis
  - Parameter template resolution (`$inputs.*`, `@step_*.outputs.*`)
  - Error handling strategies (fail_fast, retry, skip_dependents, continue)
  - Execution status tracking and cancellation
  - JSONL execution logs

- **MCP Client Management**: Connect to upstream MCP servers
  - Server registration and management
  - stdio transport support
  - Tool call proxying
  - Server lifecycle management

- **Storage Layer**: JSON-based persistence
  - Atomic writes with file locking
  - In-memory indexing for fast lookups
  - Organized file structure (skills, sessions, runs, registry)

#### MCP Tools
- `start_recording` - Start a recording session
- `stop_recording` - Stop active recording
- `list_recording_sessions` - List all sessions
- `create_skill_from_session` - Create skill from session
- `list_skills` - List all skills with filtering
- `get_skill` - Get skill details
- `delete_skill` - Delete a skill
- `get_run_status` - Query execution status
- `cancel_run` - Cancel running skill
- `register_upstream_server` - Register upstream MCP server
- `list_upstream_servers` - List registered servers
- `skill__<id>` - Dynamic tools for each skill

#### Developer Experience
- Complete Pydantic data models with type safety
- Comprehensive async/await implementation
- pytest test suite with async support
- uv package management integration
- Detailed documentation (README, Quick Start, Usage Guide)
- Example configurations and skills

#### Documentation
- README.md - Project overview and features
- QUICKSTART.md - 5-minute getting started guide
- USAGE_GUIDE.md - Comprehensive usage documentation
- PROJECT_SUMMARY.md - Project summary and architecture
- QUICK_REFERENCE.md - Quick reference card

### Technical Details

#### Architecture
- Python 3.11+ with full type hints
- MCP Python SDK v1.21.1+
- Pydantic v2.12+ for data validation
- aiofiles for async file I/O
- filelock for concurrent write safety

#### File Structure
```
data/
├── skills/{skill_id}/
├── sessions/
├── runs/{date}/
└── registry/
```

### Known Limitations

- Only stdio transport is currently implemented
- HTTP+SSE transport not yet available
- No skill nesting (skills calling skills)
- No conditional execution (if/else)
- No loop execution (for/while)
- No web UI

## [Unreleased]

### Planned Features

#### Phase 2: Transport Layer
- [ ] HTTP+SSE transport support
- [ ] Streamable HTTP transport support
- [ ] WebSocket transport support

#### Phase 3: Advanced Execution
- [ ] Skill nesting and composition
- [ ] Conditional nodes (if/else/switch)
- [ ] Loop nodes (for/while)
- [ ] Parameter transformation expressions (JSONPath, Jinja2)

#### Phase 4: Enterprise Features
- [ ] Multi-tenancy support
- [ ] Access control and permissions
- [ ] Skill marketplace
- [ ] Audit logging

#### Phase 5: User Experience
- [ ] Web UI control panel
- [ ] Visual DAG editor
- [ ] Execution monitoring dashboard
- [ ] Skill debugging tools

---

## Version History

- **v0.1.0** (2025-01-16) - Initial MVP release

## Migration Guide

### From Nothing to v0.1.0

This is the initial release. To start using SkillFlow:

1. Install with `uv sync`
2. Configure in Claude Desktop or other MCP client
3. See QUICKSTART.md for first steps

---

For detailed information about each release, see the corresponding git tags and release notes.
