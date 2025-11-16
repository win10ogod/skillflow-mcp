# SkillFlow Usage Guide

This guide provides detailed instructions on how to use SkillFlow MCP Server to record, create, and execute skills.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Basic Workflow](#basic-workflow)
3. [Advanced Features](#advanced-features)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)

## Environment Setup

### Install SkillFlow

```bash
cd skillflow-mcp
uv sync
```

### Configure MCP Client

Add to Claude Desktop configuration file:

**macOS/Linux**: `~/.config/claude/config.json`
**Windows**: `%APPDATA%\Claude\config.json`

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/path/to/skillflow-mcp"
    }
  }
}
```

### Verify Installation

Restart Claude Desktop, then type in the conversation:

```
Please list all available MCP tools
```

You should see SkillFlow's tools, including:
- `start_recording`
- `stop_recording`
- `list_skills`
- And more

## Basic Workflow

### Scenario: Automate "Open Notepad and Type Text"

#### Step 1: Register Upstream MCP Server

Assuming you have an MCP server that provides OS operation tools:

```
Please help me register an MCP server:
- server_id: os-tools
- name: OS Automation Tools
- transport: stdio
- config:
  - command: python
  - args: ["-m", "os_automation_mcp"]
```

SkillFlow will call the `register_upstream_server` tool.

#### Step 2: Start Recording

```
Please start recording, session name "notepad_demo"
```

SkillFlow calls `start_recording(session_name="notepad_demo")` and returns a session ID.

#### Step 3: Execute Tool Calls

In recording mode, execute the operations you want to automate:

```
Please use os-tools to perform the following operations:
1. Open Notepad application
2. Focus on Notepad window
3. Type text "Hello from SkillFlow!"
```

These tool calls will be automatically recorded in the session.

#### Step 4: Stop Recording

```
Please stop recording
```

SkillFlow calls `stop_recording()`, and the session is saved.

#### Step 5: Create Skill

```
Please create a skill from the recent session:
- skill_id: open_notepad_and_type
- name: Open Notepad and Type Text
- description: Automatically open Notepad and type custom text
- tags: ["windows", "notepad", "automation"]
- Expose the text parameter from step 3 as skill input
```

SkillFlow will:
1. Read the session
2. Generate skill draft
3. Convert specified parameters to templates
4. Save the skill

#### Step 6: Use the Skill

After creation, the skill is automatically registered as an MCP tool:

```
Please use the skill__open_notepad_and_type skill with text "This is an automation test"
```

SkillFlow will execute the entire tool chain.

## Advanced Features

### Parallel Execution

#### Define Parallel Phases

If your skill contains steps that can be executed in parallel, you can manually edit after creation:

```json
{
  "graph": {
    "concurrency": {
      "mode": "phased",
      "phases": {
        "1": ["download_file_1", "download_file_2", "download_file_3"],
        "2": ["process_all_files"],
        "3": ["upload_results"]
      }
    }
  }
}
```

#### Full Parallel Mode

Set `"mode": "full_parallel"`, and SkillFlow will automatically analyze dependencies and maximize parallelism.

### Error Handling

#### Configure Retry

Add retry strategy for specific nodes in the skill definition:

```json
{
  "nodes": [
    {
      "id": "unreliable_api_call",
      "kind": "tool_call",
      "server": "api-tools",
      "tool": "call_api",
      "error_strategy": "retry",
      "retry_config": {
        "max_retries": 5,
        "backoff_ms": 2000,
        "backoff_multiplier": 2.0
      }
    }
  ]
}
```

#### Skip Failed Nodes

```json
{
  "error_strategy": "skip_dependents"
}
```

On failure, only dependent nodes will be skipped; other independent nodes continue execution.

### Advanced Parameter Templates

#### Nested Parameter References

```json
{
  "args_template": {
    "config": {
      "endpoint": "$inputs.api_endpoint",
      "auth_token": "@step_auth.outputs.token",
      "retry_count": 3
    }
  }
}
```

#### JSONPath Output Extraction

```json
{
  "export_outputs": {
    "user_id": "$.response.data.user.id",
    "session_token": "$.response.headers.authorization"
  }
}
```

### Skill Version Management

#### Update Skills

When you modify a skill, SkillFlow automatically creates a new version:

```python
# Load existing skill
skill = await skill_manager.get_skill("my_skill")

