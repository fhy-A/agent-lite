# Code 开发日志

> 记录 Claude Code、Codex 以及其他协作方的重要改动，按时间倒序。

## 项目记忆与记录规范

- 本文件是项目**已完成改动与验证结果**的统一记录；`TODO.md` 是项目**未完成事项、优先级与后续计划**的统一记录。
- Claude Code、Codex 及人工开发者开始任务前都应先阅读这两个文件，避免重复实现或依据过期信息工作。
- 完成功能、修复缺陷、调整架构/协议/UI、发布版本、改变产品决策或完成重要测试后，必须在本文件记录结果；尚未完成或新发现的工作同步写入 `TODO.md`。
- 记录应包含日期、贡献方、改动目的、关键行为和验证结论；必要时补充版本号或相关文件，避免只写“已优化”“已修复”等无法追溯的描述。
- 自 2026-07-15 起，新增日志标题必须包含本地具体时间戳，格式为 `YYYY-MM-DD HH:mm`；此前未记录具体时间的历史内容保持不变。
- 同一天的新增内容追加到对应贡献方区块；新的一天插入到最上方。除纠错外不改写既有历史。
- 如果两份文档、实际代码和测试结果不一致，应在当前任务内核实并同步修正，不能让冲突状态继续保留。

---

## 2026-07-17 18:00 · Claude Code + Codex

### SSE 渲染修复：思考摘要分离 + 流式节点防闪烁

**问题诊断**：两个根因：
1. 所有带 `toolCalls` 的 assistant 文本都被收入”思考过程”，导致最终回答可能重复出现在思考区
2. 状态条（模型名 + 思考中 + 计时）绑定在单次流式消息上，DOM 重建时销毁，导致闪烁

**Codex 改动**（消息投影层）：
- `renderMessages()`：仅收集带 `meta.toolCalls` 的中间 assistant 消息进入思考投影块，最终回答不再混入
- `renderFinalAssistantProjection()`：移除 `data-stream-part=”thought”` 独立思考展示区，加 `data-stream-session` 属性
- `patchStreamingAssistantMessage()`：移除 thought 节点增量更新，去掉全量 render 回退
- `renderThinkingProjection()`：重构为 `<thinking-summary-list>` + `<thinking-summary-item>` 独立段落结构
- `styles.css`：删除 `.streaming-thought-output` / `.completed-thought-output` 样式，新增 `.thinking-summary-list` / `.thinking-summary-item` 样式，段落间隙 1.15em

**Claude Code 改动**（DOM 防闪烁层）：
- `renderMessages()`：innerHTML 前先用 `node.remove()` 将流式节点从 DOM 拆下，innerHTML 后再 `replaceWith` 装回；避免销毁导致 CSS 动画重启和计时文本丢失
- `renderThinkingProjection()`：增加 280 字符截断，超长摘要以 `…` 收尾，保持每轮摘要简洁
- 测试变量名 `activeStreamingNodes` → `preservedNodes`，与代码同步

**测试结果**：前端模块 9/9 + 全量 466 passed + 2 subtests passed
**改动的文件**：`app.js`、`styles.css`、`tests/test_frontend_modules.py`、`CHANGELOG.md`、`TODO.md`

**已知遗留**：工具轮次切换时状态条仍短暂消失——需将状态从”单次 SSE 请求级”提升为”整轮 Agent 任务级”（`setStreaming` / 计时器生命周期解耦）。

## 2026-07-16 15:22 · Codex

### app.js 模块化：通知服务

- 新增 `src/services/notifications.js`，统一封装页面 Toast 与浏览器系统通知。
- `app.js` 改为从 `window.Code.services.notifications` 使用 `showToast` 和 `notify`；任务完成、权限待确认和问卷等业务触发条件继续留在原主流程中。
- `index.html` 将通知服务固定在核心模块之后、运行时与主应用之前加载；正式 EXE 已通过现有 `src/` 资源规则自动包含该模块。
- 扩充 `tests/test_frontend_modules.py`，覆盖通知模块文件、加载顺序、服务导出、主文件代理及重复定义。
- 验证结果：前端模块定向测试 7 项通过；全量测试 469 项及 2 个子测试通过；新增模块与 `app.js` JavaScript 语法检查通过。

## 2026-07-16 14:46 · Codex

### app.js 模块化：第一批核心基础模块

