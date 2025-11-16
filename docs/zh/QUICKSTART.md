# 快速開始指南

5 分鐘內開始使用 SkillFlow MCP！

## 前置需求

- Python 3.10 或更高版本
- `uv` 套件管理器（推薦）或 `pip`
- Git

## 安裝

### 1. 克隆專案

```bash
git clone <repository-url>
cd skillflow-mcp
```

### 2. 安裝依賴項

#### 選項 A：完整安裝（推薦）

```bash
uv sync --extra full
```

這將安裝所有功能，包括：
- 核心 MCP 功能
- HTTP/WebSocket 傳輸
- 進階轉換（JSONPath、Jinja2）
- Web UI 與監控

#### 選項 B：基本安裝

```bash
uv sync
```

僅核心功能（MCP 伺服器、技能錄製、DAG 執行）。

#### 選項 C：僅 Web UI

```bash
uv sync --extra web
```

## 快速開始選項

### 選項 1：MCP 伺服器模式（Claude Desktop 整合）

#### 配置 Claude Desktop

在 `claude_desktop_config.json` 中添加：

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

#### 啟動 Claude Desktop

重新啟動 Claude Desktop。SkillFlow 將作為 MCP 伺服器可用，提供所有技能工具。

### 選項 2：獨立 Web UI

#### 啟動 Web 伺服器

```bash
uv run skillflow-web
```

或使用自訂配置：

```bash
uv run skillflow-web --host 0.0.0.0 --port 8080 --data-dir ./data
```

#### 存取 Web UI

在瀏覽器中開啟：http://localhost:8080

可用頁面：
- **儀表板** (`/`) - 系統概覽和指標
- **技能** (`/skills`) - 管理所有技能
- **DAG 編輯器** (`/editor`) - 視覺化技能編輯器
- **進階編輯器** (`/editor-advanced`) - 基於節點的拖放編輯器
- **監控** (`/monitoring`) - 執行監控
- **增強監控** (`/monitoring-v2`) - 即時圖表和分析
- **除錯工具** (`/debug`) - 技能除錯
- **技能構建器** (`/builder`) - 逐步創建技能

## 你的第一個技能

### 使用 Claude Desktop（MCP 模式）

#### 1. 開始錄製

在 Claude 中說：
```
開始錄製會話 'hello_world'
```

#### 2. 執行操作

執行你想要自動化的操作：
```
使用檔案系統工具創建名為 test.txt 的檔案，內容為 "Hello World"
```

#### 3. 停止錄製

```
停止錄製
```

#### 4. 創建技能

```
從最後一個會話創建技能
```

#### 5. 執行技能

```
執行 skill__hello_world
```

### 使用 Web UI

#### 1. 開啟技能構建器

導航至 http://localhost:8080/builder

#### 2. 創建簡單技能

- 點擊「添加節點」
- 選擇節點類型：`tool_call`
- 配置：
  - 工具名稱：`filesystem__write_file`
  - 參數：`{"path": "test.txt", "content": "Hello World"}`
- 點擊「保存技能」

#### 3. 從技能頁面執行

- 前往 `/skills`
- 找到你的技能
- 點擊「執行」

## 下一步

- [使用指南](USER_GUIDE.md) - 完整功能文檔
- [API 參考](API_REFERENCE.md) - REST API 文檔
- [範例](EXAMPLES.md) - 更複雜的範例
- [疑難排解](TROUBLESHOOTING.md) - 常見問題

## 常用命令

```bash
# 啟動 MCP 伺服器
uv run skillflow

# 啟動 Web UI
uv run skillflow-web

# 使用自訂埠啟動
uv run skillflow-web --port 3000

# 執行測試
pytest tests/

# 檢查版本
uv run python -c "import skillflow; print(skillflow.__version__)"
```

## 獲取幫助

- 查看[疑難排解指南](TROUBLESHOOTING.md)
- 查看[架構文檔](ARCHITECTURE.md)
- 查看[API 參考](API_REFERENCE.md)

## 接下來做什麼？

- 探索**進階功能**，如條件判斷、迴圈和巢狀技能
- 透過 Web UI 設置 **MCP 伺服器測試**
- 配置**自訂 MCP 伺服器**以擴展功能
- 了解使用 JSONPath 和 Jinja2 的**參數轉換**
- 使用**即時指標**和**稽核日誌**監控你的技能

---

**使用 SkillFlow 快樂自動化！🚀**
