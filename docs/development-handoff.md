# Code 开发交接快照

> 更新时间：2026-07-23
>
> 用途：为新任务提供最小、可核验的接手上下文。
>
> 事实源：已完成改动以 [`../CHANGELOG.md`](../CHANGELOG.md) 为准，未完成事项以 [`../TODO.md`](../TODO.md) 为准。本文件只做导航；开始开发前必须重新核对 Git 状态和上述两份文档。

## 一、当前仓库状态

- 项目目录：`C:\Users\Admin\Desktop\api中转站\code`
- 当前分支：`master`
- 本快照建立前的 HEAD：`b367307 feat: complete skill dependency collaboration flow`
- 当前发布基线：Code v0.5.6
- 本地服务入口：`server.py`，默认监听 `127.0.0.1:3010`
- 前端仍以原生 JavaScript、HTML 和 CSS 为主，主状态保留在 `app.js`，部分功能已迁入 `src/`。
- 模型平台和 Base URL 固定为 `https://workbar.ai`，前端不展示或编辑该地址。
- 仓库根目录存在未跟踪的 `package.json` 和 `package-lock.json`。它们不属于最近已验收阶段，接手者不得擅自暂存、删除或覆盖。

开始新任务后先执行：

```powershell
Set-Location "C:\Users\Admin\Desktop\api中转站\code"
Get-Content CHANGELOG.md -Encoding utf8 -TotalCount 120
Get-Content TODO.md -Encoding utf8
git status --short
git log -8 --oneline
```

如果 Git 状态、HEAD 或待办已经变化，以现场结果为准，不要机械沿用本快照。

## 二、近期稳定基线

### Workbar 与设置

- Code 必须通过 Workbar 授权后使用；登录认证、Key 同步和模型刷新已经重做。
- 自动同步只合并 Workbar 侧实时 Key，不应覆盖用户手动维护的其他 Key；退出登录会清理授权、Key 和模型状态，不清理本地会话与项目文件。
- 设置页已经完成导航分组、Workbar 账号信息、Key 列表、模型列表、主题与语言交互的主要重构。
- 设置页固定文案和动态内容支持中英文即时切换；新增用户可见文本必须继续维护 `src/core/i18n.js`，不得在业务文件中新增局部语言字典。

### AgentRun、会话与消息

- 四种权限模式的新任务均由服务端持久 AgentRun 执行，浏览器负责创建、观察 SSE、问卷和授权交互。
- 主任务运行时的普通新消息进入 FIFO 主队列；只有明确的并行操作才创建后台 AgentRun。排队消息保存发送时的模型、模式和思考强度快照。
- 模型 `task` 工具会创建一层 Child AgentRun；同一模型轮次最多并发 3 个，不允许递归委托。
- 会话使用 JSONL 持久化。分支会话复制父会话消息与累计统计，父子会话之后独立保存，并在界面显示分支关系。
- 页面刷新、切换会话或新建会话不应取消其他正在运行的任务；恢复依赖稳定的 AgentRun ID、请求 ID 和事件游标。

### Skills 依赖管理

- `dependencies.json` 已支持按能力声明 Python、Node 和系统依赖，并可从常见依赖文件、静态导入和明确安装说明中自动发现候选项。
- Skill 首次使用会按具体能力预检。多能力 Skill 未指定能力时只能报告状态，不能批量安装全部能力依赖。
- Python 与 Node 依赖只能在 Code 管理的隔离运行时中、经用户授权后安装；系统依赖只返回说明和 `installHint`，不由模型直接执行系统包管理器。
- 已阻止系统安装器、包装安装脚本、PATH 修改、全局命令包装器和重复安装循环；相同安装命令最多尝试两次，安装超时上限为 300 秒。
- DOCX Skill 已按创建、读取、渲染等能力分别报告状态，并为 Pandoc、LibreOffice、Poppler 提供 Windows 安装提示。
- 当前尚缺设置页的安装、修复、卸载、进度和失败恢复入口，这是最适合继续完成的下一阶段。

## 三、建议的下一阶段

### 首选：Skill 依赖设置页操作闭环

目标只覆盖设置页，不扩展新的依赖协议：