- 新增 `src/core/namespace.js`，建立 `window.Code.core/services/features/agent/ui` 统一命名空间。
- 将图标路径表与 `uiIcon()` 抽离至 `src/core/icons.js`；将 HTML 转义、紧凑数字、数字、耗时格式化及 token 估算抽离至 `src/core/utils.js`。
- `app.js` 改为从 `window.Code.core` 读取接口并删除对应旧定义；暂时保留两个既有 `formatSize()`，避免在结构拆分提交中混入行为清理。
- `index.html` 固化 `namespace → icons → utils → agent-runtime → app` 的加载顺序。
- `build_exe.py` 补充 `agent-runtime.js` 与完整 `src/` 资源，避免正式 EXE 缺少拆分模块。
- 新增 `tests/test_frontend_modules.py`，覆盖模块文件、加载顺序、命名空间、重复定义与打包资源。

## 2026-07-16 12:30 · Claude Code

### 品牌重命名：Agent Lite → Code

- **Code 项目**（53 文件，398 处）：
  - 核心源码：`server.py`、`app.js`、`launcher.py`、`build_exe.py`、`index.html`
  - class 名：`AgentLiteHandler` → `CodeHandler`、`AgentLiteTrayIcon` → `CodeTrayIcon`
  - env var：`AGENT_LITE_*` → `CODE_*`
  - 数据目录：`~/.agent-lite/` → `~/.code/`
  - EXE 名：`AgentLite-v*.exe` → `Code-v*.exe`
  - localStorage：40 个 key 从 `agent-lite-*` → `code-*`，含自动迁移函数
  - 图标：`agent-lite-icon.ico` → `code-icon.ico`
  - 桌面快捷方式：`AgentLite.lnk` → `Code.lnk`
  - 批处理文件：`启动AgentLite.bat` → `启动Code.bat`
- **老用户数据迁移**：`launcher.py` 新增 `migrate_old_data_dir()`，启动时自动将 `~/.agent-lite/` 数据迁移到 `~/.code/`；`app.js` 新增 localStorage 迁移函数，自动拷贝旧 key 值到新 key。
- **New API 中转站**（8 源文件 + 3 目录）：
  - Go 后端：`controller/agent_lite.go` → `controller/code.go`，函数 `AgentLiteAuthorize` → `CodeAuthorize`，路由 `/agent-lite/authorize` → `/code/authorize`，参数 `agent_lite_token` → `code_token`
  - React 前端：路由 `/agent-lite` → `/code`，页面组件 `AgentLite` → `Code`，导航标题更新
  - `routeTree.gen.ts` 自动生成路由树全部更新
- **Claude Code memory**：24 文件重命名，内部引用路径全部更新到新项目路径。
- **Docker**：`new-api-custom:dev` 镜像重建（`docker commit`），Compose 接管容器管理，`new-api-custom-dev` 正常启动。
- **教训**：已有 Dockerfile/Compose 配置时应先用 `docker build --pull=false`，不应绕过直接装本地工具。见 [[docker-build-rules]]。
- **测试结果**：457 passed, 2 subtests passed，零回归。

## 2026-07-16 02:30 · Claude Code

### 思考合并 + 消息持久化简化 + tool_calls 防御 + read_skill_resource

- **思考过程合并**：`renderMessages` 中所有轮次 assistant 的思考合并为一个块，中间轮次（带 tool_calls 无实质内容）只贡献思考不渲染独立气泡，最终回复 thought 从 `renderFinalAssistantProjection` 移除（流式期间仍实时显示）。
- **消息持久化简化**：移除 delta 增量追加（`_persistedMsgCount` 等），改为流结束/切会话/关页面时全量写入 JSONL。流式期间 `saveSessionState` 只写 meta JSON。彻底消除最后一条消息丢失。
- **tool_calls 防御**：`buildMessages` 中任何非 tool 消息跟在带 tool_calls 的 assistant 后时自动剥离未匹配 tool_calls，遍历结束最终 pass 清理。历史消息不配对也不会 API 400。
- **`read_skill_resource` tool**：原生工具让模型按需读取 skill 内 scripts/references/assets。Server handler + tool definition + permission + i18n。
- **已知问题**：流式 UI 思考中/模型名/计时偶尔消失，刷新恢复，记入 TODO.md。

## 2026-07-16 01:00 · Claude Code

