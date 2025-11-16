# SkillFlow 快速參考

## 常用命令

### 安裝與設置
```bash
# 安裝依賴
uv sync

# 安裝開發依賴
uv sync --dev

# 運行測試
uv run pytest tests/ -v

# 啟動 server（本地測試）
uv run skillflow
```

### 文件結構
```
data/
├── skills/{skill_id}/      # 技能定義
│   ├── meta.json           # 元數據
│   └── v0001.json          # 版本 1
├── sessions/               # 錄製 Session
│   └── {session_id}.json
├── runs/{date}/            # 執行日誌
│   └── {run_id}.jsonl
└── registry/               # Server 註冊
    └── servers.json
```

## MCP 工具速查

### 錄製
| 工具 | 描述 | 參數 |
|------|------|------|
| `start_recording` | 開始錄製 | `session_name?` |
| `stop_recording` | 停止錄製 | - |
| `list_recording_sessions` | 列出 Session | - |

### 技能管理
| 工具 | 描述 | 參數 |
|------|------|------|
| `create_skill_from_session` | 創建技能 | `session_id`, `skill_id`, `name`, `description`, `tags?`, `expose_params?` |
| `list_skills` | 列出技能 | `query?`, `tags?` |
| `get_skill` | 獲取技能 | `skill_id`, `version?` |
| `delete_skill` | 刪除技能 | `skill_id`, `hard?` |

### 執行
| 工具 | 描述 | 參數 |
|------|------|------|
| `skill__<id>` | 執行技能 | 技能定義的輸入 |
| `get_run_status` | 查詢狀態 | `run_id` |
| `cancel_run` | 取消執行 | `run_id` |

### Server 管理
| 工具 | 描述 | 參數 |
|------|------|------|
| `register_upstream_server` | 註冊 Server | `server_id`, `name`, `transport`, `config` |
| `list_upstream_servers` | 列出 Server | - |

## JSON Schema 範例

### 技能輸入 Schema
```json
{
  "type": "object",
  "properties": {
    "param_name": {
      "type": "string",
      "description": "參數描述"
    }
  },
  "required": ["param_name"]
}
```

### Server 配置（stdio）
```json
{
  "server_id": "my-server",
  "name": "My Server",
  "transport": "stdio",
  "config": {
    "command": "python",
    "args": ["-m", "my_server"],
    "env": null
  }
}
```

### 參數暴露配置
```json
{
  "name": "text",
  "description": "要輸入的文字",
  "schema": {"type": "string"},
  "source_path": "logs[3].args.text"
}
```

## 參數模板語法

### 引用技能輸入
```json
{
  "args_template": {
    "field": "$inputs.param_name"
  }
}
```

### 引用前置節點輸出
```json
{
  "args_template": {
    "field": "@step_1.outputs.result_field"
  }
}
```

### 混合使用
```json
{
  "args_template": {
    "user_input": "$inputs.name",
    "previous_result": "@step_auth.outputs.token",
    "static_value": "constant"
  }
}
```

## 並行模式

### Sequential（順序）
```json
{
  "concurrency": {
    "mode": "sequential"
  }
}
```

### Phased（分階段）
```json
{
  "concurrency": {
    "mode": "phased",
    "phases": {
      "1": ["step_a", "step_b"],
      "2": ["step_c"]
    }
  }
}
```

### Full Parallel（完全並行）
```json
{
  "concurrency": {
    "mode": "full_parallel",
    "max_parallel": 10
  }
}
```

## 錯誤策略

### Fail Fast（預設）
```json
{
  "error_strategy": "fail_fast"
}
```

### 重試
```json
{
  "error_strategy": "retry",
  "retry_config": {
    "max_retries": 3,
    "backoff_ms": 1000,
    "backoff_multiplier": 2.0
  }
}
```

### 跳過依賴節點
```json
{
  "error_strategy": "skip_dependents"
}
```

### 繼續執行
```json
{
  "error_strategy": "continue"
}
```

## 常見工作流程

### 1. 錄製並創建技能
```
1. start_recording(session_name="my_workflow")
2. [執行一系列工具調用]
3. stop_recording()
4. create_skill_from_session(
     session_id="...",
     skill_id="my_skill",
     name="My Skill",
     ...
   )
```

### 2. 註冊 Server 並使用
```
1. register_upstream_server(...)
2. [在錄製中使用該 server 的工具]
3. [創建包含該 server 工具的技能]
```

### 3. 執行並監控
```
1. skill__my_skill(inputs)
   → 返回 run_id
2. get_run_status(run_id)
   → 查看進度
3. [可選] cancel_run(run_id)
```

## 調試技巧

### 查看執行日誌
```bash
cat data/runs/2025-01-16/run_abc123.jsonl | jq
```

### 查看技能定義
```bash
cat data/skills/my_skill/v0001.json | jq
```

### 查看 Session
```bash
cat data/sessions/session_xyz.json | jq
```

## 環境變量

```bash
# 數據目錄（可選，預設: ./data）
export SKILLFLOW_DATA_DIR=/path/to/data

# 最大並行數（可選，預設: 32）
export SKILLFLOW_MAX_CONCURRENCY=64
```

## Claude Desktop 配置範例

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/absolute/path/to/skillflow-mcp"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    }
  }
}
```

## 技能 ID 命名規範

✅ 推薦：
- `backup_daily_logs`
- `send_weekly_report`
- `process_uploaded_files`

❌ 避免：
- `skill1`, `test`, `temp`
- `做一些事情`, `日常任務` (非 ASCII)
- `very-long-and-descriptive-skill-name-that-is-hard-to-read`

## 相關連結

- [完整文檔](README.md)
- [快速開始](docs/QUICKSTART.md)
- [使用指南](docs/USAGE_GUIDE.md)
- [項目總結](PROJECT_SUMMARY.md)

---

**提示**：使用 `jq` 格式化 JSON 輸出以提高可讀性
