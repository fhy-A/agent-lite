# Codex / Claude Code Agent 设计分析报告

> 分析日期：2026-07-21  
> 分析方法：文件系统探索 + 会话记录分析 + 配置文件逆向 + 源码阅读  
> 分析范围：Codex CLI (gpt-5.6-sol) · Claude Code CLI (2.1.216) · code (v0.5.5)

---

## 一、总览对比

| 维度 | Codex | Claude Code | code（本项目） |
|------|-------|-------------|---------------|
| **产品形态** | Electron 桌面应用 + CLI | 纯 CLI（npm 全局包） | Web 应用（localhost:3010） |
| **模型** | gpt-5.6-sol（OpenAI） | Claude 5 系列（Anthropic） | 用户自配（OpenAI 兼容 API） |
| **推理强度** | xhigh | 自动 | 用户可选 |
| **沙盒模型** | 三层：进程 ACE deny + Node REPL + Sky 桌面 API | Sandbox 可选（filesystem + network egress） | 命令白名单 + 权限策略 |
| **子 Agent** | Agent Tree V2（6 个工具） | Task 工具（agent() 函数） | dispatchBackgroundSubAgent |
| **任务规划** | automation_update（cron/heartbeat） + 线程协调 | Workflow（pipeline/parallel/loop） | 无独立规划器 |
| **上下文窗口** | 258,400 tokens | 200,000 tokens | 取决于上游 API |
| **技能系统** | Plugins + Skills（Marketplace） | Skills（CLAUDE.md + SKILL.md） | Skills（frontmatter SKILL.md） |
| **Hook 系统** | 6 个生命周期 Hook（SessionStart 等） | Hooks（settings.json 配置） | 无 |
| **并发** | 4 槽位 Agent Tree | pipeline() + parallel() | 单主 Agent + 后台队列 |

---

## 二、Codex 架构详解

### 2.1 进程架构

```
codex.exe (350MB, Electron/Chromium shell)
  ├─ codex-code-mode-host.exe       ← 代码执行宿主（子 Agent 运行环境）
  ├─ codex-windows-sandbox-setup.exe ← 沙盒初始化（ACL 配置）
  ├─ codex-command-runner.exe        ← 沙盒命令执行器
  └─ node_repl.exe                   ← JS 运行时（受限 Node.js）
       └─ @oai/sky                   ← 桌面计算机使用 API
```

### 2.2 沙盒机制（三层隔离）

#### 第一层：进程级文件系统 ACL

启动时 `codex-windows-sandbox-setup.exe` 执行：
1. 扫描 900+ 个目录，标记 world-writable 目录
2. 对危险目录应用 capability deny ACE
3. 保护 `.git`、`.agents`、`.codex` 目录

```
AUDIT: world-writable scan FAILED; checked=951; flagged: \?\C:\Users\Public\SogouInput
AUDIT: applied capability deny ACE to \\?\C:\Users\Public\SogouInput
```

#### 第二层：Node REPL 运行时隔离

`node_repl.exe` 通过环境变量限制：
- `NODE_REPL_TRUSTED_CODE_PATHS` — 代码执行白名单
- `NODE_REPL_TRUSTED_BROWSER_CLIENT_SHA256S` — 浏览器客户端哈希校验
- `CODEX_HOME` — 数据目录隔离

#### 第三层：Sky 桌面 API 抽象

模型不能直接调用系统 API，只能通过 `@oai/sky` 的标准化接口：

```typescript
// 模型可用的唯一桌面接口
sky.get_screenshot()                        // 截图
sky.click({ x, y })                         // 坐标点击
sky.type_text({ text })                     // 键入文本
sky.press_key({ key })                      // 键盘操作
sky.drag({ from_x, from_y, to_x, to_y })   // 拖拽
sky.scroll({ direction, ... })              // 滚动
```

#### 策略分级（per-thread）

| 策略 | 文件系统 | 网络 | 使用场景 |
|------|----------|------|---------|
| `dangerFullAccess` | 无限制 | 启用 | 用户明确信任 |
| `workspaceWrite` | 限制写入根 | 禁用 | 默认模式 |
| `readOnly` | 只读 | 禁用 | 分析/审查 |

沙盒用户：`CodexSandboxOffline` / `CodexSandboxOnline`（DPAPI 加密密码）

---

### 2.3 子 Agent 调度 — Agent Tree V2

这是 Codex 最核心的 Agent 架构设计。

#### Agent 树模型

