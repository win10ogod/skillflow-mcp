# Claude Code Configuration Guide

This guide explains how to set up SkillFlow MCP server with Claude Code (both Desktop and CLI versions).

## What is Claude Code?

Claude Code is an AI-powered coding assistant that uses the Model Context Protocol (MCP) to connect to external tools and services. SkillFlow MCP server provides powerful workflow automation capabilities to Claude Code.

## Configuration Format

Claude Code uses the standard MCP configuration format defined in `claude_desktop_config.json` (for Claude Desktop) or MCP client configuration files.

### Basic Configuration

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/absolute/path/to/skillflow-mcp",
      "env": {}
    }
  }
}
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | ✅ | Command to run the MCP server (`uv` for SkillFlow) |
| `args` | array | ✅ | Command arguments (`["run", "skillflow"]`) |
| `cwd` | string | ✅ | Absolute path to the skillflow-mcp directory |
| `env` | object | ❌ | Environment variables (optional) |

## Platform-Specific Setup

### macOS

**Configuration file location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Steps:**

1. Open Terminal
2. Navigate to your SkillFlow directory:
   ```bash
   cd /path/to/skillflow-mcp
   ```
3. Get the absolute path:
   ```bash
   pwd
   ```
4. Edit Claude Desktop config:
   ```bash
   code ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
5. Add the SkillFlow server configuration (replace `<PATH>` with your actual path):
   ```json
   {
     "mcpServers": {
       "skillflow": {
         "command": "uv",
         "args": ["run", "skillflow"],
         "cwd": "<PATH>/skillflow-mcp"
       }
     }
   }
   ```
6. Restart Claude Desktop

### Windows

**Configuration file location:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Steps:**

1. Open Command Prompt or PowerShell
2. Navigate to your SkillFlow directory:
   ```cmd
   cd C:\path\to\skillflow-mcp
   ```
3. Get the absolute path:
   ```cmd
   cd
   ```
4. Edit Claude Desktop config:
   ```cmd
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```
5. Add the SkillFlow server configuration (replace `<PATH>` with your actual path):
   ```json
   {
     "mcpServers": {
       "skillflow": {
         "command": "uv",
         "args": ["run", "skillflow"],
         "cwd": "C:\\path\\to\\skillflow-mcp"
       }
     }
   }
   ```
   **Note:** Use double backslashes (`\\`) in Windows paths.
6. Restart Claude Desktop

### Linux

**Configuration file location:**
```
~/.config/Claude/claude_desktop_config.json
```

**Steps:**

1. Open Terminal
2. Navigate to your SkillFlow directory:
   ```bash
   cd /path/to/skillflow-mcp
   ```
3. Get the absolute path:
   ```bash
   pwd
   ```
4. Edit Claude Desktop config:
   ```bash
   nano ~/.config/Claude/claude_desktop_config.json
   ```
5. Add the SkillFlow server configuration (replace `<PATH>` with your actual path):
   ```json
   {
     "mcpServers": {
       "skillflow": {
         "command": "uv",
         "args": ["run", "skillflow"],
         "cwd": "<PATH>/skillflow-mcp"
       }
     }
   }
   ```
6. Restart Claude Desktop

## Verification

After setting up the configuration, verify that SkillFlow is working:

### Method 1: Using Claude Desktop

1. Open Claude Desktop
2. Start a new conversation
3. Ask Claude: "What tools do you have available from SkillFlow?"
4. You should see tools like:
   - `start_recording` - Start recording tool calls
   - `stop_recording` - Stop recording
   - `list_skills` - List available skills
   - `skill__*` - Execution tools for each skill

### Method 2: Using Test Script

Run the provided test script to verify the server:

```bash
cd /path/to/skillflow-mcp
uv run python test_mcp_client.py
```

Expected output:
```
================================================================================
SkillFlow MCP Server Test
================================================================================

📡 Connecting to SkillFlow MCP server...
✅ Connection initialized successfully

📋 Test 1: Listing all available tools
--------------------------------------------------------------------------------
✅ Found 29 tools:
  📹 Recording Tools (3)
  ⚡ Skill Execution Tools (2)
  🐛 Debug Tools (5)
  💾 Cache Management Tools (4)
  🔧 Other Tools (15)