1. 对可由 Code 管理的 Python/Node 依赖提供“安装 / 修复 / 卸载”。
2. 操作前展示目标能力、安装位置、命令摘要和授权范围。
3. 展示进行中、完成、失败、取消和重新检查状态。
4. 系统级依赖继续只显示安装说明，不提供一键执行。
5. 操作完成后刷新该 Skill 的能力状态，不重新扫描无关页面或丢失当前选择。
6. 补齐中英文文案、接口测试、前端状态测试和浏览器人工验收。

验收时重点观察：重复点击、切换 Skill、切换语言、刷新页面、取消操作、安装失败后重试，以及已经安装的依赖是否被误删。

### 后续独立阶段

- 统一委托 `Context Envelope`：为 Child AgentRun 和用户并行任务提供受预算、安全过滤、可恢复的上下文契约。
- `app.js` 第四阶段拆分：迁移剩余高耦合的会话与运行时逻辑。
- 错误分类与恢复建议、Skill 执行证据校验、Workbar Token/成本体验。
- 结构化计划能力必须等 Context Envelope 稳定后再开始；Cron、Monitor、Workflow 和 worktree 隔离更晚评估。

详细顺序见 [`agent-refactoring-execution-plan.md`](./agent-refactoring-execution-plan.md)。

## 四、验证与提交规则

每个阶段遵循 [`../AGENTS.md`](../AGENTS.md) 的协作流程：

1. 一次只做一个阶段，旁支问题不阻塞就写入 `TODO.md`。
2. 先运行直接相关的定向测试，再按风险选择主测试集、语法检查和 `git diff --check`。
3. 视觉、焦点、流式时序和浏览器差异必须交给用户人工确认，确认前不提交。
4. 验收后更新 `CHANGELOG.md` 和 `TODO.md`，只暂存本阶段文件并独立提交。
5. 最终报告测试结果、提交哈希和仍保留的未提交文件。

常用检查：

```powershell
python -m py_compile server.py skill_dependencies.py launcher.py
node --check app.js
node --check src/core/i18n.js
python -m pytest tests/test_skill_dependencies.py tests/test_frontend_modules.py tests/test_server.py -q
git diff --check
```

测试集合会继续变化，不能把本文件中的命令或历史数量当成固定基线。最近一次已记录验证结果请查阅 `CHANGELOG.md`。

## 五、环境与安全注意事项

- Workbar Access Token、API Key、Authorization 头和完整请求凭据不得写入 AgentRun、交接文档、测试输出或 Git。
- `data/` 中包含本地会话、授权状态、运行检查点和备份；除非任务明确要求，不要批量清理。
- 先前依赖调试曾在当前用户的 `%APPDATA%\npm` 下产生 `pandoc.cmd`、`soffice.cmd`、`pdftoppm.cmd` 包装器。为避免破坏当前机器已可用的依赖，它们未被自动删除；后续处理必须先确认真实目标并取得用户授权。
- 不要用 `git reset --hard`、`git checkout --` 或其他破坏性操作处理共享工作区。
- Windows 构建遵循已有 Dockerfile 和打包脚本；Docker 构建优先使用 `--pull=false`。

## 六、可直接粘贴到新任务的启动消息

```text
请接手 C:\Users\Admin\Desktop\api中转站\code 的后续开发。

开始前完整阅读 AGENTS.md、CHANGELOG.md、TODO.md 和 docs/development-handoff.md，并用 git status --short、git log -8 --oneline 核对现场状态。CHANGELOG.md 是已完成改动的事实源，TODO.md 是未完成事项的事实源；交接快照与现场冲突时以现场为准。

当前建议先完成“Skill 依赖设置页操作闭环”：只增加隔离运行时内 Python/Node 依赖的安装、修复、卸载、进度与失败恢复；系统依赖继续只显示 installHint，禁止模型直接运行系统包管理器、修改 PATH 或创建全局包装器。保持现有依赖协议、首次使用预检、安全边界和中英文即时切换不退化。

仍有未跟踪的 package.json 与 package-lock.json，不要擅自暂存、删除或覆盖。一次只推进一个阶段；自动测试充分时自行验证、更新 CHANGELOG/TODO 并提交，涉及界面和时序时先给我人工测试步骤，等我确认后再提交。
```
