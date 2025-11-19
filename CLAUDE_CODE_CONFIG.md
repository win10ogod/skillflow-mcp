# Claude Code 配置兼容性指南

## 概述

**好消息！** SkillFlow MCP 的配置格式**已經完全符合 Claude Code 標準**，無需任何轉換即可直接使用。

本指南提供了配置管理工具，讓您可以輕鬆地從 Claude Code 導入配置、驗證配置格式，以及管理上游 MCP 服務器。

---

## ✅ 當前格式已是標準格式

### SkillFlow 配置格式

```json
{
  "servers": {
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
        "description": "使用 Puppeteer 進行瀏覽器自動化",
        "tools": ["puppeteer_navigate", "puppeteer_screenshot", "puppeteer_click"]
      }
    }
  }
}
```

### Claude Code 配置格式

**完全相同！** 這就是 Claude Code 的標準格式。

---

## 🚀 新增的配置管理工具

我們添加了 5 個 MCP 工具，讓配置管理更加便捷：

### 1. `import_claude_code_config`
從 Claude Code 格式導入配置。

**參數**:
```json
{
  "config_json": "{\"servers\": {...}}",  // JSON 字符串
  "merge": true,         // 是否與現有配置合併（默認 true）
  "overwrite": false     // 合併時是否覆蓋現有服務器（默認 false）
}
```

**示例**:
```javascript
import_claude_code_config({
  config_json: JSON.stringify({
    "servers": {
      "filesystem": {
        "server_id": "filesystem",
        "name": "File System Tools",
        "transport": "stdio",
        "config": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
          "env": null
        },
        "enabled": true,
        "metadata": {
          "description": "提供檔案系統操作工具"
        }
      }
    }
  }),
  merge: true,      // 與現有配置合併
  overwrite: false  // 不覆蓋已存在的服務器
})
```

**返回**:
```
✅ Imported 1 servers and merged with existing config.
Total servers: 3
Overwrite mode: false
```

---

### 2. `export_claude_code_config`
導出當前配置為 Claude Code 兼容格式。

**參數**: 無

**返回**:
```json
Current MCP Configuration (Claude Code compatible):

{
  "servers": {
    "filesystem": {
      "server_id": "filesystem",
      "name": "File System Tools",
      ...
    }
  }
}

Total servers: 3
```

---

### 3. `validate_mcp_config`
驗證 MCP 配置格式。

**參數**:
```json
{
  "config_json": "{\"servers\": {...}}"  // 可選，省略則驗證當前配置
}
```

**示例 1 - 驗證 JSON 字符串**:
```javascript
validate_mcp_config({
  config_json: JSON.stringify({
    "servers": {
      "test": {
        "server_id": "test",
        "name": "Test Server",
        "transport": "stdio",
        "config": { "command": "test" }
      }
    }
  })
})
```

**返回**:
```
✅ Configuration is valid and compatible with Claude Code!
```

**示例 2 - 驗證當前配置**:
```javascript
validate_mcp_config({})
```

**返回**:
```
✅ Current configuration is valid!
Total servers: 3
```

**錯誤示例**:
```
❌ Configuration validation failed:

  • Server 'test': Missing required field: command
  • Server 'invalid': Invalid transport: invalid_type
```

---

### 4. `add_mcp_server`
添加或更新單個 MCP 服務器。

**參數**:
```json
{
  "server_id": "my-server",
  "name": "My MCP Server",
  "transport": "stdio",
  "command": "node",
  "args": ["server.js"],
  "env": {
    "LOG_LEVEL": "INFO"
  },
  "enabled": true,
  "metadata": {
    "description": "My custom server",
    "tools": ["tool1", "tool2"]
  }
}
```

**示例**:
```javascript
add_mcp_server({
  server_id: "weather",
  name: "Weather API",
  transport: "stdio",
  command: "python",
  args: ["-m", "weather_server"],
  env: {
    "API_KEY": "your-api-key"
  },
  enabled: true,
  metadata: {
    "description": "提供天氣查詢功能"
  }
})
```

**返回**:
```
✅ Added MCP server 'weather' (Weather API)
Transport: stdio
Enabled: true
Total servers: 4
```

---

### 5. `remove_mcp_server`
移除 MCP 服務器。

**參數**:
```json
{
  "server_id": "server-to-remove"
}
```

**示例**:
```javascript
remove_mcp_server({
  server_id: "weather"
})
```

**返回**:
```
✅ Removed MCP server 'weather' (Weather API)
Remaining servers: 3
```

---

## 📖 使用場景

### 場景 1: 從 Claude Code 批量導入配置

假設您有一個 Claude Code 配置文件 `claude_config.json`:

```json
{
  "servers": {
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
      "metadata": {}
    },
    "filesystem": {
      "server_id": "filesystem",
      "name": "File System",
      "transport": "stdio",
      "config": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": null
      },
      "enabled": true,
      "metadata": {}
    }
  }
}
```

**步驟**:

1. 讀取文件內容（複製 JSON）

2. 調用導入工具:
```javascript
import_claude_code_config({
  config_json: `{
    "servers": {
      "puppeteer": {...},
      "filesystem": {...}
    }
  }`,
  merge: true,      // 與現有配置合併
  overwrite: false  // 保留已存在的服務器
})
```

3. 驗證導入成功:
```javascript
validate_mcp_config({})
```

---

### 場景 2: 添加新的 MCP 服務器

**使用 `add_mcp_server` 工具**:

```javascript
// 添加天氣服務
add_mcp_server({
  server_id: "openweather",
  name: "OpenWeather API",
  transport: "stdio",
  command: "python",
  args: ["-m", "openweather_mcp"],
  env: {
    "API_KEY": "your-openweather-api-key",
    "UNITS": "metric"
  },
  enabled: true,
  metadata: {
    "description": "提供天氣數據查詢",
    "tools": ["get_weather", "get_forecast"]
  }
})
```

