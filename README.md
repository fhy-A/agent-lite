<p align="center">
  <img src="agent-lite-icon.ico" width="80" alt="Agent Lite" />
</p>

<h1 align="center">Agent Lite</h1>
<p align="center">轻量级本地 AI 编程助手 · 浏览器即界面 · API 中转站驱动</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.5.3-blue" />
  <img src="https://img.shields.io/badge/python-3.12+-green" />
  <img src="https://img.shields.io/badge/tests-412%20passed-brightgreen" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" />
</p>

---

## 这是什么

Agent Lite 是一个**运行在你本机的 AI 编程助手**。打开浏览器就能用，拥有完整的文件读写、命令执行、Git 操作能力。通过 New API 聚合网关接入各类大模型。

**核心理念**：你只需要一个浏览器。不需要安装 IDE 插件，不需要终端，不需要记住命令行。用自然语言描述需求，Agent Lite 帮你完成。

## 快速开始

### 方式一：直接运行

```bash
pip install pystray pillow
python server.py
# 浏览器打开 http://127.0.0.1:3010
```

### 方式二：下载 EXE（Windows）

从 [Releases](https://github.com/fhy-A/agent-lite/releases) 下载 `AgentLite-v0.5.3.exe`，双击运行，托盘图标常驻。

## 功能

| 分类 | 能力 |
|------|------|
| **模型** | 通过 New API 接入 OpenAI / Anthropic / DeepSeek 等，支持多 Key 切换 |
| **文件** | 项目文件树浏览、读写编辑、跨项目路径自动降级 |
| **命令** | 白名单安全策略，支持 PowerShell / Git / Python / Node 等 |
| **办公文档** | Word / Excel / PPT / PDF 的读取与生成 |
| **图片** | 粘贴 / 拖拽 / @路径 三种方式上传，支持视觉模型识图 |
| **会话分支** | 从任意位置创建分支探索替代路径，树形分支面板 |
| **子 Agent** | 后台并行委派任务，自动合并结果 |
| **上下文压缩** | 超过 95% 自动压缩历史消息，长对话不丢上下文 |
| **Skill 系统** | Markdown + frontmatter 自定义技能，内置 Office / Design 等 |
| **记忆系统** | 跨会话持久记忆，自动索引与召回 |
| **系统托盘** | 最小化到托盘，后台静默运行 |
| **中英双语** | 全界面 i18n，模型自动匹配用户语言 |

## 截图

> 待补充

## 技术栈

```
浏览器 Web UI  ←→  Python HTTP Server  ←→  New API  ←→  LLM
                       ↓
                 本地工具层（FS / Shell / Git）
```

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12, http.server + ThreadingHTTPServer |
| 前端 | Vanilla JS (ES6), HTML5, CSS3 |
| 打包 | PyInstaller --onefile (≈40MB) |
| 托盘 | pystray + PIL |
| 测试 | pytest, 412 tests, 20s 全量 |

## 配置

首次启动后在 **Settings → Models** 中配置：

1. **Base URL** — New API 网关地址（默认 `http://localhost:3000`）
2. **API Keys** — 一行一个，支持 `名称:sk-xxx` 格式命名
3. 点击 **Refresh Models** 拉取可用模型列表
4. 在输入框上方选择模型即可开始对话

## 开发

```bash
# 运行测试
python -m pytest tests/ -q

# 构建 EXE
python build_exe.py
```

## License

MIT

---

<p align="center">🤖 Built with <a href="https://claude.com/claude-code">Claude Code</a></p>
