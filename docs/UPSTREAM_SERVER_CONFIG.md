# Upstream Server Configuration Guide

This guide explains how to configure upstream MCP servers in SkillFlow using the standard Claude Code/Claude Desktop MCP configuration format.

## Overview

SkillFlow now supports **standard Claude Code MCP configuration format** for upstream servers. This means you can:

1. ✅ Copy-paste server configurations directly from your Claude Desktop config
2. ✅ Use the same format across all your MCP tools
3. ✅ Avoid learning a new configuration syntax
4. ✅ Maintain compatibility with the MCP ecosystem

## Supported Formats

SkillFlow automatically detects and supports multiple configuration formats:

### 1. Claude Code/Claude Desktop Standard Format ⭐ **Recommended**

This is the standard format used by Claude Desktop and Claude Code CLI:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

### 2. Nested Claude Code Format

Alternative format with servers under a "servers" key:

```json
{
  "servers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

### 3. SkillFlow Internal Format (Legacy)

SkillFlow's original format with additional metadata:

```json
{
  "servers": {
    "server-name": {
      "server_id": "server-name",
      "name": "Display Name",
      "transport": "stdio",
      "config": {
        "command": "command-to-run",
        "args": ["arg1", "arg2"],
        "env": {"ENV_VAR": "value"}
      },
      "enabled": true,
      "metadata": {
        "description": "Server description",
        "version": "1.0.0"
      }
    }
  }
}
```

## Configuration File Location

Place your upstream server configuration at:
```
data/registry/servers.json
```

SkillFlow will automatically detect the format and convert if necessary.

## Quick Start Examples

### Example 1: Official MCP Servers

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/directory"
      ]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"
      }
    },
    "puppeteer": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-puppeteer"
      ]
    }
  }
}
```

### Example 2: Custom Python MCP Server

```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "env": {
        "LOG_LEVEL": "INFO",
        "DATA_DIR": "/path/to/data"
      }
    }
  }
}
```

### Example 3: UV-based Server

```json
{
  "mcpServers": {
    "my-uv-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/server",
        "run",
        "main.py"
      ],
      "env": {
        "SERVER_CONFIG": "production"
      }
    }
  }
}
```

### Example 4: Mixed Format (Advanced)

You can mix Claude Code format with SkillFlow format for servers that need extra metadata:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "custom-server": {
      "server_id": "custom-server",
      "name": "My Custom Server",
      "transport": "stdio",
      "config": {
        "command": "python",
        "args": ["-m", "my_server"]
      },
      "enabled": true,
      "metadata": {
        "description": "Custom server with metadata",
        "version": "2.0.0",
        "author": "Your Name"
      }
    }
  }
}
```

## How It Works

### Automatic Format Detection

When SkillFlow loads `data/registry/servers.json`:

1. **Detects** the configuration format automatically
2. **Converts** Claude Code format to internal format if needed
3. **Saves** the converted format back to disk (preserving full metadata)
4. **Uses** the internal format for server management

### Format Conversion

The conversion process:

```
Claude Code Format       SkillFlow Internal Format
─────────────────   →   ──────────────────────────
{                       {
  "mcpServers": {         "servers": {
    "test": {               "test": {
      "command": "npx",       "server_id": "test",
      "args": [...]           "name": "test",
    }                         "transport": "stdio",
  }                           "config": {
}                               "command": "npx",
                                "args": [...]
                              },
                              "enabled": true,
                              "metadata": {}
                            }
                          }
                        }