---

### 場景 3: 導出配置供其他工具使用

```javascript
// 獲取當前配置
export_claude_code_config({})

// 複製輸出的 JSON
// 可以直接用於 Claude Code 或其他 MCP 客戶端
```

---

### 場景 4: 驗證配置正確性

**在導入配置前驗證**:

```javascript
// 先驗證 JSON 字符串
validate_mcp_config({
  config_json: `{...}`
})

// 確認無誤後再導入
import_claude_code_config({
  config_json: `{...}`
})
```

---

## 🎯 配置格式說明

### 必需字段

```json
{
  "servers": {
    "<server_id>": {
      "server_id": "string",      // 唯一ID（必需）
      "name": "string",            // 顯示名稱（必需）
      "transport": "stdio|http_sse|websocket",  // 傳輸類型（必需）
      "config": {},                // 傳輸配置（必需）
      "enabled": true,             // 是否啟用（可選，默認 true）
      "metadata": {}               // 額外元數據（可選）
    }
  }
}
```

### STDIO 傳輸配置

```json
{
  "config": {
    "command": "string",    // 執行命令（必需）
    "args": ["string"],     // 命令參數（可選）
    "env": {               // 環境變量（可選）
      "KEY": "value"
    }
  }
}
```

### HTTP+SSE 傳輸配置

```json
{
  "config": {
    "url": "string",       // 服務器 URL（必需）
    "headers": {}          // HTTP 標頭（可選）
  }
}
```

---

## ⚠️ 注意事項

### 1. JSON 字符串格式

在使用 `import_claude_code_config` 時，`config_json` 必須是**有效的 JSON 字符串**：

**✅ 正確**:
```javascript
import_claude_code_config({
  config_json: JSON.stringify({servers: {...}})
})
```

**❌ 錯誤**:
```javascript
import_claude_code_config({
  config_json: {servers: {...}}  // 這是對象，不是字符串
})
```

### 2. server_id 必須匹配

`servers` 對象的鍵必須與 `server_id` 字段一致：

**✅ 正確**:
```json
{
  "servers": {
    "puppeteer": {
      "server_id": "puppeteer",  // 匹配
      ...
    }
  }
}
```

**❌ 錯誤**:
```json
{
  "servers": {
    "puppeteer": {
      "server_id": "browser",  // 不匹配
      ...
    }
  }
}
```

### 3. 合併行為

- `merge: true` - 將新配置與現有配置合併
  - `overwrite: false` - 保留已存在的服務器
  - `overwrite: true` - 新服務器覆蓋舊服務器

- `merge: false` - 完全替換配置（危險！會刪除所有現有服務器）

**建議**: 總是使用 `merge: true` 以保留現有配置。

---

## 🔧 命令行工具（可選）

### 驗證配置文件

```bash
python -c "
from pathlib import Path
from skillflow.config_utils import print_validation_report

print_validation_report(Path('data/registry/servers.json'))
"
```

**輸出**:
```
============================================================
Configuration Validation Report
============================================================
File: data/registry/servers.json
Status: ✅ VALID

✅ Configuration is valid and compatible with Claude Code!
============================================================
```

---

## 📚 配置示例

### 完整的配置示例

```json
{
  "servers": {
    "filesystem": {
      "server_id": "filesystem",
      "name": "File System Tools",
      "transport": "stdio",
      "config": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "/tmp",
          "/Users/username/documents"
        ],
        "env": null
      },
      "enabled": true,
      "metadata": {
        "description": "提供檔案系統操作工具",
        "tools": [
          "read_file",
          "write_file",
          "list_directory",
          "search_files"
        ]
      }
    },
    "puppeteer": {
      "server_id": "puppeteer",
      "name": "Browser Automation",
      "transport": "stdio",
      "config": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-puppeteer"
        ],
        "env": null
      },
      "enabled": true,
      "metadata": {
        "description": "使用 Puppeteer 進行瀏覽器自動化",
        "tools": [
          "puppeteer_navigate",
          "puppeteer_screenshot",
          "puppeteer_click",
          "puppeteer_fill",
          "puppeteer_select"
        ]
      }
    },
    "custom-python-server": {
      "server_id": "custom-python-server",
      "name": "My Python MCP Server",
      "transport": "stdio",
      "config": {
        "command": "python",
        "args": [
          "-m",
          "my_mcp_server"
        ],
        "env": {
          "LOG_LEVEL": "INFO",
          "API_KEY": "secret-key",
          "DATABASE_URL": "sqlite:///data.db"
        }
      },
      "enabled": true,
      "metadata": {
        "description": "自定義 Python MCP 服務器",
        "version": "1.0.0",
        "author": "Your Name"
      }
    }
  }
}
```

---

## 🎉 總結

### 關鍵要點

1. ✅ **SkillFlow 配置格式已經是 Claude Code 標準格式**
2. ✅ **無需任何轉換即可直接使用**
3. ✅ **提供5個便捷工具管理配置**
4. ✅ **支持批量導入、驗證、導出**
5. ✅ **完全向後兼容**

### 推薦工作流程

1. **導入配置**:
   ```javascript
   import_claude_code_config({config_json: "...", merge: true})
   ```

2. **驗證配置**:
   ```javascript
   validate_mcp_config({})
   ```

3. **導出備份**:
   ```javascript
   export_claude_code_config({})
   ```

4. **按需管理**:
   ```javascript
   add_mcp_server({...})      // 添加新服務器
   remove_mcp_server({...})   // 移除服務器
   ```

您現在可以輕鬆地管理 MCP 服務器配置了！🎊