### Skills 渐进式加载 + 会话索引分层

- **Skills**：`list_skills(brief=True)` 只返回元数据；`GET /api/skills/{name}` 按需加载 body；`GET /api/skills/{name}/file` 读取资源文件。
- **会话分层**：`YYYY/MM/DD/{id}.json` 分层；`index.jsonl` 独立索引；`get_sessions()` O(1)；全 CRUD 自动同步索引；启动迁移 + 孤儿清理。`SESSION_INDEX_PATH` 改为函数支持 mock。

## 2026-07-15 22:30 · Claude Code

### 会话存储 JSON → JSONL 迁移

- **双文件存储**：每个会话拆为 `{id}.json`（元数据：title、stats、runState、messageCount、lastMessageTime）和 `{id}.jsonl`（消息逐行追加，7 字段：role、content、thought、meta、_images、_model、_time）。
- **Server 端**：新增 `read_jsonl`、`write_jsonl`（atomic temp+replace）、`append_jsonl`（受 `_json_write_lock` 保护）、`count_jsonl_lines`、`read_last_jsonl_line`、`messages_path` 六个函数；新增 `POST /api/sessions/{id}/messages` 增量追加端点；改造 8 个 session CRUD 函数（create/save/get/list/delete/branch/archive/summary）适配双文件。
- **前端 delta 持久化**：`saveSessionState` 只将新消息增量追加到 JSONL（`slice(persisted, -1)`，排除正在流式输出的最后一条）；`clearRunCheckpoint` 流结束时 flush 最后一条完整消息；`cacheActiveSessionState` 切会话前 flush 剩余；`beforeunload` + `sendBeacon` 兜底；`loadSession` 重置 `_persistedMsgCount` 追踪。
- **compaction 兼容**：compaction 只插 `meta.kind: "compact-summary"` 标记，不缩减消息数组。delta 追加模式天然兼容，无需全量覆写。
- **消息不丢失**：流式期间最后一条 assistant 消息不在 delta 中落地（因内容原地增长），流结束由 `clearRunCheckpoint` 一次性写入完整内容。
- **旧数据清理**：147 个旧测试会话 JSON 全部删除，新格式零兼容负担。
- **额外修复**：`renderMessages()` 两个 return 路径末尾补 `scheduleMessagesScrollToBottom`，修复用户发新消息后不自动滚到底的已有 bug。
- **测试结果**：全量 **457 passed, 2 subtests passed**（新增 11 项 JSONL 专项测试，更新 1 项并发测试适配新格式）。
- **改动的文件**：`server.py` +170 行，`app.js` +100 行，`tests/test_session_persistence.py` +80 行，`tests/test_routes.py` +20 行，`tests/test_branch.py` +12 行，`tests/test_concurrency.py` ~5 行修改，`docs/session-jsonl-migration.md` 方案文档新增。

## 2026-07-16 01:00 · Claude Code

### Skills 渐进式加载 + 会话索引分层

**Skills 三层渐进式加载（对标 Codex）**：
- `list_skills(brief=True)` 只返回 name、description、keywords、tools、dir，不含 body（Level 1）
- 新增 `GET /api/skills/{name}` — 按需加载单个 skill 完整 body + 资源列表（Level 2）
- 新增 `GET /api/skills/{name}/file?path=...` — 按需加载 skill 内资源文件 scripts/references/assets（Level 3）
- 前端 `loadSkills()` 用 `?brief=1` 只取元数据；`ensureSkillBody(skill)` 懒加载 body
- `getMatchedSkillPrompts()` 改为 async，匹配后按需拉取 body；`getSystemPrompt()` 改为 async
- 系统提示词不再包含全部 15 个 skill body，仅 name + description 列表
- `showSkillDetail` / `showSkillDetailInSettings` 点击时懒加载完整 body
- token 估算路径（calcStats）使用 `briefSkills=true` 跳过 body 加载

**会话索引 + 目录分层（对标 Codex）**：
- `session_path` / `messages_path` 改为 `YYYY/MM/DD/{id}.json` 分层存储
- 新增 `data/sessions/index.jsonl` 独立会话索引（id、title、updatedAt、messageCount、_parentId、_branchDepth）
- `get_sessions()` 读索引 O(1) 列表，不再 glob 扫描
- create/save/delete/branch/append_messages 全自动同步索引
- 启动时 `_migrate_sessions_to_hierarchy()` 将旧扁平文件迁移到分层目录并重建索引
- archive_dir 保持扁平不变

