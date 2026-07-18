<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/code-logo-white.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/code-logo-black.svg">
    <img src="assets/code-logo-black.svg" width="88" height="88" alt="Code Logo">
  </picture>
</p>

<h1 align="center">Code</h1>

<p align="center"><strong>本地 Web 服务 · AI Coding Agent</strong></p>
<p align="center">让 AI 真正进入你的项目，而不是停在对话框里。</p>

<p align="center">
  <a href="https://github.com/fhy-A/Code/releases/latest"><img src="https://img.shields.io/badge/version-0.5.4-2563EB" alt="Version 0.5.4"></a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4" alt="Windows">
  <img src="https://img.shields.io/badge/python-3.12+-3776AB" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/tests-488%20passed-16A34A" alt="488 tests passed">
  <a href="docs/LICENSE"><img src="https://img.shields.io/badge/license-MIT-6B7280" alt="MIT License"></a>
</p>

---

## 项目简介

Code 是一个运行在本机的 AI 编程 Agent。它以浏览器作为交互界面，通过 OpenAI 兼容 API 接入模型，并在用户选定的项目目录中读取文件、搜索代码、执行命令、修改内容和验证结果。

它不是 IDE 插件，也不是只能生成代码片段的聊天页面。一次任务可以从理解项目开始，经过多轮工具调用、测试和修复，最终把结果直接落到真实工作区。

Code 当前聚焦三个目标：

- **项目上下文**：围绕完整目录、依赖关系和历史会话工作，而不是只理解粘贴进来的片段。
- **持续执行**：任务由本地服务承载；刷新页面、切换会话或新建会话不会打断其他正在运行的任务。
- **可见且可控**：文件修改、命令结果、结构化问卷和最终回答都保留在会话中，用户可以随时停止、确认或继续调整。

## 核心能力

| 领域 | 当前能力 |
|---|---|
| 项目理解 | 文件树、全文搜索、跨文件关联、项目记忆、长对话上下文压缩 |
| 文件操作 | 读取、创建、编辑、目录管理、备份与项目外路径处理 |
| 命令执行 | PowerShell、Git、Python、Node 等本地命令，带超时与输出回传 |
| Agent 循环 | 多轮“分析 → 工具 → 验证 → 回答”，单任务最多 200 轮工具交互 |
| 后台任务 | 服务端运行任务、SSE 流式输出、刷新续接、多会话并行与独立停止 |
| 文件预览 | 图片、Markdown、PDF、CSV、TSV 以及常见文本和代码文件 |
| 图片输入 | 粘贴、拖拽、路径引用，以及工具读取失败后的视觉模型回退 |
| 结构化交互 | 单选、多选、补充输入、风险确认等任务内问卷 |
| 会话系统 | JSONL 持久化、分支会话、层级索引、异常恢复和历史导出 |
| Skills | Markdown 技能、渐进式说明加载、资源读取及内置办公/设计工具包 |
| 通知 | 断网重试、任务完成、待确认和问卷通知 |
| 界面 | 中英双语、浅色/深色/跟随系统主题、托盘常驻和响应式布局 |

## 工作方式

```text
浏览器界面
    │  会话、SSE、问卷、文件预览
    ▼
本地 Python 服务（127.0.0.1:3010）
    ├── 模型任务运行时与会话持久化
    ├── 文件 / 搜索 / 命令 / Git 工具
    └── OpenAI 兼容代理
              │
              ▼
       New API 或其他兼容网关
```

前端负责展示与交互，本地服务负责模型请求、任务状态、会话数据和工具执行。模型 API Key 只用于请求，不写入持久化的任务运行状态。

服务端现已具备独立的持久化只读 AgentRun：选择“只读分析”权限后，一次任务会由服务端连续完成模型请求与 `list_files`、`read_file`、`search_files`、`glob_files` 四个项目读取工具调用；遇到无法从项目中确认的关键决策时，服务端会持久化 `request_user_input`、暂停任务，并在浏览器提交答案后继续原运行。AgentRun 协议也已支持 `web_fetch`、`use_skill`、`read_skill_resource` 和 `run_command` 的服务端持久执行，供后续计划/接受编辑档位切换所有权；命令在接受编辑档位先持久等待授权，运行中保存有限输出并支持取消，服务重启后会报告结果未知且不自动重放。浏览器只负责持久事件、子模型 SSE 和交互界面投影。页面关闭后任务仍可恢复，重新打开时会按 `agentRunId + 事件游标` 续接；服务重启后则等待前端重新注入内存态凭据。服务端也已建立编辑提案、持久授权、冲突检测与幂等应用协议，前端能够将授权状态恢复为 diff 审查卡片并继续同一运行。计划、接受编辑和自动模式目前仍使用原浏览器 Agent 循环，因为直接写入/删除、记忆保存与子任务尚未完成迁移；工具覆盖完成前不会通过缩减能力提前切换所有权。详见[服务端 Agent 循环迁移计划](docs/SERVER_AGENT_LOOP_PLAN.md)。

## 快速开始

### Windows 单文件版

