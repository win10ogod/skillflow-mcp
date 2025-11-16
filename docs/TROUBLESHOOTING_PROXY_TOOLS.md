# 故障排除：代理工具不可见

## 问题症状

运行 `debug_upstream_tools` 显示：
```json
{
  "registered_servers": [
    {"id": "windows-driver-input", "name": "...", "enabled": true}
  ],
  "proxy_tools": [],  // ❌ 空的！
  "errors": []
}
```

**结果**：
- ❌ 无法调用 `upstream__windows-driver-input__*` 工具
- ❌ 录制显示 "Total calls: 0"
- ❌ 无法创建包含上游工具的技能

## 根本原因

**问题**：您的 MCP 客户端配置中同时注册了两个服务器：

```
MCP 客户端
  ├─ skillflow           ← Skillflow 服务器
  └─ windows-driver-input ← 上游服务器（直接注册）
```

当两者都注册时：
1. **客户端启动 `windows-driver-input`** 作为独立进程
2. **Skillflow 也尝试启动 `windows-driver-input`** 来获取工具列表
3. **冲突**：无法同时运行两个实例
4. **结果**：Skillflow 连接失败，`proxy_tools` 为空

## 解决方案

### 方案 A：移除直接注册（推荐）⭐

#### 步骤 1：找到 MCP 客户端配置文件

根据您使用的客户端：

**Fount（您的情况）**：
- Windows: `%APPDATA%\fount\config.json`
- 或者查看 Fount 设置页面

**Claude Desktop**：
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

#### 步骤 2：修改配置

**当前配置**（有问题）：
```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "I:\\凌星開發計畫\\凌星\\VYO-MCP\\skillflow-mcp"
    },
    "windows-driver-input": {  // ❌ 这会导致冲突
      "command": "uv",
      "args": [
        "--directory",
        "I:\\凌星開發計畫\\凌星OS\\input_driver_server",
        "run",
        "main.py"
      ],
      "env": {
        "WINDOWS_INPUT_LOG_LEVEL": "INFO",
        "WINDOWS_MCP_INPUT_BACKEND": "ibsim-dll",
        "WINDOWS_MCP_INPUT_DRIVER": "SendInput",
        "WINDOWS_MCP_RATE_CPS": "8.0",
        "WINDOWS_MCP_RATE_KPS": "12.0",
        "WINDOWS_MCP_RATE_MAX_DELTA": "60",
        "WINDOWS_MCP_RATE_MOVE_HZ": "60",
        "WINDOWS_MCP_RATE_SMOOTH": "0.0"
      }
    }
  }
}
```

**修改为**（正确）：
```json
{
  "mcpServers": {
    "skillflow": {
      "command": "uv",
      "args": ["run", "skillflow"],
      "cwd": "I:\\凌星開發計畫\\凌星\\VYO-MCP\\skillflow-mcp"
    }
    // ✅ 移除 windows-driver-input
    // 它会通过 Skillflow 的上游服务器机制自动连接
  }
}
```

#### 步骤 3：验证 Skillflow 中的上游服务器配置

确认文件存在并正确：
`I:\凌星開發計畫\凌星\VYO-MCP\skillflow-mcp\data\registry\servers.json`

应该包含：
```json
{
  "servers": {
    "windows-driver-input": {
      "server_id": "windows-driver-input",
      "name": "Windows Driver Input",
      "transport": "stdio",
      "config": {
        "command": "uv",
        "args": [
          "--directory",
          "I:\\凌星開發計畫\\凌星OS\\input_driver_server",
          "run",
          "main.py"
        ],
        "env": {
          "WINDOWS_INPUT_LOG_LEVEL": "INFO",
          "WINDOWS_MCP_INPUT_BACKEND": "ibsim-dll",
          "WINDOWS_MCP_INPUT_DRIVER": "SendInput",
          "WINDOWS_MCP_RATE_CPS": "8.0",
          "WINDOWS_MCP_RATE_KPS": "12.0",
          "WINDOWS_MCP_RATE_MAX_DELTA": "60",
          "WINDOWS_MCP_RATE_MOVE_HZ": "60",
          "WINDOWS_MCP_RATE_SMOOTH": "0.0"
        }
      },
      "enabled": true
    }
  }
}
```

#### 步骤 4：重启客户端

完全关闭并重新启动 Fount。

#### 步骤 5：验证修复

