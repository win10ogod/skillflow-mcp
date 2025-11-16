# API Reference

Complete REST API documentation for SkillFlow MCP Web Server.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, no authentication is required. Future versions will support API keys and OAuth.

---

## Skills API

### List All Skills

Get a list of all available skills.

**Endpoint**: `GET /api/skills`

**Response**:
```json
{
  "skills": [
    {
      "id": "skill_id",
      "name": "Skill Name",
      "description": "Skill description",
      "graph": {
        "nodes": [...],
        "edges": [...]
      },
      "concurrency_mode": "sequential",
      "max_parallel": 10,
      "created_at": "2025-11-16T10:30:00Z",
      "updated_at": "2025-11-16T10:30:00Z"
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8080/api/skills
```

---

### Get Skill Details

Get detailed information about a specific skill.

**Endpoint**: `GET /api/skills/{skill_id}`

**Parameters**:
- `skill_id` (path) - Unique skill identifier

**Response**:
```json
{
  "id": "skill_id",
  "name": "Skill Name",
  "description": "Detailed description",
  "graph": {
    "nodes": [
      {
        "id": "node1",
        "kind": "tool_call",
        "tool_name": "filesystem__read_file",
        "args_template": {...},
        "depends_on": []
      }
    ],
    "edges": [
      {"from": "node1", "to": "node2"}
    ]
  },
  "concurrency_mode": "sequential",
  "max_parallel": 10,
  "metadata": {...}
}
```

**Example**:
```bash
curl http://localhost:8080/api/skills/my_skill
```

---

### Execute Skill

Execute a skill with given inputs.

**Endpoint**: `POST /api/skills/{skill_id}/execute`

**Parameters**:
- `skill_id` (path) - Unique skill identifier

