# SkillFlow MCP Server - 文檔索引

## 📖 快速導航

### 🚀 新手入門
1. **[README.md](README.md)** - 項目概覽與功能介紹
2. **[INSTALL.md](INSTALL.md)** - 詳細安裝指南
3. **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 5分鐘快速開始

### 📚 使用文檔
1. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 快速參考卡片
2. **[docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - 完整使用指南
3. **[CHANGELOG.md](CHANGELOG.md)** - 版本變更記錄

### 🔧 Context7 整合
1. **[QUICK_TEST.md](QUICK_TEST.md)** - ⭐ 5分鐘快速測試（從這裡開始！）
2. **[CONTEXT7_INTEGRATION_SUMMARY.md](CONTEXT7_INTEGRATION_SUMMARY.md)** - 整合總結與方案
3. **[TEST_CONTEXT7.md](TEST_CONTEXT7.md)** - 完整測試指南
4. **[demo_context7_integration.md](demo_context7_integration.md)** - 技術細節

### 💻 開發文檔
1. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - 項目總結與架構
2. **[test_context7_skill.py](test_context7_skill.py)** - 測試腳本
3. **[LICENSE](LICENSE)** - MIT 許可證

## 🎯 根據目標選擇

### 我想... 快速開始使用 SkillFlow
→ 閱讀 [INSTALL.md](INSTALL.md) → [docs/QUICKSTART.md](docs/QUICKSTART.md)

### 我想... 測試 Context7 整合
→ 閱讀 [QUICK_TEST.md](QUICK_TEST.md) ⭐

### 我想... 了解如何創建技能
→ 閱讀 [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) 的「基本工作流程」章節

### 我想... 查看 API 參考
→ 閱讀 [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### 我想... 了解技術架構
→ 閱讀 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

### 我想... 解決問題
→ 查看 [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) 的「故障排除」章節

## 📂 文件結構

```
skillflow-mcp/
├── 📖 文檔
│   ├── README.md                           # 項目主頁
│   ├── INSTALL.md                          # 安裝指南
│   ├── QUICK_REFERENCE.md                  # 快速參考
│   ├── CHANGELOG.md                        # 變更日誌
│   ├── LICENSE                             # 許可證
│   ├── INDEX.md                            # 本文檔
│   └── docs/
│       ├── QUICKSTART.md                   # 快速開始
│       └── USAGE_GUIDE.md                  # 使用指南
│
├── 🔧 Context7 整合
│   ├── QUICK_TEST.md                       # ⭐ 快速測試（推薦起點）
│   ├── CONTEXT7_INTEGRATION_SUMMARY.md     # 整合總結
│   ├── TEST_CONTEXT7.md                    # 完整測試指南
│   ├── demo_context7_integration.md        # 技術細節
│   └── test_context7_skill.py              # 測試腳本
│
├── 💻 源代碼
│   └── src/skillflow/
│       ├── server.py                       # MCP 服務器
│       ├── engine.py                       # 執行引擎
│       ├── storage.py                      # JSON 儲存
│       ├── skills.py                       # 技能管理
│       ├── recording.py                    # 錄製管理
│       ├── mcp_clients.py                  # MCP 客戶端
│       └── schemas.py                      # 數據模型
│
├── 📦 數據
│   └── data/
│       ├── skills/                         # 技能定義
│       │   ├── fetch_library_docs/         # Context7 整合技能
│       │   └── fetch_react_docs/           # 示例技能
│       ├── sessions/                       # 錄製會話
│       ├── runs/                           # 執行日誌
│       └── registry/                       # Server 註冊
│
├── 🧪 測試
│   └── tests/
│       ├── test_storage.py                 # 儲存層測試
│       └── __init__.py
│
└── 📝 示例
    └── examples/
        ├── example_skill.json              # 技能示例
        └── example_server_config.json      # Server 配置示例
```

## 🎓 學習路徑

### 路徑 A: 快速體驗（推薦）
1. ✅ 安裝 SkillFlow ([INSTALL.md](INSTALL.md))
2. ✅ 快速開始 ([docs/QUICKSTART.md](docs/QUICKSTART.md))
3. ⭐ 測試 Context7 整合 ([QUICK_TEST.md](QUICK_TEST.md))
4. ✅ 查看參考 ([QUICK_REFERENCE.md](QUICK_REFERENCE.md))

### 路徑 B: 深入學習
1. ✅ 閱讀項目概覽 ([README.md](README.md))
2. ✅ 學習完整使用指南 ([docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md))
3. ✅ 了解技術架構 ([PROJECT_SUMMARY.md](PROJECT_SUMMARY.md))
4. ✅ 探索 Context7 整合 ([CONTEXT7_INTEGRATION_SUMMARY.md](CONTEXT7_INTEGRATION_SUMMARY.md))

### 路徑 C: 開發貢獻
1. ✅ 閱讀項目總結 ([PROJECT_SUMMARY.md](PROJECT_SUMMARY.md))
2. ✅ 查看源代碼 (`src/skillflow/`)
3. ✅ 運行測試 (`tests/`)
4. ✅ 創建 Pull Request

## 🔗 快速鏈接

| 任務 | 文檔 | 預計時間 |
|------|------|---------|
| 安裝 SkillFlow | [INSTALL.md](INSTALL.md) | 5 分鐘 |
| 第一個技能 | [docs/QUICKSTART.md](docs/QUICKSTART.md) | 10 分鐘 |
| 測試 Context7 | [QUICK_TEST.md](QUICK_TEST.md) | 5 分鐘 |
| 查 API | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | 隨時 |
| 解決問題 | [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md#故障排除) | 按需 |

## 📊 文檔統計

- **總文檔數**: 13 個主要文檔
- **代碼文件**: 8 個核心模組
- **測試文件**: 基礎測試套件
- **示例**: 2 個配置示例 + 2 個技能示例

## 🆕 最近更新

- ✅ **Context7 整合**: 完整的測試技能和文檔
- ✅ **快速測試指南**: [QUICK_TEST.md](QUICK_TEST.md)
- ✅ **整合總結**: [CONTEXT7_INTEGRATION_SUMMARY.md](CONTEXT7_INTEGRATION_SUMMARY.md)

## 💡 提示

- 🌟 推薦從 [QUICK_TEST.md](QUICK_TEST.md) 開始測試 Context7 整合
- 📖 使用 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 作為日常參考
- 🔍 遇到問題先查看 [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) 的故障排除章節

---

**最後更新**: 2025-01-16  
**維護者**: SkillFlow Team
