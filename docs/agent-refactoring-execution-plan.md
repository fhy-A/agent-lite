# Code Agent 改造执行方案

> 基于 [Codex/Claude Code Agent 设计分析报告](./codex-claude-code-agent-design-analysis.md)  
> 版本：v1.0 · 2026-07-21

---

## 一、改造目标

将 code 的子 Agent 从「无差别后台自动 dispatch」升级为「可控、可配置、可参数化」的委托模式，同时为后续自动化任务和 Workflow 编排预留扩展点。

---

## 二、分轮执行计划

### 第一轮：快速修复 + 基础（~3h）

#### 改造 1：explicitRequestOnly 模式

**目标**：默认不自动 dispatch 子 Agent，只在用户/Skill 显式要求时才启用。

**现状**：
```
用户发消息 → dispatchBackgroundSubAgent(msg)
  → 不管主Agent在干什么，直接创建子Agent处理
  → 子Agent只能拿到精简摘要，缺乏上下文判断
```

**目标行为**：
```
用户发消息 → 检查 dispatch 模式
  ├─ "explicit"（默认）→ 排队等主Agent空闲
  ├─ "auto"            → 当前行为（自动后台dispatch）
  └─ "off"             → 禁用，所有消息等主Agent
```

**改动文件**：

| 文件 | 改动 |
|------|------|
| `app.js` | `dispatchBackgroundSubAgent` 入口加模式判断；加 `_subAgentDispatchMode` 状态字段 |
| `settings.js` | 设置面板加 "子Agent调度" 下拉选项 |
| `i18n.js` | 新增 `subAgentDispatchMode` / `subAgentExplicit` / `subAgentAuto` / `subAgentOff` 键 |
| `index.html` | 设置面板加对应的 `<select>` |

**核心代码**（`app.js`）：

```js
// 在 dispatchBackgroundSubAgent 入口处
const SUB_AGENT_MODES = {
  explicit: "explicit",  // 默认：仅显式触发
  auto: "auto",          // 当前行为
  off: "off",            // 禁用
};

function shouldDispatchToSubAgent(msg, ctx) {
  const mode = state._subAgentDispatchMode || "explicit";
  if (mode === "off") return false;
  if (mode === "auto") return true;
  // explicit: only dispatch if user/skill explicitly requests it
  if (ctx?.explicitSubAgent) return true;
  if (isExplicitSubAgentTrigger(msg)) return true;
  return false;
}

function isExplicitSubAgentTrigger(msg) {
  // User typed something like "让子Agent帮我..." or used a skill that declares subAgent: true
  const text = getMsgText(msg) || "";
  const skill = matchSkillTrigger(text);
  if (skill?.subAgent) return true;
  return /子.?agent|后台.*处理|并行|委托|分头/.test(text);
}
```

**测试点**：
- 默认模式下用户发消息 → 不 dispatch，排队等主Agent
- 用户说"让子Agent查一下文档" → dispatch
- auto 模式 → 行为与当前一致
- off 模式 → 永远不 dispatch

---

#### 改造 4：collaboration_mode 会话标记

**目标**：给每个 session 加 `mode` 字段，控制 Agent 行为倾向。

**模式定义**：

| mode | 含义 | System Prompt 注入 |
|------|------|--------------------|
| `default` | 正常模式 | 无额外约束 |
| `plan` | 仅规划，不执行 | "You are in plan mode. Do NOT make any file changes. Only propose and explain." |
| `auto` | 自动执行，少确认 | "You are in auto mode. Proceed with changes without asking unless the operation is irreversible." |

**改动文件**：

| 文件 | 改动 |
|------|------|
| `app.js` | `buildRunContext` 读取 session mode；`sendMessage` 传递 mode 给 system prompt |
| `server.py` | session 存储 schema 加 `mode` 字段（默认 `"default"`） |
| `i18n.js` | 新增 `collabModeDefault` / `collabModePlan` / `collabModeAuto` |
| `index.html` | 输入框旁加 mode 切换下拉 |

**核心代码**（`app.js`）：

