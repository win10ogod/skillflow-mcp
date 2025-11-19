# MCP 服務器配置更新修復

## 問題描述

添加新的 MCP 服務器後，無法立即看到新服務器的工具。

### 根本原因

1. **MCPClientManager 緩存了 registry**
   - 在初始化時加載了服務器註冊表
   - 當添加/刪除服務器時，registry 被保存到磁盤
   - 但是 MCPClientManager 的內存緩存 `_registry` 沒有更新

2. **list_servers() 使用緩存**
   - `list_servers()` 優先使用緩存的 `_registry`
   - 只有在 `_registry` 為 None 時才重新加載
   - 所以新添加的服務器不會被發現

3. **_get_upstream_tools() 看不到新服務器**
   - 調用 `list_servers()` 獲取服務器列表
   - 因為使用舊緩存，所以看不到新服務器
   - 新服務器的工具不會被獲取

---

## 修復方案

### 1. 添加 reload_registry() 方法

**文件**: `src/skillflow/mcp_clients.py`

```python
async def reload_registry(self):
    """Reload server registry from storage.

    Call this after adding/removing/updating servers to pick up changes.
    """
    self._registry = await self.storage.load_registry()
    logger.info(f"Reloaded registry with {len(self._registry.servers)} servers")
```

### 2. 在配置更改後自動重新加載

**文件**: `src/skillflow/server.py`

#### add_mcp_server 工具
```python
# Save registry
await self.storage.save_registry(registry)

# Reload registry in MCP client manager
await self.mcp_clients.reload_registry()

# Invalidate upstream tool cache for this server
await self._upstream_tool_cache.invalidate(server_id)
```

#### remove_mcp_server 工具
```python
# Save registry
await self.storage.save_registry(registry)

# Reload registry in MCP client manager
await self.mcp_clients.reload_registry()

# Invalidate upstream tool cache
await self._upstream_tool_cache.invalidate(server_id)

# Disconnect if currently connected
await self.mcp_clients.disconnect_server(server_id)
```

#### import_claude_code_config 工具
```python
# Save registry
await self.storage.save_registry(merged_registry)

# Reload registry and invalidate caches
await self.mcp_clients.reload_registry()
await self._upstream_tool_cache.invalidate()  # Clear all
```

---

## 使用說明

### 添加服務器後看到新工具

**方法 1: 自動刷新（推薦）**

添加服務器後，registry 會自動重新加載，但 MCP 客戶端需要刷新：

```javascript
// 1. 添加服務器
add_mcp_server({
  server_id: "my-server",
  name: "My Server",
  transport: "stdio",
  command: "node",
  args: ["server.js"]
})

// 2. 在 MCP 客戶端中刷新工具列表
// Claude Desktop: 重新連接或重啟
// 其他客戶端: 調用 list_tools()
```

**方法 2: 手動觸發工具獲取**

```javascript
// 1. 添加服務器
add_mcp_server({...})

// 2. 立即刷新上游工具
refresh_upstream_tools()

// 3. 現在新工具已經被獲取並緩存
// 下次 list_tools() 會包含新工具
```

---

## 工作流程

### 添加服務器後的完整流程

```
1. 用戶調用 add_mcp_server
   ↓
2. 創建 ServerConfig 並保存到 registry.servers
   ↓
3. 保存 registry 到磁盤 (data/registry/servers.json)
   ↓
4. 調用 mcp_clients.reload_registry()
   → MCPClientManager 重新加載 registry
   → _registry 現在包含新服務器 ✅
   ↓
5. 失效上游工具緩存
   → 下次 _get_upstream_tools() 會重新獲取
   ↓
6. MCP 客戶端刷新（需要用戶操作）
   → 調用 list_tools()
   → _get_upstream_tools() 看到新服務器
   → 連接到新服務器並獲取工具
   → 返回包含新工具的列表 ✅
```

---

## MCP 客戶端緩存問題

### 為什麼還需要刷新客戶端？

MCP 協議的限制：
- 客戶端（如 Claude Desktop）在初始化時調用 `list_tools()`
- 客戶端緩存工具列表在本地
- 服務器**無法主動推送**工具列表更新

### 解決方法

**方法 1: 重新連接**
- Claude Desktop: 斷開並重新連接
- 這會觸發新的 `list_tools()` 調用

**方法 2: 調用 refresh_upstream_tools**
```javascript
// 添加服務器後
add_mcp_server({...})

// 立即獲取新工具（服務器端）
refresh_upstream_tools()

// 然後刷新客戶端以看到新工具
```

**方法 3: 重啟客戶端**
- 最簡單但最慢的方法

---

## 返回消息改進

現在所有配置更改工具都會提示用戶：

```
✅ Added MCP server 'my-server' (My Server)
Transport: stdio
Enabled: true
Total servers: 4

⚠️ Note: New tools will appear after you call list_tools() again or refresh your MCP client.
You can also call 'refresh_upstream_tools' to fetch tools immediately.
```

---

## 測試驗證

### 測試 1: 添加服務器

```javascript
// 1. 記錄當前工具數量
const before = list_tools()
console.log(`Before: ${before.length} tools`)

// 2. 添加新服務器
add_mcp_server({
  server_id: "test",
  name: "Test Server",
  transport: "stdio",
  command: "npx",
  args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
})

// 3. 刷新工具
refresh_upstream_tools()

// 4. 刷新客戶端後檢查
const after = list_tools()
console.log(`After: ${after.length} tools`)

// 應該看到新工具
```

### 測試 2: 批量導入

```javascript
// 導入多個服務器
import_claude_code_config({
  config_json: JSON.stringify({
    "servers": {
      "server1": {...},
      "server2": {...},
      "server3": {...}
    }
  })
})

// 刷新所有工具
refresh_upstream_tools()

// 刷新客戶端後應該看到所有新工具
```

---

## 調試日誌

修復後的日誌輸出：

```
[Skillflow] Registry reloaded after adding server 'my-server'
[Skillflow] Fetching tools from My Server...
[Skillflow] Found 15 tools from My Server
[Skillflow] Fetched 45 proxy tools in 1234ms
```

---

## 總結

### 修復內容

✅ 添加 `reload_registry()` 方法到 MCPClientManager
✅ 在 `add_mcp_server` 後自動重新加載 registry
✅ 在 `remove_mcp_server` 後自動重新加載 registry
✅ 在 `import_claude_code_config` 後自動重新加載 registry
✅ 自動失效相關的上游工具緩存
✅ 改進返回消息，提示用戶如何查看新工具

### 使用方法

1. **添加服務器** → 自動重新加載
2. **刷新工具**（可選）→ `refresh_upstream_tools()`
3. **刷新客戶端** → 重新連接或調用 `list_tools()`

現在添加 MCP 服務器後，工具會正確顯示！🎉
