# API 參考文檔

SkillFlow MCP Web 伺服器完整 REST API 文檔。

## 基礎 URL

```
http://localhost:8080
```

## 身份驗證

目前不需要身份驗證。未來版本將支援 API 金鑰和 OAuth。

---

## 技能 API

### 列出所有技能

獲取所有可用技能的列表。

**端點**：`GET /api/skills`

**回應**：
```json
{
  "skills": [
    {
      "id": "skill_id",
      "name": "技能名稱",
      "description": "技能描述",
      "graph": {
        "nodes": [...],
        "edges": [...]
      },
      "concurrency_mode": "sequential",
      "max_parallel": 10
    }
  ]
}
```

**範例**：
```bash
curl http://localhost:8080/api/skills
```

---

### 獲取技能詳情

獲取特定技能的詳細資訊。

**端點**：`GET /api/skills/{skill_id}`

**參數**：
- `skill_id` (路徑) - 唯一技能識別碼

**範例**：
```bash
curl http://localhost:8080/api/skills/my_skill
```

---

### 執行技能

使用給定輸入執行技能。

**端點**：`POST /api/skills/{skill_id}/execute`

**請求主體**：
```json
{
  "inputs": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**回應**：
```json
{
  "run_id": "run_abc123",
  "status": "completed",
  "outputs": {...},
  "duration_ms": 10000
}
```

**範例**：
```bash
curl -X POST http://localhost:8080/api/skills/my_skill/execute \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"file_path": "/path/to/file.txt"}}'
```

---

### 刪除技能

永久刪除技能。

**端點**：`DELETE /api/skills/{skill_id}`

**範例**：
```bash
curl -X DELETE http://localhost:8080/api/skills/my_skill
```

---

## 指標 API

### 獲取當前指標

獲取當前系統指標快照。

**端點**：`GET /api/metrics`

**回應**：
```json
{
  "current": {
    "active_executions": 5,
    "total_skills": 42,
    "memory_mb": 256.5
  },
  "performance": {
    "p50_execution_time_ms": 1000,
    "p95_execution_time_ms": 2500,
    "p99_execution_time_ms": 5000
  }
}
```

---

### 獲取儀表板指標

獲取格式化用於儀表板顯示的指標。

**端點**：`GET /api/metrics/dashboard`

---

### 獲取指標歷史

獲取特定指標的歷史資料。

**端點**：`GET /api/metrics/{metric_name}/history`

**參數**：
- `metric_name` (路徑) - 指標名稱
- `minutes` (查詢，選用) - 時間窗口（分鐘，預設：60）

**範例**：
```bash
curl "http://localhost:8080/api/metrics/execution_time_ms/history?minutes=120"
```

---

### 獲取 Prometheus 指標

以 Prometheus 格式獲取指標。

**端點**：`GET /api/metrics/prometheus`

**範例**：
```bash
curl http://localhost:8080/api/metrics/prometheus
```

---

## 稽核 API

### 查詢稽核事件

使用篩選器查詢稽核日誌事件。

**端點**：`GET /api/audit/events`

**查詢參數**：
- `event_type` (選用) - 按事件類型篩選
- `severity` (選用) - 按嚴重性篩選 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `skill_id` (選用) - 按技能 ID 篩選
- `limit` (選用) - 最大事件數（預設：100）

**回應**：
```json
{
  "events": [
    {
      "event_id": "evt_abc123",
      "event_type": "skill_executed",
      "timestamp": "2025-11-16T10:30:00Z",
      "severity": "INFO",
      "message": "技能執行成功",
      "skill_id": "my_skill"
    }
  ],
  "total": 256
}
```

**範例**：
```bash
curl "http://localhost:8080/api/audit/events?event_type=skill_executed&limit=50"
```

---

### 獲取稽核統計

從稽核日誌獲取聚合統計資訊。

**端點**：`GET /api/audit/statistics`

**查詢參數**：
- `minutes` (選用) - 時間窗口（分鐘，預設：60）

---

## MCP 伺服器測試 API

### 列出 MCP 伺服器

列出所有已配置的 MCP 伺服器。

**端點**：`GET /api/mcp/servers`

**回應**：
```json
{
  "servers": [
    {
      "server_id": "filesystem",
      "transport_type": "stdio",
      "connected": true
    }
  ]
}
```

---

### 列出伺服器工具

列出 MCP 伺服器可用的所有工具。

**端點**：`GET /api/mcp/servers/{server_id}/tools`

**參數**：
- `server_id` (路徑) - MCP 伺服器識別碼

---

### 測試伺服器連接

測試與 MCP 伺服器的連接。

**端點**：`POST /api/mcp/servers/{server_id}/test`

**回應**：
```json
{
  "server_id": "filesystem",
  "status": "connected",
  "tool_count": 15,
  "message": "成功連接。找到 15 個工具。"
}
```

---

### 調用 MCP 工具

調用 MCP 伺服器的工具進行測試。

**端點**：`POST /api/mcp/tools/invoke`

**請求主體**：
```json
{
  "server_id": "filesystem",
  "tool_name": "read_file",
  "arguments": {
    "path": "/path/to/file.txt"
  }
}
```

**範例**：
```bash
curl -X POST http://localhost:8080/api/mcp/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "filesystem",
    "tool_name": "read_file",
    "arguments": {"path": "/path/to/file.txt"}
  }'
```

---

## WebSocket API

### 即時更新

連接到 WebSocket 端點以獲取即時系統更新。

**端點**：`WS /ws`

**訊息格式**（伺服器 → 客戶端）：
```json
{
  "type": "update",
  "metrics": {...},
  "recent_events": [...]
}
```

**範例** (JavaScript)：
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  console.log('已連接');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'update') {
    console.log('指標:', data.metrics);
    console.log('事件:', data.recent_events);
  }
};
```

---

## 錯誤回應

所有 API 端點可能會返回以下格式的錯誤回應：

```json
{
  "detail": "描述錯誤的訊息"
}
```

### HTTP 狀態碼

- `200 OK` - 請求成功
- `404 Not Found` - 資源未找到
- `500 Internal Server Error` - 伺服器錯誤
- `503 Service Unavailable` - 服務暫時不可用

---

**最後更新**：2025-11-16
**版本**：0.3.0