# Modify and update
updated_skill = await skill_manager.update_skill(
    skill_id="my_skill",
    description="Updated description",
    # Other modifications...
)
# Version automatically increments from v1 -> v2
```

#### Use Specific Version

```
Please get information for version 1 of my_skill
```

```python
get_skill(skill_id="my_skill", version=1)
```

### Query Execution Status

For long-running skills:

```python
# Get execution status
get_run_status(run_id="run_abc123")
```

Returns:
```json
{
  "run_id": "run_abc123",
  "skill_id": "long_running_skill",
  "status": "running",
  "total_nodes": 10,
  "completed_nodes": 7,
  "failed_nodes": 0,
  "node_statuses": {
    "step_1": "success",
    "step_2": "success",
    ...
    "step_8": "running"
  }
}
```

### Cancel Execution

```python
cancel_run(run_id="run_abc123")
```

## Best Practices

### 1. Skill Design Principles

#### Keep Skills Single-Responsibility

❌ Bad example:
```
skill_id: "do_everything"
- Download files
- Process data
- Send emails
- Clean cache
```

✅ Good example:
```
skill_id: "download_and_process_data"
- Download files
- Process data

skill_id: "send_report_email"
- Send emails
```

#### Use Meaningful IDs and Names

```json
{
  "id": "fetch_stock_prices_and_analyze",
  "name": "Fetch Stock Prices and Analyze",
  "description": "Fetch stock prices from API, calculate moving averages, and generate report"
}
```

### 2. Parameter Design

#### Provide Clear Parameter Descriptions

```json
{
  "inputs_schema": {
    "type": "object",
    "properties": {
      "stock_symbol": {
        "type": "string",
        "description": "Stock symbol (e.g., AAPL, GOOGL)"
      },
      "days": {
        "type": "integer",
        "description": "Number of days to analyze (1-365)",
        "minimum": 1,
        "maximum": 365
      }
    }
  }
}
```

#### Set Reasonable Defaults

Provide default values for optional parameters in args_template.

### 3. Error Handling

#### Set Retry for Critical Nodes

For network requests, external API calls, and other unstable operations, use the `retry` strategy.

#### Use Appropriate Error Strategies

- Data validation: `fail_fast`
- Optional steps: `skip_dependents`
- Notification steps: `continue`

### 4. Performance Optimization

#### Identify Parallelizable Steps

```json
{
  "concurrency": {
    "mode": "phased",
    "phases": {
      "1": ["fetch_data_source_a", "fetch_data_source_b", "fetch_data_source_c"],
      "2": ["merge_data"],
      "3": ["analyze_merged_data"]
    }
  }
}
```

#### Set Reasonable Concurrency Limits

Set `max_parallel` in skills to avoid resource exhaustion.

### 5. Documentation and Maintenance

#### Use Tags to Organize Skills

```json
{
  "tags": ["automation", "data-processing", "api", "daily-task"]
}
```

#### Record Additional Information in Metadata

```json
{
  "metadata": {
    "author_email": "user@example.com",
    "created_date": "2025-01-16",
    "dependencies": ["os-tools", "api-client"],
    "notes": "Requires API key configuration"
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Skill Execution Fails: Upstream Server Not Found

**Error Message**: `Server os-tools not found in registry`

**Solution**:
```
Please list all registered upstream servers
```

If the server is not registered, use `register_upstream_server` to register it.

#### 2. Parameter Template Resolution Error

**Error Message**: `Failed to resolve template: @step_xyz.outputs.field`

**Causes**:
- Typo in node ID
- Preceding node did not execute successfully
- Output field does not exist

**Solution**:
1. Check node IDs in skill definition
2. Review execution logs to confirm preceding node outputs
3. Use `get_run_status` to view detailed status

#### 3. Recorded Tool Calls Not Being Logged

**Causes**:
- Recording not started
- Tool calls not made through SkillFlow proxy

**Solution**:
- Confirm `start_recording` was called
- Confirm tools are called through registered upstream servers

#### 4. Skill Creation Fails: Parameter Extraction Error

**Error Message**: `Invalid source_path: logs[5].args.text`

**Causes**:
- Session does not have a 5th tool call
- Path format is incorrect

**Solution**:
```
Please get detailed information for session <session_id>
```

Review the actual logs structure and adjust `source_path`.

### Debugging Tips

#### 1. View Execution Logs

```bash
# In data/runs/<date>/<run_id>.jsonl
cat data/runs/2025-01-16/run_abc123.jsonl | jq
```

#### 2. Manually Test Tool Calls

Before creating skills, manually test each tool call to ensure they work properly.

#### 3. Build Skills Incrementally

Start with simple 2-3 step skills, validate, then add more steps.

#### 4. Use Test Data

Validate skills with test data before using in production.

## Next Steps

- Explore [API Reference Documentation](API_REFERENCE.md)
- View [Example Skills](../examples/)
- Read [Architecture Design Documentation](ARCHITECTURE.md)

---

Have questions? Ask on [GitHub Issues](https://github.com/your-repo/skillflow-mcp/issues).