**Request Body**:
```json
{
  "inputs": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Response**:
```json
{
  "run_id": "run_abc123",
  "status": "completed",
  "outputs": {...},
  "node_executions": [
    {
      "node_id": "node1",
      "status": "success",
      "outputs": {...},
      "started_at": "2025-11-16T10:30:00Z",
      "completed_at": "2025-11-16T10:30:05Z"
    }
  ],
  "started_at": "2025-11-16T10:30:00Z",
  "completed_at": "2025-11-16T10:30:10Z",
  "duration_ms": 10000
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/skills/my_skill/execute \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"file_path": "/path/to/file.txt"}}'
```

---

### Delete Skill

Delete a skill permanently.

**Endpoint**: `DELETE /api/skills/{skill_id}`

**Parameters**:
- `skill_id` (path) - Unique skill identifier

**Response**:
```json
{
  "message": "Skill deleted successfully"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8080/api/skills/my_skill
```

---

## Metrics API

### Get Current Metrics

Get current system metrics snapshot.

**Endpoint**: `GET /api/metrics`

**Response**:
```json
{
  "current": {
    "active_executions": 5,
    "total_skills": 42,
    "memory_mb": 256.5
  },
  "aggregated": {
    "total_executions": 1523,
    "total_tool_calls": 4569,
    "success_rate": 98.5,
    "error_rate": 1.5
  },
  "performance": {
    "avg_execution_time_ms": 1234,
    "p50_execution_time_ms": 1000,
    "p95_execution_time_ms": 2500,
    "p99_execution_time_ms": 5000
  }
}
```

**Example**:
```bash
curl http://localhost:8080/api/metrics
```

---

### Get Dashboard Metrics

Get metrics formatted for dashboard display.

**Endpoint**: `GET /api/metrics/dashboard`

**Response**:
```json
{
  "current": {
    "active_executions": 5,
    "memory_mb": 256.5
  },
  "performance": {
    "p50": 1000,
    "p95": 2500,
    "p99": 5000
  },
  "throughput": {
    "executions_per_minute": 12.5
  },
  "error_rate": 1.5,
  "recent_executions": [...]
}
```

**Example**:
```bash
curl http://localhost:8080/api/metrics/dashboard
```

---

### Get Metric History

Get historical data for a specific metric.

**Endpoint**: `GET /api/metrics/{metric_name}/history`

**Parameters**:
- `metric_name` (path) - Name of the metric
- `minutes` (query, optional) - Time window in minutes (default: 60)

**Response**:
```json
{
  "metric": "execution_time_ms",
  "points": [
    {
      "timestamp": "2025-11-16T10:30:00Z",
      "value": 1234
    },
    {
      "timestamp": "2025-11-16T10:31:00Z",
      "value": 1456
    }
  ]
}
```

**Example**:
```bash
curl "http://localhost:8080/api/metrics/execution_time_ms/history?minutes=120"
```

---

### Get Prometheus Metrics

Get metrics in Prometheus exposition format.

**Endpoint**: `GET /api/metrics/prometheus`

**Response** (text/plain):
```
# HELP skillflow_executions_total Total number of skill executions
# TYPE skillflow_executions_total counter
skillflow_executions_total 1523

# HELP skillflow_execution_time_ms Execution time in milliseconds
# TYPE skillflow_execution_time_ms histogram
skillflow_execution_time_ms_bucket{le="100"} 234
skillflow_execution_time_ms_bucket{le="500"} 890
skillflow_execution_time_ms_bucket{le="1000"} 1200
skillflow_execution_time_ms_sum 1890456
skillflow_execution_time_ms_count 1523
```

**Example**:
```bash
curl http://localhost:8080/api/metrics/prometheus
```

---

## Audit API

### Query Audit Events

Query audit log events with filters.

**Endpoint**: `GET /api/audit/events`

**Query Parameters**:
- `event_type` (optional) - Filter by event type
- `severity` (optional) - Filter by severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `skill_id` (optional) - Filter by skill ID
- `limit` (optional) - Maximum number of events (default: 100)

**Response**:
```json
{
  "events": [
    {
      "event_id": "evt_abc123",
      "event_type": "skill_executed",
      "timestamp": "2025-11-16T10:30:00Z",
      "severity": "INFO",
      "message": "Skill executed successfully",
      "skill_id": "my_skill",
      "run_id": "run_abc123",
      "metadata": {...}
    }
  ],
  "total": 256
}
```

**Example**:
```bash
curl "http://localhost:8080/api/audit/events?event_type=skill_executed&limit=50"
```

---

### Get Audit Statistics

Get aggregated statistics from audit logs.

**Endpoint**: `GET /api/audit/statistics`

**Query Parameters**:
- `minutes` (optional) - Time window in minutes (default: 60)

**Response**:
```json
{
  "time_window_minutes": 60,
  "total_events": 1234,
  "by_type": {
    "skill_executed": 500,
    "skill_created": 50,
    "tool_call_completed": 600
  },
  "by_severity": {
    "INFO": 1000,
    "WARNING": 200,
    "ERROR": 34
  },
  "error_rate": 2.76
}
```

**Example**:
```bash
curl "http://localhost:8080/api/audit/statistics?minutes=120"
```

---

## MCP Server Testing API

### List MCP Servers

List all configured MCP servers.

**Endpoint**: `GET /api/mcp/servers`

**Response**:
```json
{
  "servers": [
    {
      "server_id": "filesystem",
      "transport_type": "stdio",
      "connected": true
    },
    {
      "server_id": "web_search",
      "transport_type": "http_sse",
      "connected": false
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8080/api/mcp/servers
```

---

### List Server Tools

List all tools available from an MCP server.

**Endpoint**: `GET /api/mcp/servers/{server_id}/tools`

**Parameters**:
- `server_id` (path) - MCP server identifier

**Response**:
```json
{
  "server_id": "filesystem",
  "tools": [
    {
      "name": "read_file",
      "description": "Read contents of a file",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string"}
        },
        "required": ["path"]
      }
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8080/api/mcp/servers/filesystem/tools
```

---

### Test Server Connection

Test connection to an MCP server.

**Endpoint**: `POST /api/mcp/servers/{server_id}/test`

**Parameters**:
- `server_id` (path) - MCP server identifier

**Response**:
```json
{
  "server_id": "filesystem",
  "status": "connected",
  "tool_count": 15,
  "message": "Successfully connected. Found 15 tools."
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/mcp/servers/filesystem/test
```

---

### Invoke MCP Tool

Invoke a tool from an MCP server for testing.

**Endpoint**: `POST /api/mcp/tools/invoke`

**Request Body**:
```json
{
  "server_id": "filesystem",
  "tool_name": "read_file",
  "arguments": {
    "path": "/path/to/file.txt"
  }
}
```

**Response**:
```json
{
  "server_id": "filesystem",
  "tool_name": "read_file",
  "result": {
    "content": "File contents here...",
    "size": 1234
  },
  "status": "success"
}
```

**Example**:
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

### Real-time Updates

Connect to the WebSocket endpoint for real-time system updates.

**Endpoint**: `WS /ws`

**Message Format** (Server → Client):
```json
{
  "type": "update",
  "metrics": {
    "current": {...},
    "performance": {...}
  },
  "recent_events": [...]
}
```

**Example** (JavaScript):
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'update') {
    console.log('Metrics:', data.metrics);
    console.log('Events:', data.recent_events);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

---

## Error Responses

All API endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200 OK` - Request successful
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

---

## Rate Limiting

Currently, there is no rate limiting. Future versions will implement rate limiting to prevent abuse.

---

## Versioning

API version is indicated in the server response headers:

```
X-API-Version: 0.3.0
```

Breaking changes will be introduced with major version increments.

---

**Last Updated**: 2025-11-16
**Version**: 0.3.0
