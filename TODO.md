# Code TODO

_上次更新：2026-07-23_

本清单只保留尚未完成的工作；已交付内容统一查阅 `CHANGELOG.md`。

---

## P0 · Workbar 上线后收口

- 完成 Workbar 品牌 Logo、首页内容与用户文档。
- 完成生产环境运维闭环：备份、监控、告警、安全检查与恢复演练。
- 完成 Epay 真实支付闭环验证：支付、回调、退款、对账与通知。系统配置已完成，不再重复列配置任务。
- 确定正式 API 上游、模型组合与定价方案。
- 完成商业主体、经营许可和后续支付渠道升级准备。
- 配置并启用企业域名邮箱。

---

## P1 · Code 核心能力

- 实现统一委托 `Context Envelope`：为模型子任务与用户并行任务提供受限、可预算、可审计的上下文。
- 增强错误分类与恢复建议，区分瞬时上游故障、配置错误、权限问题和不可重试错误。
- 重做登录后的新手指引，使 Workbar 授权、Key 获取、模型选择与首次任务形成连续流程；旧版指引已移除。
- 加强 Skill 执行证据校验，避免只输出结论而未实际完成 Skill 要求。
- 继续拆分 `app.js` 第四阶段，迁移剩余高耦合的会话与运行时逻辑。
- 补全 Workbar 用量体验：在不暴露敏感信息的前提下展示账号、会话和任务维度的 Token / 成本信息。

---

## P2 · 规划与自动化

- 在现有 AgentRun / Child AgentRun 上实现结构化计划：步骤依赖、并发槽位、预算、验证证据和恢复状态。
- 结构化计划稳定后，再评估 Cron、Monitor、Workflow 与 worktree 隔离。
- 评估 macOS / Linux 支持与原生客户端形态。
- 准备公开发布所需的产品演示、使用案例和推广素材。

---

详细 Agent 路线：

- [`docs/agent-refactoring-execution-plan.md`](docs/agent-refactoring-execution-plan.md)
- [`docs/codex-claude-code-agent-design-analysis.md`](docs/codex-claude-code-agent-design-analysis.md)
