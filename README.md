# SkillFlow MCP Server

Transform MCP tool call chains into reusable skills.

## Features

- Record tool call sequences
- Convert recordings into skills
- Replay skills as single MCP tools
- Support for DAG execution with parallelism
- JSON-based storage (no database required)

## Installation

```bash
uv sync
```

## Quick Start

1. Configure in Claude Desktop or other MCP client
2. Start recording: `start_recording()`
3. Execute tool calls
4. Stop recording: `stop_recording()`
5. Create skill from session
6. Execute skill with one call

See `docs/QUICKSTART.md` for detailed instructions.

## Documentation

- [Quick Start](docs/QUICKSTART.md)
- [Usage Guide](docs/USAGE_GUIDE.md)
- [Quick Reference](QUICK_REFERENCE.md)
- [Project Summary](PROJECT_SUMMARY.md)

## License

MIT
