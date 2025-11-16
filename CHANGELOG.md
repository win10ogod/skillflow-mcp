# Changelog

All notable changes to Skillflow-MCP will be documented in this file.

## [0.2.0] - 2025-11-16

### Added - Phase 2: Transport Layer Extensions 🌐

- **HTTP+SSE Transport Support** 🔌
  - Full implementation of HTTP Server-Sent Events transport
  - Real-time bidirectional communication with MCP servers
  - Auto-reconnection and error handling
  - Module: `http_sse_client.py`
  - Install: `pip install skillflow-mcp[http]`

- **WebSocket Transport Support** 🔌
  - Complete WebSocket transport implementation
  - Persistent bidirectional connections
  - Automatic ping/pong keepalive
  - Module: `websocket_client.py`
  - Install: `pip install skillflow-mcp[websocket]`

- **Transport Type Support**:
  - ✅ stdio (existing)
  - ✅ http_sse (new)
  - ✅ websocket (new)
  - ⏳ streamable_http (schema ready, implementation pending)

### Added - Phase 3: Advanced Features 🚀

- **Conditional Nodes (if/else/switch)** 🔀
  - Support for conditional branching in skills
  - Multiple branch types: if_else, switch
  - Condition evaluation via JSONPath, Jinja2, or Python expressions
  - Default branch for fallback logic
  - Schema models: `ConditionalType`, `ConditionalBranch`, `ConditionalConfig`

- **Loop Nodes (for/while)** 🔄
  - Iterate over collections with FOR loops
  - Conditional iteration with WHILE loops
  - Numeric range iteration with FOR_RANGE loops
  - Safety limits to prevent infinite loops
  - Access to iteration variables in nested nodes
  - Schema models: `LoopType`, `LoopConfig`

- **Skill Nesting and Composition** 🏗️
  - Skills can now call other skills
  - NodeKind.SKILL_CALL support
  - skill_id field in SkillNode
  - Recursive skill execution with dependency management
  - Enables building complex workflows from simple skills

- **Parameter Transformation (JSONPath & Jinja2)** 🔧
  - Transform parameters using JSONPath queries
  - Template parameters with Jinja2
  - Module: `parameter_transform.py`
  - Schema model: `ParameterTransform`
  - Install: `pip install skillflow-mcp[transforms]`
  - Example:
    ```python
    {
      "parameter_transform": {
        "engine": "jsonpath",
        "expression": "$.data.items[*].name"
      }
    }
    ```

- **Enhanced Node Types**:
  - TOOL_CALL (existing)
  - SKILL_CALL (new - for skill nesting)
  - CONTROL (existing)
  - CONDITIONAL (new - for if/else/switch)
  - LOOP (new - for for/while)

### Changed - 2025-11-16

- **Hot Reload Confirmed** ♻️
  - Skills are dynamically discovered on every tool list request
  - No server restart needed for new skills
  - Skill edits and deletions take effect immediately
  - Already implemented in previous versions, now documented

- **Version Bump**: 0.1.0 → 0.2.0
  - Reflects major feature additions
  - Breaking changes: None (fully backward compatible)

### Installation Options

```bash
# Core features only
pip install skillflow-mcp

# With HTTP+SSE transport
pip install skillflow-mcp[http]

# With WebSocket transport
pip install skillflow-mcp[websocket]

# With parameter transformations
pip install skillflow-mcp[transforms]

# With all advanced features
pip install skillflow-mcp[full]
```

### Roadmap Progress

- ✅ Phase 1: Core Features (Complete)
- ✅ Phase 2: Transport Layer (HTTP+SSE ✅, WebSocket ✅, Streamable HTTP ⏳)
- ✅ Phase 3: Advanced Features (COMPLETE!)
  - ✅ Schemas defined for all features
  - ✅ Parameter transformation module complete
  - ✅ Engine execution logic for conditional nodes (IMPLEMENTED in engine.py)
  - ✅ Engine execution logic for loop nodes (IMPLEMENTED in engine.py)
  - ✅ Engine execution logic for skill nesting (IMPLEMENTED in engine.py)
  - ✅ Parameter transformation integration
  - ✅ Loop variable support ($loop.var_name)
  - ⏳ Integration of new transports into mcp_clients.py (next release)

