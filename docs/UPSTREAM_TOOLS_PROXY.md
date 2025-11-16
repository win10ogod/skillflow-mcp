# 上游工具代理功能

## 概述

Skillflow-MCP 现在支持**自动代理**已注册上游服务器的工具，这意味着：

1. ✅ 注册上游 MCP 服务器后，它们的工具会自动暴露
2. ✅ 可以直接通过 Skillflow 调用这些工具
3. ✅ 所有调用都会被录制（如果录制已启动）
4. ✅ 可以从录制的会话创建可重用的技能

## 工作原理

### 1. 注册上游服务器

```python
# 使用 register_upstream_server 工具
register_upstream_server(
    server_id="windows-driver-input",
    name="Windows Driver Input",
    transport="stdio",
    config={
        "command": "node",
        "args": ["path/to/build/index.js"],
        "env": {...}
    }
)
```

### 2. 自动工具暴露

注册后，Skillflow 会：
- 连接到上游服务器
- 获取该服务器提供的所有工具
- 创建代理工具，命名格式：`upstream__<server_id>__<tool_name>`

例如，如果 `windows-driver-input` 提供了 `Desktop_Info` 工具，
Skillflow 会暴露：`upstream__windows-driver-input__Desktop_Info`

### 3. 调用代理工具

通过 MCP 客户端直接调用：

```python
# 原始工具名：Desktop_Info
# 代理工具名：upstream__windows-driver-input__Desktop_Info

result = upstream__windows-driver-input__Desktop_Info()
```

### 4. 录制功能

启动录制后，所有通过代理调用的工具都会被记录：

```python
# 1. 启动录制
start_recording(session_name="mouse_automation")

# 2. 调用上游工具（会被自动录制）
desktop_info = upstream__windows-driver-input__Desktop_Info()
upstream__windows-driver-input__Move_Tool(to_loc=[960, 540])

# 3. 停止录制
stop_recording()
# 输出：Recording stopped. Session ID: xxx, Total calls: 2 ✅

# 4. 创建技能
create_skill_from_session(
    session_id="session_xxx",
    skill_id="move_mouse_center",
    name="移动鼠标到中心",
    description="获取屏幕信息并移动鼠标到中心位置"
)
```

## 完整示例：Windows 鼠标自动化

### 步骤 1：注册 Windows Driver Input 服务器

```python
register_upstream_server(
    server_id="windows-driver-input",
    name="Windows Driver Input",
    transport="stdio",
    config={
        "command": "node",
        "args": ["C:/path/to/windows-mcp/packages/windows-driver-input/build/index.js"],
        "env": {"NODE_ENV": "production"}
    }
)
```

**验证注册**：
```python
list_upstream_servers()
# 应显示 windows-driver-input 服务器
```

### 步骤 2：查看可用工具

MCP 客户端会自动列出所有代理工具：

```
# 通过 MCP 客户端查看工具列表
list_tools()

# 会看到类似这样的工具：
- upstream__windows-driver-input__Desktop_Info
- upstream__windows-driver-input__Move_Tool
- upstream__windows-driver-input__Click_Tool
...
```

### 步骤 3：开始录制

```python
start_recording(session_name="move_to_center")
```

### 步骤 4：执行操作

```python
# 获取桌面信息
desktop = upstream__windows-driver-input__Desktop_Info()
# 返回：{"width": 1920, "height": 1080, ...}

# 计算中心点（这一步由 AI 助手完成）
# center_x = 960, center_y = 540

# 移动鼠标到中心
upstream__windows-driver-input__Move_Tool(to_loc=[960, 540])
```

### 步骤 5：停止录制

```python
stop_recording()
# 输出：Recording stopped. Session ID: session_xxx, Total calls: 2
```

### 步骤 6：创建技能

```python
create_skill_from_session(
    session_id="session_xxx",
    skill_id="move_mouse_to_center",
    name="移动鼠标到屏幕中心",
    description="自动获取屏幕尺寸并将鼠标移动到中心位置",
    tags=["windows", "mouse", "automation"]
)
```