```
/root (主 Agent)
  ├─ sub-agent-A (spawn_agent)
  │   └─ sub-agent-A-1 (子 Agent 可递归创建)
  ├─ sub-agent-B
  └─ sub-agent-C
```

**4 个并发槽位**：root + 最多 3 个子 Agent 同时活跃

**共享文件系统**：所有 Agent 共享同一工作目录，编辑立即可见

#### 6 个协作工具

| 工具 | 函数 | 用途 |
|------|------|------|
| `spawn_agent` | 创建新子 Agent | `fork_turns` 控制上下文继承 |
| `followup_task` | 给已有 Agent 新任务 | 触发一个 turn |
| `send_message` | 给运行中 Agent 发消息 | 不触发 turn |
| `wait_agent` | 等待 Agent 完成 | 同步等待 |
| `interrupt_agent` | 中断运行中 Agent | 取消任务 |
| `list_agents` | 列出所有 Agent | 状态查询 |

#### 上下文继承（fork_turns）

```
fork_turns = "all"  → 全量历史 fork，继承父 Agent 的模型和推理强度
fork_turns = "none" → 空白上下文，可覆盖模型/推理设置
fork_turns = N      → 最近 N 轮历史
```

#### 关键策略：explicitRequestOnly

> **默认不自发并行。** 子 Agent 只在以下情况触发：
> 1. 用户明确要求
> 2. AGENTS.md 指令要求
> 3. Skill 指令要求

子 Agent 间通过 **结构化消息通道** 通信：
```
Message Type: MESSAGE | FINAL_ANSWER
Task name: <recipient>
Sender: <author>
Payload: <payload text>
```

---

### 2.4 长链路任务规划

Codex 没有独立的规划模块，而是组合两种机制：

#### 自动化系统（automation_update）

| 类型 | 用途 | 调度 |
|------|------|------|
| `cron` | 独立周期性任务 | RRULE（每小时/每周），可指定模型和推理强度 |
| `heartbeat` | 附加到当前线程的跟进 | 分钟/天/周间隔，`destination=thread` |

#### 线程协调

| 工具 | 用途 |
|------|------|
| `create_thread` | 创建线程（project-scoped 或 projectless） |
| `fork_thread` | fork 线程（同目录或 worktree 隔离） |
| `wait_threads` | 等待最多 8 个线程完成 |
| `send_message_to_thread` | 给线程发后续消息 |

#### 单回合执行模型

```
session start
  ├─ task_started (collaboration_mode: "default", model_context_window: 258400)
  │   ├─ model response → tool calls
  │   ├─ tool execution → results
  │   └─ event_msg: task_complete
  ├─ task_started (next turn)
  │   └─ ...
  └─ session end
```

**followUpQueueMode = "steer"**：模型完成一回合后可自主决定是否继续，而非固定轮次。

---

### 2.5 技能与插件系统

#### 插件架构

| 插件 | 版本 | 用途 |
|------|------|------|
| browser | 26.715.61943 | 应用内浏览器 + Chrome 控制 |
| computer-use | 26.715.61943 | 桌面自动化（SendInput + UI Automation + Graphics.Capture） |
| chrome | — | Chrome 浏览器操作 |
| visualize | — | 数据可视化 |
| documents | — | 文档处理 |
| pdf | — | PDF 处理 |
| spreadsheets | — | 表格处理 |
| presentations | — | 演示文稿 |

#### Skill 结构

每个 Skill 是 `SKILL.md` + `agents/openai.yaml`：

```yaml
# agents/openai.yaml
interface:
  display_name: "Browser"
  short_description: "Browser lets ChatGPT open and control the in-app browser..."
  default_prompt: "Inspect the current in-app browser tab or open a local app..."
```

#### 内置系统 Skill

- `skill-creator` — 创建 Skill（含子 Agent 前向测试）
- `review-agent` — 代码审查（设计为被委托使用）
- `plugin-creator` — 插件脚手架
- `imagegen` — 图像生成/编辑
- `skill-installer` — Skill 安装

---

### 2.6 Hook 生命周期

6 个生命周期事件全部可挂钩：

| 事件 | 超时 | 用途 |
|------|------|------|
| `SessionStart` | 30s | 会话开始通知 |
| `UserPromptSubmit` | 30s | 用户输入感知 |
| `PreToolUse` | 30s | 工具调用前拦截 |
| `PermissionRequest` | 600s | 权限审批（最长） |
| `PostToolUse` | 30s | 工具调用后回调 |
| `Stop` | 30s | 会话结束 |