### Engine Enhancements (engine.py)

- **ExecutionContext Extensions**:
  - Added `loop_vars` dictionary for loop iteration variables
  - Added `parent_context` for nested skill calls

- **ExecutionEngine Extensions**:
  - Added `skill_manager` parameter for skill nesting support
  - `_execute_conditional()` - Full conditional node execution
  - `_execute_loop()` - Complete loop node execution (FOR, WHILE, FOR_RANGE)
  - `_execute_loop_body()` - Loop body execution with proper scoping
  - `_execute_skill_call()` - Complete nested skill execution
  - Extended `_resolve_template_string()` to support $loop.var_name
  - Parameter transformation applied in `_execute_node()`

### Template Variable Support

Skills now support three types of template variables:
- `$inputs.field` - Access skill input parameters
- `@step_id.outputs.field` - Access outputs from previous steps
- `$loop.var_name` - Access loop iteration variables (Phase 3)

## [Unreleased]

### Added - 2025-11-16 (New Features) ✨

- **支持技能并发执行模式** 🚀
  - 🎯 **功能**：允许在创建技能时配置执行模式，支持顺序、分阶段、完全并行三种模式
  - ✅ **执行模式**：
    - `sequential` (顺序) - 默认模式，节点按拓扑顺序一个接一个执行
    - `phased` (分阶段) - 定义执行阶段，每个阶段内的节点并行执行
    - `full_parallel` (完全并行) - 在依赖关系允许的情况下最大化并行执行
  - 📦 **配置参数**：
    - `concurrency_mode`: 选择执行模式
    - `concurrency_phases`: 分阶段模式的阶段定义 (例如: `{"phase1": ["step_1", "step_2"]}`)
    - `max_parallel`: 限制最大并行任务数量
  - 🌟 **使用场景**：
    - 顺序执行：适合有明确依赖的步骤（如：获取数据 → 处理 → 保存）
    - 分阶段：适合批量操作（如：同时截图多个窗口，然后统一处理）
    - 完全并行：适合独立任务（如：同时调用多个 API 获取数据）
  - 💡 **示例**：
    ```python
    # 创建完全并行执行的技能
    create_skill_from_session({
      "session_id": "...",
      "skill_id": "parallel_fetch",
      "name": "Parallel Data Fetch",
      "description": "Fetch data from multiple sources in parallel",
      "concurrency_mode": "full_parallel",
      "max_parallel": 5  # 最多同时执行 5 个任务
    })
    ```

- **支持上游 MCP 服务器的 Resources 和 Prompts** 📚
  - 🎯 **功能**：完整支持 MCP 协议的 Resources 和 Prompts，允许访问上游服务器的资源和提示词
  - ✅ **新增工具**：
    - `list_upstream_resources` - 列出上游服务器的所有资源
    - `read_upstream_resource` - 读取指定 URI 的资源内容
    - `list_upstream_prompts` - 列出上游服务器的所有提示词
    - `get_upstream_prompt` - 获取指定提示词及其内容
  - 📦 **MCP Resources**：
    - 访问上游服务器暴露的文件、数据、文档等资源
    - 支持任何符合 MCP 协议的资源类型
    - 返回完整的资源内容和元数据
  - 📦 **MCP Prompts**：
    - 访问上游服务器定义的提示词模板
    - 支持参数化提示词（传递 arguments）
    - 获取结构化的提示词内容
  - 🌟 **使用场景**：
    - 读取上游服务器的配置文件、日志文件
    - 访问文档、API 规范等资源
    - 使用上游服务器提供的预定义提示词模板
  - 💡 **示例**：
    ```python
    # 列出资源
    list_upstream_resources({"server_id": "file-server"})

    # 读取资源
    read_upstream_resource({
      "server_id": "file-server",
      "uri": "file:///path/to/config.json"
    })

    # 获取提示词
    get_upstream_prompt({
      "server_id": "prompt-server",
      "prompt_name": "code_review",
      "arguments": {"language": "python"}
    })
    ```

