# SkillFlow MCP 使用指南

## 快速開始

### 安裝

```bash
# 克隆專案
git clone <repository-url>
cd skillflow-mcp

# 安裝基本依賴
uv sync

# 或安裝所有進階功能
uv sync --extra full
```

### 啟動服務

#### 1. MCP 伺服器模式（Claude Desktop 整合）

配置 Claude Desktop (`claude_desktop_config.json`):

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

#### 2. 獨立 Web UI 模式

```bash
# 啟動 Web UI（需要 web 擴展）
uv run skillflow-web

# 自訂配置
uv run skillflow-web --host 0.0.0.0 --port 8080 --data-dir ./data
```

Web UI 將在 http://localhost:8080 提供服務

## 核心功能

### 1. 技能錄製與重播

#### 開始錄製
```
在 Claude 中說：「開始錄製會話 'my_workflow'」
```

#### 執行操作
執行您想要自動化的多步驟操作

#### 停止錄製
```
在 Claude 中說：「停止錄製」
```

#### 創建技能
```
在 Claude 中說：「從最後一個會話創建技能」
```

#### 執行技能
```
在 Claude 中說：「執行 skill__my_workflow」
```

### 2. 進階功能（Phase 3）

#### 條件節點

創建包含條件邏輯的技能：

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
          "nodes": ["success_handler"]
        }
      ],
      "default_branch": ["error_handler"]
    }
  }
}
```

#### 迴圈節點

迭代處理集合：

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

#### 技能巢狀

在技能中調用其他技能：

```json
{
  "node": {
    "id": "call_sub_skill",
    "kind": "skill_call",
    "skill_id": "helper_skill",
    "args_template": {
      "input": "$inputs.data"
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

使用 Jinja2 範本：

```json
{
  "parameter_transform": {
    "engine": "jinja2",
    "expression": "{{ value | upper }} - {{ loop.index }}"
  }
}
```

### 3. Web UI 功能（Phase 5）

#### 儀表板（Dashboard）
- URL: http://localhost:8080/
- 查看即時指標
- 效能圖表
- 最近事件

#### 技能管理（Skills）
- URL: http://localhost:8080/skills
- 瀏覽所有技能
- 搜尋和過濾
- 檢視技能詳情
- 執行技能
- 刪除技能

#### DAG 編輯器（Editor）
- URL: http://localhost:8080/editor
- 視覺化技能編輯
- 拖放式節點創建
- 自動佈局
- 屬性編輯

#### 監控儀表板（Monitoring）
- URL: http://localhost:8080/monitoring
- 即時執行追蹤
- 效能圖表
- 執行歷史

#### 除錯工具（Debug）
- URL: http://localhost:8080/debug
- 技能檢查器
- 試運行模擬
- 測試輸入/輸出

#### 技能構建器（Builder）
- URL: http://localhost:8080/builder
- 逐步精靈
- 視覺化節點管理
- JSON 預覽

### 4. 稽核與監控（Phase 4）

#### 查看稽核日誌

稽核日誌儲存在 `data/audit/YYYY/MM/DD/`

通過 API 查詢：
```bash
curl http://localhost:8080/api/audit/events?limit=100
```

#### 查看指標

```bash
# 取得當前指標
curl http://localhost:8080/api/metrics

# 取得儀表板指標
curl http://localhost:8080/api/metrics/dashboard

# Prometheus 格式
curl http://localhost:8080/api/metrics/prometheus
```

#### 指標類型

- **執行時間**: P50, P95, P99 百分位數
- **吞吐量**: 每分鐘執行次數
- **錯誤率**: 失敗百分比
- **並發**: 活躍執行數
- **記憶體**: 使用量（MB）

## 進階配置

### 並發模式

```python
# 創建技能時指定並發模式
create_skill_from_session({
  "session_id": "...",
  "skill_id": "parallel_task",
  "concurrency_mode": "full_parallel",  # sequential | phased | full_parallel
  "max_parallel": 10
})
```

### 分階段執行

```python
create_skill_from_session({
  "session_id": "...",
  "concurrency_mode": "phased",
  "concurrency_phases": {
    "phase1": ["step_1", "step_2"],  # 並行執行
    "phase2": ["step_3", "step_4"]   # phase1 完成後執行
  }
})
```

### 上游伺服器連接

#### HTTP+SSE 傳輸

```json
{
  "server_id": "my_server",
  "transport": {
    "type": "http_sse",
    "url": "http://localhost:3000/sse"
  }
}
```

#### WebSocket 傳輸

```json
{
  "server_id": "my_server",
  "transport": {
    "type": "websocket",
    "url": "ws://localhost:3000/ws"
  }
}
```

## 範本變數

在技能中使用範本變數：

- `$inputs.field_name` - 技能輸入參數
- `@step_id.outputs.field` - 先前步驟輸出
- `$loop.item` - 當前迴圈項目
- `$loop.index` - 當前迴圈索引

範例：

```json
{
  "args_template": {
    "user_id": "$inputs.user_id",
    "previous_result": "@fetch_data.outputs.result",
    "item_name": "$loop.item.name",
    "iteration": "$loop.index"
  }
}
```

## 疑難排解

### Web UI 無法啟動

確保已安裝 web 擴展：

```bash
uv sync --extra web
```

### 指標不更新

確保已啟動 metrics collector：

```python
await metrics_collector.start()
```

### 稽核日誌未記錄

檢查 `data/audit/` 目錄權限

### 技能執行失敗

1. 查看稽核日誌：`data/audit/YYYY/MM/DD/*.json`
2. 使用除錯工具：http://localhost:8080/debug
3. 檢查執行追蹤

## API 參考

### 技能 API

- `GET /api/skills` - 列出所有技能
- `GET /api/skills/{skill_id}` - 取得技能詳情
- `POST /api/skills/{skill_id}/execute` - 執行技能
- `DELETE /api/skills/{skill_id}` - 刪除技能

### 指標 API

- `GET /api/metrics` - 取得當前指標
- `GET /api/metrics/dashboard` - 取得儀表板指標
- `GET /api/metrics/{metric_name}/history` - 取得指標歷史
- `GET /api/metrics/prometheus` - Prometheus 格式

### 稽核 API

- `GET /api/audit/events` - 查詢稽核事件
- `GET /api/audit/statistics` - 取得稽核統計

## 最佳實踐

1. **技能命名**: 使用描述性名稱，如 `backup_files` 而非 `task1`
2. **錯誤處理**: 使用條件節點處理錯誤情況
3. **迴圈限制**: 始終設置 `max_iterations` 防止無限迴圈
4. **監控**: 定期檢查儀表板了解系統健康狀況
5. **稽核**: 保留稽核日誌以便問題追蹤
6. **備份**: 定期備份 `data/` 目錄

## 效能優化

1. **使用並發**: 對獨立任務使用 `full_parallel` 模式
2. **分階段執行**: 對有依賴關係的任務使用 `phased` 模式
3. **限制並發數**: 設置適當的 `max_parallel` 值
4. **監控指標**: 使用 P95/P99 識別效能瓶頸

## 安全考慮

1. **Web UI**: 僅在受信任的網路上暴露
2. **API 存取**: 考慮添加身份驗證（未來功能）
3. **稽核日誌**: 包含敏感資訊，妥善保護
4. **資料目錄**: 設置適當的檔案權限

## 更多資源

- [完整文件](docs/)
- [範例技能](examples/)
- [更新日誌](CHANGELOG.md)
- [疑難排解](docs/TROUBLESHOOTING.md)