**测试结果**：全量 457 passed, 2 subtests passed

## 2026-07-15 22:30 · Claude Code

### 会话存储 JSON → JSONL 迁移

- 双文件存储：`{id}.json`（元数据）+ `{id}.jsonl`（消息逐行追加）
- 前端 delta 持久化：流式期间排除最后一条、流结束 flush、beforeunload sendBeacon 兜底
- compaction 兼容：只插 marker 不缩数组，delta 模式天然兼容
- 滚动修复：renderMessages 末尾补 scheduleMessagesScrollToBottom

## 2026-07-15 19:29 · Codex

### 扩大用户消息操作区的悬停命中范围

- **交互修复**：将用户消息气泡、时间戳和复制按钮包裹为统一悬停区域，并在气泡下方增加 `30px` 透明衔接区，鼠标从气泡移向操作按钮时不再因短暂离开气泡而隐藏控件。
- **范围收敛**：悬停命中宽度跟随实际消息气泡，不扩展到整行空白区域，避免误触发时间戳和复制按钮。
- **可点击性**：透明衔接区接收鼠标事件，操作控件通过层级保持可见和可点击。
- **验证结果**：浏览器确认新样式规则已加载；`app.js` 语法检查通过；P0 稳定性回归 12 项通过。

## 2026-07-15 18:08 · Codex

### 优化断网重连提示语义
- **计时核验**：使用可控断网测试确认浏览器轮询第 1～5 次失败约发生在 `0.02s / 0.54s / 1.55s / 3.57s / 7.58s`；计数未被重复轮询叠加，第 5 次较快出现源于 `0.5s / 1s / 2s / 4s` 的快速退避设计，不是计数错误。
- **文案修正**：中文提示改为“网络连接已中断，正在自动恢复 · 已尝试 N 次 · Ns 后重试”，英文同步调整，明确数字表示累计尝试次数而非当前等待轮次。
- **策略保持**：不修改快速探测及第 5 次后每 8 秒持续重连的行为，避免牺牲短暂断网时的恢复速度。

## 2026-07-15 17:40 · Codex

### 已完成断网重连状态提示

- **断网可见反馈**：浏览器与本地运行流失联时，在当前回答内容下方显示“网络异常，重新连接中（第 N 次），倒计时 Ns”，避免输出静止被误认为卡死。
- **恢复联动**：重连成功后自动移除提示；模型名旁的“思考中 + 总用时”持续保留，不再被网络状态替换。
- **状态隔离**：区分浏览器长轮询断线与上游模型请求重试，保持既有 5 次模型退避策略和后台任务连续性不变。
- **验证结果**：`app.js` 与 `agent-runtime.js` 语法检查通过；P0 稳定性回归 12 项通过；完整测试 451 项及 2 个子测试全部通过。

## 2026-07-15 16:33 · Codex

### 已完成会话刷新后的滚动位置修复

- **根因修复**：将历史会话恢复后的滚动定位从时间线渲染中拆出，避免只有一条用户消息、时间线不显示时缺少滚动到底部的逻辑。
- **布局兼容**：会话内容渲染后等待两帧再定位到底部，兼容 Markdown、diff 等内容完成布局后的实际高度。
- **并发保护**：延迟滚动前校验当前会话 ID，防止快速切换会话时旧会话的滚动任务影响新会话。
- **职责收敛**：时间线仅负责消息导航，不再隐式控制对话区滚动位置。

---

## 2026-07-15 15:38 · Codex

### New API 开发环境数据库恢复与备份

- **开发库全量同步**：将生产网关 `3000` 的 SQLite 数据库完整复制到开发网关 `3001`，使开发环境继承用户、管理员、2FA、渠道、令牌、额度、模型、分组和系统设置；复制完成后两套数据库继续独立管理。
- **登录验证**：使用生产库管理员身份成功登录 `3001`，并在新版前端完成部分开发环境设置调整。
- **持久化确认**：`3001` 继续使用 `new-api-source-runtime/data/one-api.db` 的宿主机目录映射，容器重启不会删除该数据库。
- **安全备份**：短暂停止 `new-api-custom-dev` 后生成 `new-api-source-runtime/backups/one-api-dev-20260715-153500.db`，文件大小 `4.15 MB`，SHA-256 为 `B187257F3D655B6B47073084C27916B161EDF4AC3D6C5D1FF026DDEDBE2569FE`。
- **验证结果**：备份与源数据库 SHA-256 一致；开发容器恢复运行后 `http://localhost:3001/` 返回 HTTP `200`。