- **实现 Skillflow 自身的 MCP Resources 和 Prompts** ⭐📚
  - 🎯 **功能**：Skillflow 现在不仅能访问上游服务器的 Resources/Prompts，自身也作为完整的 MCP 服务器提供这些功能
  - ✅ **完整 MCP 协议支持**：
    - ✅ **Tools** - 工具调用（已有功能）
    - ✅ **Resources** - 资源访问（新增）
    - ✅ **Prompts** - 提示词模板（新增）
  - 📦 **Skillflow Resources**（通过自定义 URI 方案暴露）：
    - `skill://<skill_id>` - 访问技能定义（完整的 SkillDraft JSON）
    - `session://<session_id>` - 访问录制会话数据
    - `run://<run_id>` - 访问技能执行日志
  - 📦 **Skillflow Prompts**（预定义的开发指南）：
    - `create_skill` - 从录制会话创建技能的分步指南
      - 参数：session_id, concurrency（可选，默认 sequential）
      - 包含：会话审查、参数分析、并发模式选择、创建和测试
    - `debug_skill` - 调试技能执行问题的诊断指南
      - 参数：skill_id, run_id（可选）
      - 包含：执行日志分析、节点失败诊断、参数问题检测
    - `optimize_skill` - 优化技能性能的最佳实践
      - 参数：skill_id, focus（可选：performance/reliability/maintainability）
      - 包含：并发优化、错误处理、参数验证、文档改进
    - `skill_best_practices` - 技能开发和维护的最佳实践总结
      - 无参数
      - 包含：设计原则、测试策略、版本控制、文档规范
  - 🌟 **使用场景**：
    - AI 助手可以通过 Resources 直接访问技能定义和执行历史
    - AI 助手可以通过 Prompts 获取结构化的操作指南
    - 实现完整的 MCP 生态集成（Skillflow 既是客户端也是服务器）
  - 💡 **示例**：
    ```python
    # 通过 MCP Resources API 访问技能定义
    # 客户端调用：read_resource(uri="skill://my-skill-id")
    # 返回：完整的 SkillDraft JSON，包含图结构、参数模板、并发配置等

    # 通过 MCP Prompts API 获取创建技能的指南
    # 客户端调用：get_prompt(name="create_skill", arguments={"session_id": "xxx", "concurrency": "phased"})
    # 返回：结构化的分步指南，包含具体的工具调用示例和参数说明

    # 通过 MCP Resources API 访问执行日志
    # 客户端调用：read_resource(uri="run://run-2025-11-16-001")
    # 返回：详细的执行日志数组，包含每个节点的参数、结果、耗时等
    ```
  - 🔧 **技术实现**：
    - 在 server.py 中新增 `_setup_resources()` 和 `_setup_prompts()` 方法
    - 使用 `@self.server.list_resources()` 和 `@self.server.read_resource()` 装饰器
    - 使用 `@self.server.list_prompts()` 和 `@self.server.get_prompt()` 装饰器
    - 在服务器初始化时自动注册这些端点

### Fixed - 2025-11-16 (Compatibility Fix) 🔧