### 步骤 7：使用技能

技能创建后会自动注册为工具：

```python
# 直接调用技能（一步完成所有操作）
skill__move_mouse_to_center()
```

## 技术细节

### 工具命名规范

- **格式**：`upstream__<server_id>__<original_tool_name>`
- **示例**：
  - Server ID: `windows-driver-input`
  - Original Tool: `Desktop_Info`
  - Proxy Tool: `upstream__windows-driver-input__Desktop_Info`

### 工具描述增强

代理工具的描述会自动添加服务器名称前缀：

```
原始描述: "Get desktop information"
代理描述: "[Windows Driver Input] Get desktop information"
```

### 录制机制

1. 当调用代理工具时，Skillflow 的 `handle_tool_call` 会：
   - 解析工具名称，提取 `server_id` 和 `actual_tool_name`
   - 调用 `_execute_tool(server_id, tool_name, args)`

2. `_execute_tool` 方法会：
   - 通过 MCP 客户端调用上游服务器
   - 如果有活动的录制会话，记录这次调用
   - 返回结果

3. 录制的数据包括：
   - 服务器 ID
   - 工具名称
   - 参数
   - 结果
   - 执行时间
   - 状态（成功/失败）

## 与旧版本的区别

### 旧版本（问题）

```
1. 注册上游服务器 ✅
2. 启动录制 ✅
3. 尝试调用上游工具 ❌ 工具不可见
4. 录制结果：Total calls: 0 ❌
```

### 新版本（已修复）

```
1. 注册上游服务器 ✅
2. 上游工具自动暴露为代理工具 ✅
3. 启动录制 ✅
4. 调用代理工具 ✅ 工具可见且可调用
5. 录制结果：Total calls: N ✅ 正确记录
6. 创建技能 ✅
```

## 故障排除

### 问题：看不到上游工具

**症状**：注册了服务器，但 `list_tools()` 没有显示 `upstream__*` 工具

**检查**：
1. 确认服务器已注册：`list_upstream_servers()`
2. 确认服务器已启用：检查 `enabled: true`
3. 重启 Skillflow 服务器
4. 检查连接：服务器命令和参数是否正确

### 问题：调用代理工具失败

**症状**：调用 `upstream__*` 工具时出错

**检查**：
1. 工具名称是否正确（包括大小写）
2. 参数是否符合工具的 inputSchema
3. 上游服务器是否正常运行
4. 查看错误消息获取详细信息

### 问题：录制仍然是 0 次调用

**症状**：调用了代理工具，但录制显示 0 次

**检查**：
1. 确认已调用 `start_recording()`
2. 确认使用的是 `upstream__*` 格式的工具名
3. 确认工具调用成功（没有错误）
4. 检查 session 详情：可能工具调用失败了

## 最佳实践

### 1. 使用有意义的 session 名称

```python
# 好的示例
start_recording(session_name="automate_login_flow")
start_recording(session_name="data_extraction_workflow")

# 不好的示例
start_recording(session_name="test1")
```

### 2. 验证工具调用结果

```python
# 在录制时，确保每个工具调用都成功
desktop = upstream__windows-driver-input__Desktop_Info()
print(f"Desktop size: {desktop}")  # 验证结果

# 然后再执行下一步
```

### 3. 逐步构建技能

```python
# 从简单的 1-2 步开始
start_recording()
result1 = upstream__server__tool1()
stop_recording()
create_skill_from_session(...)

# 验证后再添加更多步骤
```

### 4. 使用标签组织技能

```python
create_skill_from_session(
    ...,
    tags=["windows", "input", "automation", "mouse"]
)
```

## 参考

- [MCP 规范](https://modelcontextprotocol.io/)
- [Skillflow 使用指南](USAGE_GUIDE.md)
- [如何添加 MCP Server](HOW_TO_ADD_MCP_SERVERS.md)