```js
// buildRunContext
const COLLAB_MODES = ["default", "plan", "auto"];

function buildRunContext(sessionId) {
  // ...existing logic...
  const sessionMode = getSessionMode(sessionId) || "default";
  return {
    // ...existing fields...
    collaborationMode: sessionMode,
  };
}

// sendMessage → buildModelRequestPayload
function injectModeDirective(systemPrompt, mode) {
  if (mode === "plan") {
    return systemPrompt + "\n\n**MODE: PLAN ONLY.** Do not make any file changes. "
      + "Propose edits, explain your reasoning, but do NOT call write_file, delete_file, "
      + "or any command that modifies the filesystem.";
  }
  if (mode === "auto") {
    return systemPrompt + "\n\n**MODE: AUTO.** Proceed with changes without asking "
      + "for confirmation unless an operation is irreversible (rm -rf, dropping tables, etc.).";
  }
  return systemPrompt;
}
```

**测试点**：
- plan 模式下 Agent 不会调用 write_file
- auto 模式下权限审批自动通过
- session 重载后 mode 保持

---

### 第二轮：子 Agent 能力升级（~7h）

#### 改造 2：fork_turns 上下文参数化

**目标**：子 Agent 的上下文继承不再是固定的精简摘要，改为可配置。

**上下文模式**：

| 模式 | fork_turns 值 | 行为 |
|------|--------------|------|
| `summary`（默认） | — | 当前行为：精简摘要 |
| `all` | `"all"` | 完整消息历史 fork |
| `last-N` | 正整数 | 最近 N 条消息 |

**改动文件**：

| 文件 | 改动 |
|------|------|
| `app.js` | `dispatchBackgroundSubAgent` 接受 `contextMode` 参数；`buildSubAgentContext` 根据模式构造消息列表 |
| `agent-runtime.js` | 子 Agent 创建时传递 `fork_turns` / `contextMode` |
| `server.py` | 子 Agent session 创建接口支持 `contextMode` 参数 |

**核心代码**（`app.js`）：

```js
async function dispatchBackgroundSubAgent(userMsg, options = {}) {
  const contextMode = options.contextMode || state._subAgentContextMode || "summary";

  let inheritedMessages;
  if (contextMode === "all") {
    // Full fork: clone all messages except internal markers
    inheritedMessages = state.messages
      .filter(m => !isInternalMessage(m) && !m.meta?.kind?.startsWith("error-"))
      .map(m => sanitizeForSubAgent(m));
  } else if (typeof contextMode === "number") {
    // Last N messages
    inheritedMessages = state.messages.slice(-contextMode)
      .filter(m => !isInternalMessage(m))
      .map(m => sanitizeForSubAgent(m));
  } else {
    // summary mode (default): compact the conversation
    inheritedMessages = await buildContextSummary(state.messages);
  }

  const subCtx = buildSubAgentContext(userMsg, inheritedMessages, options);
  // ...rest of dispatch logic...
}

function sanitizeForSubAgent(msg) {
  // Strip UI-only fields but keep role/content/thought/tool info
  return {
    role: msg.role,
    content: msg.content,
    thought: msg.thought,
    meta: {
      action: msg.meta?.action,
      path: msg.meta?.path,
      toolCalls: msg.meta?.toolCalls,
    },
  };
}
```

**测试点**：
- `contextMode: "all"` → 子 Agent 能看到完整历史
- `contextMode: 10` → 子 Agent 只能看到最近 10 条
- `contextMode: "summary"` → 行为与当前一致
- 不同模式下的子 Agent 输出质量对比

---

#### 改造 6：并发槽位管理

**目标**：限制同时活跃的子 Agent 数量，防止资源耗尽。

**当前问题**：
- 后台 dispatch 无上限，快速连续发消息可能创建大量子 Agent
- 每个子 Agent 持有独立 session 和 API 连接

**目标行为**：
- 最多 3 个并发子 Agent 槽位
- 超出的请求排队（FIFO）
- 槽位释放在 Agent 完成后自动触发

**改动文件**：

| 文件 | 改动 |
|------|------|
| `app.js` | `state._subAgentSlots` 槽位管理器；`dispatchBackgroundSubAgent` 入队逻辑 |
| `agent-runtime.js` | 子 Agent 完成/失败时回调释放槽位 |

**核心代码**（`app.js`）：