所有 Hook 通过 stdin JSON 通信，外部进程通过 Node.js 执行。

---

## 三、Claude Code 架构分析

### 3.1 分发模式演变

| 版本 | 入口 | 文件数 | 大小 | Node |
|------|------|--------|------|------|
| 0.2.x | `cli.mjs`（纯 JS） | 424 | ~33MB | ≥18 |
| 2.1.216（当前） | `bin/claude.exe`（原生二进制） | 7（薄壳） | ~250MB | ≥22 |

当前版本是薄壳包 + 8 个平台专用 optionalDependencies。`postinstall` 脚本（`install.cjs`）负责从 optionalDependencies 中复制/硬链接实际二进制到 `bin/claude.exe`。

### 3.2 子 Agent 系统 — Workflow

Claude Code 的子 Agent 设计完全围绕 `Workflow` 脚本：

```
workflow script (JavaScript DSL)
  ├─ agent(prompt, {schema, model, effort, isolation})
  ├─ pipeline(items, stage1, stage2, ...)
  ├─ parallel(thunks)
  ├─ phase(title)
  └─ log(message)
```

#### 并发控制

- 最多 `min(16, cpu_cores - 2)` 个并发 agent()
- 同一 workflow 生命周期内最多 1000 个 agent()
- pipeline() 无屏障（流水线执行），parallel() 有屏障（全收集后继续）

#### 隔离模式

| 模式 | 用途 |
|------|------|
| `isolation: "worktree"` | Git worktree 隔离（~200-500ms 启动成本） |
| 默认（无隔离） | 共享工作目录 |

#### 质量模式

- **Adversarial verify** — N 个独立质疑者，多数投票决定
- **Perspective-diverse verify** — 不同视角（正确性/安全/性能/可复现）的验证
- **Judge panel** — N 个独立方案 → 并行评分 → 合成最佳
- **Loop-until-dry** — 未知大小的发现任务，直到连续 K 轮无新结果
- **Multi-modal sweep** — 按容器/内容/实体/时间多维度搜索
- **Completeness critic** — 最终检查"还有什么遗漏"

### 3.3 沙盒

- `sandbox.filesystem.disabled` — 跳过文件系统隔离但保留网络出口控制
- Worktree 隔离 — 通过 git worktree 实现文件级隔离
- 命令白名单 + 安全策略（类似 code 的命令拦截）

### 3.4 任务规划

- **无独立规划器** — 依赖模型自身推理
- **Workflow 脚本**支持循环、条件、动态缩放（`budget.total` / `budget.remaining()`）
- **CronCreate** — 会话级定时任务（5 字段 cron + recurring 标志）
- **Monitor** — 事件驱动的后台监控（tail -f / WebSocket / 轮询）

---

## 四、设计模式对比

### 4.1 子 Agent 调度策略

| | Codex | Claude Code | code |
|---|---|---|---|
| **触发方式** | explicitRequestOnly（默认不自动） | 脚本显式调用 agent() | 后台自动 dispatch |
| **上下文传递** | fork_turns（all/none/N） | prompt 参数（自由文本） | 精简摘要 |
| **并发模型** | 4 槽位 Agent Tree | pipeline + parallel（最多 min(16, cores-2)） | 单主 + 后台队列 |
| **通信方式** | 结构化消息通道（MESSAGE/FINAL_ANSWER） | 返回值（string 或 schema 验证） | 消息追加 |
| **层级** | 递归树（Agent 可创建子 Agent） | 一层（workflow 内部 fan-out） | 一层 |

### 4.2 沙盒隔离层级

```
Codex:           Claude Code:         code:
┌─────────┐      ┌─────────┐          ┌─────────┐
│ Sky API │      │ Sandbox │          │ 权限策略 │
│ (桌面抽象)│      │ (可选)   │          │ (全局)   │
├─────────┤      ├─────────┤          ├─────────┤
│ Node    │      │ Git     │          │ 命令白名单│
│ REPL    │      │ Worktree│          │ (全局)   │
├─────────┤      ├─────────┤          ├─────────┤
│ ACL     │      │ 命令行  │          │ 项目目录 │
│ Deny    │      │ 沙盒    │          │ 限制    │
└─────────┘      └─────────┘          └─────────┘
 (三层)           (两层)               (一层半)
```

### 4.3 任务规划能力

