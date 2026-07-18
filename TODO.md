# Code TODO  _上次更新：2026-07-18 17:55_

> 只记录尚未完成且可以继续执行的事项；已完成内容统一查阅 `CHANGELOG.md`。

## P0 · 上线前

- [ ] **固定平台连接地址** — Base URL 与登录认证地址使用部署后的中转站地址，前端不再展示或允许自定义。
- [ ] **准备上线资料** — 确认服务器、域名、HTTPS、备份、监控、文档与合规要求。
- [ ] **注册邮箱通知模板** — 完成中转站注册与验证邮件的内容和发送配置。
- [ ] **接入充值系统** — 对接 `https://epay.580ai.net`，补齐支付回调、订单状态和异常处理。

## P1 · 核心能力

- [ ] **退役旧浏览器 Agent 循环** — 历史 `executionOwner=browser` 活动检查点已改为保留消息并明确失败，不再自动重放；下一步迁移“同一会话输出中再次发送消息”的浏览器后台子任务，再删除 `app.js` 中的旧模型/工具编排代码。详见 [`docs/SERVER_AGENT_LOOP_PLAN.md`](docs/SERVER_AGENT_LOOP_PLAN.md)。
- [ ] **继续拆分 `app.js`** — 按 [`docs/APP_JS_SPLIT_PLAN.md`](docs/APP_JS_SPLIT_PLAN.md) 迁移 state、agent-loop、tools、render、events 和 session；边界稳定后再接入 esbuild。
- [ ] **统一 i18n 架构** — 合并 HTML `data-i18n`、JS `t()`、服务端错误字典以及重复的 `LANG` / `I18N` 字典。
- [ ] **评估 Token 优化效果** — 基于实际使用复查截断和压缩策略的成本收益及能力副作用。

## P2 · 后续路线

- [ ] **Agent 规划任务能力** — 支持复杂任务自动拆解、依赖排序和分阶段执行。
- [ ] **中转站深度整合** — 打通 Token 用量统计、统一模型选择器和 Key 管理闭环。
- [ ] **macOS / Linux 支持** — 适配 shell、进程管理、托盘和安装流程。
- [ ] **客户端应用** — 评估并开发 Windows / macOS 原生客户端。
- [ ] **营销获客** — 规划推广渠道、内容与 SEO。
