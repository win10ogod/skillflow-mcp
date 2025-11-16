# ✅ MCP Server 添加完成

## 已完成的操作

### 1. 創建了詳細指南
- **[HOW_TO_ADD_MCP_SERVERS.md](HOW_TO_ADD_MCP_SERVERS.md)** - 完整的 MCP server 添加指南
  - 包含兩種方法（工具註冊 vs 手動編輯）
  - 提供 7 個常見 server 的配置示例
  - 故障排除指南

### 2. 創建了示例腳本
- **[add_mcp_server_example.py](add_mcp_server_example.py)** - 以編程方式添加 server 的示例
  - 展示如何添加 Filesystem server
  - 展示如何添加 Puppeteer server
  - 展示如何添加自定義 server
  - 包含列出和移除 server 的功能

### 3. 實際添加了兩個 MCP Server

已成功註冊並保存到 `data/registry/servers.json`：

#### Server 1: Filesystem ✅
- **ID**: `filesystem`
- **名稱**: File System Tools
- **功能**: 檔案系統操作
- **工具**: read_file, write_file, list_directory, search_files
- **配置**:
  ```bash
  npx -y @modelcontextprotocol/server-filesystem /tmp
  ```

#### Server 2: Puppeteer ✅
- **ID**: `puppeteer`
- **名稱**: Browser Automation
- **功能**: 瀏覽器自動化
- **工具**: puppeteer_navigate, puppeteer_screenshot, puppeteer_click
- **配置**:
  ```bash
  npx -y @modelcontextprotocol/server-puppeteer
  ```

## 如何使用

### 方法 A: 在 SkillFlow 中驗證

重啟 SkillFlow 後，使用以下工具：

```
請使用 list_upstream_servers 工具
```

**預期輸出**:
```
Registered servers (2):

✅ 啟用 filesystem: File System Tools (stdio)
✅ 啟用 puppeteer: Browser Automation (stdio)
```

### 方法 B: 在技能中使用

創建使用這些 server 的技能：

```json
{
  "nodes": [
    {
      "id": "read_file",
      "kind": "tool_call",
      "server": "filesystem",
      "tool": "read_file",
      "args_template": {
        "path": "$inputs.file_path"
      }
    },
    {
      "id": "screenshot",
      "kind": "tool_call",
      "server": "puppeteer",
      "tool": "puppeteer_screenshot",
      "args_template": {
        "url": "$inputs.website_url"
      },
      "depends_on": ["read_file"]
    }
  ]
}
```

### 方法 C: 錄製並創建技能

```
1. start_recording(session_name="file_and_web")
2. [使用 filesystem 讀取文件]
3. [使用 puppeteer 訪問網站]
4. stop_recording()
5. create_skill_from_session(...)
```

## 添加更多 MCP Server

### 快速方法（推薦）

運行示例腳本並修改：

```python
# 編輯 add_mcp_server_example.py
# 取消註釋並修改自定義 server 部分

async def add_my_server():
    storage = StorageLayer("data")
    registry = await storage.load_registry()

    my_config = ServerConfig(
        server_id="my-server",
        name="My Custom Server",
        transport=TransportType.STDIO,
        config={
            "command": "your-command",
            "args": ["your", "args"],
            "env": None
        },
        enabled=True
    )

    registry.servers["my-server"] = my_config
    await storage.save_registry(registry)

# 在 main() 中調用
await add_my_server()
```

然後運行：
```bash
uv run python add_mcp_server_example.py
```

### 使用 SkillFlow 工具

在 MCP 客戶端中：

```
請使用 register_upstream_server 工具註冊新 server

參數:
- server_id: "new-server"
- name: "New Server Name"
- transport: "stdio"
- config: {
    "command": "command",
    "args": ["arg1", "arg2"]
  }
```

### 手動編輯

直接編輯 `data/registry/servers.json`，添加新的 server 配置。

## 常見 MCP Server 列表

### 官方 MCP Servers

