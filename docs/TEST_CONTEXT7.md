# Context7 與 SkillFlow 整合測試指南

## 測試目標

驗證 SkillFlow 技能能夠：
1. 調用 context7 MCP 工具
2. 處理返回的文檔數據
3. 將結果輸出給用戶

## 當前狀態

✅ **已完成**:
- SkillFlow MCP server 已部署並運行
- Context7 MCP 工具可用
- 示例技能定義已創建

⚠️ **架構考量**:
SkillFlow 目前設計用於調用**外部 MCP server**，而 context7 是**同環境的 MCP 工具**。需要測試兩種整合方式。

## 測試方案

### 方案 A: 直接 MCP 工具調用（驗證 context7 可用性）

這個方案驗證 context7 工具在您的環境中正常工作。

#### 步驟 1: 測試 resolve-library-id

在 Claude Code 或 MCP 客戶端中執行：

```
請使用 mcp__context7__resolve-library-id 工具查找 "react" 庫
```

**預期結果**: 返回 React 庫的列表，包含 library ID 如 `/websites/react_dev`

#### 步驟 2: 測試 get-library-docs

```
請使用 mcp__context7__get-library-docs 工具獲取 React 文檔

參數:
- context7CompatibleLibraryID: "/websites/react_dev"
- topic: "hooks"
- tokens: 3000
```

**預期結果**: 返回 React hooks 相關的文檔內容

### 方案 B: 通過 SkillFlow 技能調用（完整整合測試）

#### 步驟 1: 確認技能已加載

```
請使用 list_skills 工具列出所有技能
```

**預期結果**: 看到 `fetch_library_docs` 技能

#### 步驟 2: 查看技能詳情

```
請使用 get_skill 工具獲取 fetch_library_docs 技能的詳細信息
```

**預期結果**: 顯示技能的完整定義，包括兩個節點：
- `resolve_library`: 解析庫 ID
- `get_docs`: 獲取文檔

#### 步驟 3: 執行技能（需要架構支持）

```
請執行 skill__fetch_library_docs 技能

參數:
- library_name: "vue"
- topic: "components"
```

**預期結果**:
- ✅ 如果架構已擴展: 返回 Vue components 文檔
- ⚠️ 如果架構未擴展: 可能報錯「找不到 server」

## 架構擴展方案（使技能正常工作）

如果方案 B 步驟 3 失敗，需要擴展 SkillFlow 架構。

### 選項 1: 修改執行引擎（推薦）

修改 `src/skillflow/engine.py` 以支持本地 MCP 工具：

```python
async def _execute_tool_call(self, context, node, args):
    """Execute a tool call."""

    # 檢測是否為本地 MCP 工具
    if node.tool.startswith("mcp__"):
        # TODO: 實現本地 MCP 工具調用
        # 這需要訪問當前 MCP session 的工具列表
        raise NotImplementedError(
            f"本地 MCP 工具 {node.tool} 調用尚未實現。"
            f"請使用 wrapper 工具或註冊為上游 server。"
        )

    # 調用上游 server 工具
    return await self.tool_executor(node.server, node.tool, args)
```

### 選項 2: 創建 Wrapper 工具（快速方案）

在 `src/skillflow/server.py` 中添加：

```python
@self.server.call_tool()
async def fetch_docs_from_context7(
    library_name: str,
    topic: Optional[str] = None,
    max_tokens: int = 5000
) -> list[TextContent]:
    """從 context7 獲取庫文檔（wrapper 工具）."""

    import json

    # 注意: 這是示意代碼
    # 實際需要調用 context7 MCP 工具的機制

    result = {
        "library": library_name,
        "topic": topic or "general",
        "status": "需要實現 context7 調用邏輯",
        "note": "這是一個 wrapper 工具示例"
    }

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2, ensure_ascii=False)
    )]
```

然後創建使用這個 wrapper 的技能：

```json
{
  "nodes": [
    {
      "id": "fetch_docs",
      "kind": "tool_call",
      "server": null,
      "tool": "fetch_docs_from_context7",
      "args_template": {
        "library_name": "$inputs.library_name",
        "topic": "$inputs.topic"
      }
    }
  ]
}
```

### 選項 3: 註冊 Context7 為上游 Server（變通方案）

如果 context7 可以作為獨立 MCP server 運行：

```
請使用 register_upstream_server 工具註冊 context7

參數:
- server_id: "context7"
- name: "Context7 Documentation"
- transport: "stdio"
- config: {
    "command": "...",
    "args": [...]
  }
```

然後在技能中使用：
```json
{
  "server": "context7",
  "tool": "resolve-library-id"
}
```

## 實際測試結果記錄

### 測試環境
- SkillFlow 版本: 0.1.0
- MCP 客戶端: [填寫]
- Context7 版本: [填寫]

### 方案 A 測試結果

| 步驟 | 狀態 | 結果 | 備註 |
|------|------|------|------|
| resolve-library-id | [ ] | | |
| get-library-docs | [ ] | | |

### 方案 B 測試結果

| 步驟 | 狀態 | 結果 | 備註 |
|------|------|------|------|
| list_skills | [ ] | | |
| get_skill | [ ] | | |
| 執行技能 | [ ] | | |

## 成功標準

✅ **基本成功**: 方案 A 所有步驟通過
✅ **部分成功**: 方案 B 步驟 1-2 通過（技能已創建並可查看）
✅ **完全成功**: 方案 B 所有步驟通過（技能可正常執行）

## 故障排除

### 問題 1: context7 工具找不到

**症狀**: `Tool mcp__context7__resolve-library-id not found`

**解決方案**:
1. 檢查 MCP 客戶端配置
2. 確認 context7 MCP server 已啟動
3. 使用 `/mcp list` 查看已連接的 server

### 問題 2: 技能執行失敗

**症狀**: `Server context7 not found in registry`

**原因**: SkillFlow 無法找到 context7 作為上游 server

**解決方案**:
1. 使用選項 2（wrapper 工具）
2. 或實現選項 1（擴展執行引擎）

### 問題 3: 參數傳遞錯誤

**症狀**: 技能調用時參數未正確傳遞

**檢查**:
1. 查看技能定義中的 `args_template`
2. 確認參數模板語法正確（`$inputs.xxx`）
3. 使用 `get_run_status` 查看詳細錯誤

## 下一步

根據測試結果：

1. **如果方案 A 通過**: Context7 工具可用 ✅
2. **如果方案 B 步驟 1-2 通過**: 技能定義正確 ✅
3. **如果方案 B 步驟 3 失敗**: 需要實現架構擴展

選擇一個架構擴展選項並實施：
- [ ] 選項 1: 修改執行引擎
- [ ] 選項 2: 創建 wrapper 工具
- [ ] 選項 3: 註冊為上游 server

## 參考資料

- SkillFlow 文檔: `USAGE_GUIDE.md`
- Context7 MCP 文檔: [鏈接]
- 技能定義: `data/skills/fetch_library_docs/v0001.json`