```

## Configuration Fields

### Required Fields (Claude Code Format)

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | Command to execute (e.g., `"npx"`, `"python"`, `"uv"`) |
| `args` | array | Command arguments |

### Optional Fields (Claude Code Format)

| Field | Type | Description |
|-------|------|-------------|
| `env` | object | Environment variables (use `null` for no env vars) |

### Additional Fields (SkillFlow Format)

| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | Unique server identifier |
| `name` | string | Display name |
| `transport` | string | Transport type (`stdio`, `http_sse`, `websocket`) |
| `enabled` | boolean | Enable/disable server |
| `metadata` | object | Custom metadata (description, version, etc.) |

## Transport Types

SkillFlow automatically detects transport types:

- **stdio**: Standard input/output (default)
- **http_sse**: HTTP with Server-Sent Events
- **websocket**: WebSocket connection

Detection logic:
- Commands containing "http" and "sse" → `http_sse`
- Commands containing "ws" or "websocket" → `websocket`
- Everything else → `stdio` (default)

## Managing Servers

### Via Configuration File

1. Edit `data/registry/servers.json`
2. Add your servers in Claude Code format
3. Restart SkillFlow (or trigger hot-reload)

### Via MCP Tools

Register servers dynamically using the `register_upstream_server` tool:

```json
{
  "server_id": "new-server",
  "name": "New Server",
  "transport": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-example"]
  }
}
```

List registered servers:
```json
{
  "tool": "list_upstream_servers"
}
```

## Testing Your Configuration

### Method 1: Run Converter Tests

```bash
uv run python test_config_converter.py
```

This tests:
- ✅ Format detection
- ✅ Claude Code → SkillFlow conversion
- ✅ SkillFlow → Claude Code conversion
- ✅ Round-trip conversion
- ✅ Example configuration files

### Method 2: Test Server Connectivity

Use the `debug_upstream_tools` tool to verify servers are connecting:

Ask Claude (via SkillFlow):
```
Please call debug_upstream_tools to check if my upstream servers are working
```

### Method 3: List Proxied Tools

Check if tools from upstream servers are available:

```bash
uv run python test_mcp_client.py
```

Look for tools with `up_<server>_<toolname>` prefix.

## Troubleshooting

### Issue: "Unknown configuration format"

**Cause**: Configuration file doesn't match any supported format

**Solution**:
1. Ensure you're using `mcpServers` or `servers` as the top-level key
2. Check JSON syntax (use a validator like jsonlint.com)
3. Verify command and args fields are present

### Issue: Servers not loading

**Cause**: Missing required fields or invalid configuration

**Solution**:
1. Run `uv run python test_config_converter.py` to validate format
2. Check logs in SkillFlow output for error messages
3. Ensure `command` field is present for each server
4. Verify paths are absolute and commands are in PATH

### Issue: Format converted but metadata lost

**Cause**: Claude Code format doesn't support metadata

**Solution**:
- Use SkillFlow format for servers requiring metadata
- Or use mixed format (see Example 4 above)
- SkillFlow preserves metadata when converting back

### Issue: Environment variables not working

**Cause**: `env` field is set to `null` or missing

**Solution**:
```json
{
  "mcpServers": {
    "myserver": {
      "command": "python",
      "args": ["-m", "server"],
      "env": {
        "MY_VAR": "value"
      }
    }
  }
}
```

## Migration Guide

### From SkillFlow Format to Claude Code Format

If you have existing servers in SkillFlow format and want to simplify:

**Before** (SkillFlow format):
```json
{
  "servers": {
    "test": {
      "server_id": "test",
      "name": "Test Server",
      "transport": "stdio",
      "config": {
        "command": "python",
        "args": ["-m", "test"]
      },
      "enabled": true,
      "metadata": {}
    }
  }
}
```

**After** (Claude Code format):
```json
{
  "mcpServers": {
    "test": {
      "command": "python",
      "args": ["-m", "test"]
    }
  }
}
```

### From Claude Desktop to SkillFlow

Copy your servers from Claude Desktop config directly:

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
```

**SkillFlow** (`data/registry/servers.json`):
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
```

No changes needed! ✨

## Best Practices

1. **Use Claude Code format** for simplicity and portability
2. **Add metadata** only when you need extra information (version, description)
3. **Test configurations** with `test_config_converter.py` before deploying
4. **Keep backups** of your configuration files
5. **Use absolute paths** for file system servers
6. **Store tokens** in environment variables, not directly in config
7. **Document** your custom servers in metadata fields

## Example Files

Check the `examples/` directory for reference configurations:

- `upstream_servers_claude_code_format.json` - Standard Claude Code format
- `upstream_servers_mixed_format.json` - Mixed format with metadata
- `example_server_config.json` - Legacy SkillFlow format

## Additional Resources

- [Claude Code Setup Guide](CLAUDE_CODE_SETUP.md)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)

## Support

For issues or questions:
- Run tests: `uv run python test_config_converter.py`
- Check connectivity: Use `debug_upstream_tools` tool
- Review logs: Check SkillFlow server output
- File issues: GitHub repository