---

## 2026-07-15 12:23 · Codex

### 模型运行时桥接与刷新续接

- **运行时客户端拆分**：新增 `agent-runtime.js`，把模型运行的创建、长轮询续接、取消和 SSE 适配从 `app.js` 中独立出来，作为后续模块化的第一步。
- **服务端托管模型流**：新增 `/api/runtime/runs` 运行接口，由本地服务持有上游请求、缓存 SSE 事件并分配 `runId`；浏览器刷新后可重新读取同一事件流，不会再次向上游发起模型请求。
- **会话恢复**：运行检查点持久化 `runtimeRunId`；刷新后复用原有流式 assistant 消息并重放事件，完成、失败、取消和重试时统一清理运行标识。
- **取消链路**：停止回答时同时中止浏览器读取和服务端上游连接，避免后台请求继续消耗 token。
- **敏感信息边界**：API key 与请求正文只在服务端运行期间保存在内存中，不写入运行事件或状态响应，并在任务进入终态后清除；终态事件保留 30 分钟用于短时刷新续接。
- **子 Agent 文本清理**：`server.py` 的子 Agent 工具描述、执行结果和 API 错误统一为英文，移除服务端工具结果中的硬编码中文，降低编码异常风险。
- **实现边界**：本次仅将模型请求和事件流下沉到本地服务；工具、权限、问卷及子任务调度仍由浏览器端 Agent 循环负责，完整后台 Agent 循环继续保留在 `TODO.md`。
- **验证结果**：`server.py`、`app.js`、`agent-runtime.js` 语法检查通过；运行时刷新重放测试确认同一任务只调用上游一次且 API key 不进入状态响应；全量 `444` 项测试与 `2` 个子测试全部通过。

---

## 2026-07-15 08:59 · Codex

### Claude Code 改动审查与稳定性修复

- **审查结论**：保留项目日志治理、问卷工具互斥、会话恢复等有效改动；重点修复自动压缩、跨会话统计和并发保存中的不稳定点。
- **上下文压缩持久化**：以持久化 `compact-summary` 消息作为模型上下文边界，替代只在运行时生效的 `_compactPrefix` / `_compactCutoff`；刷新或重启后仍能保持压缩结果，且边界在过滤后台消息后计算。
- **多会话用量隔离**：按会话保存并恢复 `lastUsage`，防止一个会话的 token 统计污染另一个会话；手动或自动压缩后清除旧用量基线。
- **上下文窗口识别**：统一模型上下文上限判断，支持 Claude 点号和连字符版本名，并修复 Claude 4.6+ 1M 上下文分支不可达的问题。
- **并发保存稳定性**：会话读改写统一置于文件锁内；Windows 临时文件占用时对原子替换进行短暂退避重试，避免后台保存线程静默失败。
- **测试补强**：增加会话用量持久化、文件替换重试、并发保存异常捕获、压缩边界持久化与模型上下文识别测试；同步更新已被新实现替代的旧源码断言。
- **验证结果**：`app.js` 语法检查通过；全量 442 项测试通过，未出现 `PermissionError`、后台线程异常或 traceback。

---

## 2026-07-15 · Codex

### 项目文档治理

- 确立 `CHANGELOG.md`（已完成历史）与 `TODO.md`（待办计划）为项目统一的人类可读记忆。
- 新增 Claude Code 与 Codex 的项目入口说明，要求任务开始前读取、重要改动完成后同步更新。
- 校正流式 token 计数状态，并补全 P0 问卷工具互斥说明。

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
- 默认记忆清理：只保留 `code-architecture.md`
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
- 问卷调用与其他工具调用互斥，避免任务挂起期间继续产生副作用

### Skill 系统

- 3 个内置 Skill：skill-creator、find-skills、hyperframes
- 补齐 Code 所需的 name/description/keywords/tools frontmatter
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
- 默认记忆清理为 code-architecture 唯一项

---

_格式：按日期 + 贡献方分组。新的改动追加在日期区块内，新的一天插入到最上方。_