- **修复 Fount 客户端的 60 字符限制问题**
  - 🎯 **根本原因**：Fount 添加 `mcp_skillflow_` 前缀（13 字符）
  - 🎯 **旧实现**：代理工具最大 60 字符，加前缀后超限
    ```
    mcp_skillflow_up_windows-driver-input_Input-RateLimiter-Config
    ^^^^^^^^^^^^^                                                    = 13
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^     = 48
    总计：61 字符 ❌ 超过限制！
    ```
  - ✅ **新实现**：代理工具最大 47 字符，为前缀预留空间
    ```
    mcp_skillflow_up_1b58650e_Input-RateLimiter-Config
    ^^^^^^^^^^^^^                                       = 13
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^    = 36
    总计：49 字符 ✅ 符合限制！
    ```
  - 📦 **智能策略**：
    - 短名称：使用 compact 格式 `up_<server_id>_<tool_name>` (如果 ≤47)
    - 长名称：自动切换到 hash 格式 `up_<hash>_<tool_name>` (如果 >47)
    - 超长工具名：自动截断并添加 `..` 后缀
  - 🔄 **向后兼容**：仍支持解析旧的 `upstream__` 格式

- **修复技能工具无法调用的问题**
  - 🎯 **问题**：技能创建后返回 "Unknown tool: skill__xxx"
  - 🎯 **根本原因**：技能工具只在 list_tools 中出现，但 handle_tool_call 没有处理逻辑
  - ✅ **解决方案**：动态加载技能工具
    - 在 handle_tool_call 中检测 `skill__` 前缀
    - 按需加载和执行技能，无需预注册
    - 技能创建后**立即可调用**（服务器端）
  - 📦 **好处**：
    - ✅ 即时可用 - 创建后立即可调用
    - ✅ 内存效率 - 只在需要时加载
    - ✅ 始终最新 - 每次调用都读取最新版本
  - ⚠️ **客户端缓存问题**：
    - 某些客户端（如 Fount）会缓存工具列表
    - 新技能在服务器端立即可用，但可能不会立即出现在客户端工具列表中
    - 解决方案：刷新客户端或直接调用 `skill__<id>`
    - 创建技能后的消息会包含使用提示

- **修复 debug_upstream_tools 的进程泄漏**
  - 🎯 **问题**：调试工具测试连接时，异常路径没有清理进程
  - 🎯 **根本原因**：只在超时时清理，其他异常未清理
  - ✅ **解决方案**：
    - 在所有异常路径（不仅是超时）都调用 disconnect_server
    - 使用 try-except 确保清理不会失败
    - 防止孤立进程累积

- **修复服务器关闭时上游进程未终止的问题** 🔧
  - 🎯 **问题**：Skillflow 服务器关闭后，上游 MCP 服务器进程仍在后台运行
  - 🎯 **根本原因**：服务器退出时没有调用 cleanup 清理上游连接
  - ✅ **解决方案**：
    - 添加 `cleanup()` 方法调用 `mcp_clients.close_all()`
    - 在 `main()` 的 `finally` 块中确保 cleanup 被调用
    - 使用 `atexit` 注册清理函数，处理正常退出
    - 改进信号处理器（SIGINT/SIGTERM）触发 `KeyboardInterrupt`
    - 跨平台兼容：Windows 和 Unix 都能正确清理
  - 📦 **清理流程**：
    1. 服务器收到退出信号（Ctrl+C 或 SIGTERM）
    2. 触发 `KeyboardInterrupt` 异常
    3. `finally` 块调用 `cleanup()`
    4. `close_all()` 断开所有上游客户端
    5. 每个客户端的 `stop()` 终止子进程（先 terminate，5 秒后 kill）
    6. 确保所有资源被正确释放

