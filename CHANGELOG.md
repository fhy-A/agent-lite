# Agent Lite 开发日志

> 记录 Claude Code、Codex 以及其他协作方的重要改动，按时间倒序。

---

## 2026-07-15 · Claude Code

### Token 用量优化

- **系统提示词精简**：`defaultSystemPrompt` 从 611 tokens 压缩至 199 tokens；移除冗余的"可用工具列表"和"文本协议"（tool schema 已定义）；3 条合并为 1 条；"回复风格"8 条压缩为 4 条；删除 `Tool preset` + `Allowed tools` 提示。固定开销 **-45%（~510 tokens/轮）**
- **工具结果截断**：`truncateForDisplay` 12K→6K chars；`run_command` 改为头尾保留模式（头 15 行 + 尾 60 行）；`web_fetch` 限 4K chars
- **历史消息裁剪**：新增 `trimOldToolResults()`，每轮自动折叠 >3K chars 的旧工具结果为一句话摘要，保留最近 4 条完整
- **上下文压缩**：keepCount 2→5；改为只发送压缩版给模型，完整历史保留在 `ctx.messages` 供 UI 显示（`_compactPrefix` + `_compactCutoff` 机制）
- **流式 token 计数校准**：`calcStats` 优先使用 API 返回的真实 `prompt_tokens`，回退到旧估算

### 对话问卷

- **P0 全部完成**：Codex 实现 request_user_input tool + 基础 UI
- **P1 全部完成**：每题独立取消、消息流决策记录、刷新恢复、通知体系统一
- **P2 全部完成**：决策记录索引（上下文识别）、子 Agent 上报决策（`[DECISION_POINT]` 标记 + 提示词约束）、Wizard 合并至规划任务能力
- **问卷触发策略优化**：参考 mattpocock/skills 四原则（grilling/to-spec/domain-modeling/wizard），加"扫描历史决策不重复提问"约束
- **UI 完善**：
  - 逐题显示（单题卡片 + 右上角进度徽章），不再挤一个面板
  - 面板锚定输入框上方（移入 composer，`bottom: 100%`）
  - radio/checkbox 自定义渲染（`appearance: none`，实心圆选中态）
  - 纯文本题去掉"其他"输入框，多选题标明"(多选)"
  - 摘要宽度对齐聊天气泡（复用 `.msg` 类）
  - 按钮文字简洁化（"确认此题"→"确认"）
  - 问卷焦点不触发 composer 高亮（`:has(#userInputPanel:not(.hidden))`）

### 图片消息

- 图片缩略图点击放大预览
- 模型不支持多模态时自动降级：去掉图片 → 纯文本重试（反向排除，仅跳过限流）
- 降级标注 i18n 化：`imageDroppedHint`（中英双语，无 emoji）

### 会话稳定性

- 修复非 abort 错误后 `isStreaming` 永久卡死（`chatForm` catch 分支缺 `setStreaming(false)`）
- 修复 `drainError` 抛出前未清 streaming 状态
- 多处 null guard：`renderTimeline`、`renderMessages`、`buildMessages`、`runAgentLoop`

### 通知系统

- 统一 `isUserAway()`：`visibilityState !== "visible"` 覆盖切标签页 + 最小化 + 锁屏
- 三个触发点全部收口：权限请求、任务完成、问卷弹出

### 平台集成

- 平台地址独立配置：账户面板加"平台地址"输入框，存 localStorage
- `getPlatformUrl()` 取代硬编码 `localhost:3001`
- server 端 `_handle_sync_keys` 从请求体读 `platformUrl`
- 模型 Base URL 含 `/v1` 时兼容去重（`proxy()` 方法）

### 其他修复

- 流式输出降级 bug：`rfile.read(n)` 不保证完整读取 → 循环读满
- 默认记忆清理：只保留 `agent-lite-architecture.md`
- 记忆写入由"静默写入"改为"先询问用户确认"（提示词约束）

---

## 2026-07-14~15 · Codex

### P0 稳定性功能

- 网络断开、超时、429/5xx、SSE 中断自动退避重试（最多 5 次）
- 运行状态保存到会话检查点
- 页面刷新后按会话自动续跑
- 多会话恢复使用独立锁

### 会话切换不阻塞

- 移除旧兜底逻辑（"请等待当前回答完成后再新建会话"）
- 新建会话不中止原会话的 AbortController
- 切走前缓存原会话消息和统计
- 分支标记修复（普通会话误显示"已从「」创建分支"）

### 富文件预览

- 图片：适应窗口、缩放、1:1、拖拽
- Markdown：渲染/源码切换
- PDF：浏览器原生预览
- CSV/TSV：表格预览、分页、源码切换
- 大文件拖拽性能优化（requestAnimationFrame 限流）
- 源码乱码修复（高亮器基于原始文本分词）

### UI 改进

- 左下角设置齿轮图标 + 版本更新红点提醒
- 红点点击后消失，按版本号记录已读状态
- 右侧预览栏自动换行
- 预览栏文本/代码自动换行

### P0 对话问卷

- 原生 `request_user_input` tool calling
- 单选、多选、自由文本，单轮最多 3 题
- 每题独立确认/取消 + 填写替代想法
- 全部处理完后自动恢复原任务
- 问卷结果作为摘要插入消息流
- 刷新页面后恢复未完成问卷
- 按会话隔离
- 子 Agent 禁止直接发起问卷
- 问卷调用与其他工具调

### Skill 系统

- 3 个内置 Skill：skill-creator、find-skills、hyperframes
- 补齐 Agent Lite 所需的 name/description/keywords/tools frontmatter
- 中英文关键词 + 组合关键词匹配
- `/` 命令由 Skill 名称动态生成

---

## 2026-07-13 · Claude Code

### 稳定性修复

- 第三方 API Base URL 含 `/v1` 时模型检测失败（double path）
- 大请求体导致流式输出降级为批量（body 不完整读取）
- 图片消息自动降级为纯文本重试
- 非 abort 错误后会话 isStreaming 卡死

### UI

- 图片输入缩略图点击放大预览
- 多项 null guard 防 JS 崩溃
- i18n 覆盖新增的降级提示

### 项目

- README.md 创建
- TODO.md 创建
- 默认记忆清理为 agent-lite-architecture 唯一项

---

_格式：按日期 + 贡献方分组。新的改动追加在日期区块内，新的一天插入到最上方。_
