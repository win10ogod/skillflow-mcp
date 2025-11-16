# Changelog

All notable changes to Skillflow-MCP will be documented in this file.

## [Unreleased]

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