- **完整支持 MCP 协议的所有内容类型** 🖼️🔊📦
  - 🎯 **问题**：上游 MCP 工具返回的图像、音频等多媒体内容被转换成字符串，AI 模型无法看到实际内容
  - 🎯 **根本原因**：代理逻辑只处理 TextContent，忽略了其他所有内容类型
  - ✅ **解决方案**：
    - 正确解析上游工具返回的 content 数组
    - 根据 `type` 字段创建对应的 Content 对象
    - 保留所有原始数据（base64、mimeType、resource 等）
    - 让 AI 模型能够看到上游工具返回的**所有类型**的内容
  - 📦 **支持的内容类型**（完整覆盖 MCP 协议）：
    - ✅ **TextContent** - 文本内容
    - ✅ **ImageContent** - 图像（截图、图表等，base64 + mimeType）
    - ✅ **AudioContent** - 音频（录音、TTS 等，base64 + mimeType）
    - ✅ **EmbeddedResource** - 嵌入资源（文件、数据等）
    - ✅ **未知类型** - 自动转为 TextContent，确保向前兼容
  - 🌟 **实际效果**：
    - 上游工具返回截图 → AI 模型能看到并分析图像 ✅
    - 上游工具返回音频 → AI 模型能处理音频内容 ✅
    - 上游工具返回文件 → AI 模型能访问文件资源 ✅
    - 混合返回（文本+图像+音频）→ 全部正确传递 ✅

- **改进技能元数据管理**：
  - 技能创建时自动保存 `source_session_id` 到 metadata
  - 允许追溯技能来源的录制会话
  - 便于调试和诊断技能相关问题

- **新增调试工具**：
  - `debug_skill_tools` - 检查技能工具注册状态
    - 列出所有技能及其对应的工具名
    - 显示技能工具在 list_tools 中的实际状态
    - 帮助诊断技能相关问题
  - `debug_recording_session` - 检查录制会话详情和诊断文本乱码问题
    - 显示会话中每个工具调用的详细参数
    - 对文本参数进行字符级分析（字符列表、字节表示）
    - 帮助识别文本是否在录制阶段就已损坏
  - `debug_skill_definition` - 检查技能定义
    - 显示技能图中每个节点的参数模板
    - 对文本参数进行字符级分析
    - 显示技能的 metadata（包含 source_session_id）
    - 帮助识别文本是否在技能创建阶段损坏
  - `debug_skill_execution` - 追踪技能执行过程并诊断重播时的参数损坏
    - 显示每个节点执行时的 args_resolved（执行引擎解析后的参数）
    - 对文本参数进行字符级分析（字符列表、字节表示）
    - 显示每个节点的执行状态和结果
    - **关键用途**：对比 args_template（技能定义）和 args_resolved（实际执行），定位参数在哪个阶段被损坏

- **新增文件**：
  - `src/skillflow/tool_naming.py` - 智能工具命名策略
  - `test_tool_naming.py` - 命名策略测试脚本

- **命名示例**（47 字符限制）：
  ```
  windows-driver-input + Move_Tool
  → up_windows-driver-input_Move_Tool (33 字符)
  → 加前缀：46 字符 ✅

  windows-driver-input + Input-RateLimiter-Config
  → up_1b58650e_Input-RateLimiter-Config (36 字符，使用 hash)
  → 加前缀：49 字符 ✅

  very-long-server-name-that-exceeds-limits + Very_Long_Tool_Name
  → up_395ba45f_Very_Long_Tool_Name (31 字符，使用 hash)
  → 加前缀：44 字符 ✅
  ```

### Changed - 2025-11-16 (Major Rewrite) 🚀

- **原生 MCP 客户端实现** - 完全重写连接层！
  - 🎯 **核心变化**：不再依赖官方 mcp SDK 的 stdio 客户端
  - 🚀 **直接控制**：自行实现 JSON-RPC 2.0 协议和 subprocess 管理
  - 📊 **流式解析**：实时解析 JSON-RPC 消息，buffer 处理不完整消息
  - 🔄 **双向通信**：支持服务器请求（roots/list、sampling/createMessage）
  - ⚡ **性能改进**：减少一层抽象，连接更快更稳定
  - 🐛 **更好调试**：详细日志，准确显示在哪个阶段出错

