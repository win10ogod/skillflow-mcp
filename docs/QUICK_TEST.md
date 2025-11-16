# Context7 整合快速測試

## 🚀 立即測試（5分鐘）

### 測試 1: 驗證 Context7 工具可用 ✅

在您的 MCP 客戶端中執行：

```
請使用 mcp__context7__resolve-library-id 工具查找 "react" 庫
```

**預期結果**: 顯示 React 庫列表，包含多個版本和來源

---

### 測試 2: 獲取實際文檔 ✅

```
請使用 mcp__context7__get-library-docs 工具

參數:
- context7CompatibleLibraryID: "/websites/react_dev"
- topic: "hooks"
- tokens: 3000
```

**預期結果**: 顯示 React Hooks 的詳細文檔

---

### 測試 3: 查看 SkillFlow 技能 ✅

```
請使用 list_skills 工具
```

**預期結果**: 看到 `fetch_library_docs` 和 `fetch_react_docs` 技能

---

### 測試 4: 查看技能詳情 ✅

```
請使用 get_skill 工具

參數:
- skill_id: "fetch_library_docs"
```

**預期結果**: 顯示完整的技能定義，包含：
- 2 個節點（resolve_library, get_docs）
- 參數模板
- 依賴關係

---

### 測試 5: 嘗試執行技能 ⚠️

```
請執行 skill__fetch_library_docs 技能

參數:
- library_name: "vue"
- topic: "reactivity"
```

**可能結果**:

**選項 A**: ✅ 成功執行並返回 Vue reactivity 文檔
- 表示架構已自動支持本地 MCP 工具

**選項 B**: ❌ 錯誤: "Server not found" 或類似錯誤
- 表示需要實現架構擴展（參見解決方案）

---

## 📊 測試結果記錄

| 測試 | 狀態 | 結果說明 |
|------|------|---------|
| 1. resolve-library-id | ⬜ | |
| 2. get-library-docs | ⬜ | |
| 3. list_skills | ⬜ | |
| 4. get_skill | ⬜ | |
| 5. 執行技能 | ⬜ | |

---

## 🔧 如果測試 5 失敗

### 快速解決方案：使用直接調用

繞過技能，手動執行兩步驟：

#### 步驟 1: 解析庫 ID
```
請使用 mcp__context7__resolve-library-id 工具
參數: libraryName = "vue"
```

記下返回的 library_id（例如：`/websites/vuejs_org`）

#### 步驟 2: 獲取文檔
```
請使用 mcp__context7__get-library-docs 工具
參數:
- context7CompatibleLibraryID: "/websites/vuejs_org"
- topic: "reactivity"
- tokens: 5000
```

**結果**: 獲得 Vue reactivity 文檔（與技能預期結果相同）

---

## 💡 測試成功後

### 如果所有測試通過 ✅

恭喜！整合完全成功。您可以：

1. **創建更多技能**: 覆蓋其他庫和主題
2. **批次處理**: 創建獲取多個庫文檔的技能
3. **組合技能**: 將文檔查詢與其他操作組合

### 如果測試 5 失敗 ⚠️

這是預期的架構限制。選擇一個解決方案：

**方案 A** - 快速（推薦新手）:
- 使用直接調用（上方的兩步驟方法）
- 優點：立即可用
- 缺點：無法利用技能的優勢

**方案 B** - 中等（推薦開發者）:
- 創建 wrapper 工具
- 參考：`CONTEXT7_INTEGRATION_SUMMARY.md` 的方案 B
- 優點：封裝複雜度
- 缺點：需要編寫代碼

**方案 C** - 完整（推薦長期）:
- 擴展執行引擎
- 參考：`CONTEXT7_INTEGRATION_SUMMARY.md` 的方案 A
- 優點：通用解決方案
- 缺點：需要修改核心

---

## 🎯 下一步

### 立即行動
1. ⬜ 執行上述 5 個測試
2. ⬜ 記錄測試結果
3. ⬜ 選擇適合的解決方案（如需要）

### 進階探索
1. ⬜ 閱讀 [CONTEXT7_INTEGRATION_SUMMARY.md](CONTEXT7_INTEGRATION_SUMMARY.md)
2. ⬜ 查看 [TEST_CONTEXT7.md](TEST_CONTEXT7.md) 了解詳細測試方案
3. ⬜ 實驗創建自己的整合技能

---

## 📞 需要幫助？

- 查看 [故障排除](TEST_CONTEXT7.md#故障排除)
- 檢查技能定義: `data/skills/fetch_library_docs/v0001.json`
- 查看執行日誌: `data/runs/` 目錄

---

**預計測試時間**: 5-10 分鐘
**難度級別**: 初級 → 中級