```javascript
// 1. 检查调试信息
mcp.config.usrlocalmcp.skillflow debug_upstream_tools

// 期望输出：
{
  "registered_servers": [...],
  "proxy_tools": [  // ✅ 应该有工具！
    {
      "name": "upstream__windows-driver-input__Desktop_Info",
      "description": "[Windows Driver Input] Get desktop information..."
    },
    {
      "name": "upstream__windows-driver-input__Move_Tool",
      "description": "[Windows Driver Input] Move mouse cursor..."
    },
    // ... 更多工具
  ],
  "errors": []
}
```

```javascript
// 2. 测试录制
mcp.config.usrlocalmcp.skillflow start_recording({session_name: "test"})

mcp.config.usrlocalmcp.skillflow upstream__windows-driver-input__Move_Tool({
  to_loc: [960, 540]
})

mcp.config.usrlocalmcp.skillflow stop_recording()
// 期望输出：Total calls: 1 ✅
```

### 方案 B：禁用不需要的上游服务器

如果 `proxy_tools` 仍然为空，可能是因为 Skillflow 也尝试连接 `filesystem` 和 `puppeteer` 导致超时。

编辑 `data/registry/servers.json`，禁用不需要的服务器：

```json
{
  "servers": {
    "filesystem": {
      "server_id": "filesystem",
      "name": "File System Tools",
      "transport": "stdio",
      "config": { ... },
      "enabled": false  // ✅ 改为 false
    },
    "puppeteer": {
      "server_id": "puppeteer",
      "name": "Browser Automation",
      "transport": "stdio",
      "config": { ... },
      "enabled": false  // ✅ 改为 false
    },
    "windows-driver-input": {
      "server_id": "windows-driver-input",
      "name": "Windows Driver Input",
      "transport": "stdio",
      "config": { ... },
      "enabled": true  // ✅ 保持 true
    }
  }
}
```

重启 Skillflow 后再次测试。

## 工作原理对比

### 修改前（不工作）❌

```
MCP 客户端启动:
  ├─ skillflow 进程
  │   └─ 尝试启动 windows-driver-input（失败，已被占用）
  │       └─ proxy_tools: [] ❌
  │
  └─ windows-driver-input 进程（独立运行）

AI 助手调用工具时:
  └─ 直接调用 windows-driver-input
      └─ 绕过 skillflow
          └─ 不被录制 ❌
```

### 修改后（工作）✅

```
MCP 客户端启动:
  └─ skillflow 进程
      └─ 启动 windows-driver-input（成功）
          └─ proxy_tools: [工具列表] ✅

AI 助手调用工具时:
  └─ 调用 upstream__windows-driver-input__Move_Tool
      └─ skillflow 拦截并转发
          └─ 被录制 ✅
```

## 常见问题

### Q: 修改配置后仍然不工作？

**A**: 确保：
1. 完全关闭并重启 MCP 客户端（不是刷新）
2. 检查客户端日志是否有错误
3. 运行 `debug_upstream_tools` 查看 `errors` 数组
4. 查看 Skillflow 控制台日志中的 `[Skillflow]` 消息

### Q: 可以同时保留两个注册吗？

**A**: 理论上不行，因为：
- 同一个服务器不能同时运行两个实例
- 即使可以，AI 助手会优先选择直接注册的服务器
- 这样就无法通过 Skillflow 录制

### Q: 如果我需要直接使用 windows-driver-input 怎么办？

**A**: 两个选择：
1. **临时切换**：修改配置，重启客户端
2. **使用代理工具**：通过 Skillflow 调用，功能完全相同

### Q: 代理工具有性能损失吗？

**A**:
- 延迟增加：~5-20ms（可忽略）
- 功能：完全相同
- 好处：所有调用被自动录制和追踪

## 验证清单

完成修改后，检查以下各项：

- [ ] MCP 客户端配置中只有 `skillflow`
- [ ] `data/registry/servers.json` 中有 `windows-driver-input`
- [ ] `windows-driver-input` 的 `enabled: true`
- [ ] 重启了 MCP 客户端
- [ ] `debug_upstream_tools` 显示 `proxy_tools` 不为空
- [ ] 可以调用 `upstream__windows-driver-input__*` 工具
- [ ] 录制显示非零的 `Total calls`

## 需要帮助？

如果按照上述步骤操作后仍有问题，请提供：
1. `debug_upstream_tools` 的完整输出
2. MCP 客户端控制台日志
3. Skillflow 启动时的日志（包含 `[Skillflow]` 的部分）

我们会根据具体错误继续诊断。

---

**重要提示**：这个问题的核心是**避免同一个服务器被启动两次**。通过只在 MCP 客户端注册 Skillflow，让 Skillflow 负责管理所有上游服务器，可以确保代理机制正常工作。
