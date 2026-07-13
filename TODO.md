# Agent Lite TODO

## 功能待办

- [ ] **Token 用量优化** — 降低 API 使用成本
  - 系统提示词精简（当前 SYSTEM_SECURITY_LAYER + 多段提示较长）
  - 工具结果截断（避免返回全量文件内容）
  - 上下文压缩策略优化（当前 95% 阈值触发 compact）
  - 流式输出 token 计数校准
  - 图片 base64 编码优化（压缩/缩略图）
  - 历史消息裁剪策略
- [ ] **app.js 模块化** — 399KB 单文件拆分（state / agent-loop / tools / render / events / session / utils），esbuild 打包
- [ ] **macOS / Linux 跨平台** — PowerShell→bash/zsh、进程管理、托盘适配
- [ ] **API 中转站部署**（阶段 2）— 共享 auth、Key 配置、嵌入中转站页面
- [ ] **网络异常重试机制** — 网络断开/超时时自动等待重试，而非直接报错终止
- [ ] **后台任务 + 刷新不中断**
  - 任意会话有任务执行时仍可新建/切换会话，不阻塞 UI
  - 刷新页面不打断正在执行的任务（Agent 循环下沉到 server 端）
- [ ] **深度整合**（阶段 3）— Token 用量统计、统一模型选择器、Key 管理闭环

## i18n 待办

- [ ] **server.py `_execute_subagent_tool`** — 子 Agent 工具结果硬编码中文
- [ ] **i18n 架构统一** — HTML `data-i18n` / JS `t()` / server `_serverErrorMap` 三层合并
- [ ] **LANG 与 I18N 字典合并** — 两套字典去重

---

_上次更新：2026-07-13_