- **新增文件**：
  - `src/skillflow/native_mcp_client.py` - 全新的原生 MCP 客户端
  - 完整实现：subprocess 管理、JSON-RPC、MCP 协议、错误处理

- **架构对比**：
  ```
  旧实现（SDK）:
  Skillflow → mcp.ClientSession → mcp.stdio_client → subprocess
                 ↑ 黑盒，不知道内部在做什么

  新实现（原生）:
  Skillflow → NativeMCPClient → subprocess + JSON-RPC
                 ↑ 完全掌控，所有细节可见可调试
  ```

- **关键改进**：
  - ✅ 启动超时检测（subprocess 启动 10 秒超时）
  - ✅ 握手超时检测（MCP initialize 60 秒超时）
  - ✅ 异步消息处理（独立的读取和错误流任务）
  - ✅ 请求/响应匹配（通过 message_id）
  - ✅ 完整资源清理（terminate → wait → kill）
  - ✅ 双向通信支持（处理服务器的 roots/list 和 sampling 请求）

### Added - 2025-11-16

- **上游工具代理功能** - 重大功能更新！
  - 自动将已注册上游服务器的工具暴露为 Skillflow 工具
  - 工具命名格式：`upstream__<server_id>__<tool_name>`
  - 支持录制通过代理调用的上游工具
  - 完整的工作流程：注册 → 暴露 → 调用 → 录制 → 创建技能

- **新增文档**
  - `docs/UPSTREAM_TOOLS_PROXY.md` - 上游工具代理功能完整指南

- **测试脚本**
  - `test_upstream_proxy.py` - 验证代理功能的测试脚本

### Fixed - 2025-11-16

- **修复录制功能** - 解决了 "Total calls: 0" 的问题
  - 之前：上游服务器的工具不可见，无法调用，因此无法录制
  - 现在：上游工具自动暴露，可以直接调用并被正确录制

- **修复 stdio 客户端连接问题**
  - 正确处理 `stdio_client` 的异步上下文管理器

### Changed - 2025-11-16

- **增强工具列表功能** - 现在包含上游服务器的代理工具
- **增强工具调用处理** - 支持代理上游工具调用并正确录制

## Migration Guide

如果您之前遇到了 "录制显示 0 次调用" 的问题：

1. 拉取最新代码
2. 重启 Skillflow
3. 现在可以直接调用 `upstream__<server_id>__<tool_name>` 格式的工具
4. 这些调用会被正确录制

详细信息请查看 `docs/UPSTREAM_TOOLS_PROXY.md`

### Fixed - 2025-11-16 (Hotfix)

- **修复 MCP 初始化超时问题**
  - 移除了初始化时自动连接所有上游服务器的逻辑
  - 改为延迟连接（lazy connection）- 只在需要时才连接
  - 添加了超时保护（每个服务器 3 秒）防止阻塞
  - 服务器现在可以快速启动，不会因为上游服务器不可用而超时

- **改进 stdio 客户端连接稳定性**
  - 为子进程启动添加 10 秒超时保护
  - 为 MCP 握手添加 30 秒超时保护
  - 添加详细的连接日志以便调试
  - 改进错误处理和资源清理，防止孤立进程
  - 超时或失败时确保正确清理 context 和 subprocess

### Technical Details

**问题原因**：
- 旧代码在初始化时尝试连接所有已注册的上游服务器
- 如果服务器不可用（如缺少依赖），连接会超时
- 多个服务器的累积超时导致整个 MCP 初始化失败
- `session.initialize()` 没有超时保护，可能永久挂起
- 连接失败时资源清理不完整，导致孤立进程

**解决方案**：
1. 初始化时只加载注册表，不连接服务器
2. 在 `_get_upstream_tools()` 中添加超时保护
3. 在 `_connect_stdio()` 中分别为子进程启动和 MCP 握手添加超时
4. 连接失败时确保完整的资源清理
5. 添加详细日志以便诊断连接问题