```js
const MAX_SUB_AGENT_SLOTS = 3;

function ensureSubAgentSlots() {
  if (!state._subAgentSlots) {
    state._subAgentSlots = {
      active: new Map(),     // slotId → { agentRunId, sessionId, startedAt }
      queue: [],             // pending dispatch items
      max: MAX_SUB_AGENT_SLOTS,
    };
  }
  return state._subAgentSlots;
}

async function dispatchBackgroundSubAgent(userMsg, options = {}) {
  const slots = ensureSubAgentSlots();

  if (slots.active.size >= slots.max) {
    // Queue the dispatch
    return new Promise((resolve) => {
      slots.queue.push({ userMsg, options, resolve });
    });
  }

  return await executeSubAgentDispatch(userMsg, options);
}

function releaseSubAgentSlot(slotId) {
  const slots = ensureSubAgentSlots();
  slots.active.delete(slotId);

  // Dequeue next pending dispatch
  if (slots.queue.length > 0 && slots.active.size < slots.max) {
    const next = slots.queue.shift();
    executeSubAgentDispatch(next.userMsg, next.options)
      .then(next.resolve);
  }
}
```

**测试点**：
- 同时 dispatch 5 个消息 → 3 个立即执行，2 个排队
- 子 Agent 完成后 → 槽位释放，队列前进
- 用户取消 → 槽位清理
- 跨 session 的槽位隔离

---

### 第三轮（按需）：自动化 + Workflow（~28h+）

#### 改造 3：/cron 定时任务

**设计概要**：
- 前端 `/cron` 命令 + 设置面板
- Python 端 `Scheduler` 线程（`threading.Timer` + 队列）
- 持久化到 `data/cron_jobs.json`
- 支持 cron 表达式 + heartbeat 间隔

**改造 5：Workflow 脚本**

**设计概要**：
- 轻量版，不实现完整 DSL
- 前端 `/workflow` 命令接受简化的任务描述
- parser 拆分 `step1 || step2 || step3`（并行）和 `step1 → step2 → step3`（串行）
- 每个 step 作为一个独立 agent() 调用

---

## 三、风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 子Agent模式切换导致已有session行为异常 | 低 | 中 | 新字段默认值 = 当前行为，向后兼容 |
| fork_turns: "all" 导致 API token 超限 | 中 | 中 | 加 token 计数器，超限自动降级为 summary |
| 并发槽位死锁 | 低 | 高 | 加超时自动释放（5min）；用户可手动清理 |
| collaboration_mode 与权限策略冲突 | 低 | 低 | mode 是"软约束"（system prompt 注入），权限策略是"硬约束"（工具拦截） |
| 定时任务在 dev 模式下行为不一致 | 中 | 低 | 加 `--no-cron` flag；dev 模式默认禁用 cron |
| Workflow 脚本注入风险 | 高 | 高 | 必须沙盒执行，不能直接 eval |

---

## 四、回滚策略

每个改造独立封装，可通过 settings 开关回退：

| 改造 | 回退方式 |
|------|---------|
| explicitRequestOnly | 设置面板切回 "auto" 模式 |
| fork_turns | 子 Agent 选项切回 "summary" |
| /cron | 删除所有 cron job 即停止 |
| collaboration_mode | 切回 "default" |
| 并发槽位 | 设置 `MAX_SUB_AGENT_SLOTS = 999`（无限制） |
| Workflow | 不用 `/workflow` 命令即可 |

---

## 五、验收标准

### 第一轮验收

1. ✅ 默认模式下，用户连续发 3 条消息 → 全部排队等主Agent，不创建子Agent
2. ✅ 用户说"让子Agent帮我查" → 创建子Agent
3. ✅ 设置面板可切换 explicit/auto/off
4. ✅ plan 模式下 Agent 拒绝 write_file 调用
5. ✅ auto 模式下编辑自动审批

### 第二轮验收

1. ✅ 子Agent 在 fork_turns: "all" 模式下能引用完整对话历史
2. ✅ 同时 dispatch 5 个消息 → 3 个活跃 + 2 个排队
3. ✅ 子Agent 完成后槽位正确释放
4. ✅ 现有测试全部通过

---

## 六、时间线

```
Week 1, Day 1-2:  第一轮（explicitRequestOnly + collaboration_mode）
                   预计 3h 开发 + 1h 测试 = 4h

Week 1, Day 3-4:  第二轮（fork_turns + 并发槽位）
                   预计 7h 开发 + 2h 测试 = 9h

Week 1, Day 5:    代码审查 + 全量回归测试 + 文档更新
                   预计 3h

Week 2+:           第三轮按需启动
```
