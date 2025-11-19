# MCP Server Configuration Guide

## 配置文件位置

配置文件位於: `data/registry/servers.json`

## 支持的配置格式

### 1. 標準 Claude Code 格式（推薦）

使用 `mcpServers` 鍵的格式：

```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["path/to/server"],
      "env": {
        "VAR": "value"
      }
    }
  }
}
```

### 2. SkillFlow 內部格式

使用 `servers` 鍵的格式：

```json
{
  "servers": {
    "server-name": {
      "server_id": "server-name",
      "name": "Server Name",
      "transport": "stdio",
      "config": {
        "command": "node",
        "args": ["path/to/server"],
        "env": {
          "VAR": "value"
        }
      },
      "enabled": true,
      "metadata": {}
    }
  }
}
```

### 3. 簡化格式（會自動標準化）

您可以使用簡化格式，系統會自動補全缺失的字段：

```json
{
  "servers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "server.py"]
    }
  }
}
```

**自動補全規則：**
- `server_id`: 使用鍵名（例如 "my-server"）
- `name`: 從 server_id 生成（例如 "My Server"）
- `transport`: 默認為 "stdio"
- `enabled`: 默認為 `true`
- `metadata`: 默認為 `{}`
- `config`: 如果 `command`/`args`/`env` 在根層級，會自動移到 `config` 內

## 示例配置

### 完整示例

```json
{
  "servers": {
    "screenmonitormcp-v2": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "I:\\凌星開發計畫\\凌星\\ScreenMonitorMCP",
        "python",
        "-m",
        "screenmonitormcp_v2.mcp_main"
      ],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    },
    "memory": {
      "command": "node",
      "args": ["I:\\凌星開發計畫\\凌星\\memory-mcp-server"]
    },
    "windows-driver-input": {
      "server_id": "windows-driver-input",
      "name": "Windows Driver Input",
      "transport": "stdio",
      "config": {
        "command": "uv",
        "args": [
          "--directory",
          "I:\\凌星開發計畫\\凌星\\VYO-MCP\\windows-driver-input-mcp",
          "run",
          "main.py"
        ],
        "env": {
          "WINDOWS_INPUT_LOG_LEVEL": "INFO",
          "WINDOWS_MCP_INPUT_BACKEND": "ibsim-dll",
          "WINDOWS_MCP_INPUT_DRIVER": "SendInput"
        }
      },
      "enabled": true,
      "metadata": {}
    }
  }
}
```

## 使用 MCP 工具導入配置

### 方法 1: 直接導入 JSON

```json
{
  "name": "import_claude_code_config",
  "arguments": {
    "config_json": "{\"servers\": {...}}",
    "merge": true,
    "overwrite": false
  }
}
```

### 方法 2: 導出當前配置

```json
{
  "name": "export_claude_code_config",
  "arguments": {}
}
```

### 方法 3: 添加單個服務器

```json
{
  "name": "add_mcp_server",
  "arguments": {
    "server_id": "my-server",
    "name": "My Server",
    "transport": "stdio",
    "command": "node",
    "args": ["path/to/server"],
    "env": {
      "VAR": "value"
    },
    "enabled": true
  }
}
```

### 方法 4: 驗證配置

```json
{
  "name": "validate_mcp_config",
  "arguments": {
    "config_json": "{\"servers\": {...}}"
  }
}
```

## 常見問題

### Q: 為什麼配置沒有加載？

**檢查清單：**

1. 配置文件是否在正確位置？
   ```
   data/registry/servers.json
   ```

2. JSON 格式是否正確？
   - 使用 JSON 驗證器檢查
   - 注意 Windows 路徑中的反斜線需要轉義 (`\\`)

3. 查看日誌輸出：
   - 服務器啟動時會記錄加載的服務器數量
   - 錯誤會記錄到日誌中

### Q: 如何查看當前註冊的服務器？

使用 `list_upstream_servers` 工具：

```json
{
  "name": "list_upstream_servers",
  "arguments": {}
}
```

### Q: 配置文件格式錯誤會發生什麼？

系統會：
1. 嘗試自動標準化配置
2. 記錄警告信息
3. 跳過無效的服務器
4. 繼續加載其他有效服務器

### Q: 如何啟用調試日誌？

設置環境變量：
```bash
export LOG_LEVEL=DEBUG
```

或在服務器啟動前設置 Python 日誌級別。

## 調試技巧

### 1. 使用 debug_registry 工具

```json
{
  "name": "debug_registry",
  "arguments": {}
}
```

這會顯示：
- 註冊表文件路徑
- 文件內容
- 加載狀態

### 2. 檢查配置文件權限

確保服務器有讀取權限：
```bash
ls -la data/registry/servers.json
```

### 3. 手動驗證 JSON

```bash
cat data/registry/servers.json | python -m json.tool
```

## 最佳實踐

1. **使用簡化格式**：讓系統自動補全字段
2. **定期導出配置**：作為備份
3. **使用驗證工具**：導入前驗證配置
4. **增量添加**：使用 `add_mcp_server` 逐個添加服務器
5. **啟用日誌**：便於調試問題

## 更新日誌

### 2025-11-19
- ✅ 支持標準 Claude Code `mcpServers` 格式
- ✅ 自動標準化不完整的配置
- ✅ 改進錯誤處理和日誌記錄
- ✅ 修復 logger 未定義錯誤
- ✅ 修復 registry 加載繞過標準化的問題