| 能力 | Codex | Claude Code | code |
|------|-------|-------------|------|
| 定时任务 | ✅ cron + heartbeat | ✅ CronCreate | ❌ |
| 事件监控 | ❌ | ✅ Monitor | ❌ |
| 跨线程协调 | ✅ create/fork/wait_threads | ❌（单 session） | ❌（单 session） |
| 自动化决策 | ✅ followUpQueueMode | ❌ | ❌ |
| 脚本编排 | ❌ | ✅ Workflow DSL | ❌ |

---

## 五、对 code 项目的启示

### 5.1 可借鉴的设计

#### 高优先级

1. **explicitRequestOnly 模式**（来自 Codex）
   - 问题：code 的 "子 Agent 缺乏上下文判断"，后台自动 dispatch 容易误执行
   - 方案：加一个开关，默认不自动 dispatch，只在用户/skill 显式要求时才用子 Agent
   - 实现：在 `dispatchBackgroundSubAgent` 入口加判断 `if (!ctx.explicitSubAgent) return queueForMainAgent()`

2. **fork_turns 参数**（来自 Codex）
   - 问题：code 子 Agent 的上下文固定为精简摘要
   - 方案：支持 `fork_turns: "all" | "none" | N` 参数化上下文继承
   - 实现：`dispatchBackgroundSubAgent(msg, { contextMode: "all" | "summary" | N })`

3. **自动化任务**（来自 Codex 的 automation_update + Claude Code 的 CronCreate）
   - 问题：code 无定时/事件驱动能力
   - 方案：加 `/cron` 命令，支持 cron 表达式和 heartbeat 间隔

#### 中优先级

4. **协作模式标记**（来自 Codex 的 collaboration_mode_kind）
   - 给 session 加 `mode` 字段（default/plan/auto），影响 Agent 行为
   
5. **Workflow 脚本**（来自 Claude Code）
   - 复杂任务用 pipeline/parallel/loop 模式替代当前的单 Agent 循环

6. **子 Agent 并发槽位**（来自 Codex 的 4 槽位）
   - 当前 code 是队列模型，可改为有限并发（如 3 个槽位）

### 5.2 不适合借鉴的

- **三层沙盒**（Codex）：code 是 Web 应用，不需要进程级 ACL 和桌面 API 抽象。当前命令白名单 + 权限策略已足够。
- **Agent Tree 递归**（Codex）：子 Agent 递归创建过分复杂，code 的一层扁平模型更可控。
- **Electron 桌面壳**（Codex）：与 code 的 Web 定位冲突。

---

## 六、附录：文件索引

### 6.1 Codex 关键文件

| 文件 | 用途 |
|------|------|
| `~\.codex\config.toml` | 主配置（模型/沙盒/插件/Hook） |
| `~\.codex\hooks.json` | 生命周期 Hook 注册 |
| `~\.codex\session_index.jsonl` | 会话索引 |
| `~\.codex\sessions\{year}\{month}\rollout-*.jsonl` | 会话记录（19,575 行/会话） |
| `~\.codex\.codex-global-state.json` | 全局状态（沙盒策略 per-thread） |
| `~\.codex\sandbox.*.log` | 沙盒审计日志 |
| `~\.codex\skills\` | 用户 Skill |
| `~\.codex\skills\.system\` | 系统 Skill |
| `~\.codex\plugins\cache\` | 插件缓存 |
| `~\.codex\process_manager\chat_processes.json` | 运行中进程注册表 |
| `~\AppData\Local\OpenAI\Codex\bin\{version}\codex.exe` | 主二进制 |
| `~\AppData\Local\OpenAI\Codex\runtimes\cua_node\{version}\` | CUA Node 运行时 |

### 6.2 Claude Code 关键文件

| 文件 | 用途 |
|------|------|
| `~\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\package.json` | 包描述（optionalDependencies 列表） |
| `~\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\install.cjs` | postinstall 脚本（二进制分发逻辑） |
| `~\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\cli-wrapper.cjs` | CLI 回退包装器 |
| `~\.npmrc` | npm 配置（作用域 registry） |

---

> **结论**：Codex 的子 Agent 和沙盒设计最为成熟（Agent Tree V2 + 三层隔离），Claude Code 的 Workflow 脚本编排最为灵活（pipeline/parallel/adversarial verify），code 当前处于两者之间，可以取 Codex 的 explicitRequestOnly 策略解决子 Agent 误执行问题，取 Claude Code 的 workflow 模式增强复杂任务处理能力。
