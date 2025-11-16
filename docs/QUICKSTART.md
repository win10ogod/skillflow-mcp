# SkillFlow 快速入門

5 分鐘內開始使用 SkillFlow！

## 前置需求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) 包管理器
- MCP 客戶端（如 Claude Desktop）

## 安裝

```bash
# 1. 克隆或下載 SkillFlow
git clone <repository-url>
cd skillflow-mcp

# 2. 安裝依賴
uv sync
```

## 配置

### 在 Claude Desktop 中配置

編輯配置文件（位置因作業系統而異）：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

添加 SkillFlow server：

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

**重要**：將 `cwd` 替換為 skillflow-mcp 的實際絕對路徑。

## 第一個技能：Hello World

### 步驟 1：啟動 Claude Desktop

重啟 Claude Desktop 以載入 SkillFlow。

### 步驟 2：驗證連接

在 Claude 對話中輸入：

```
請使用 list_skills 工具列出所有技能
```

應該返回空列表（因為還沒有技能）。

### 步驟 3：手動創建一個簡單技能

由於我們還沒有上游 MCP server，我們可以手動創建一個示例技能文件：

```bash
# 複製示例技能到 data 目錄
mkdir -p data/skills/hello_world
cp examples/example_skill.json data/skills/hello_world/v0001.json
```

修改示例以創建一個簡單的 "hello world" 技能：

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

創建對應的 meta.json：

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

### 步驟 4：重啟 Claude Desktop

重啟以載入新技能。

### 步驟 5：列出技能

```
請列出所有技能
```

您應該看到 `hello_world` 技能。

## 真實場景：使用 MCP Server

要創建有用的技能，您需要上游 MCP server。以下是常見的示例：

### 使用文件系統 MCP Server

1. **安裝 filesystem MCP server**：

```bash
npm install -g @modelcontextprotocol/server-filesystem
```

2. **在 Claude Desktop 中配置**：

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

3. **在 SkillFlow 中註冊**：

```
請幫我註冊一個上游 MCP server：
- server_id: filesystem
- name: File System Tools
- transport: stdio
- config:
  - command: npx
  - args: ["-y", "@modelcontextprotocol/server-filesystem", "/Users/myuser/Documents"]
```

4. **開始錄製**：

```
請開始錄製，session 名稱為 "file_backup"
```

5. **執行操作**：

```
請使用 filesystem server 執行以下操作：
1. 列出 /Users/myuser/Documents 目錄下的所有 .txt 檔案
2. 讀取第一個檔案的內容
3. 將內容複製到 backup 目錄
```

6. **停止錄製並創建技能**：

```
請停止錄製

然後從剛才的 session 創建技能：
- skill_id: backup_first_txt_file
- name: 備份第一個文字檔
- description: 找到第一個 .txt 檔並備份
- tags: ["filesystem", "backup"]
```

7. **使用技能**：

```
請執行 skill__backup_first_txt_file 技能
```

## 下一步

- 閱讀 [完整使用指南](USAGE_GUIDE.md)
- 探索 [示例技能](../examples/)
- 了解 [進階功能](USAGE_GUIDE.md#進階功能)

## 常見問題

### Q: SkillFlow 無法連接？

**A**: 檢查：
1. `cwd` 路徑是否正確（必須是絕對路徑）
2. 是否已運行 `uv sync`
3. Claude Desktop 日誌中是否有錯誤

### Q: 如何查看 Claude Desktop 日誌？

**A**:
- **macOS**: `~/Library/Logs/Claude/mcp*.log`
- **Windows**: `%APPDATA%\Claude\logs\mcp*.log`

### Q: 技能無法執行？

**A**: 確保：
1. 上游 MCP server 已正確註冊
2. 上游 server 正在運行
3. 工具名稱和參數正確

### Q: 如何刪除技能？

**A**:
```
請刪除技能 hello_world
```

或手動刪除 `data/skills/hello_world` 目錄。

---

**開始創建您的第一個自動化技能！** 🚀
