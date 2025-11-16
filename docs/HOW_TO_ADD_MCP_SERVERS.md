# 如何添加 MCP Server 到 SkillFlow

## 概述

SkillFlow 可以連接到多個上游 MCP server，並在技能中調用它們的工具。

## 方法 1: 使用 SkillFlow 工具註冊（推薦）

### 步驟 1: 準備 Server 信息

首先確定以下信息：
- **server_id**: 唯一標識符（如 "filesystem", "puppeteer"）
- **name**: 人類可讀的名稱
- **transport**: 傳輸方式（"stdio" 或 "http_sse"）
- **config**: 配置信息

### 步驟 2: 註冊 Server

在 MCP 客戶端中調用：

```
請使用 register_upstream_server 工具註冊 MCP server

參數:
- server_id: "filesystem"
- name: "File System Tools"
- transport: "stdio"
- config: {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": null
  }
```

### 步驟 3: 驗證註冊

```
請使用 list_upstream_servers 工具
```

應該能看到新註冊的 server。

## 方法 2: 手動編輯配置文件

編輯 `data/registry/servers.json`:

```json
{
  "servers": {
    "filesystem": {
      "server_id": "filesystem",
      "name": "File System Tools",
      "transport": "stdio",
      "config": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/username/Documents"],
        "env": null
      },
      "enabled": true,
      "metadata": {
        "description": "Provides file system operations"
      }
    },
    "puppeteer": {
      "server_id": "puppeteer",
      "name": "Browser Automation",
      "transport": "stdio",
      "config": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": null
      },
      "enabled": true,
      "metadata": {
        "description": "Browser automation via Puppeteer"
      }
    }
  }
}
```

然後重啟 SkillFlow。

## 常見 MCP Server 配置示例

### 1. File System Server

```json
{
  "server_id": "filesystem",
  "name": "File System Tools",
  "transport": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"],
    "env": null
  }
}
```

**可用工具**: `read_file`, `write_file`, `list_directory`, etc.

### 2. Puppeteer (Browser) Server

```json
{
  "server_id": "puppeteer",
  "name": "Browser Automation",
  "transport": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
    "env": null
  }
}
```

**可用工具**: `puppeteer_navigate`, `puppeteer_screenshot`, `puppeteer_click`, etc.

### 3. SQLite Server

```json
{
  "server_id": "sqlite",
  "name": "SQLite Database",
  "transport": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sqlite", "/path/to/database.db"],
    "env": null
  }
}
```

**可用工具**: `read_query`, `write_query`, `create_table`, etc.

### 4. Brave Search Server

```json
{
  "server_id": "brave-search",
  "name": "Brave Search API",
  "transport": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your-api-key-here"
    }
  }
}
```

**可用工具**: `brave_web_search`, `brave_local_search`, etc.

### 5. GitHub Server

```json
{
  "server_id": "github",
  "name": "GitHub API",
  "transport": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token-here"
    }
  }
}
```

**可用工具**: `create_or_update_file`, `search_repositories`, `create_issue`, etc.

### 6. 自定義 Python MCP Server

```json
{
  "server_id": "my-custom-server",
  "name": "My Custom Tools",
  "transport": "stdio",
  "config": {
    "command": "python",
    "args": ["-m", "my_mcp_server"],
    "env": null
  }
}
```

### 7. 自定義 Node.js MCP Server

```json
{
  "server_id": "my-node-server",
  "name": "My Node Server",
  "transport": "stdio",
  "config": {
    "command": "node",
    "args": ["/path/to/server.js"],
    "env": {
      "API_KEY": "secret"
    }
  }
}
```

## 在技能中使用已註冊的 Server

註冊 server 後，在技能定義中引用：

```json
{
  "nodes": [
    {
      "id": "read_file_step",
      "kind": "tool_call",
      "server": "filesystem",
      "tool": "read_file",
      "args_template": {
        "path": "$inputs.file_path"
      }
    },
    {
      "id": "search_web_step",
      "kind": "tool_call",
      "server": "brave-search",
      "tool": "brave_web_search",
      "args_template": {
        "query": "$inputs.search_query"
      },
      "depends_on": ["read_file_step"]
    }
  ]
}
```

## 測試新註冊的 Server

### 1. 列出 Server 的工具

創建一個測試技能或直接通過 SkillFlow 調用（如果已擴展）。

### 2. 創建測試技能

```python
# 使用 test_context7_skill.py 作為模板
# 修改為使用新 server 的工具
```

### 3. 錄製並創建技能

```
1. start_recording(session_name="test_new_server")
2. [通過新 server 執行一些操作]
3. stop_recording()
4. create_skill_from_session(...)
```

## 故障排除

### Server 無法連接

**症狀**: "Failed to connect to server"

**檢查**:
1. ✅ 命令是否正確（`command` 和 `args`）
2. ✅ 環境變量是否設置（如需要）
3. ✅ Server 是否已安裝（如 `npx` 命令）
4. ✅ 路徑是否正確（絕對路徑 vs 相對路徑）

**調試**:
```bash
# 手動測試命令
npx -y @modelcontextprotocol/server-filesystem /path/to/dir

# 應該啟動 server 而不報錯
```

### Server 已註冊但不可用

**症狀**: "Server not found in registry"

**解決**:
1. 檢查 `data/registry/servers.json` 是否包含該 server
2. 確認 `enabled: true`
3. 重啟 SkillFlow

### 工具調用失敗

**症狀**: "Tool not found" 或執行錯誤

**檢查**:
1. ✅ 工具名稱是否正確
2. ✅ 參數是否符合工具要求
3. ✅ Server 是否正常運行

## 高級配置

### 環境變量

對於需要 API key 的 server：

```json
{
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "BSA...",
      "CUSTOM_VAR": "value"
    }
  }
}
```

### 禁用 Server

暫時禁用而不刪除：

```json
{
  "server_id": "my-server",
  "enabled": false
}
```

### Metadata

添加額外信息：

```json
{
  "metadata": {
    "description": "Server description",
    "version": "1.0.0",
    "author": "Your Name",
    "documentation": "https://..."
  }
}
```

## 完整示例：添加並使用 Filesystem Server

### 步驟 1: 註冊

```
請使用 register_upstream_server 工具

參數:
- server_id: "filesystem"
- name: "File System"
- transport: "stdio"
- config: {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/Documents"]
  }
```

### 步驟 2: 創建技能

```
請幫我從以下流程創建技能：

1. start_recording(session_name="read_and_summarize")
2. [使用 filesystem server 讀取文件]
3. [處理內容]
4. stop_recording()
5. create_skill_from_session(
     session_id="...",
     skill_id="read_and_process",
     name="讀取並處理文件",
     ...
   )
```

### 步驟 3: 使用技能

```
請執行 skill__read_and_process 技能

參數:
- file_path: "/Users/me/Documents/data.txt"
```

## 參考資源

- [MCP Server 列表](https://github.com/modelcontextprotocol/servers)
- [創建自定義 MCP Server](https://modelcontextprotocol.io/docs/building-servers)
- [SkillFlow 使用指南](docs/USAGE_GUIDE.md)

## 下一步

1. ⬜ 選擇要添加的 MCP server
2. ⬜ 準備配置信息
3. ⬜ 使用方法 1 或 2 註冊
4. ⬜ 創建使用該 server 的技能
5. ⬜ 測試並記錄

---

**需要幫助？** 查看 [故障排除](docs/USAGE_GUIDE.md#故障排除) 或參考示例配置。
