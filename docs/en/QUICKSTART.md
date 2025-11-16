# Quick Start Guide

Get up and running with SkillFlow MCP in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`
- Git

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd skillflow-mcp
```

### 2. Install Dependencies

#### Option A: Full Installation (Recommended)

```bash
uv sync --extra full
```

This installs all features including:
- Core MCP functionality
- HTTP/WebSocket transport
- Advanced transformations (JSONPath, Jinja2)
- Web UI with monitoring

#### Option B: Basic Installation

```bash
uv sync
```

Core features only (MCP server, skill recording, DAG execution).

#### Option C: Web UI Only

```bash
uv sync --extra web
```

## Quick Start Options

### Option 1: MCP Server Mode (Claude Desktop Integration)

#### Configure Claude Desktop

Add to your `claude_desktop_config.json`:

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

#### Start Claude Desktop

Restart Claude Desktop. SkillFlow will be available as an MCP server with all skill tools.

### Option 2: Standalone Web UI

#### Start the Web Server

```bash
uv run skillflow-web
```

Or with custom configuration:

```bash
uv run skillflow-web --host 0.0.0.0 --port 8080 --data-dir ./data
```

#### Access the Web UI

Open your browser to: http://localhost:8080

Available pages:
- **Dashboard** (`/`) - System overview and metrics
- **Skills** (`/skills`) - Manage all skills
- **DAG Editor** (`/editor`) - Visual skill editor
- **Advanced Editor** (`/editor-advanced`) - Node-based editor with drag-drop
- **Monitoring** (`/monitoring`) - Execution monitoring
- **Enhanced Monitoring** (`/monitoring-v2`) - Real-time charts and analytics
- **Debug Tools** (`/debug`) - Skill debugging
- **Skill Builder** (`/builder`) - Step-by-step skill creation

## Your First Skill

### Using Claude Desktop (MCP Mode)

#### 1. Start Recording

In Claude, say:
```
Start recording a session called 'hello_world'
```

#### 2. Perform Actions

Execute the actions you want to automate:
```
Use the filesystem tool to create a file called test.txt with content "Hello World"
```

#### 3. Stop Recording

```
Stop recording
```

#### 4. Create Skill

```
Create a skill from the last session
```

#### 5. Execute Skill

```
Execute skill__hello_world
```

### Using Web UI

#### 1. Open Skill Builder

Navigate to http://localhost:8080/builder

#### 2. Create a Simple Skill

- Click "Add Node"
- Select node type: `tool_call`
- Configure:
  - Tool name: `filesystem__write_file`
  - Arguments: `{"path": "test.txt", "content": "Hello World"}`
- Click "Save Skill"

#### 3. Execute from Skills Page

- Go to `/skills`
- Find your skill
- Click "Execute"

## Next Steps

- [User Guide](USER_GUIDE.md) - Complete feature documentation
- [API Reference](API_REFERENCE.md) - REST API documentation
- [Examples](EXAMPLES.md) - More complex examples
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues

## Common Commands

```bash
# Start MCP server
uv run skillflow

# Start Web UI
uv run skillflow-web

# Start with custom port
uv run skillflow-web --port 3000

# Run tests
pytest tests/

# Check version
uv run python -c "import skillflow; print(skillflow.__version__)"
```

## Getting Help

- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Review [Architecture Documentation](ARCHITECTURE.md)
- See [API Reference](API_REFERENCE.md)

## What's Next?

- Explore **advanced features** like conditionals, loops, and nested skills
- Set up **MCP server testing** via the Web UI
- Configure **custom MCP servers** to extend functionality
- Learn about **parameter transformations** with JSONPath and Jinja2
- Monitor your skills with **real-time metrics** and **audit logs**

---

**Happy automating with SkillFlow! 🚀**