1. 从 [GitHub Releases](https://github.com/fhy-A/Code/releases/latest) 下载 `Code-v0.5.4.exe`。
2. 双击运行。Code 会常驻系统托盘，并打开 `http://127.0.0.1:3010/`。
3. 在设置中填写模型网关地址和 API Key，刷新模型列表。
4. 选择一个项目目录，在输入框中直接描述任务。

> v0.5.4 是首次使用 Code 名称发布的版本。旧版测试用户请退出 Agent Lite 后重新下载；首次运行会迁移原有用户数据与浏览器设置。

### 从源码运行

环境要求：Windows、Python 3.12+；托盘功能依赖 `pystray` 和 `Pillow`。

```powershell
git clone https://github.com/fhy-A/Code.git
Set-Location Code

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install pystray pillow pytest

python server.py
```

也可以直接运行 `启动Code.bat`。源码模式默认把运行数据保存在仓库的 `data/` 中；正式 EXE 使用用户目录下的 `.code/`。

## 模型与项目配置

首次启动后打开设置：

1. **Base URL**：填写 New API 或其他 OpenAI 兼容网关地址；本地开发默认值为 `http://localhost:3000`。
2. **API Keys**：可以添加多枚 Key，并为每枚 Key 关联可用模型。
3. **项目目录**：选择 Code 可以工作的项目根目录。
4. **模型与推理强度**：在输入区选择本次任务使用的模型和参数。

可用环境变量：

| 变量 | 作用 | 默认值 |
|---|---|---|
| `CODE_PORT` | 本地 Web 服务端口 | `3010` |
| `CODE_DATA_DIR` | 源码模式的数据目录 | `<项目>/data` |
| `NEW_API_BASE_URL` | 服务端默认模型网关 | `http://localhost:3000` |

## 数据与隐私

正式 EXE 的用户数据位于 `%USERPROFILE%\.code\`：

```text
.code/
├── config.json          # 项目目录等本地配置
├── sessions/            # 会话元数据、JSONL 消息与运行检查点
├── agent-runs/          # 服务端多轮 AgentRun 状态、事件与工具检查点
├── attachments/         # 会话附件
├── file-backups/        # 文件修改备份
├── memory/              # 项目记忆
├── skills/              # 用户与内置技能
├── update.log           # 自动更新日志（如有）
└── crash.log            # 启动异常记录（如有）
```

- Web 服务只监听 `127.0.0.1`，默认不向局域网暴露。
- 项目文件和会话保存在本机；发送给模型的上下文仍会经过你配置的 API 网关及其上游模型服务。
- Code 拥有真实文件和命令执行能力，请只选择可信项目并检查重要改动；关键项目建议同时使用 Git。

## 会话与后台任务

每个模型任务都拥有独立的运行 ID、消息队列、停止信号和恢复检查点。页面刷新后会重新连接原任务的 SSE 事件流；切换或新建会话只改变前台视图，不会取消后台任务。

会话正文采用 JSONL 持久化，元数据与消息分开保存。历史 JSON 会话可以迁移，长会话则通过上下文压缩减少重复 Token，同时保留必要任务背景与近期交互。

## 项目结构

```text
Code/
├── server.py                # HTTP 服务、模型代理、任务运行时和本地工具
├── launcher.py              # EXE 启动、托盘、数据目录与浏览器接管
├── index.html               # 应用结构
├── app.js                   # 前端主流程与状态投影
├── agent-runtime.js         # 浏览器侧任务运行时桥接
├── styles.css               # 主题与响应式样式
├── src/                     # 已拆分的前端核心与服务模块
├── data/skills/             # 随程序分发的 Skills
├── assets/                  # Code 品牌与界面资产
├── tests/                   # 自动化测试与测试夹具
├── docs/                    # 使用、迁移、架构计划与版本说明
├── build_exe.py             # PyInstaller 单文件构建入口
├── VERSION                  # 当前版本号
├── CHANGELOG.md             # 已完成开发记录
└── TODO.md                  # 尚未完成的路线清单
```

## 开发与验证

```powershell
# 全量测试
python -m pytest tests -q

# JavaScript 语法检查
node --check app.js
node --check agent-runtime.js

# Python 编译检查
python -m py_compile server.py launcher.py build_exe.py

# 构建 Windows 单文件程序
python build_exe.py
```

构建产物位于 `dist/Code-v<version>.exe`。发布前应同时核对：

- `VERSION`、`file_version_info.txt` 和 README 版本号一致；
- 全量测试与语法检查通过；
- EXE 的 Windows 版本元数据、文件名和内置版本一致；
- SHA-256 已写入对应的 `docs/releases/` 版本说明；
- Git 标签和 GitHub Release 使用同一版本号。

## 文档与路线

- [使用指南](docs/GUIDE.md)
- [v0.5.4 发布说明](docs/releases/v0.5.4.md)
- [会话 JSONL 迁移说明](docs/session-jsonl-migration.md)
- [服务端 Agent 循环迁移计划](docs/SERVER_AGENT_LOOP_PLAN.md)
- [前端模块拆分计划](docs/APP_JS_SPLIT_PLAN.md)
- [开发日志](CHANGELOG.md)
- [待办与路线](TODO.md)

## 当前边界

- 正式打包和托盘流程目前仅支持 Windows。
- Code 依赖外部 OpenAI 兼容模型网关，本仓库不提供模型服务或 API 额度。
- Agent 循环仍由本地服务和浏览器共同完成；让任务在浏览器完全关闭后持续运行是后续路线。
- 当前前端仍以原生 JavaScript 为主，`app.js` 的进一步模块化正在进行。

## 许可证

本项目采用 [MIT License](docs/LICENSE)。
