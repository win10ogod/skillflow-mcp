# SkillFlow Installation Guide

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- MCP-compatible client (Claude Desktop, Claude Code, etc.)

## Installation Steps

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install SkillFlow

```bash
# Navigate to skillflow-mcp directory
cd skillflow-mcp

# Install dependencies
uv sync
```

### 3. Verify Installation

```bash
# Test the server (will timeout - that's expected)
timeout 2 uv run skillflow || echo "OK"

# Should see no error messages
```

## Configuration

### For Claude Desktop

Edit your Claude Desktop configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/skillflow-mcp", "skillflow"],
      "cwd": "/ABSOLUTE/PATH/TO/skillflow-mcp"
    }
  }
}
```

**Important:** Replace `/ABSOLUTE/PATH/TO/skillflow-mcp` with the actual absolute path to your skillflow-mcp directory.

### For Claude Code

Create or edit `.claude/mcp_settings.json` in your workspace:

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/ABSOLUTE/PATH/TO/skillflow-mcp"
    }
  }
}
```

## Verify Configuration

### 1. Restart Claude Desktop/Code

After updating the configuration, restart your MCP client.

### 2. Check MCP Status

In Claude Code, run:
```
/mcp list
```

You should see `skillflow` in the list of connected servers.

### 3. Test a Tool

Try listing skills:
```
Please use the list_skills tool
```

If successful, you should see an empty list (since no skills have been created yet).

## Troubleshooting

### Server Won't Start

**Check logs:**
- **macOS:** `~/Library/Logs/Claude/mcp*.log`
- **Windows:** `%APPDATA%\Claude\logs\mcp*.log`
- **Linux:** `~/.local/state/claude/logs/mcp*.log`

**Common issues:**

1. **Path not absolute**
   - Error: `No such file or directory`
   - Solution: Use full absolute path in configuration

2. **uv not in PATH**
   - Error: `command not found: uv`
   - Solution: Run `source ~/.bashrc` or restart terminal

3. **Python version**
   - Error: `requires-python >=3.11`
   - Solution: Install Python 3.11+

### Import Errors

If you see `ModuleNotFoundError`:

```bash
cd skillflow-mcp
uv sync --reinstall
```

### Permission Issues

On Unix systems:

```bash
chmod +x .venv/bin/skillflow
```

## Development Installation

For development with testing:

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest tests/ -v
```

## Uninstallation

To remove SkillFlow:

1. Remove the `skillflow` entry from your MCP client configuration
2. Delete the `skillflow-mcp` directory
3. (Optional) Remove uv if no longer needed:
   ```bash
   rm -rf ~/.cargo/bin/uv
   ```

## Next Steps

- Read [QUICKSTART.md](docs/QUICKSTART.md) for your first skill
- Explore [USAGE_GUIDE.md](docs/USAGE_GUIDE.md) for detailed features
- Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command reference

## Support

- Check [GitHub Issues](https://github.com/your-repo/skillflow-mcp/issues)
- Read troubleshooting in [USAGE_GUIDE.md](docs/USAGE_GUIDE.md#故障排除)
- Review examples in `examples/` directory
