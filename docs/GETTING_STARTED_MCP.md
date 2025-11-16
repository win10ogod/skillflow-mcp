# 🚀 SkillFlow + MCP Server 快速開始

## 30 秒總結

您現在可以：
1. ✅ 添加任意 MCP server 到 SkillFlow
2. ✅ 在技能中使用這些 server 的工具
3. ✅ 創建跨多個 MCP server 的複合技能

## 已經完成的設置

### ✅ 已添加的 MCP Server

**Filesystem Server** - 檔案操作
```bash
Server ID: filesystem
工具: read_file, write_file, list_directory, search_files
```

**Puppeteer Server** - 瀏覽器自動化
```bash
Server ID: puppeteer
工具: puppeteer_navigate, puppeteer_screenshot, puppeteer_click
```

### 📁 配置位置

所有 MCP server 配置保存在：
```
data/registry/servers.json
```

## 快速測試（3分鐘）

### 測試 1: 列出已註冊的 Server

在 MCP 客戶端中：
```
請使用 list_upstream_servers 工具
```

**預期結果**: 看到 filesystem 和 puppeteer 兩個 server

### 測試 2: 創建使用 Server 的技能

方法 A - 手動創建：
```
參考 data/skills/fetch_library_docs/ 的結構
修改 nodes 中的 server 為 "filesystem" 或 "puppeteer"
```

方法 B - 錄製創建：
```
1. start_recording()
2. [調用 filesystem 或 puppeteer 的工具]
3. stop_recording()
4. create_skill_from_session(...)
```

## 添加更多 MCP Server

### 方法 1: 運行示例腳本（最快）

```bash
uv run python add_mcp_server_example.py
```

編輯腳本可以添加：
- Brave Search
- SQLite
- GitHub
- 或任何自定義 server

### 方法 2: 使用 SkillFlow 工具

```
請使用 register_upstream_server 工具

參數:
- server_id: "github"
- name: "GitHub API"
- transport: "stdio"
- config: {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"}
  }
```

### 方法 3: 手動編輯配置

編輯 `data/registry/servers.json`，添加新 server。

## 常見使用場景

### 場景 1: 讀取文件並處理

```json
{
  "nodes": [
    {
      "id": "read",
      "server": "filesystem",
      "tool": "read_file",
      "args_template": {"path": "$inputs.file_path"}
    },
    {
      "id": "process",
      "tool": "some_processing_tool",
      "args_template": {"data": "@read.outputs.content"}
    }
  ]
}
```

### 場景 2: 網頁截圖

```json
{
  "nodes": [
    {
      "id": "screenshot",
      "server": "puppeteer",
      "tool": "puppeteer_screenshot",
      "args_template": {
        "url": "$inputs.website_url",
        "fullPage": true
      }
    }
  ]
}
```

### 場景 3: 組合多個 Server

```json
{
  "nodes": [
    {
      "id": "read_config",
      "server": "filesystem",
      "tool": "read_file"
    },
    {
      "id": "open_browser",
      "server": "puppeteer",
      "tool": "puppeteer_navigate",
      "depends_on": ["read_config"]
    },
    {
      "id": "search",
      "server": "brave-search",
      "tool": "brave_web_search",
      "depends_on": ["open_browser"]
    }
  ]
}
```

## 參考文檔

| 文檔 | 用途 |
|------|------|
| [HOW_TO_ADD_MCP_SERVERS.md](HOW_TO_ADD_MCP_SERVERS.md) | 詳細添加指南 |
| [MCP_SERVER_SETUP_COMPLETE.md](MCP_SERVER_SETUP_COMPLETE.md) | 設置完成總結 |
| [add_mcp_server_example.py](add_mcp_server_example.py) | 示例腳本 |

## 官方 MCP Server 列表

| Server | 用途 | Package |
|--------|------|---------|
| Filesystem | 檔案操作 | `@modelcontextprotocol/server-filesystem` |
| Puppeteer | 瀏覽器自動化 | `@modelcontextprotocol/server-puppeteer` |
| SQLite | 資料庫 | `@modelcontextprotocol/server-sqlite` |
| Brave Search | 網頁搜索 | `@modelcontextprotocol/server-brave-search` |
| GitHub | GitHub API | `@modelcontextprotocol/server-github` |
| Google Drive | Google Drive | `@modelcontextprotocol/server-gdrive` |
| Slack | Slack 整合 | `@modelcontextprotocol/server-slack` |

## 下一步

1. ⬜ 測試已添加的 filesystem 和 puppeteer server
2. ⬜ 添加您需要的其他 MCP server
3. ⬜ 創建使用這些 server 的技能
4. ⬜ 探索技能組合的可能性

## 常見問題

**Q: 如何知道 server 有哪些工具？**

A: 查看官方文檔或運行 server 後通過 MCP protocol 查詢

**Q: 可以同時使用多個 server 嗎？**

A: 可以！技能的不同節點可以調用不同 server 的工具

**Q: Server 配置保存在哪裡？**

A: `data/registry/servers.json`

**Q: 如何禁用某個 server？**

A: 在配置中設置 `"enabled": false`

---

**準備就緒！** 開始創建您的 SkillFlow + MCP server 技能吧！ 🚀
