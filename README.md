# Agent Lite

本地 Web 编程 Agent。前端（app.js + index.html + styles.css）负责 AI 智能和交互，后端（server.py）负责文件系统操作和 API 代理。

## 核心能力

### Agent 循环
- 原生 Tool Calling：list_files / read_file / search_files / glob_files / propose_edit / write_file / delete_file / run_command / web_fetch / task / use_skill
- 最多 200 轮工具调用，自动上下文压缩（超 80% 触发）
- 多 Key 自动回退：按顺序尝试，Key 级别独立重试
- 推理强度控制：支持 Claude extended thinking / OpenAI reasoning_effort / Gemini thinkingLevel

### 用户体验
- 流式 SSE 输出，思考过程实时展示（流式时自动展开，完成后折叠）
- 消息队列：任务执行中按 Enter 排队，完成后一次性发送所有排队消息
- propose_edit 权限确认：生成 diff → 用户审核 → 确认写入 + 自动备份
- 权限通知：切走页面时标题闪烁 🔔 + 桌面通知
- 模型选择器药丸下拉（按 provider 分组）、推理强度选择器、权限级选择器

### 文件与编辑
- 文件树浏览 + 筛选 + @ 引用
- 预览区：代码高亮、图片预览、自动刷新、行号可点击复制
- 文件写入自动备份到 `data/file-backups/`

### 图片多模态
- 粘贴 (Ctrl+V) 或拖拽图片到输入框，自动压缩后 base64 编码
- 支持 Claude / GPT / Gemini 等多模态模型

### Skill 系统
- 斜杠命令 `/skillname` 显式激活，`/help` 列出所有
- 三级关键词自动匹配（keywords → name → description）
- Skills 管理面板：新建/编辑/启用/禁用

### 设置
- 统一设置弹窗：Models / Memory / Skills / System Prompt / Theme / Language
- API Key 管理：多 Key、命名、拖拽排序、开关、批量导入
- Memory 管理：新建/编辑、删除确认
- i18n 框架：中英文切换

## 启动方式

双击 `server-launcher.vbs`（无窗口），或在项目目录运行：

```powershell
python server.py
```

访问 `http://127.0.0.1:3010/`

默认读取 New API 网关 `http://localhost:3000`，可通过环境变量 `NEW_API_BASE_URL` 修改。

## 架构

```
浏览器 (app.js + index.html + styles.css)
    ↕ HTTP (localhost:3010)
Python Server (server.py)
    ↕ HTTP 代理
New API 网关 → 模型
```

- **app.js** (~9900行)：全部 AI 智能 — Agent 循环、消息构建、SSE 解析、工具调度、UI 渲染
- **server.py** (~2200行)：纯 HTTP 路由 + 文件系统 + 透明代理 + 安全沙箱
- **index.html**：DOM 骨架
- **styles.css**：CSS 变量驱动的亮/暗主题

## 数据存储

所有数据保存在 `data/` 目录下，与 exe 分离：
- `data/sessions/` — 会话 JSON
- `data/memory/` — Memory 文件
- `data/skills/` — Skill 定义
- `data/file-backups/` — 文件修改备份
- `data/config.json` — 项目配置

环境变量 `AGENT_LITE_DATA_DIR` 可自定义数据目录。

## 安全边界

- 命令白名单 + 危险模式拦截（`rm`、`del`、管道、重定向等）
- 运行时代码执行拦截（`python -c`、`node -e` 等）
- SSRF 防护：web_fetch 拦截私有/回环/保留 IP
- 路径沙箱：文件操作限制在项目根目录内
- propose_edit 生成 diff，用户确认后才写入，不自动修改文件