🎉 All tests passed! MCP server is working correctly.
```

## Available Tools

Once configured, SkillFlow provides these categories of tools to Claude Code:

### 📹 Recording Tools
- `start_recording` - Start recording tool calls
- `stop_recording` - Stop active recording
- `list_recording_sessions` - List all sessions

### ⚙️ Skill Management
- `create_skill_from_session` - Convert recording to reusable skill
- `list_skills` - List all available skills
- `get_skill` - Get detailed skill information
- `delete_skill` - Delete a skill

### ⚡ Skill Execution
- `skill__<id>` - Execute a specific skill (auto-generated for each skill)

### 🔗 Upstream Server Management
- `register_upstream_server` - Register another MCP server
- `list_upstream_servers` - List registered servers
- `list_upstream_resources` - List resources from upstream servers
- `read_upstream_resource` - Read a resource
- `list_upstream_prompts` - List available prompts
- `get_upstream_prompt` - Get a prompt template

### 🐛 Debug Tools
- `debug_upstream_tools` - Check upstream tool connectivity
- `debug_skill_tools` - Check skill registration
- `debug_skill_definition` - Inspect skill structure
- `debug_skill_execution` - Trace execution flow
- `debug_recording_session` - Analyze recording data

### 💾 Cache Management
- `get_cache_stats` - Get cache statistics
- `invalidate_cache` - Clear cache
- `refresh_upstream_tools` - Refresh tool list
- `get_skill_cache_stats` - Get skill cache stats
- `invalidate_skill_cache` - Clear skill cache
- `force_skill_reload` - Reload skills from disk
- `trigger_hot_reload` - Trigger hot-reload check

## Troubleshooting

### Issue: "Server not found" or "Connection failed"

**Solutions:**
1. Verify the `cwd` path is absolute and correct
2. Ensure `uv` is installed and in your PATH:
   ```bash
   uv --version
   ```
3. Install uv if missing:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
4. Check server logs in Claude Desktop (Help → View Logs)

### Issue: "No tools available"

**Solutions:**
1. Verify SkillFlow is installed:
   ```bash
   cd /path/to/skillflow-mcp
   uv sync
   ```
2. Test the server manually:
   ```bash
   uv run python test_mcp_client.py
   ```
3. Check if the server starts without errors:
   ```bash
   uv run skillflow
   ```
   (Press Ctrl+C to stop)

### Issue: "Module not found" errors

**Solutions:**
1. Reinstall dependencies:
   ```bash
   cd /path/to/skillflow-mcp
   uv sync
   ```
2. For advanced features, install optional dependencies:
   ```bash
   uv sync --extra full
   ```

### Issue: Skills not appearing

**Solutions:**
1. Check if skills exist:
   ```bash
   ls data/skills/
   ```
2. Trigger a hot-reload via Claude:
   "Please call the `trigger_hot_reload` tool"
3. Force skill reload:
   "Please call the `force_skill_reload` tool"

## Advanced Configuration

### Adding Environment Variables

You can pass environment variables to SkillFlow:

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/path/to/skillflow-mcp",
      "env": {
        "SKILLFLOW_LOG_LEVEL": "DEBUG",
        "SKILLFLOW_DATA_DIR": "/custom/data/path"
      }
    }
  }
}
```

### Multiple MCP Servers

You can run SkillFlow alongside other MCP servers:

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/path/to/skillflow-mcp"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"
      }
    }
  }
}
```

## Bidirectional Communication

SkillFlow supports full bidirectional communication with Claude Code:

### Client → Server
- Tool calls (executing skills, recording, etc.)
- Resource requests (reading skill definitions)
- Prompt requests (getting help templates)

### Server → Client
- Tool results (skill execution results, logs)
- Resource content (skill definitions, session data)
- Prompt templates (guided workflows)
- Error messages and debugging information

### Verification

The test script (`test_mcp_client.py`) verifies bidirectional communication:
- ✅ Server can send responses (tool listing worked)
- ✅ Client can send requests (tool call worked)
- ✅ Bidirectional communication verified!

## Best Practices

1. **Use absolute paths**: Always use absolute paths for `cwd`
2. **Restart after config changes**: Restart Claude Desktop after editing config
3. **Test before using**: Run `test_mcp_client.py` to verify setup
4. **Monitor logs**: Check Claude Desktop logs if issues occur
5. **Keep updated**: Regularly update SkillFlow and uv

## Example Workflow

1. Configure SkillFlow in Claude Desktop
2. Restart Claude Desktop
3. Ask Claude: "Start recording with session name 'data_pipeline'"
4. Perform your workflow (e.g., API calls, data processing)
5. Ask Claude: "Stop recording"
6. Ask Claude: "Create a skill from the last session called 'process_data'"
7. Ask Claude: "Execute skill__process_data"

Your workflow is now automated! 🎉

## Support

For issues or questions:
- Check [Troubleshooting Guide](TROUBLESHOOTING_PROXY_TOOLS.md)
- Review [Project Documentation](../README.md)
- Run diagnostics: `uv run python test_mcp_client.py`
- File an issue on GitHub

## Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [SkillFlow Documentation](../README.md)
- [Usage Guide](USAGE_GUIDE.md)
- [Quick Start](QUICKSTART.md)
