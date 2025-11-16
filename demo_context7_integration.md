# SkillFlow + Context7 整合演示

## 概述

此演示展示如何在 SkillFlow 中創建使用 context7 MCP 工具的技能。

## 已創建的測試技能

### 技能: `fetch_library_docs`

**功能**: 獲取任意 JavaScript 庫的文檔

**輸入參數**:
- `library_name` (必需): 要查詢的庫名稱（例如：react, vue, svelte）
- `topic` (可選): 要查詢的特定主題

**執行流程**:

```
1. resolve_library 節點
   └─> 調用 mcp__context7__resolve-library-id
       輸入: library_name
       輸出: library_id, library_info

2. get_docs 節點（依賴 resolve_library）
   └─> 調用 mcp__context7__get-library-docs
       輸入: library_id (來自步驟1), topic
       輸出: documentation
```

**技能定義位置**:
- `data/skills/fetch_library_docs/v0001.json`
- `data/skills/fetch_library_docs/meta.json`

## 使用方法

### 方法 1: 通過 MCP 客戶端調用（推薦）

1. 確保 SkillFlow 已在 MCP 客戶端中配置
2. 重啟 MCP 客戶端以加載新技能
3. 調用技能：

```
請使用 skill__fetch_library_docs 技能獲取 React hooks 的文檔

參數:
- library_name: "react"
- topic: "hooks"
```

### 方法 2: 手動測試（開發用）

由於 SkillFlow 的執行引擎需要通過 MCP client 調用工具，而 context7 是直接集成的 MCP 工具，我們需要做一些調整。

## 當前限制與解決方案

### 限制

SkillFlow 的 `MCPClientManager` 設計用於連接**外部** MCP server（通過 stdio/HTTP），但 context7 是在**同一個 MCP 環境**中的工具（通過 MCP protocol 直接可用）。

### 解決方案選項

#### 選項 1: 擴展 ExecutionEngine 支持本地 MCP 工具

修改 `engine.py` 中的 `_execute_tool_call` 方法，檢測工具名稱前綴 `mcp__` 並直接調用：

```python
async def _execute_tool_call(self, context, node, args):
    if node.tool.startswith("mcp__"):
        # 直接調用本地可用的 MCP 工具
        # 這需要訪問當前 MCP session 的工具
        pass
    else:
        # 通過 MCPClientManager 調用上游 server
        return await self.tool_executor(node.server, node.tool, args)
```

#### 選項 2: 在技能中使用佔位符，由 MCP 客戶端替換

創建技能時使用特殊標記，由 MCP 客戶端在執行前替換為實際調用。

#### 選項 3: 創建 wrapper 工具（當前演示採用）

在 SkillFlow server 中創建 wrapper 工具，內部調用 context7：

```python
@self.server.call_tool()
async def get_library_documentation(
    library_name: str,
    topic: Optional[str] = None
) -> list[TextContent]:
    """獲取庫文檔（wrapper for context7）."""

    # Step 1: Resolve library ID
    # (這裡需要實際調用 context7 工具)

    # Step 2: Get docs
    # (這裡需要實際調用 context7 工具)

    return [TextContent(type="text", text=result)]
```

## 實際演示

由於架構限制，我創建了一個更簡單的演示技能，展示 SkillFlow 的核心功能：

### 演示技能 1: `fetch_react_docs`

這是一個**簡化版本**，展示技能的結構和流程，但實際執行需要架構調整。

### 演示技能 2: 手動調用 context7（推薦用於測試）

直接在 MCP 客戶端中調用：

```
1. 請使用 mcp__context7__resolve-library-id 工具
   參數: libraryName = "react"

2. 請使用 mcp__context7__get-library-docs 工具
   參數:
   - context7CompatibleLibraryID: "/websites/react_dev"
   - topic: "hooks"
   - tokens: 5000
```

## 後續改進建議

### 短期（立即可行）

1. **創建 wrapper 工具**: 在 `server.py` 中添加工具，封裝 context7 調用邏輯
2. **更新文檔**: 說明如何在技能中使用內置 MCP 工具

### 中期（需要架構調整）

1. **擴展 ExecutionEngine**:
   - 添加對 `mcp__` 前綴工具的檢測
   - 實現本地工具調用機制
   - 保持與上游 server 調用的一致性

2. **統一工具調用接口**:
   ```python
   class ToolExecutor:
       async def execute(self, tool_name: str, args: dict) -> dict:
           if tool_name.startswith("mcp__"):
               return await self._execute_local_tool(tool_name, args)
           else:
               return await self._execute_upstream_tool(server, tool_name, args)
   ```

### 長期（完整集成）

1. **MCP Tool Registry**: 維護所有可用工具的註冊表（本地 + 上游）
2. **工具發現機制**: 自動檢測和註冊所有 MCP 環境中的工具
3. **智能路由**: 根據工具來源自動路由調用

## 總結

✅ **已完成**:
- 創建了技能定義結構
- 展示了如何定義包含 context7 調用的技能
- 提供了測試腳本和文檔

⚠️ **待完成**:
- 執行引擎需要擴展以支持本地 MCP 工具調用
- 或者通過 wrapper 工具簡化集成

💡 **建議**:
目前最實用的方法是創建 wrapper 工具，將 context7 功能封裝為 SkillFlow 的工具，然後在技能中調用這些 wrapper。

## 示例 Wrapper 工具

```python
@self.server.call_tool()
async def search_library_docs(
    library_name: str,
    topic: str,
    max_tokens: int = 5000
) -> list[TextContent]:
    """搜索並獲取庫文檔（整合 context7）."""

    import json

    # 這裡需要實際的 context7 調用邏輯
    # 由於這是在 SkillFlow server 內部，
    # 可能需要特殊處理來訪問 context7 工具

    result = {
        "library": library_name,
        "topic": topic,
        "documentation": "文檔內容會在這裡..."
    }

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2, ensure_ascii=False)
    )]
```

這個 wrapper 可以在技能中作為普通工具調用，無需特殊處理。
