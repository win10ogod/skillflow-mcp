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

#### Phase 2: Transport Layer Extensions ✅
- **HTTP+SSE Transport**: Connect to MCP servers via HTTP with Server-Sent Events
  - Real-time server-to-client notifications
  - RESTful tool invocation
  - Automatic reconnection handling
- **WebSocket Transport**: Full-duplex communication with MCP servers
  - JSON-RPC 2.0 protocol support
  - Ping/pong keepalive mechanism
  - Bidirectional message handling
- **Flexible Transport Selection**: Choose the best transport for your use case
  - stdio: Default, process-based communication
  - HTTP+SSE: Scalable, HTTP-based architecture
  - WebSocket: Real-time, persistent connections

#### Phase 3: Advanced Control Flow ✅
- **Conditional Nodes**: Dynamic branching logic in skills
  - **if/else**: Simple conditional execution
  - **switch**: Multi-branch conditional logic
  - Condition evaluation using JSONPath, Jinja2, or Python expressions
  - Default branch fallback support

- **Loop Nodes**: Iterate over data and repeat operations
  - **FOR loops**: Iterate over collections with JSONPath selection
  - **WHILE loops**: Conditional looping with dynamic evaluation
  - **FOR_RANGE loops**: Numeric range iteration
  - Safety limits with `max_iterations` to prevent infinite loops
  - Access loop variables: `$loop.item`, `$loop.index`

- **Skill Nesting**: Compose complex skills from simpler ones
  - Call skills within skills for modular design
  - Recursive execution with proper context isolation
  - Reuse existing skills as building blocks

- **Parameter Transformation**: Dynamic parameter generation
  - **JSONPath**: Extract and transform data from previous outputs
  - **Jinja2 Templates**: Generate complex parameters with templating
  - Context-aware transformations with access to inputs, outputs, and loop variables
  - Template variables: `$inputs.field`, `@step_id.outputs.field`, `$loop.var_name`

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

# Install base dependencies
uv sync

# Optional: Install advanced features
uv sync --extra http          # HTTP+SSE transport support
uv sync --extra websocket     # WebSocket transport support
uv sync --extra transforms    # JSONPath & Jinja2 parameter transformations
uv sync --extra full          # All advanced features
```

### Optional Dependencies

- **http** (`aiohttp>=3.9.0`): HTTP+SSE transport for upstream MCP servers
- **websocket** (`websockets>=12.0`): WebSocket transport for real-time communication
- **transforms** (`jsonpath-ng>=1.6.0`, `jinja2>=3.1.0`): Advanced parameter transformations
- **full**: All optional dependencies combined

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
├── schemas.py              # Pydantic data models (extended for Phase 3)
├── storage.py              # JSON storage layer
├── skills.py               # Skill management
├── recording.py            # Recording manager
├── engine.py               # Execution engine (DAG, concurrency, Phase 3 features)
├── mcp_clients.py          # Upstream MCP client manager
├── native_mcp_client.py    # Native MCP client implementation (stdio)
├── http_sse_client.py      # HTTP+SSE transport client (Phase 2)
├── websocket_client.py     # WebSocket transport client (Phase 2)
├── parameter_transform.py  # JSONPath & Jinja2 transformations (Phase 3)
├── tool_naming.py          # Smart tool naming strategy
└── server.py               # MCP server implementation
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

### Phase 3 Advanced Examples

#### Conditional Nodes

Create skills with conditional logic:

```json
{
  "node": {
    "id": "check_status",
    "kind": "conditional",
    "conditional_config": {
      "type": "if_else",
      "branches": [
        {
          "condition": "$.status == 'success'",
          "nodes": ["success_handler"],
          "description": "Handle success case"
        }
      ],
      "default_branch": ["error_handler"]
    }
  }
}
```

#### Loop Nodes

Iterate over collections or ranges:

```json
{
  "node": {
    "id": "process_items",
    "kind": "loop",
    "loop_config": {
      "type": "for",
      "collection_path": "$.items",
      "iteration_var": "current_item",
      "body_nodes": ["process_single_item"],
      "max_iterations": 100
    }
  }
}
```

#### Parameter Transformation

Use JSONPath to extract data:

```json
{
  "parameter_transform": {
    "engine": "jsonpath",
    "expression": "$.results[*].id"
  }
}
```

Use Jinja2 templates for complex transformations:

```json
{
  "parameter_transform": {
    "engine": "jinja2",
    "expression": "{{ value | upper }} - {{ loop.index }}"
  }
}
```

#### Template Variables

Access context in your skill parameters:

- `$inputs.field_name` - Access skill input parameters
- `@step_id.outputs.field` - Access outputs from previous steps
- `$loop.item` - Current loop item
- `$loop.index` - Current loop iteration index

Example:
```json
{
  "args_template": {
    "user_id": "$inputs.user_id",
    "previous_result": "@fetch_data.outputs.result",
    "item_name": "$loop.item.name"
  }
}
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

### Phase 2: Transport Layer ✅ COMPLETE
- ✅ HTTP+SSE transport support
- ✅ WebSocket transport support
- ✅ Flexible transport selection for upstream servers

### Phase 3: Advanced Features ✅ COMPLETE
- ✅ Skill nesting and composition
- ✅ Conditional nodes (if/else/switch)
- ✅ Loop nodes (for/while/for_range)
- ✅ Parameter transformation expressions (JSONPath, Jinja2)
- ✅ Enhanced template variables ($inputs, @outputs, $loop)

### Phase 4: Enterprise Features
- [ ] Multi-tenancy support
- [ ] Permissions and access control
- [ ] Skill marketplace and sharing
- [ ] Audit logs
- [ ] Advanced monitoring and metrics

### Phase 5: User Experience
- [ ] Web UI control panel
- [ ] Visual DAG editor
- [ ] Execution monitoring dashboard
- [ ] Skill debugging tools
- [ ] Interactive skill builder

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
