# SkillFlow 使用指南

本指南詳細介紹如何使用 SkillFlow MCP Server 錄製、創建和執行技能。

## 目錄

1. [環境設定](#環境設定)
2. [基本工作流程](#基本工作流程)
3. [進階功能](#進階功能)
4. [最佳實踐](#最佳實踐)
5. [故障排除](#故障排除)

## 環境設定

### 安裝 SkillFlow

```bash
cd skillflow-mcp
uv sync
```

### 配置 MCP 客戶端

在 Claude Desktop 的配置檔中添加：

**macOS/Linux**: `~/.config/claude/config.json`
**Windows**: `%APPDATA%\Claude\config.json`

```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "/path/to/skillflow-mcp"
    }
  }
}
```

### 驗證安裝

重啟 Claude Desktop，然後在對話中輸入：

```
請列出所有可用的 MCP 工具
```

您應該看到 SkillFlow 提供的工具，包括：
- `start_recording`
- `stop_recording`
- `list_skills`
- 等等

## 基本工作流程

### 場景：自動化「打開記事本並輸入文字」

#### 步驟 1：註冊上游 MCP Server

假設您有一個提供 OS 操作工具的 MCP server：

```
請幫我註冊一個 MCP server：
- server_id: os-tools
- name: OS Automation Tools
- transport: stdio
- config:
  - command: python
  - args: ["-m", "os_automation_mcp"]
```

SkillFlow 會調用 `register_upstream_server` 工具。

#### 步驟 2：開始錄製

```
請開始錄製，session 名稱為 "notepad_demo"
```

SkillFlow 調用 `start_recording(session_name="notepad_demo")`，返回 session ID。

#### 步驟 3：執行工具調用

在錄製模式下，執行您想要自動化的操作：

```
請使用 os-tools 執行以下操作：
1. 打開記事本應用
2. 聚焦到記事本視窗
3. 輸入文字 "Hello from SkillFlow!"
```

這些工具調用會被自動記錄到 session 中。

#### 步驟 4：停止錄製

```
請停止錄製
```

SkillFlow 調用 `stop_recording()`，session 被保存。

#### 步驟 5：創建技能

```
請從剛才的 session 創建技能：
- skill_id: open_notepad_and_type
- name: 開啟記事本並輸入文字
- description: 自動開啟記事本並輸入自訂文字
- tags: ["windows", "notepad", "automation"]
- 將第三步的 text 參數暴露為技能輸入
```

SkillFlow 會：
1. 讀取 session
2. 生成技能草稿
3. 將指定的參數轉換為模板
4. 保存技能

#### 步驟 6：使用技能

技能創建後會自動註冊為 MCP 工具：

```
請使用 skill__open_notepad_and_type 技能，輸入文字 "這是自動化測試"
```

SkillFlow 會執行整個工具鏈。

## 進階功能

### 並行執行

#### 定義並行階段

如果您的技能包含可並行執行的步驟，可以在創建技能後手動編輯：

```json
{
  "graph": {
    "concurrency": {
      "mode": "phased",
      "phases": {
        "1": ["download_file_1", "download_file_2", "download_file_3"],
        "2": ["process_all_files"],
        "3": ["upload_results"]
      }
    }
  }
}
```

#### 完全並行模式

設置 `"mode": "full_parallel"`，SkillFlow 會自動分析依賴並最大化並行。

### 錯誤處理

#### 配置重試

在技能定義中為特定節點添加重試策略：

```json
{
  "nodes": [
    {
      "id": "unreliable_api_call",
      "kind": "tool_call",
      "server": "api-tools",
      "tool": "call_api",
      "error_strategy": "retry",
      "retry_config": {
        "max_retries": 5,
        "backoff_ms": 2000,
        "backoff_multiplier": 2.0
      }
    }
  ]
}
```

#### 跳過失敗節點

```json
{
  "error_strategy": "skip_dependents"
}
```

失敗時，只有依賴此節點的後續節點會被跳過，其他獨立節點繼續執行。

### 參數模板進階用法

#### 巢狀參數引用

```json
{
  "args_template": {
    "config": {
      "endpoint": "$inputs.api_endpoint",
      "auth_token": "@step_auth.outputs.token",
      "retry_count": 3
    }
  }
}
```

#### JSONPath 輸出提取

```json
{
  "export_outputs": {
    "user_id": "$.response.data.user.id",
    "session_token": "$.response.headers.authorization"
  }
}
```

### 技能版本管理

#### 更新技能

當您修改技能時，SkillFlow 會自動創建新版本：

```python
# 載入現有技能
skill = await skill_manager.get_skill("my_skill")

# 修改並更新
updated_skill = await skill_manager.update_skill(
    skill_id="my_skill",
    description="更新的描述",
    # 其他修改...
)
# 版本自動從 v1 -> v2
```

#### 使用特定版本

```
請獲取 my_skill 的版本 1 資訊
```

```python
get_skill(skill_id="my_skill", version=1)
```

### 查詢執行狀態

對於長時間運行的技能：

```python
# 獲取執行狀態
get_run_status(run_id="run_abc123")
```

返回：
```json
{
  "run_id": "run_abc123",
  "skill_id": "long_running_skill",
  "status": "running",
  "total_nodes": 10,
  "completed_nodes": 7,
  "failed_nodes": 0,
  "node_statuses": {
    "step_1": "success",
    "step_2": "success",
    ...
    "step_8": "running"
  }
}
```

### 取消執行

```python
cancel_run(run_id="run_abc123")
```

## 最佳實踐

### 1. 技能設計原則

#### 保持技能單一職責

❌ 不好的例子：
```
skill_id: "do_everything"
- 下載檔案
- 處理數據
- 發送郵件
- 清理緩存
```

✅ 好的例子：
```
skill_id: "download_and_process_data"
- 下載檔案
- 處理數據

skill_id: "send_report_email"
- 發送郵件
```

#### 使用有意義的 ID 和名稱

```json
{
  "id": "fetch_stock_prices_and_analyze",
  "name": "獲取股價並分析",
  "description": "從 API 獲取指定股票價格，計算移動平均線並生成報告"
}
```

### 2. 參數設計

#### 提供清晰的參數描述

```json
{
  "inputs_schema": {
    "type": "object",
    "properties": {
      "stock_symbol": {
        "type": "string",
        "description": "股票代碼（如 AAPL, GOOGL）"
      },
      "days": {
        "type": "integer",
        "description": "分析的天數（1-365）",
        "minimum": 1,
        "maximum": 365
      }
    }
  }
}
```

#### 設置合理的預設值

在 args_template 中為可選參數提供預設值。

### 3. 錯誤處理

#### 為關鍵節點設置重試

對於網絡請求、外部 API 調用等不穩定操作，使用 `retry` 策略。

#### 使用適當的錯誤策略

- 數據驗證：`fail_fast`
- 可選步驟：`skip_dependents`
- 通知步驟：`continue`

### 4. 效能優化

#### 識別可並行的步驟

```json
{
  "concurrency": {
    "mode": "phased",
    "phases": {
      "1": ["fetch_data_source_a", "fetch_data_source_b", "fetch_data_source_c"],
      "2": ["merge_data"],
      "3": ["analyze_merged_data"]
    }
  }
}
```

#### 設置合理的併發限制

在技能中設置 `max_parallel` 避免資源耗盡。

### 5. 文檔與維護

#### 使用 tags 組織技能

```json
{
  "tags": ["automation", "data-processing", "api", "daily-task"]
}
```

#### 在 metadata 中記錄額外資訊

```json
{
  "metadata": {
    "author_email": "user@example.com",
    "created_date": "2025-01-16",
    "dependencies": ["os-tools", "api-client"],
    "notes": "需要配置 API key"
  }
}
```

## 故障排除

### 常見問題

#### 1. 技能執行失敗：找不到上游 server

**錯誤訊息**：`Server os-tools not found in registry`

**解決方法**：
```
請列出所有已註冊的上游 server
```

如果 server 未註冊，使用 `register_upstream_server` 註冊。

#### 2. 參數模板解析錯誤

**錯誤訊息**：`Failed to resolve template: @step_xyz.outputs.field`

**原因**：
- 節點 ID 拼寫錯誤
- 前置節點未成功執行
- 輸出欄位不存在

**解決方法**：
1. 檢查技能定義中的節點 ID
2. 查看執行日誌確認前置節點輸出
3. 使用 `get_run_status` 查看詳細狀態

#### 3. 錄製的工具調用未被記錄

**原因**：
- 未啟動錄製
- 工具調用不是通過 SkillFlow 代理

**解決方法**：
- 確認已調用 `start_recording`
- 確認工具是通過註冊的上游 server 調用

#### 4. 技能創建失敗：參數提取錯誤

**錯誤訊息**：`Invalid source_path: logs[5].args.text`

**原因**：
- Session 中沒有第 5 個工具調用
- 路徑格式錯誤

**解決方法**：
```
請獲取 session <session_id> 的詳細資訊
```

查看實際的 logs 結構，調整 `source_path`。

### 調試技巧

#### 1. 查看執行日誌

```bash
# 在 data/runs/<date>/<run_id>.jsonl
cat data/runs/2025-01-16/run_abc123.jsonl | jq
```

#### 2. 手動測試工具調用

在創建技能前，手動測試各個工具調用確保它們正常工作。

#### 3. 逐步構建技能

從簡單的 2-3 步技能開始，驗證後再添加更多步驟。

#### 4. 使用測試數據

在正式環境前，用測試數據驗證技能。

## 下一步

- 探索 [API 參考文檔](API_REFERENCE.md)
- 查看 [示例技能](../examples/)
- 閱讀 [架構設計文檔](ARCHITECTURE.md)

---

有問題？請在 [GitHub Issues](https://github.com/your-repo/skillflow-mcp/issues) 提問。
