# SkillFlow Quick Start

Get started with SkillFlow in 5 minutes!

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- MCP client (e.g., Claude Desktop)

## Installation

```bash
# 1. Clone or download SkillFlow
git clone <repository-url>
cd skillflow-mcp

# 2. Install dependencies
uv sync
```

## Configuration

### Configure in Claude Desktop

Edit the configuration file (location varies by operating system):

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

Add the SkillFlow server:

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

## Your First Skill: Hello World

### Step 1: Launch Claude Desktop

Restart Claude Desktop to load SkillFlow.

### Step 2: Verify Connection

In Claude's chat, type:

```
Please use the list_skills tool to list all skills
```

Should return an empty list (since you don't have any skills yet).

### Step 3: Manually Create a Simple Skill

Since we don't have upstream MCP servers yet, we can manually create an example skill file:

```bash
# Copy example skill to data directory
mkdir -p data/skills/hello_world
cp examples/example_skill.json data/skills/hello_world/v0001.json
```

Modify the example to create a simple "hello world" skill:

```json
{
  "id": "hello_world",
  "name": "Hello World Skill",
  "version": 1,
  "description": "A simple hello world skill for testing",
  "tags": ["example", "test"],
  "created_at": "2025-01-16T00:00:00Z",
  "updated_at": "2025-01-16T00:00:00Z",
  "author": {
    "workspace_id": "default",
    "client_id": "quickstart"
  },
  "inputs_schema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Your name"
      }
    },
    "required": ["name"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "message": {
        "type": "string"
      }
    }
  },
  "graph": {
    "nodes": [],
    "edges": [],
    "concurrency": {
      "mode": "sequential",
      "phases": {}
    }
  },
  "metadata": {
    "quickstart": true
  }
}
```

Create corresponding meta.json:

```json
{
  "id": "hello_world",
  "name": "Hello World Skill",
  "version": 1,
  "description": "A simple hello world skill for testing",
  "tags": ["example", "test"],
  "created_at": "2025-01-16T00:00:00Z",
  "updated_at": "2025-01-16T00:00:00Z",
  "author": {
    "workspace_id": "default",
    "client_id": "quickstart"
  }
}
```

### Step 4: Restart Claude Desktop

Restart to load the new skill.

### Step 5: List Skills

```
Please list all skills
```

You should see the `hello_world` skill.

## Real Scenario: Using MCP Servers

To create useful skills, you need upstream MCP servers. Here's a common example:

### Using the Filesystem MCP Server

1. **Install filesystem MCP server**:

```bash
npm install -g @modelcontextprotocol/server-filesystem
```

2. **Configure in Claude Desktop**:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]
    },
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/path/to/skillflow-mcp"
    }
  }
}
```

3. **Register in SkillFlow**:

```
Please help me register an upstream MCP server:
- server_id: filesystem
- name: File System Tools
- transport: stdio
- config:
  - command: npx
  - args: ["-y", "@modelcontextprotocol/server-filesystem", "/Users/myuser/Documents"]
```

4. **Start Recording**:

```
Please start recording, session name "file_backup"
```

5. **Execute Operations**:

```
Please use the filesystem server to execute the following operations:
1. List all .txt files in /Users/myuser/Documents directory
2. Read the content of the first file
3. Copy the content to the backup directory
```

6. **Stop Recording and Create Skill**:

```
Please stop recording

Then create a skill from the last session:
- skill_id: backup_first_txt_file
- name: Backup First Text File
- description: Find the first .txt file and back it up
- tags: ["filesystem", "backup"]
```

7. **Use the Skill**:

```
Please execute the skill__backup_first_txt_file skill
```

## Next Steps

- Read the [Complete Usage Guide](USAGE_GUIDE.md)
- Explore [Example Skills](../examples/)
- Learn about [Advanced Features](USAGE_GUIDE.md#advanced-features)

## FAQ

### Q: SkillFlow can't connect?

**A**: Check:
1. Is the `cwd` path correct (must be absolute path)?
2. Have you run `uv sync`?
3. Are there any errors in Claude Desktop logs?

### Q: How to view Claude Desktop logs?

**A**:
- **macOS**: `~/Library/Logs/Claude/mcp*.log`
- **Windows**: `%APPDATA%\Claude\logs\mcp*.log`

### Q: Skill won't execute?

**A**: Make sure:
1. Upstream MCP server is correctly registered
2. Upstream server is running
3. Tool names and parameters are correct

### Q: How to delete a skill?

**A**:
```
Please delete the skill hello_world
```

Or manually delete the `data/skills/hello_world` directory.

---

**Start creating your first automation skill!** 🚀