| Server | Package | 用途 |
|--------|---------|------|
| Filesystem | `@modelcontextprotocol/server-filesystem` | 檔案操作 |
| Puppeteer | `@modelcontextprotocol/server-puppeteer` | 瀏覽器自動化 |
| SQLite | `@modelcontextprotocol/server-sqlite` | 資料庫操作 |
| Brave Search | `@modelcontextprotocol/server-brave-search` | 網頁搜索 |
| GitHub | `@modelcontextprotocol/server-github` | GitHub API |
| Google Drive | `@modelcontextprotocol/server-gdrive` | Google Drive |
| Slack | `@modelcontextprotocol/server-slack` | Slack 整合 |

### 安裝示例

```bash
# 所有官方 server 都可通過 npx 直接使用
npx -y @modelcontextprotocol/server-filesystem /path/to/dir
npx -y @modelcontextprotocol/server-puppeteer
npx -y @modelcontextprotocol/server-sqlite /path/to/db.sqlite
```

## 配置示例

### 需要 API Key 的 Server

```json
{
  "server_id": "brave-search",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your-api-key"
    }
  }
}
```

### 自定義 Python Server

```json
{
  "server_id": "my-python-server",
  "config": {
    "command": "uv",
    "args": ["run", "python", "-m", "my_server"],
    "env": null
  }
}
```

### 本地 Node.js Server

```json
{
  "server_id": "local-node-server",
  "config": {
    "command": "node",
    "args": ["/absolute/path/to/server.js"],
    "env": {
      "PORT": "3000"
    }
  }
}
```

## 測試新 Server

### 1. 驗證 Server 可啟動

```bash
# 手動測試命令
npx -y @modelcontextprotocol/server-filesystem /tmp

# 應該啟動 MCP server（可能會等待輸入）
# Ctrl+C 停止
```

### 2. 在 SkillFlow 中測試

```
請使用 list_upstream_servers 工具
```

應該看到新添加的 server。

### 3. 創建測試技能

使用新 server 的工具創建簡單技能，驗證可以正常調用。

## 故障排除

### Server 無法啟動

**檢查**:
1. ✅ 命令路徑正確（`which npx` 或 `which python`）
2. ✅ 參數正確
3. ✅ 如果是 npm 包，先安裝：`npm install -g @modelcontextprotocol/server-xxx`

### Server 已註冊但不可用

**解決**:
1. 重啟 SkillFlow
2. 檢查 `data/registry/servers.json` 格式
3. 查看 SkillFlow 日誌

### 工具調用失敗

**檢查**:
1. Server 是否正常運行
2. 工具名稱是否正確
3. 參數格式是否符合要求

## 下一步

### 立即行動
1. ⬜ 重啟 SkillFlow 加載新 server
2. ⬜ 使用 `list_upstream_servers` 驗證
3. ⬜ 創建使用新 server 的測試技能

### 進階操作
1. ⬜ 添加更多 MCP server（參考指南）
2. ⬜ 創建複合技能（組合多個 server）
3. ⬜ 探索官方 MCP server 列表

### 學習資源
- [HOW_TO_ADD_MCP_SERVERS.md](HOW_TO_ADD_MCP_SERVERS.md) - 完整指南
- [add_mcp_server_example.py](add_mcp_server_example.py) - 示例腳本
- [MCP Server 列表](https://github.com/modelcontextprotocol/servers) - 官方資源

## 總結

✅ **已完成**:
- 創建詳細的 MCP server 添加指南
- 提供可執行的示例腳本
- 實際添加了 2 個 MCP server（filesystem, puppeteer）
- 配置已保存到 `data/registry/servers.json`

✅ **可用方法**:
1. 使用 SkillFlow 工具註冊
2. 運行示例腳本
3. 手動編輯配置文件

🚀 **準備就緒**: 您現在可以在 SkillFlow 技能中使用這些 MCP server！

---

**需要幫助？** 查看 [HOW_TO_ADD_MCP_SERVERS.md](HOW_TO_ADD_MCP_SERVERS.md) 獲取更多信息。
