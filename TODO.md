# Code TODO

_上次更新：2026-07-23_

本清单只保留尚未完成的工作；已交付内容统一查阅 `CHANGELOG.md`。

---

## P0 · workbar 上线后收口

- ~~workbar品牌统一为小写字母~~ ✅ Code 部分已完成（i18n/UI/文档/测试/注释），主站（New API 前端）待同步。
- 确定正式 API 上游、模型组合与定价方案。只用一个分组（倍率），初期定价策略为保证15%的毛利率。
- 创建令牌时选择模型限制加入供应商级联下拉框
- 完成 workbar 品牌 Logo、首页内容与用户文档。
- 配置并启用企业域名邮箱。
- 完成生产环境运维闭环：备份、监控、告警、安全检查与恢复演练。
- 完成商业主体、经营许可和后续支付渠道升级准备。

---

## P1 · Code 核心能力

- 实现统一委托 `Context Envelope`：为模型子任务与用户并行任务提供受限、可预算、可审计的上下文。
- 增强错误分类与恢复建议，区分瞬时上游故障、配置错误、权限问题和不可重试错误。
- 重做登录后的新手指引，使 workbar 授权、Key 获取、模型选择与首次任务形成连续流程；旧版指引已移除。
- 加强 Skill 执行证据校验，避免只输出结论而未实际完成 Skill 要求。
- 继续拆分 `app.js` 第四阶段，迁移剩余高耦合的会话与运行时逻辑。
- 补全 workbar 用量体验：在不暴露敏感信息的前提下展示账号、会话和任务维度的 Token / 成本信息。
- **EXE 安装路径与桌面快捷方式**：将 EXE 固定放在 `%USERPROFILE%\.code\` 下，首次运行时自动创建桌面快捷方式，后续更新只替换 `.code\` 下的 EXE 文件（快捷方式无需重建）。注意 Windows .lnk 编码陷阱：路径避免中文、PS 5.1 用 BOM、直接调 `powershell.exe` 而非通过批处理包装。

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
