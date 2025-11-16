# SkillFlow MCP 伺服器

將 MCP 工具調用鏈轉換為可重複使用的自動化技能。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.21.1+-green.svg)](https://modelcontextprotocol.io/)

## 概述

SkillFlow 是 Model Context Protocol (MCP) 伺服器的完整實現，能夠錄製、管理和重播工具調用鏈作為可重複使用的「技能」。將複雜的多步驟操作轉換為單一命令的自動化工作流程。

**核心價值**：將重複性的多步驟操作轉化為可重複使用的自動化技能。

## ✨ 主要功能

### 🎯 核心能力

- **📹 錄製模式**：自動捕獲工具調用序列
- **🔄 技能創建**：將錄製內容轉換為參數化技能
- **⚡ 一鍵執行**：使用單一命令執行複雜工作流程
- **🌐 DAG 執行**：支援具有依賴關係管理的並行執行
- **💾 零資料庫**：基於 JSON 的儲存（無需資料庫）
- **🔌 完整 MCP 協議**：完整支援 Tools、Resources 和 Prompts

### 🚀 進階功能（最新）

#### 並發控制
- **順序模式**：逐一執行步驟（預設）
- **分階段模式**：將步驟分組以並行執行
- **完全並行模式**：在依賴關係內最大化並行性

#### 上游 MCP 整合
- **代理工具**：自動暴露上游伺服器工具
- **資源存取**：列出並讀取已連接 MCP 伺服器的資源
- **提示詞存取**：從上游伺服器檢索和使用提示詞範本
- **原生 MCP 客戶端**：具有完整協議控制的自訂實現

#### SkillFlow 自身的 MCP 端點
- **Resources（資源）**：透過自訂 URI 方案暴露技能、會話和執行日誌
  - `skill://<skill_id>` - 存取技能定義
  - `session://<session_id>` - 存取錄製會話
  - `run://<run_id>` - 存取執行日誌
- **Prompts（提示詞）**：內建技能開發指南
  - `create_skill` - 逐步技能創建指南
  - `debug_skill` - 除錯協助
  - `optimize_skill` - 效能優化提示
  - `skill_best_practices` - 開發最佳實踐

#### 內容類型支援
完整的 MCP 協議內容類型支援：
- ✅ TextContent（文字內容）
- ✅ ImageContent（圖像：螢幕截圖、圖表）
- ✅ AudioContent（音訊：錄音、TTS）
- ✅ EmbeddedResource（嵌入資源：檔案、資料）

#### 階段 2：傳輸層擴展 ✅
- **HTTP+SSE 傳輸**：透過 HTTP 和伺服器推送事件連接 MCP 伺服器
  - 即時伺服器到客戶端通知
  - RESTful 工具調用
  - 自動重新連接處理
- **WebSocket 傳輸**：與 MCP 伺服器的全雙工通訊
  - JSON-RPC 2.0 協議支援
  - Ping/pong 保持連線機制
  - 雙向訊息處理
- **靈活的傳輸選擇**：為您的使用案例選擇最佳傳輸方式
  - stdio：預設，基於進程的通訊
  - HTTP+SSE：可擴展的 HTTP 架構
  - WebSocket：即時、持久連接

#### 階段 3：進階控制流程 ✅
- **條件節點**：技能中的動態分支邏輯
  - **if/else**：簡單的條件執行
  - **switch**：多分支條件邏輯
  - 使用 JSONPath、Jinja2 或 Python 表達式進行條件評估
  - 預設分支回退支援

- **迴圈節點**：迭代資料並重複操作
  - **FOR 迴圈**：使用 JSONPath 選擇迭代集合
  - **WHILE 迴圈**：具有動態評估的條件迴圈
  - **FOR_RANGE 迴圈**：數值範圍迭代
  - 使用 `max_iterations` 安全限制以防止無限迴圈
  - 存取迴圈變數：`$loop.item`、`$loop.index`

- **技能巢狀**：從簡單技能組合複雜技能
  - 在技能中調用技能以實現模組化設計
  - 具有適當上下文隔離的遞迴執行
  - 重複使用現有技能作為構建模組

- **參數轉換**：動態參數生成
  - **JSONPath**：從先前的輸出中提取和轉換資料
  - **Jinja2 範本**：使用範本生成複雜參數
  - 具有上下文感知的轉換，可存取輸入、輸出和迴圈變數
  - 範本變數：`$inputs.field`、`@step_id.outputs.field`、`$loop.var_name`

## 📦 安裝

### 前置需求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) 套件管理器
- MCP 客戶端（例如：Claude Desktop）

### 安裝依賴項

```bash
# 複製儲存庫
git clone <repository-url>
cd skillflow-mcp

# 安裝基本依賴項
uv sync

# 選用：安裝進階功能
uv sync --extra http          # HTTP+SSE 傳輸支援
uv sync --extra websocket     # WebSocket 傳輸支援
uv sync --extra transforms    # JSONPath 和 Jinja2 參數轉換
uv sync --extra full          # 所有進階功能
```

### 選用依賴項

- **http** (`aiohttp>=3.9.0`): 用於上游 MCP 伺服器的 HTTP+SSE 傳輸
- **websocket** (`websockets>=12.0`): 用於即時通訊的 WebSocket 傳輸
- **transforms** (`jsonpath-ng>=1.6.0`, `jinja2>=3.1.0`): 進階參數轉換
- **full**: 所有選用依賴項的組合

## ⚙️ 配置

### Claude Desktop 設定

編輯您的 Claude Desktop 配置檔案：

**macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**：`%APPDATA%\Claude\claude_desktop_config.json`
**Linux**：`~/.config/Claude/claude_desktop_config.json`

新增 SkillFlow 伺服器：

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

## 🚀 快速開始

### 基本工作流程

1. **開始錄製**
   ```
   詢問 Claude：「請開始錄製，會話名稱為 'my_workflow'」
   ```

2. **執行工具調用**
   ```
   透過 Claude 執行您的多步驟操作
   ```

3. **停止錄製**
   ```
   詢問 Claude：「請停止錄製」
   ```

4. **創建技能**
   ```
   詢問 Claude：「從最後一個會話創建技能」
   ```

5. **執行技能**
   ```
   詢問 Claude：「執行 skill__my_workflow」
   ```

### 範例：檔案備份自動化

```
1. 開始錄製：「開始錄製會話 'backup_docs'」

2. 執行操作：
   - 列出 Documents 中的所有 .txt 檔案
   - 讀取第一個檔案
   - 將內容複製到備份目錄

3. 停止錄製：「停止錄製」

4. 創建技能：「從最後一個會話創建技能 'backup_first_txt'」

5. 使用技能：「執行 skill__backup_first_txt」
```

## 📖 可用工具

### 錄製控制
- `start_recording` - 開始新的錄製會話
- `stop_recording` - 停止當前錄製會話

### 技能管理
- `create_skill_from_session` - 將錄製轉換為技能
- `list_skills` - 列出所有可用技能
- `get_skill` - 取得技能詳情
- `delete_skill` - 刪除技能

### 執行控制
- `skill__<id>` - 執行特定技能（為每個技能自動生成）
- `get_run_status` - 檢查執行狀態
- `cancel_run` - 取消正在執行的任務

### 上游伺服器管理
- `register_upstream_server` - 註冊 MCP 伺服器
- `list_upstream_servers` - 列出已註冊的伺服器
- `disconnect_server` - 斷開與伺服器的連接

### 上游資源和提示詞
- `list_upstream_resources` - 列出上游伺服器的資源
- `read_upstream_resource` - 讀取特定資源
- `list_upstream_prompts` - 列出可用提示詞
- `get_upstream_prompt` - 檢索提示詞範本

### 除錯工具
- `debug_recording_session` - 分析錄製資料
- `debug_skill_definition` - 檢查技能結構
- `debug_skill_execution` - 追蹤執行流程
- `debug_upstream_tools` - 測試上游伺服器連接性

## 🏗️ 架構

### 核心組件

```
src/skillflow/
├── schemas.py              # Pydantic 資料模型（為階段 3 擴展）
├── storage.py              # JSON 儲存層
├── skills.py               # 技能管理
├── recording.py            # 錄製管理器
├── engine.py               # 執行引擎（DAG、並發、階段 3 功能）
├── mcp_clients.py          # 上游 MCP 客戶端管理器
├── native_mcp_client.py    # 原生 MCP 客戶端實現（stdio）
├── http_sse_client.py      # HTTP+SSE 傳輸客戶端（階段 2）
├── websocket_client.py     # WebSocket 傳輸客戶端（階段 2）
├── parameter_transform.py  # JSONPath 和 Jinja2 轉換（階段 3）
├── tool_naming.py          # 智慧工具命名策略
└── server.py               # MCP 伺服器實現
```

### 資料流程

```
錄製流程：
start_recording() → RecordingSession → 記錄工具調用 → stop_recording() → 儲存至 data/sessions/

技能創建流程：
create_skill_from_session() → 載入會話 → 生成 SkillGraph（節點 + 邊）
→ 應用參數範本 → 儲存至 data/skills/ → 註冊為 MCP 工具

技能執行流程：
skill__<id>(inputs) → ExecutionEngine.run_skill() → 解析 DAG、拓撲排序
→ 執行節點（順序/分階段/並行）→ 調用上游工具
→ 記錄執行至 data/runs/ → 回傳 SkillRunResult
```

## 🎨 使用案例

### 1. 工作流程自動化
錄製重複性的多步驟操作，並使用單一命令執行它們。

### 2. 工作流程編排
將來自多個 MCP 伺服器的工具組合成複雜的工作流程。

### 3. 批次處理
並行執行多個獨立任務（批次下載、處理）。

### 4. 技能庫
在團隊中分享常用的自動化技能。

### 5. CI/CD 整合
將技能整合到自動化部署管線中。

## 🔧 進階配置

### 並發模式

創建技能時，您可以指定執行策略：

```python
create_skill_from_session({
  "session_id": "...",
  "skill_id": "parallel_fetch",
  "name": "並行資料擷取",
  "concurrency_mode": "full_parallel",  # sequential | phased | full_parallel
  "max_parallel": 5  # 限制並發執行數
})
```

### 分階段執行

定義執行階段以實現分組並行：

```python
create_skill_from_session({
  "session_id": "...",
  "concurrency_mode": "phased",
  "concurrency_phases": {
    "phase1": ["step_1", "step_2"],  # 並行執行
    "phase2": ["step_3", "step_4"]   # 在 phase1 之後執行
  }
})
```

### 階段 3 進階範例

#### 條件節點

創建具有條件邏輯的技能：

```json
{
  "node": {
    "id": "check_status",
    "kind": "conditional",
    "conditional_config": {
      "type": "if_else",
      "branches": [
        {
          "condition": "$.status == 'success'",
          "nodes": ["success_handler"],
          "description": "處理成功情況"
        }
      ],
      "default_branch": ["error_handler"]
    }
  }
}
```

#### 迴圈節點

迭代集合或範圍：

```json
{
  "node": {
    "id": "process_items",
    "kind": "loop",
    "loop_config": {
      "type": "for",
      "collection_path": "$.items",
      "iteration_var": "current_item",
      "body_nodes": ["process_single_item"],
      "max_iterations": 100
    }
  }
}
```

#### 參數轉換

使用 JSONPath 提取資料：

```json
{
  "parameter_transform": {
    "engine": "jsonpath",
    "expression": "$.results[*].id"
  }
}
```

使用 Jinja2 範本進行複雜轉換：

```json
{
  "parameter_transform": {
    "engine": "jinja2",
    "expression": "{{ value | upper }} - {{ loop.index }}"
  }
}
```

#### 範本變數

在技能參數中存取上下文：

- `$inputs.field_name` - 存取技能輸入參數
- `@step_id.outputs.field` - 存取先前步驟的輸出
- `$loop.item` - 當前迴圈項目
- `$loop.index` - 當前迴圈迭代索引

範例：
```json
{
  "args_template": {
    "user_id": "$inputs.user_id",
    "previous_result": "@fetch_data.outputs.result",
    "item_name": "$loop.item.name"
  }
}
```

## 📚 文件

- [快速入門指南](docs/QUICKSTART.md)
- [使用指南](docs/USAGE_GUIDE.md)
- [專案摘要](docs/PROJECT_SUMMARY.md)
- [上游工具代理](docs/UPSTREAM_TOOLS_PROXY.md)
- [原生 MCP 客戶端](docs/NATIVE_MCP_CLIENT.md)
- [疑難排解](docs/TROUBLESHOOTING_PROXY_TOOLS.md)
- [更新日誌](CHANGELOG.md)

英文文件請參見 [README.md](README.md)。

## 🛠️ 開發

### 執行測試

```bash
uv run pytest tests/ -v
```

### 程式碼風格

- 遵循 PEP 8
- 使用型別提示
- 為所有公共 API 撰寫文件字串

## 🗺️ 開發藍圖

### 階段 2：傳輸層 ✅ 完成
- ✅ HTTP+SSE 傳輸支援
- ✅ WebSocket 傳輸支援
- ✅ 上游伺服器的靈活傳輸選擇

### 階段 3：進階功能 ✅ 完成
- ✅ 技能巢狀和組合
- ✅ 條件節點（if/else/switch）
- ✅ 迴圈節點（for/while/for_range）
- ✅ 參數轉換表達式（JSONPath、Jinja2）
- ✅ 增強的範本變數（$inputs、@outputs、$loop）

### 階段 4：企業功能
- [ ] 多租戶支援
- [ ] 權限和存取控制
- [ ] 技能市場和分享
- [ ] 稽核日誌
- [ ] 進階監控和指標

### 階段 5：使用者體驗
- [ ] Web UI 控制面板
- [ ] 視覺化 DAG 編輯器
- [ ] 執行監控儀表板
- [ ] 技能除錯工具
- [ ] 互動式技能構建器

## 🤝 貢獻

歡迎貢獻！請遵循以下準則：

1. Fork 儲存庫
2. 創建功能分支
3. 為新功能撰寫測試
4. 提交 Pull Request

### 測試要求
- 新功能必須包含測試
- 維持測試覆蓋率 > 80%

## 📄 授權

MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案。

## 🙏 致謝

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Astral uv](https://github.com/astral-sh/uv)
- [Pydantic](https://docs.pydantic.dev/)
- 所有貢獻者

## 📊 專案狀態

✅ **MVP 完成** - 可用於生產環境測試

**最後更新**：2025-11-16
**維護者**：SkillFlow Team

---

**立即開始自動化您的工作流程！** 🚀
