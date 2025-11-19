# 診斷：看不到 MCP 服務器工具

## 診斷步驟

請按順序執行以下工具來診斷問題：

### 1. 檢查服務器註冊

```javascript
list_upstream_servers()
```

**期望結果**: 應該看到所有註冊的服務器列表
- 如果看不到任何服務器 → 配置文件可能有問題
- 如果能看到服務器 → 繼續下一步

---

### 2. 檢查上游工具緩存狀態

```javascript
get_cache_stats()
```

**查看**:
- 上游工具緩存是否有數據？
- 緩存命中率是多少？
- 是否有錯誤？

---

### 3. 強制刷新上游工具

```javascript
refresh_upstream_tools()
```

**這會**:
- 清除所有上游工具緩存
- 重新連接所有啟用的服務器
- 重新獲取工具

**注意輸出中的錯誤消息**

---

### 4. 測試特定服務器連接

```javascript
// 替換 "puppeteer" 為您的服務器 ID
list_upstream_tools("puppeteer")
```

**可能的結果**:
- ✅ 成功：返回工具列表
- ❌ 超時：30 秒後超時
- ❌ 連接失敗：服務器無法啟動
- ❌ 命令不存在：command 路徑錯誤

---

## 常見問題診斷

### 問題 1: 配置文件路徑錯誤

**症狀**: Windows 路徑使用反斜杠

**錯誤配置**:
```json
{
  "config": {
    "args": ["--directory", "I:\\path\\to\\server"]
  }
}
```

**正確配置**:
```json
{
  "config": {
    "args": ["--directory", "I:/path/to/server"]
  }
}
```

或使用雙反斜杠：
```json
{
  "config": {
    "args": ["--directory", "I:\\\\path\\\\to\\\\server"]
  }
}
```

---

### 問題 2: 命令不在 PATH 中

**症狀**: 找不到 command

**檢查**:
```bash
# 在命令行測試
npx -y @modelcontextprotocol/server-puppeteer
uv --version
python --version
```

**修復**: 使用絕對路徑
```json
{
  "config": {
    "command": "C:/Program Files/nodejs/npx.cmd"
  }
}
```

---

### 問題 3: 服務器啟動超時

**症狀**: 30 秒超時

**原因**:
- 服務器啟動太慢
- 網絡問題（npm/uv 下載依賴）
- 環境變量缺失

**臨時修復**:
```javascript
// 等待一會兒後重試
refresh_upstream_tools()
```

---

### 問題 4: 環境變量問題

**症狀**: 服務器啟動但沒有工具

**檢查配置**:
```json
{
  "config": {
    "env": {
      "PATH": "/usr/local/bin:/usr/bin",
      "NODE_ENV": "production"
    }
  }
}
```

---

## 手動測試服務器

在命令行直接測試服務器是否能啟動：

```bash
# 測試 puppeteer
npx -y @modelcontextprotocol/server-puppeteer

# 測試 filesystem
npx -y @modelcontextprotocol/server-filesystem /tmp

# 測試 Python 服務器
uv --directory "I:/path/to/server" run main.py
```

**期望**: 服務器應該啟動並等待 STDIO 輸入

---

## 查看配置文件

```bash
cat data/registry/servers.json
```

或使用工具：
```javascript
export_claude_code_config()
```

檢查：
- server_id 是否正確
- command 路徑是否正確
- args 是否正確
- enabled 是否為 true

---

## 啟用詳細日誌

修改 Python 日誌級別：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

然後重啟服務器，查看詳細的連接和錯誤日誌。

---

## 緊急修復

如果所有服務器都看不到工具，可能是緩存問題：

```javascript
// 1. 清除所有緩存
invalidate_cache()

// 2. 清除技能緩存
invalidate_skill_cache()

// 3. 強制重新加載
force_skill_reload()

// 4. 刷新上游工具
refresh_upstream_tools()

// 5. 重啟 MCP 客戶端
```

---

請先執行這些診斷步驟，然後告訴我結果，我可以進一步幫您修復。
