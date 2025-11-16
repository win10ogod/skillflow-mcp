# SkillFlow MCP Server

Transform MCP tool call chains into reusable, automated skills.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.21.1+-green.svg)](https://modelcontextprotocol.io/)

## Overview

SkillFlow is a complete implementation of the Model Context Protocol (MCP) server that enables recording, managing, and replaying tool call chains as reusable "skills". Transform complex multi-step operations into single-command automated workflows.

**Core Value**: Convert repetitive, multi-step operations into reusable automation skills.

## ✨ Key Features

### 🎯 Core Capabilities

- **📹 Recording Mode**: Capture tool call sequences automatically
- **🔄 Skill Creation**: Convert recordings into parameterized skills
- **⚡ One-Click Execution**: Run complex workflows with a single command
- **🌐 DAG Execution**: Support for parallel execution with dependency management
- **💾 Zero Database**: JSON-based storage (no database required)
- **🔌 Full MCP Protocol**: Complete support for Tools, Resources, and Prompts

### 🚀 Advanced Features (Latest)

#### Concurrency Control
- **Sequential Mode**: Execute steps one-by-one (default)
- **Phased Mode**: Group steps for parallel execution
- **Full Parallel Mode**: Maximize parallelism within dependencies

#### Upstream MCP Integration
- **Proxy Tools**: Automatically expose upstream server tools
- **Resources Access**: List and read resources from connected MCP servers
- **Prompts Access**: Retrieve and use prompt templates from upstream servers
- **Native MCP Client**: Custom implementation with full protocol control

#### SkillFlow's Own MCP Endpoints
- **Resources**: Expose skills, sessions, and run logs via custom URI schemes
  - `skill://<skill_id>` - Access skill definitions
  - `session://<session_id>` - Access recording sessions
  - `run://<run_id>` - Access execution logs
- **Prompts**: Built-in guides for skill development
  - `create_skill` - Step-by-step skill creation guide
  - `debug_skill` - Debugging assistance
  - `optimize_skill` - Performance optimization tips
  - `skill_best_practices` - Development best practices

#### Content Type Support
Full MCP protocol content type support:
- ✅ TextContent
- ✅ ImageContent (screenshots, charts)
- ✅ AudioContent (recordings, TTS)
- ✅ EmbeddedResource (files, data)

## 📦 Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- MCP client (e.g., Claude Desktop)

### Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd skillflow-mcp

# Install dependencies
uv sync
```

## ⚙️ Configuration

### Claude Desktop Setup

Edit your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

Add SkillFlow server:

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/absolute/path/to/skillflow-mcp"
    }
  }
}
```

**Important**: Replace `cwd` with the actual absolute path to skillflow-mcp.

## 🚀 Quick Start

### Basic Workflow

1. **Start Recording**
   ```
   Ask Claude: "Please start recording with session name 'my_workflow'"
   ```

2. **Execute Tool Calls**
   ```
   Perform your multi-step operations through Claude
   ```

3. **Stop Recording**
   ```
   Ask Claude: "Please stop recording"
   ```

4. **Create Skill**
   ```
   Ask Claude: "Create a skill from the last session"
   ```

5. **Execute Skill**
   ```
   Ask Claude: "Execute skill__my_workflow"
   ```

### Example: File Backup Automation

```
1. Start recording: "Start recording session 'backup_docs'"

2. Execute operations:
   - List all .txt files in Documents
   - Read the first file
   - Copy content to backup directory

3. Stop recording: "Stop recording"

4. Create skill: "Create skill 'backup_first_txt' from last session"

5. Use skill: "Execute skill__backup_first_txt"
```

## 📖 Available Tools

### Recording Control
- `start_recording` - Start a new recording session
- `stop_recording` - Stop current recording session

### Skill Management
- `create_skill_from_session` - Convert recording to skill
- `list_skills` - List all available skills
- `get_skill` - Get skill details
- `delete_skill` - Delete a skill

### Execution Control
- `skill__<id>` - Execute a specific skill (auto-generated for each skill)
- `get_run_status` - Check execution status
- `cancel_run` - Cancel running execution

### Upstream Server Management
- `register_upstream_server` - Register an MCP server
- `list_upstream_servers` - List registered servers
- `disconnect_server` - Disconnect from a server

### Upstream Resources & Prompts
- `list_upstream_resources` - List resources from upstream servers
- `read_upstream_resource` - Read a specific resource
- `list_upstream_prompts` - List available prompts
- `get_upstream_prompt` - Retrieve a prompt template

### Debug Tools
- `debug_recording_session` - Analyze recording data
- `debug_skill_definition` - Inspect skill structure
- `debug_skill_execution` - Trace execution flow
- `debug_upstream_tools` - Test upstream server connectivity

## 🏗️ Architecture

### Core Components

```
src/skillflow/
├── schemas.py          # Pydantic data models
├── storage.py          # JSON storage layer
├── skills.py           # Skill management
├── recording.py        # Recording manager
├── engine.py           # Execution engine (DAG, concurrency)
├── mcp_clients.py      # Upstream MCP client manager
├── native_mcp_client.py # Native MCP client implementation
├── tool_naming.py      # Smart tool naming strategy
└── server.py           # MCP server implementation
```

### Data Flow

```
Recording Flow:
start_recording() → RecordingSession → Log tool calls → stop_recording() → Save to data/sessions/

Skill Creation Flow:
create_skill_from_session() → Load session → Generate SkillGraph (nodes + edges)
→ Apply parameter templates → Save to data/skills/ → Register as MCP tool

Skill Execution Flow:
skill__<id>(inputs) → ExecutionEngine.run_skill() → Parse DAG, topological sort
→ Execute nodes (sequential/phased/parallel) → Call upstream tools
→ Record execution to data/runs/ → Return SkillRunResult
```

## 🎨 Use Cases

### 1. Workflow Automation
Record repetitive multi-step operations and execute them with one command.

### 2. Workflow Orchestration
Combine tools from multiple MCP servers into complex workflows.

### 3. Batch Processing
Execute multiple independent tasks in parallel (batch downloads, processing).

### 4. Skill Library
Share common automation skills across your team.

### 5. CI/CD Integration
Integrate skills into automated deployment pipelines.

## 🔧 Advanced Configuration

### Concurrency Modes

When creating skills, you can specify execution strategy:

```python
create_skill_from_session({
  "session_id": "...",
  "skill_id": "parallel_fetch",
  "name": "Parallel Data Fetch",
  "concurrency_mode": "full_parallel",  # sequential | phased | full_parallel
  "max_parallel": 5  # Limit concurrent executions
})
```

### Phased Execution

Define execution phases for grouped parallelism:

```python
create_skill_from_session({
  "session_id": "...",
  "concurrency_mode": "phased",
  "concurrency_phases": {
    "phase1": ["step_1", "step_2"],  # Execute in parallel
    "phase2": ["step_3", "step_4"]   # Execute after phase1
  }
})
```

## 📚 Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [Usage Guide](docs/USAGE_GUIDE.md)
- [Project Summary](docs/PROJECT_SUMMARY.md)
- [Upstream Tools Proxy](docs/UPSTREAM_TOOLS_PROXY.md)
- [Native MCP Client](docs/NATIVE_MCP_CLIENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING_PROXY_TOOLS.md)
- [Changelog](CHANGELOG.md)

For Traditional Chinese documentation, see [README_ZH.md](README_ZH.md).

## 🛠️ Development

### Run Tests

```bash
uv run pytest tests/ -v
```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public APIs

## 🗺️ Roadmap

### Phase 2: Transport Layer
- [ ] HTTP+SSE transport support
- [ ] WebSocket transport support

### Phase 3: Advanced Features
- [ ] Skill nesting and composition
- [ ] Conditional nodes (if/else/switch)
- [ ] Loop nodes (for/while)
- [ ] Parameter transformation expressions (JSONPath, Jinja2)

### Phase 4: Enterprise Features
- [ ] Multi-tenancy support
- [ ] Permissions and access control
- [ ] Skill marketplace and sharing
- [ ] Audit logs

### Phase 5: User Experience
- [ ] Web UI control panel
- [ ] Visual DAG editor
- [ ] Execution monitoring dashboard
- [ ] Skill debugging tools

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Submit a Pull Request

### Testing Requirements
- New features must include tests
- Maintain test coverage > 80%

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Astral uv](https://github.com/astral-sh/uv)
- [Pydantic](https://docs.pydantic.dev/)
- All contributors

## 📊 Project Status

✅ **MVP Complete** - Ready for production testing

**Last Updated**: 2025-11-16
**Maintainer**: SkillFlow Team

---

**Start automating your workflows today!** 🚀
