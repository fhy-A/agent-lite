const state = {

  sessionId: null,

  sessions: [],

  messages: [],

  mode: "build",

  permissionProfile: localStorage.getItem("agent-lite-permission-profile") || "accept",

  currentDir: "",

  previewContent: "",

  previewPath: "",

  previewWidth: Number(localStorage.getItem("agent-lite-preview-width") || 420),

  sidebarSessionHeight: Number(localStorage.getItem("agent-lite-session-height") || 0),

  sidebarWidth: Number(localStorage.getItem("agent-lite-sidebar-width") || 264),

  lastUsage: null,

  responseUsage: null,

  abortController: null,

  isStreaming: false,

  pendingEdits: {},

  confirmingEditId: null,

  renamingSessionId: null,

  projectContext: null,

  memoryContext: null,

  skills: [],

  explicitSkill: null,

  disabledSkills: new Set(JSON.parse(localStorage.getItem("agent-lite-disabled-skills") || "[]")),

  attachedImages: [],

  responseStartTime: null,
  messageQueue: [],

  lang: localStorage.getItem("agent-lite-lang") || "zh",

  modelKeyMap: {},

  stats: {

    input: 0,

    output: 0,

    cache: 0,

  },

};



const els = {

  shell: document.querySelector(".pi-shell"),

  workbench: document.querySelector(".workbench"),

  chatPane: document.querySelector(".chat-pane"),

  apiKey: document.getElementById("apiKey"),

  baseUrl: document.getElementById("baseUrl"),

  rememberKey: document.getElementById("rememberKey"),

  modelPillBtn: document.getElementById("modelPillBtn"),

  modelPillLabel: document.getElementById("modelPillLabel"),

  modelPillDropdown: document.getElementById("modelPillDropdown"),

  modelPillWrap: document.getElementById("modelPillWrap"),

  modelListBox: document.getElementById("modelListBox"),

  attachFile: document.getElementById("attachFile"),

  filePicker: document.getElementById("filePicker"),

  refreshModelsBtn: document.getElementById("refreshModelsBtn"),

  temperature: document.getElementById("temperature"),

  maxTokens: document.getElementById("maxTokens"),

  thinkingPillBtn: document.getElementById("thinkingPillBtn"),

  thinkingPillLabel: document.getElementById("thinkingPillLabel"),

  thinkingPillDropdown: document.getElementById("thinkingPillDropdown"),

  thinkingPillWrap: document.getElementById("thinkingPillWrap"),

  toolPreset: document.getElementById("toolPreset"),

  permissionProfile: document.getElementById("permissionProfile"),

  messages: document.getElementById("messages"),

  prompt: document.getElementById("prompt"),

  chatForm: document.getElementById("chatForm"),

  sendBtn: document.getElementById("sendBtn"),

  stopBtn: document.getElementById("stopBtn"),

  newChat: document.getElementById("newChat"),

  exportChat: document.getElementById("exportChat"),

  sessionList: document.getElementById("sessionList"),

  sidebarSplitter: document.getElementById("sidebarSplitter"),

  sidebarResizer: document.getElementById("sidebarResizer"),

  piShell: document.getElementById("piShell"),

  sessionTitle: document.getElementById("sessionTitle"),

  projectRoot: document.getElementById("projectRoot"),

  projectRootShort: document.getElementById("projectRootShort"),

  cwdPathText: document.getElementById("cwdPathText"),

  cwdInputRow: document.getElementById("cwdInputRow"),

  saveProjectRoot: document.getElementById("saveProjectRoot"),

  newFolderBtn: document.getElementById("newFolderBtn"),

  refreshFiles: document.getElementById("refreshFiles"),

  goUp: document.getElementById("goUp"),

  filePathBar: document.getElementById("filePathBar"),

  fileTree: document.getElementById("fileTree"),

  fileSearch: document.getElementById("fileSearch"),

  previewPane: document.getElementById("previewPane"),

  previewResizer: document.getElementById("previewResizer"),

  filePreview: document.getElementById("filePreview"),

  previewTitle: document.getElementById("previewTitle"),

  previewMeta: document.getElementById("previewMeta"),

  previewLanguage: document.getElementById("previewLanguage"),

  refreshPreview: document.getElementById("refreshPreview"),

  copyPreview: document.getElementById("copyPreview"),

  closePreview: document.getElementById("closePreview"),

  toggleSidebar: document.getElementById("toggleSidebar"),
  sidebarPeekZone: document.getElementById("sidebarPeekZone"),

  togglePreview: document.getElementById("togglePreview"),

  themeToggle: document.getElementById("themeToggle"),

  toolLogToggle: document.getElementById("toolLogToggle"),

  statsPanel: document.getElementById("statsPanel"),

  toolLogPanel: document.getElementById("toolLogPanel"),

  toolLogSummary: document.getElementById("toolLogSummary"),

  toolLogList: document.getElementById("toolLogList"),

  systemPromptText: document.getElementById("systemPromptText"),

  resetSystemPrompt: document.getElementById("resetSystemPrompt"),

  modePromptPreview: document.getElementById("modePromptPreview"),

  settingsMenuBtn: document.getElementById("settingsMenuBtn"),

  settingsModal: document.getElementById("settingsModal"),

  memoryModal: document.getElementById("memoryModal"),

  memoryList: document.getElementById("memoryList"),

  memoryName: document.getElementById("memoryName"),

  memoryDesc: document.getElementById("memoryDesc"),

  memoryBody: document.getElementById("memoryBody"),

  memoryForm: document.getElementById("memoryForm"),

  closeMemory: document.getElementById("closeMemory"),

  cancelMemory: document.getElementById("cancelMemory"),

  saveMemory: document.getElementById("saveMemory"),

  closeSettings: document.getElementById("closeSettings"),

  confirmEditModal: document.getElementById("confirmEditModal"),

  confirmEditPath: document.getElementById("confirmEditPath"),

  cancelApplyEdit: document.getElementById("cancelApplyEdit"),

  cancelApplyEditX: document.getElementById("cancelApplyEditX"),

  confirmApplyEdit: document.getElementById("confirmApplyEdit"),

  permPillBtn: document.getElementById("permPillBtn"),

  permPillLabel: document.getElementById("permPillLabel"),

  permPillDropdown: document.getElementById("permPillDropdown"),

  permPillWrap: document.getElementById("permPillWrap"),

  statInput: document.getElementById("statInput"),

  usageStrip: document.getElementById("usageStrip"),

  statOutput: document.getElementById("statOutput"),

  statCache: document.getElementById("statCache"),

  statContext: document.getElementById("statContext"),

  sessionFile: document.getElementById("sessionFile"),

  sessionIdLabel: document.getElementById("sessionIdLabel"),

  copySessionPath: document.getElementById("copySessionPath"),

  copySessionId: document.getElementById("copySessionId"),

  msgUser: document.getElementById("msgUser"),

  msgAssistant: document.getElementById("msgAssistant"),

  msgToolCalls: document.getElementById("msgToolCalls"),

  msgToolResults: document.getElementById("msgToolResults"),

  msgTotal: document.getElementById("msgTotal"),

  tokenInput: document.getElementById("tokenInput"),

  tokenOutput: document.getElementById("tokenOutput"),

  tokenCache: document.getElementById("tokenCache"),

  tokenTotal: document.getElementById("tokenTotal"),

  tokenContext: document.getElementById("tokenContext"),

  liveTimer: document.getElementById("liveTimer"),

};



const MAX_TOOL_ROUNDS = 200;



const toolPolicy = {

  plan: new Set(["list_files", "read_file", "search_files", "glob_files", "web_fetch", "propose_edit", "use_skill"]),

  accept: new Set(["list_files", "read_file", "search_files", "glob_files", "web_fetch", "propose_edit", "run_command", "task", "use_skill", "write_file", "delete_file"]),

  bypass: new Set(["list_files", "read_file", "search_files", "glob_files", "web_fetch", "propose_edit", "run_command", "task", "use_skill", "write_file", "delete_file"]),

};



const nativeTools = [

  {

    type: "function",

    function: {

      name: "list_files",

      description: "列出项目目录中的文件和文件夹，用于了解目录结构。默认只返回一层，可设置 maxDepth 做浅层递归。",

      parameters: {

        type: "object",

        properties: {

          path: {

            type: "string",

            description: "可选的相对目录，留空表示项目根目录。",

          },

          maxDepth: {

            type: "integer",

            description: "递归层数，建议 1-3，默认 1。",

          },

        },

        required: [],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "read_file",

      description: "读取当前项目目录内或 attachments/ 下的文本文件内容。支持按行读取，避免一次塞入过长文件。",

      parameters: {

        type: "object",

        properties: {

          path: {

            type: "string",

            description: "相对项目根目录的文件路径，例如 agent-lite/app.js",

          },

          startLine: {

            type: "integer",

            description: "可选，起始行号，从 1 开始。",

          },

          endLine: {

            type: "integer",

            description: "可选，结束行号，包含该行。",

          },

        },

        required: ["path"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "search_files",

      description: "按文件名和文件内容搜索项目内文件，支持关键词、正则、文件类型过滤和上下文行。默认跳过 node_modules、.git、构建产物等目录。",

      parameters: {

        type: "object",

        properties: {

          query: {

            type: "string",

            description: "搜索关键词（子串匹配）或正则表达式（当 regex=true 时）。",

          },

          path: {

            type: "string",

            description: "可选的相对搜索目录，留空表示项目根目录。",

          },

          regex: {

            type: "boolean",

            description: "是否启用正则匹配，默认 false。",

          },

          type: {

            type: "string",

            description: "文件类型过滤，如 \"js,ts,py\" 只搜索这些扩展名的文件。",

          },

          glob: {

            type: "string",

            description: "文件名 glob 模式，如 \"**/*.ts\" 只搜索匹配该模式的文件。",

          },

          contextAround: {

            type: "integer",

            description: "每个匹配行前后显示的行数，默认 0。",

          },

        },

        required: ["query"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "glob_files",

      description: "按 glob 模式匹配项目中的文件名和路径，用于快速查找符合命名规范的文件。默认跳过依赖、构建产物等目录。",

      parameters: {

        type: "object",

        properties: {

          pattern: {

            type: "string",

            description: "glob 模式，如 \"**/*.py\"、\"*.js\"、\"src/**/*.tsx\"。",

          },

          path: {

            type: "string",

            description: "可选的搜索起始目录，留空表示项目根目录。",

          },

        },

        required: ["pattern"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "propose_edit",

      description: "生成文件修改方案和 unified diff。该工具不会直接写入文件，必须等待用户点击应用修改。",

      parameters: {

        type: "object",

        properties: {

          path: {

            type: "string",

            description: "相对项目根目录的文件路径。",

          },

          oldText: {

            type: "string",

            description: "需要替换的原文片段。局部修改时使用。",

          },

          newText: {

            type: "string",

            description: "替换后的新片段。局部修改时使用。",

          },

          newContent: {

            type: "string",

            description: "完整的新文件内容。新建文件或整文件重写时使用。",

          },

        },

        required: ["path"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "run_command",

      description: "运行低风险命令，用于查看、测试、构建、git 查询或 docker compose 查询。",

      parameters: {

        type: "object",

        properties: {

          command: {

            type: "string",

            description: "要运行的命令，例如 dir、git status、npm test。",

          },

        },

        required: ["command"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "task",

      description: "启动一个只读子 Agent 来并行处理搜索、分析、代码审查等独立子任务。子 Agent 有自己的工具（读文件、搜索、glob），但不能写文件或运行命令。用于将大任务拆分成并行的独立分析步骤。",

      parameters: {

        type: "object",

        properties: {

          prompt: {

            type: "string",

            description: "子任务的详细描述，包括要搜索什么、分析什么、返回什么格式的结果。",

          },

        },

        required: ["prompt"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "use_skill",

      description: "加载一个已安装的 Skill 来获取专业指导。传入 name 参数指定 skill 名称（如 code-review、python-testing）。加载后你会收到该领域的详细工作规范。如果 skill 不存在，返回错误并列出所有可用 skill。",

      parameters: {

        type: "object",

        properties: {

          name: { type: "string", description: "Skill 名称，如 python-testing。" },

        },

        required: ["name"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "write_file",

      description: "创建新文件或覆盖已有文件。会自动备份原文件到 data/file-backups/。需要用户确认后才会执行。",

      parameters: {

        type: "object",

        properties: {

          path: {

            type: "string",

            description: "相对项目根目录的文件路径。",

          },

          content: {

            type: "string",

            description: "文件的完整内容。",

          },

        },

        required: ["path", "content"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "delete_file",

      description: "删除项目内的文件或空目录。文件会自动备份到 data/file-backups/。需要用户确认后才会执行。",

      parameters: {

        type: "object",

        properties: {

          path: {

            type: "string",

            description: "相对项目根目录的文件或空目录路径。",

          },

        },

        required: ["path"],

        additionalProperties: false,

      },

    },

  },

  {

    type: "function",

    function: {

      name: "web_fetch",

      description: "抓取网页或 API 内容。用于查阅在线文档、API 参考、错误码说明等。返回纯文本（HTML 会自动剥离标签）。",

      parameters: {

        type: "object",

        properties: {

          url: {

            type: "string",

            description: "要抓取的 URL，如 https://docs.python.org/3/library/re.html。",

          },

        },

        required: ["url"],

        additionalProperties: false,

      },

    },

  },

];



const defaultSystemPrompt = `

你是 Agent Lite，一个运行在本地 Web 服务中的 AI 编程助手。你的目标是高效地帮助用户阅读、搜索、修改和验证代码。



运行环境：Windows + PowerShell。命令必须用 Windows 语法（dir、findstr、Get-ChildItem，不是 ls、grep）。



## 核心原则



### 1. 编码前思考

- 不确定时提问，不能猜测。指令有歧义时列出选项让用户选择，而非自行决定。

- 发现需求不合理或有更简单方案时，主动说出来。

- 宁可多问一句，不要跑偏后返工。



### 2. 简洁优先

- 用最少代码解决问题，不加用户未要求的功能。

- 不为一次性操作创建完整流程。如果写了 200 行发现 50 行能搞定，立即重写。

- 检验标准：一个有经验的人看了会觉得过度设计吗？



### 3. 精准修改

- 只改必须改的，不碰无关代码，不主动"顺手优化"。

- 匹配项目现有风格和格式，哪怕你更习惯另一种写法。

- propose_edit 的 oldText 尽可能短但仍保证在文件中唯一。同一文件多处修改合并为一次调用。



### 4. 目标驱动执行

- 接受可验证的成功标准，不只是操作指令。

- 自主循环：未达标则继续改，达标则停止，不需要用户反复确认。



## 工具使用规范



- 必须通过原生 tool/function calling 调用工具，不要只说"准备调用工具"。

- search_files 是首选搜索工具（正则 + 类型过滤 + 上下文行），优于 run_command findstr。

- read_file 用 startLine/endLine 控制范围，避免全文件读取。

- 写文件走 propose_edit 生成 diff，用户点击应用后才写入。

- run_command 仅用于查看、测试、构建、git 查询等低风险命令。

- 不清楚结构时先用 glob_files 或 list_files 定位文件。

- task 子 Agent 用于并行处理独立的搜索/分析子任务。



## 可用工具

list_files | read_file | search_files | glob_files | propose_edit | write_file | delete_file | run_command | web_fetch | task



不支持原生工具调用时，退回到文本协议：

\`\`\`agent-tool

{"action":"read_file","path":"agent-lite/app.js"}

\`\`\`

`.trim();





const permissionInstructions = {

  plan: "权限策略：计划模式。可读取、搜索、生成修改方案，但不能运行命令或直接写入文件。",

  accept: "权限策略：接受编辑模式。可执行命令和写入文件，但操作前需用户确认。",

  bypass: "权限策略：自动模式。所有操作自动执行，无需确认。",

};



// ── Key config storage ──



function loadKeyConfig() {

  try { return JSON.parse(localStorage.getItem("agent-lite-key-config") || "[]"); } catch { return []; }

}

function saveKeyConfig(cfg) {

  localStorage.setItem("agent-lite-key-config", JSON.stringify(cfg));

}



function parseKeyLines(raw) {

  if (!raw) return [];

  const cfg = loadKeyConfig();

  const lines = raw.split("\n").map((l) => l.trim());

  if (lines.length === 1 && !lines[0]) return [{ name: "", key: "", enabled: true }];

  return lines.map((line) => {

    const idx = line.indexOf(":");

    const name = idx > 0 ? line.slice(0, idx).trim() : "";

    const key = idx > 0 ? line.slice(idx + 1).trim() : line.trim();

    const existing = cfg.find((c) => c.key === key);

    return { name, key, enabled: existing ? existing.enabled !== false : true };

  });

}



function serializeKeys(entries) {

  return entries.map((e) => {

    const k = (e.key || "").trim();

    const n = (e.name || "").trim();

    return n ? `${n}: ${k}` : k;

  }).filter((l) => l).join("\n");

}



function maskKey(k) {

  if (!k) return "";

  if (k.length <= 13) return k[0] + "***" + k[k.length - 1];

  return k.slice(0, 7) + "***" + k.slice(-3);

}



function renderKeyEditor(raw, newRow = false) {

  const entries = parseKeyLines(raw);

  if (!entries.length) entries.push({ name: "", key: "", enabled: true });

  const rows = entries.map((e, i) => {

    const isNew = newRow && i === entries.length - 1;

    const actions = isNew ? keyConfirmActions(i) : keyNormalActions(e, i);

    return `

    <div class="key-row ${e.enabled === false && !isNew ? "disabled" : ""}" data-idx="${i}">

      <span class="key-drag-handle" title="拖拽排序" draggable="true">⠿</span>

      <input class="key-name-input" placeholder="名称" value="${escapeHtml(e.name)}" data-idx="${i}" />

      <div class="key-value-wrap">

        <input class="key-value-input" type="password" value="${escapeHtml(e.key)}" data-idx="${i}" />

      </div>

      ${actions}

    </div>`;}).join("");

  return rows;

}



function keyNormalActions(e, i) {

  return `<div class="key-actions">

    <button class="key-act-btn key-eye" type="button" title="显示/隐藏" data-idx="${i}">${eyeIcon()}</button>

    <label class="toggle-switch key-enable" title="${e.enabled !== false ? '已启用' : '已禁用'}">

      <input type="checkbox" ${e.enabled !== false ? "checked" : ""} data-idx="${i}" />

      <span class="toggle-track"><span class="toggle-thumb"></span></span>

    </label>

    <button class="key-act-btn key-trash" type="button" title="删除" data-idx="${i}">${trashIcon()}</button>

  </div>`;

}



function keyConfirmActions(i) {

  return `<div class="key-actions">

    <button class="key-act-btn key-confirm" type="button" title="确认" data-idx="${i}">

      <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 7l2.5 2.5L11 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>

    </button>

    <button class="key-act-btn key-cancel" type="button" title="取消" data-idx="${i}">

      <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 3l8 8M11 3L3 11" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>

    </button>

  </div>`;

}



function eyeIcon() { return `<svg width="14" height="14" viewBox="0 0 1024 1024" fill="currentColor"><path d="M942.2 486.2C847.4 286.5 704.1 186 512 186c-192.2 0-335.4 100.5-430.2 300.3-7.7 16.2-7.7 35.2 0 51.5C176.6 737.5 319.9 838 512 838c192.2 0 335.4-100.5 430.2-300.3 7.7-16.2 7.7-35 0-51.5zM512 766c-161.3 0-279.4-81.8-362.7-254C232.6 339.8 350.7 258 512 258c161.3 0 279.4 81.8 362.7 254C791.5 684.2 673.4 766 512 766z"/><path d="M508 336c-97.2 0-176 78.8-176 176s78.8 176 176 176 176-78.8 176-176-78.8-176-176-176z m0 288c-61.9 0-112-50.1-112-112s50.1-112 112-112 112 50.1 112 112-50.1 112-112 112z"/></svg>`; }

function eyeOffIcon() { return `<svg width="14" height="14" viewBox="0 0 1024 1024" fill="currentColor"><path d="M913.86 396.86c11.76-14.71 9.36-36.18-5.33-47.94-14.72-11.77-36.14-9.34-47.97 5.33-1.23 1.57-128.74 157.74-348.56 157.74-218.58 0-347.36-156.22-348.56-157.74-11.79-14.67-33.21-17.12-47.97-5.33-14.69 11.76-17.09 33.23-5.33 47.94 2.11 2.64 21.66 26.32 56.68 55.72l-59.81 72.89 52.73 43.27 61.98-75.53c25.71 16.71 55.66 33.14 89.71 47.2l-34.34 95.02 64.16 23.18 34.82-96.36c31.36 8.41 65.38 14.16 101.82 16.5l0 103.8 68.22 0 0-103.83c37.15-2.39 71.75-8.36 103.61-17.04l35.19 96.27 64.06-23.44-34.65-94.79c32.3-13.47 60.72-29.1 85.46-45l61.61 76.04 53-42.95-59.44-73.37C891.43 424.18 911.7 399.56 913.86 396.86z"/></svg>`; }

function trashIcon() { return `<svg width="14" height="14" viewBox="0 0 1024 1024"><path d="M799.2 874.4c0 34.4-28 62.4-62.4 62.4H287.2c-34.4 0-62.4-28-62.4-62.4V212h574.4v662.4zM349.6 100c0-7.2 5.6-12.8 12.8-12.8h300c7.2 0 12.8 5.6 12.8 12.8v37.6H349.6V100z m636.8 37.6H749.6V100c0-48-39.2-87.2-87.2-87.2h-300c-48 0-87.2 39.2-87.2 87.2v37.6H37.6C16.8 137.6 0 154.4 0 175.2s16.8 37.6 37.6 37.6h112v661.6c0 76 61.6 137.6 137.6 137.6h449.6c76 0 137.6-61.6 137.6-137.6V212h112c20.8 0 37.6-16.8 37.6-37.6s-16.8-36.8-37.6-36.8zM512 824c20.8 0 37.6-16.8 37.6-37.6v-400c0-20.8-16.8-37.6-37.6-37.6s-37.6 16.8-37.6 37.6v400c0 20.8 16.8 37.6 37.6 37.6m-175.2 0c20.8 0 37.6-16.8 37.6-37.6v-400c0-20.8-16.8-37.6-37.6-37.6s-37.6 16.8-37.6 37.6v400c.8 20.8 17.6 37.6 37.6 37.6m350.4 0c20.8 0 37.6-16.8 37.6-37.6v-400c0-20.8-16.8-37.6-37.6-37.6s-37.6 16.8-37.6 37.6v400c0 20.8 16.8 37.6 37.6 37.6" fill="currentColor"/></svg>`; }



function collectKeyEntries(container) {

  const rows = container.querySelectorAll(".key-row");

  const entries = [];

  rows.forEach((row) => {

    const name = row.querySelector(".key-name-input")?.value || "";

    const key = row.querySelector(".key-value-input")?.value || "";

    const enabled = row.querySelector(".key-enable input")?.checked !== false;

    if (key.trim()) entries.push({ name: name.trim(), key: key.trim(), enabled });

  });

  return entries;

}



function refreshKeyEditor(container) {

  const entries = collectKeyEntries(container);

  container.innerHTML = renderKeyEditor(serializeKeys(entries));

  bindKeyEditorEvents(container);

}



function bindKeyEditorEvents(container) {

  // Drag-and-drop reorder (handle only)

  let dragSrc = null;

  container.querySelectorAll(".key-drag-handle").forEach((handle) => {

    handle.addEventListener("dragstart", (e) => {

      dragSrc = handle.closest(".key-row");

      dragSrc.classList.add("dragging");

      e.dataTransfer.effectAllowed = "move";

    });

    handle.addEventListener("dragend", () => {

      if (dragSrc) dragSrc.classList.remove("dragging");

      dragSrc = null;

      container.querySelectorAll(".key-row").forEach((r) => r.classList.remove("drag-over"));

    });

  });

  container.querySelectorAll(".key-row").forEach((row) => {

    row.addEventListener("dragover", (e) => {

      e.preventDefault();

      e.dataTransfer.dropEffect = "move";

      row.classList.add("drag-over");

    });

    row.addEventListener("dragleave", () => { row.classList.remove("drag-over"); });

    row.addEventListener("drop", (e) => {

      e.preventDefault();

      row.classList.remove("drag-over");

      if (!dragSrc || dragSrc === row) return;

      const rows = [...container.querySelectorAll(".key-row")];

      const srcIdx = rows.indexOf(dragSrc);

      const dstIdx = rows.indexOf(row);

      if (srcIdx < dstIdx) {

        row.after(dragSrc);

      } else {

        row.before(dragSrc);

      }

      dragSrc.classList.remove("dragging");

      dragSrc = null;

      const entries = collectKeyEntries(container);

      els.apiKey.value = serializeKeys(entries);

      saveKeyConfig(entries);

      saveLocalSettings();

    });

  });



  container.querySelectorAll(".key-name-input, .key-value-input").forEach((inp) => {

    inp.addEventListener("change", () => {

      const entries = collectKeyEntries(container);

      els.apiKey.value = serializeKeys(entries);

      saveKeyConfig(entries);

      saveLocalSettings();

    });

  });

  // Eye toggle: switch password <-> text + icon

  container.querySelectorAll(".key-eye").forEach((btn) => {

    btn.addEventListener("click", () => {

      const row = btn.closest(".key-row");

      const inp = row.querySelector(".key-value-input");

      const showing = inp.type === "text";

      inp.type = showing ? "password" : "text";

      btn.innerHTML = showing ? eyeIcon() : eyeOffIcon();

    });

  });

  // Enable toggle

  container.querySelectorAll(".key-enable input").forEach((cb) => {

    cb.addEventListener("change", () => {

      const entries = collectKeyEntries(container);

      els.apiKey.value = serializeKeys(entries);

      saveKeyConfig(entries);

      saveLocalSettings();

    });

  });

  // Confirm new row

  container.querySelectorAll(".key-confirm").forEach((btn) => {

    btn.addEventListener("click", () => {

      const entries = collectKeyEntries(container);

      els.apiKey.value = serializeKeys(entries);

      saveKeyConfig(entries);

      saveLocalSettings();

      container.innerHTML = renderKeyEditor(els.apiKey.value);

      bindKeyEditorEvents(container);

    });

  });

  // Cancel new row — just remove the DOM row, no save

  container.querySelectorAll(".key-cancel").forEach((btn) => {

    btn.addEventListener("click", () => {

      btn.closest(".key-row").remove();

      const entries = collectKeyEntries(container);

      els.apiKey.value = serializeKeys(entries);

      saveKeyConfig(entries);

    });

  });

  // Delete with inline confirm

  container.querySelectorAll(".key-trash").forEach((btn) => {

    btn.addEventListener("click", () => {

      const row = btn.closest(".key-row");

      const name = row.querySelector(".key-name-input")?.value || "未命名";

      showInlineKeyDeleteConfirm(row, name, () => {

        row.remove();

        const entries = collectKeyEntries(container);

        els.apiKey.value = serializeKeys(entries);

        saveKeyConfig(entries);

        saveLocalSettings();

      });

    });

  });

  // Add row via event delegation on the settings detail

  const detail = document.getElementById("settingsDetail");

  if (detail && !detail._keyDelegationBound) {

    detail._keyDelegationBound = true;

    detail.addEventListener("click", (e) => {

      if (e.target.id === "settingsKeyAddRow" || e.target.closest("#settingsKeyAddRow")) {

        const area = document.getElementById("settingsKeyAddArea");

        area.innerHTML = `

          <textarea id="keyBulkInput" class="key-bulk-input" placeholder="支持添加多个key，一行一个&#10;格式：名称 key（空格分隔）或者直接粘贴key" rows="5"></textarea>

          <div class="key-bulk-actions">

            <button id="keyBulkSave" class="mini-btn" type="button">保存</button>

            <button id="keyBulkCancel" class="mini-btn" type="button">取消</button>

          </div>`;

        const bulkInput = document.getElementById("keyBulkInput");

        const bulkSave = document.getElementById("keyBulkSave");

        bulkInput.addEventListener("input", () => {

          bulkSave.classList.toggle("primary-btn", bulkInput.value.trim().length > 0);

        });

        document.getElementById("keyBulkCancel").addEventListener("click", () => {

          area.innerHTML = `<button id="settingsKeyAddRow" class="key-add-btn" type="button">${t("addKey")}</button>`;

        });

        document.getElementById("keyBulkSave").addEventListener("click", () => {

          const raw = document.getElementById("keyBulkInput").value;

          const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);

          if (lines.length === 0) return;

          const newEntries = lines.map((line) => {

            const m = line.match(/^(.+?)\s+(sk-\S+)/i);

            if (m) return { name: m[1].trim(), key: m[2].trim(), enabled: true };

            return { name: "", key: line, enabled: true };

          });

          const keyList = document.getElementById("settingsKeyList");

          const existing = collectKeyEntries(keyList);

          const merged = [...existing, ...newEntries];

          els.apiKey.value = serializeKeys(merged);

          saveKeyConfig(merged);

          saveLocalSettings();

          keyList.innerHTML = renderKeyEditor(els.apiKey.value);

          bindKeyEditorEvents(keyList);

          area.innerHTML = `<button id="settingsKeyAddRow" class="key-add-btn" type="button">${t("addKey")}</button>`;

        });

      }

    });

  }

}



// ── i18n ──

const LANG = {

  zh: {

    settings: "设置", models: "Models", memory: "Memory", skills: "Skills", system: "System Prompt", theme: "Theme", language: "Language",

    baseUrl: "Base URL", apiKeys: "API Keys", refreshModels: "刷新", availableModels: "可用模型",

    temperature: "温度", maxTokens: "最大输出", show: "显示", hide: "隐藏", save: "保存", cancel: "取消",

    name: "名称", description: "描述", keywords: "关键词", tools: "工具", body: "正文",

    addKey: "+ 添加 Key", confirmDelete: "确认", newMemory: "新建记忆", editing: "编辑中",

    enabled: "已启用", disabled: "已禁用", noMemory: "暂无记忆", noSkills: "暂无 Skill",

    light: "亮", dark: "暗", system: "系统",

    skillPath: "文件路径", skillExplicitOnly: "此 Skill 仅支持显式调用",

  },

  en: {

    settings: "Settings", models: "Models", memory: "Memory", skills: "Skills", system: "System Prompt", theme: "Theme", language: "Language",

    baseUrl: "Base URL", apiKeys: "API Keys", refreshModels: "Refresh", availableModels: "Models",

    temperature: "Temperature", maxTokens: "Max Tokens", show: "Show", hide: "Hide", save: "Save", cancel: "Cancel",

    name: "Name", description: "Description", keywords: "Keywords", tools: "Tools", body: "Body",

    addKey: "+ Add Key", confirmDelete: "Confirm", newMemory: "New Memory", editing: "Editing",

    enabled: "Enabled", disabled: "Disabled", noMemory: "No memories", noSkills: "No skills",

    light: "Light", dark: "Dark", system: "System",

    skillPath: "File Path", skillExplicitOnly: "This skill requires explicit invocation via",

  },

};

function t(key) {

  const lang = (state.lang || "zh") === "zh" ? "zh" : "en";

  return LANG[lang][key] || LANG.zh[key] || key;

}

function setLang(lang) {

  state.lang = lang;

  localStorage.setItem("agent-lite-lang", lang);

}



function showToast(msg, type = "error") {

  const container = document.getElementById("toastContainer");

  const toast = document.createElement("div");

  toast.className = `toast ${type}`;

  toast.textContent = msg;

  container.appendChild(toast);

  setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity .2s"; setTimeout(() => toast.remove(), 200); }, 3000);

}


function showToast(msg, type = "error") {

  const container = document.getElementById("toastContainer");

  const toast = document.createElement("div");

  toast.className = `toast ${type}`;

  toast.textContent = msg;

  container.appendChild(toast);

  setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity .2s"; setTimeout(() => toast.remove(), 200); }, 3000);

}

// ── Permission notification ──

const _originalTitle = document.title;
let _pendingPermNotify = false;

function notifyPermissionNeeded(action, path) {
  if (!document.hidden) return;
  _pendingPermNotify = true;
  const label = action === "propose_edit" ? "修改方案" : "文件写入";
  document.title = `🔔 ${label}待确认 — ${path}`;
  if (!state._titleInterval) {
    state._titleInterval = setInterval(() => {
      if (!_pendingPermNotify) { clearInterval(state._titleInterval); state._titleInterval = null; return; }
      document.title = document.title.startsWith("🔔") ? document.title.replace("🔔", "") : `🔔${document.title}`;
    }, 2000);
  }
  try {
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("Agent 请求确认", { body: `${label}：${path}` });
    }
  } catch (_) {}
}

function clearPermissionNotify() {
  _pendingPermNotify = false;
  document.title = _originalTitle;
  if (state._titleInterval) { clearInterval(state._titleInterval); state._titleInterval = null; }
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && _pendingPermNotify) {
    clearPermissionNotify();
  }
});

function escapeHtml(text = "") {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatSize(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(num >= 10_000_000 ? 1 : 2)}M`;

  if (num >= 1_000) return `${Math.round(num / 100) / 10}k`;

  return String(Math.round(num));

}

function formatCompact(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(num >= 10_000_000 ? 1 : 2)}M`;
  if (num >= 1_000) return `${Math.round(num / 100) / 10}k`;
  return String(num);
}

function formatNumber(num) {
  return (num || 0).toLocaleString();
}



function formatElapsed(ms) {

  if (!ms || ms < 0) return "";

  const s = Math.floor(ms / 1000);

  if (s < 60) return s + "s";

  const m = Math.floor(s / 60);

  const rs = s % 60;

  if (m < 60) return m + "m " + rs + "s";

  const h = Math.floor(m / 60);

  const rm = m % 60;

  return h + "h " + rm + "m " + rs + "s";

}



function getMsgText(msg) {

  const c = (msg || {}).content;

  if (!c) return "";

  if (Array.isArray(c)) return c.find((p) => p.type === "text")?.text || "";

  return String(c);

}



function estimateTokens(text = "") {

  return Math.ceil(String(text).length / 3.2);

}



function authHeaders(model) {

  const key = getBestKey(model);

  return key ? { Authorization: `Bearer ${key}` } : {};

}



function getBestKey(model) {

  const keys = getApiKeys();

  if (model && state.modelKeyMap[model]) return state.modelKeyMap[model];

  return keys[0] || "";

}



function getFallbackKeys(model) {

  const keys = getApiKeys();

  const best = getBestKey(model);

  const fallbacks = keys.filter((k) => k !== best);

  return [best, ...fallbacks];

}



function getApiKeys() {

  const cfg = loadKeyConfig();

  const raw = (els.apiKey.value || "").split("\n").map((k) => k.trim()).filter(Boolean);

  // Parse name:key lines, extract key only. Fallback to config.

  const keys = raw.map((line) => {

    const idx = line.indexOf(":");

    return idx > 0 ? line.slice(idx + 1).trim() : line.trim();

  });

  // Only return enabled keys (from config)

  if (cfg.length > 0) {

    return keys.filter((k) => {

      const entry = cfg.find((c) => c.key === k);

      return !entry || entry.enabled !== false;

    });

  }

  return keys;

}



function getSystemPrompt() {

  const customPrompt = els.systemPromptText.value.trim() || defaultSystemPrompt;

  const permissionProfile = getPermissionProfile();

  const parts = [customPrompt];

  if (state.projectContext?.found) {

    parts.push(`=== 项目上下文（仅本项目，来自 ${state.projectContext.name}） ===\n${state.projectContext.content}`);

  }

  if (state.memoryContext?.found) {

    parts.push(`=== 长期记忆（跨会话保留） ===\n${state.memoryContext.content}`);

  }

  // Inject explicit skill first, then auto-matched

  if (state.explicitSkill) {

    const skill = state.skills.find((s) => s.name === state.explicitSkill);

    if (skill) {

      parts.push(`=== 已激活 Skill: ${skill.name} ===\n${skill.body}`);

    }

  } else {

    const lastUserMsg = [...state.messages].reverse().find((m) => m.role === "user");

    if (lastUserMsg) {

      const skillPrompt = getMatchedSkillPrompts(lastUserMsg.content || "");

      if (skillPrompt) {

        parts.push(`=== 匹配的 Skill（自动加载） ===\n${skillPrompt}`);

      }

    }

  }

  parts.push(

    permissionInstructions[permissionProfile] || permissionInstructions.confirm,

    `Tool preset: ${els.toolPreset.value}`,

    `Allowed tools: ${[...getAllowedToolNames()].join(", ")}`,

  );

  return parts.join("\n\n");

}



async function loadProjectContext() {

  try {

    state.projectContext = await apiJson("/api/project-context");

  } catch {

    state.projectContext = { found: false, path: null, name: null, content: null };

  }

  updateProjectContextIndicator();

}



function updateProjectContextIndicator() {

  const panel = document.getElementById("projectContextInfo");

  if (!panel) return;

  if (state.projectContext?.found) {

    panel.innerHTML = `<span class="ctx-badge ctx-project">📄 项目上下文</span><span class="ctx-hint">${escapeHtml(state.projectContext.name)} · 仅当前项目生效，切换项目目录后自动更换</span>`;

    panel.style.display = "flex";

  } else {

    panel.innerHTML = `<span class="ctx-badge muted">📄 无项目上下文</span><span class="ctx-hint">在项目根目录放置 CLAUDE.md 或 AGENT.md 文件，描述项目结构和约定</span>`;

    panel.style.display = "flex";

  }

}



// ── Skills ──



async function loadSkills() {

  try {

    const data = await apiJson("/api/skills");

    state.skills = data.data || [];

  } catch { state.skills = []; }

}



function getMatchedSkillPrompts(userMessage) {

  if (!userMessage || state.skills.length === 0) return "";

  const text = Array.isArray(userMessage) ? (userMessage.find((c) => c.type === "text")?.text || "") : String(userMessage || "");

  const lower = text.toLowerCase();

  // Skills that should only be triggered explicitly (too large/generic for auto-match)

  const explicitOnly = new Set(["dispatching-parallel-agents", "subagent-driven-development", "executing-plans", "writing-plans"]);

  const active = state.skills.filter((s) => !state.disabledSkills.has(s.name) && !explicitOnly.has(s.name));

  const matched = active.filter((s) => {

    // 1. Check explicit keywords

    const kwList = s.keywords || [];

    if (kwList.some((kw) => kw.length >= 2 && lower.includes(kw.toLowerCase()))) return true;

    // 2. Check skill name

    const name = (s.name || "").toLowerCase();

    if (name.length >= 2 && lower.includes(name)) return true;

    // 3. Check description

    const desc = (s.description || "").toLowerCase();

    if (!desc) return false;

    const descWords = desc.replace(/,/g, " ").split(/\s+/).filter((w) => w.length >= 2);

    return descWords.some((w) => lower.includes(w));

  });

  if (matched.length === 0) return "";

  // Cap at 3, prefer skills with explicit keyword matches (shorter body = more targeted)

  const sorted = matched.sort((a, b) => (a.body || "").length - (b.body || "").length).slice(0, 3);

  return sorted.map((s) => `[Skill: ${s.name}]\n${s.body}`).join("\n\n---\n\n");

}



function showSkillsPanel() {

  document.getElementById("skillsModal").classList.remove("hidden");

  renderSkillsList();

  const first = state.skills[0];

  if (first) {

    const item = document.querySelector(`.skill-list-item[data-skill-name="${escapeHtml(first.name)}"]`);

    if (item) { item.classList.add("active"); showSkillDetail(first); }

    else showSkillDetail(null);

  } else showSkillDetail(null);

}



function renderSkillsList() {

  const list = document.getElementById("skillsList");

  const active = state.skills.filter((s) => !state.disabledSkills.has(s.name));

  const disabled = state.skills.filter((s) => state.disabledSkills.has(s.name));

  const sorted = [...active, ...disabled];



  if (sorted.length === 0) {

    list.innerHTML = `<div class="muted-line" style="padding:12px; font-size:12px;">暂无 Skill</div>`;

  } else {

    list.innerHTML = sorted.map((s) => {

      const on = !state.disabledSkills.has(s.name);

      const explicitOnly = ["dispatching-parallel-agents", "subagent-driven-development", "executing-plans", "writing-plans"].includes(s.name);

      return `

        <div class="skill-list-item" data-skill-name="${escapeHtml(s.name)}">

          <span class="dot ${on ? 'on' : 'off'}"></span>

          <span>${escapeHtml(s.name)}</span>

          ${explicitOnly ? `<span class="skill-explicit-badge" title="仅支持显式调用 /${escapeHtml(s.name)}">/</span>` : ""}

        </div>

      `;

    }).join("");

  }



  list.querySelectorAll(".skill-list-item").forEach((item) => {

    item.addEventListener("click", () => {

      list.querySelectorAll(".skill-list-item").forEach((el) => el.classList.remove("active"));

      item.classList.add("active");

      const skill = state.skills.find((s) => s.name === item.dataset.skillName);

      showSkillDetail(skill);

    });

  });

}



function showSkillDetail(skill) {

  const panel = document.getElementById("skillsDetail");

  if (!skill) {

    if (state.skills.length === 0) {

      panel.innerHTML = `<div class="skills-detail-empty">

        <strong>暂无 Skill</strong>

        <span style="margin-top:6px">点击左侧「+ 新建 Skill」创建第一个 Skill</span>

        <span style="margin-top:4px; font-size:11px">或在 data/skills/ 目录下创建 SKILL.md 文件</span>

      </div>`;

    } else {

      panel.innerHTML = `<div class="skills-detail-empty">← 选择左侧 Skill 查看详情</div>`;

    }

    return;

  }

  const isOn = !state.disabledSkills.has(skill.name);

  panel.innerHTML = `

    <div class="skill-detail-head">

      <div class="skill-detail-name">${escapeHtml(skill.name)}</div>

      <div class="skill-detail-head-actions">

        <label class="toggle-switch" title="${isOn ? '已启用' : '已禁用'}">

          <input type="checkbox" ${isOn ? 'checked' : ''} id="skillToggleBtn" />

          <span class="toggle-track"><span class="toggle-thumb"></span></span>

        </label>

        <button class="skill-edit-icon" id="skillEditBtn" title="编辑">

          <svg class="icon" viewBox="0 0 1097 1024" width="14" height="14"><path d="M925.72 1024H161.13C72 1024 0 952.32 0 863.57V160.43C0 71.68 72 0 161.16 0h613.67c20.58 0 34.3 13.65 34.3 34.13s-13.72 34.14-34.3 34.14H161.16a91.99 91.99 0 00-92.55 92.16v699.73c0 54.61 41.13 95.57 92.55 95.57h764.59c51.44 0 92.57-40.96 92.57-92.16V337.92c0-20.48 13.7-34.13 34.28-34.13s34.28 13.65 34.28 34.13v525.65c3.41 88.75-72 160.43-161.16 160.43zM456 658.77c-10.29 0-17.14-3.41-24-10.24-13.72-13.65-13.72-34.13 0-47.78L1038.85 23.89a33.26 33.26 0 0148.03 0c13.7 13.66 13.7 34.14 0 47.79L479.96 648.53c-6.83 6.83-13.7 10.24-24 10.24z" fill="currentColor"/></svg>

        </button>

      </div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">描述</div>

      <div class="skill-detail-value">${escapeHtml(skill.description || "无")}</div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">关键词</div>

      <div class="skill-detail-value">${escapeHtml((skill.keywords || []).join(", ") || "无")}</div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">工具</div>

      <div class="skill-detail-value">${escapeHtml((skill.tools || []).join(", ") || "无")}</div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">文件路径</div>

      <div class="skill-detail-value">${escapeHtml(skill.path || `data/skills/${skill.dir || skill.name}/SKILL.md`)}</div>

    </div>

  `;

  document.getElementById("skillToggleBtn").addEventListener("change", () => {

    toggleSkill(skill.name);

    showSkillDetail(state.skills.find((s) => s.name === skill.name));

    renderSkillsList();

  });

  document.getElementById("skillEditBtn").addEventListener("click", () => openSkillEditor(skill));

}



// ── Skill editor modal ──



let _editingSkillName = null;



function openSkillEditor(skill) {

  _editingSkillName = skill ? skill.name : null;

  document.getElementById("skillEditorTitle").textContent = skill ? `编辑 ${skill.name}` : "新建 Skill";

  document.getElementById("skillEditName").value = skill ? skill.name : "";

  document.getElementById("skillEditDesc").value = skill ? (skill.description || "") : "";

  document.getElementById("skillEditKeywords").value = skill ? (skill.keywords || []).join(", ") : "";

  document.getElementById("skillEditTools").value = skill ? (skill.tools || []).join(", ") : "";

  document.getElementById("skillEditBody").value = skill ? (skill.body || "") : "";

  document.getElementById("skillEditorModal").classList.remove("hidden");

}



function closeSkillEditor() {

  document.getElementById("skillEditorModal").classList.add("hidden");

  _editingSkillName = null;

}



async function saveSkillEdit() {

  const name = document.getElementById("skillEditName").value.trim();

  const desc = document.getElementById("skillEditDesc").value.trim();

  const keywords = document.getElementById("skillEditKeywords").value.trim();

  const tools = document.getElementById("skillEditTools").value.trim();

  const body = document.getElementById("skillEditBody").value.trim();

  if (!name) { showToast("请输入名称", "error"); return; }

  if (!body) { showToast("请输入正文", "error"); return; }



  // Check duplicate name

  const conflict = state.skills.find((s) => s.name === name && s.name !== _editingSkillName);

  if (conflict) { showToast(`名称 "${name}" 已存在，请使用其他名称`, "error"); return; }



  try {

    if (_editingSkillName && _editingSkillName !== name) {

      // Name changed: delete old, create new

      await apiJson(`/api/skills?name=${encodeURIComponent(_editingSkillName)}`, { method: "DELETE" });

    }

    await apiJson("/api/skills", {

      method: "POST",

      body: JSON.stringify({ name, description: desc, keywords, tools, body }),

    });

    await loadSkills();

    closeSkillEditor();

    renderSkillsList();

    renderSettingsSkillsSidebar();

    const updated = state.skills.find((s) => s.name === name);

    if (updated) showSkillDetail(updated);

    if (updated) { const s = document.getElementById("settingsSkillsDetail"); if (s) showSkillDetailInSettings(updated); }

    else showSkillDetail(null);

  } catch (err) {

    showToast(`保存失败：${err.message}`, "error");

  }

}



function toggleSkill(name) {

  if (state.disabledSkills.has(name)) {

    state.disabledSkills.delete(name);

  } else {

    state.disabledSkills.add(name);

  }

  localStorage.setItem("agent-lite-disabled-skills", JSON.stringify([...state.disabledSkills]));

}



async function deleteSkillConfirm(name) {

  const btn = document.getElementById("skillDeleteBtn");

  document.querySelector(".key-delete-confirm")?.remove();

  const confirm = document.createElement("div");

  confirm.className = "key-delete-confirm";

  confirm.innerHTML = `

    <span>删除 Skill「${escapeHtml(name)}」？</span>

    <button class="key-confirm-yes" type="button">确认</button>

    <button class="key-confirm-no" type="button">取消</button>

  `;

  btn.closest(".skill-detail-actions")?.after(confirm);

  confirm.querySelector(".key-confirm-yes").addEventListener("click", async () => {

    confirm.remove();

    try {

      await apiJson(`/api/skills?name=${encodeURIComponent(name)}`, { method: "DELETE" });

      await loadSkills();

      renderSkillsList();

      showSkillDetail(null);

    } catch (err) {

      showToast(`删除失败：${err.message}`, "error");

    }

  });

  confirm.querySelector(".key-confirm-no").addEventListener("click", () => confirm.remove());

}



function showInlineKeyDeleteConfirm(row, name, onConfirm) {

  // Remove any existing confirm

  document.querySelector(".key-delete-confirm")?.remove();

  const confirm = document.createElement("div");

  confirm.className = "key-delete-confirm";

  confirm.innerHTML = `

    <span>删除「${escapeHtml(name.slice(0, 20))}」？</span>

    <button class="key-confirm-yes" type="button">确认</button>

    <button class="key-confirm-no" type="button">取消</button>

  `;

  row.after(confirm);

  confirm.querySelector(".key-confirm-yes").addEventListener("click", () => {

    confirm.remove();

    onConfirm();

  });

  confirm.querySelector(".key-confirm-no").addEventListener("click", () => confirm.remove());

}



// ── Slash suggestion dropdown ──



function showSlashSuggestions() {

  const existing = document.getElementById("slashSuggest");

  const val = els.prompt.value;

  // Only show when line starts with / and cursor is near

  if (!val.match(/^\/\w*$/)) {

    if (existing) existing.remove();

    return;

  }

  const partial = val.slice(1).toLowerCase();

  const active = state.skills.filter((s) => !state.disabledSkills.has(s.name));

  const matches = active.filter((s) => s.name.startsWith(partial));

  if (matches.length === 0) {

    if (existing) existing.remove();

    return;

  }

  if (!existing) {

    const dd = document.createElement("div");

    dd.id = "slashSuggest";

    dd.className = "slash-suggest";

    els.chatForm.insertBefore(dd, els.prompt);

  }

  const dd = document.getElementById("slashSuggest");

  dd.innerHTML = matches.map((s) => `

    <div class="slash-item" data-skill="${escapeHtml(s.name)}">

      <span class="slash-name">/${escapeHtml(s.name)}</span>

      <span class="slash-desc">${escapeHtml((s.description || "").slice(0, 40))}</span>

    </div>

  `).join("");

  dd.querySelectorAll(".slash-item").forEach((item) => {

    item.addEventListener("click", () => {

      els.prompt.value = "/" + item.dataset.skill + " ";

      dd.remove();

      els.prompt.focus();

      updateSendButtonState();

    });

  });

}



async function loadMemoryContext() {

  try {

    state.memoryContext = await apiJson("/api/memory-context");

  } catch {

    state.memoryContext = { found: false, content: null };

  }

  updateMemoryContextIndicator();

}



function updateMemoryContextIndicator() {

  const panel = document.getElementById("memoryContextInfo");

  if (!panel) return;

  const count = state.memoryContext?.count || 0;

  if (state.memoryContext?.found && count > 0) {

    panel.innerHTML = `<span class="ctx-badge ctx-memory">🧠 长期记忆</span><span class="ctx-hint">${count} 条 · 跨会话/跨项目保留，通过 Memory 面板管理</span>`;

    panel.style.display = "flex";

  } else {

    panel.innerHTML = `<span class="ctx-badge muted">🧠 无长期记忆</span><span class="ctx-hint">通过 Memory 面板添加跨会话保留的知识，Agent 每次对话都能引用</span>`;

    panel.style.display = "flex";

  }

}



function saveSystemPrompt() {

  const value = els.systemPromptText.value.trim();

  if (value && value !== defaultSystemPrompt) {

    localStorage.setItem("agent-lite-system-prompt", value);

  } else {

    localStorage.removeItem("agent-lite-system-prompt");

  }

  updateModePromptPreview();

}



function updateModePromptPreview() {

  const permissionProfile = getPermissionProfile();

  const lines = [

    permissionInstructions[permissionProfile] || permissionInstructions.confirm,

    "",

    `Tool preset: ${els.toolPreset.value}`,

    `Allowed tools: ${[...getAllowedToolNames()].join(", ")}`,

  ];

  if (state.projectContext?.found) {

    lines.unshift(`[项目上下文: ${state.projectContext.name} · ${state.projectContext.content.length} 字]`);

  }

  if (state.memoryContext?.found && state.memoryContext.count > 0) {

    lines.unshift(`[持久记忆: ${state.memoryContext.count} 条 · 已注入全文]`);

  }

  els.modePromptPreview.textContent = lines.join("\n");

}



function closeTopPanels() {

  els.statsPanel.classList.remove("open");

  els.toolLogPanel.classList.remove("open");

  els.usageStrip.classList.remove("active");

  els.toolLogToggle.classList.remove("active");

}



async function apiJson(url, options = {}) {

  const res = await fetch(url, {

    ...options,

    headers: {

      "Content-Type": "application/json",

      ...(options.headers || {}),

    },

  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) throw new Error(data.error || data?.error?.message || `HTTP ${res.status}`);

  return data;

}



function sessionFilePath() {

  return state.sessionId ? `agent-lite/data/sessions/${state.sessionId}.json` : "-";

}



function calcStats() {

  const counts = {

    user: state.messages.filter((msg) => msg.role === "user").length,

    assistant: state.messages.filter((msg) => msg.role === "assistant").length,

    toolCalls: state.messages.filter((msg) => msg.role === "tool-call").length,

    toolResults: state.messages.filter((msg) => msg.role === "tool-result").length,

  };

  counts.total = counts.user + counts.assistant + counts.toolCalls + counts.toolResults;



  // Accumulated API stats (from usage callbacks)

  const apiInput = state.stats.input;

  const apiOutput = state.stats.output;

  const apiCache = state.stats.cache || 0;



  // Estimate current context load from actual messages

  const contextTokens = state.messages

    .filter((msg) => !msg.streaming)

    .reduce((sum, msg) => sum + estimateTokens(getMsgText(msg)), 0)

    + estimateTokens(getSystemPrompt());



  const model = getSelectedModel() || "";

  let ctxLimit = 128000; // 默认

  if (/claude.*(?:4\.[5-9]|[5-9]\.)/i.test(model)) ctxLimit = 200000;

  else if (/claude.*(?:4\.[6-9]|[5-9])/i.test(model)) ctxLimit = 1000000;

  else if (/claude|opus|sonnet|haiku/i.test(model)) ctxLimit = 200000;

  else if (/gpt-4\.1|gpt-5\.[2-9]/i.test(model)) ctxLimit = 1000000;

  else if (/gpt|o1|o3|o4|openai/i.test(model)) ctxLimit = 128000;

  else if (/deepseek.*v4/i.test(model)) ctxLimit = 1000000;

  else if (/deepseek/i.test(model)) ctxLimit = 128000;

  else if (/gemini/i.test(model)) ctxLimit = 1000000;

  const contextPct = Math.min(100, (contextTokens / ctxLimit) * 100);



  return { counts, input: apiInput, output: apiOutput, cache: apiCache, contextTokens, ctxLimit, contextPct };

}



function updateStatsPanel() {

  const stats = calcStats();

  els.statInput.textContent = formatCompact(stats.input);

  els.statOutput.textContent = formatCompact(stats.output);

  els.statCache.textContent = formatCompact(stats.cache);

  els.statContext.textContent = `${stats.contextPct.toFixed(0)}%`;

  els.usageStrip.title = `上下文 ${formatCompact(stats.contextTokens || 0)} / ${formatCompact(stats.ctxLimit || 200000)} tokens`;

  // Update ring chart

  const ring = document.getElementById("ctxRingFill");

  if (ring) {

    const pct = Math.min(stats.contextPct, 100) / 100;

    const circumference = 2 * Math.PI * 5; // r=5

    ring.setAttribute("stroke-dasharray", `${pct * circumference} ${circumference}`);

    ring.setAttribute("stroke", stats.contextPct >= 80 ? "var(--red)" : stats.contextPct >= 60 ? "var(--yellow)" : "var(--muted)");

  }



  // Context usage warning

  const ctxPct = stats.contextPct;

  els.usageStrip.classList.remove("warn", "danger");

  els.statContext.classList.remove("warn", "danger");

  if (ctxPct >= 80) {

    els.usageStrip.classList.add("danger");

    els.statContext.classList.add("danger");

  } else if (ctxPct >= 60) {

    els.usageStrip.classList.add("warn");

    els.statContext.classList.add("warn");

  }



  els.sessionFile.textContent = sessionFilePath();

  els.sessionIdLabel.textContent = state.sessionId || "-";

  els.msgUser.textContent = stats.counts.user;

  els.msgAssistant.textContent = stats.counts.assistant;

  els.msgToolCalls.textContent = stats.counts.toolCalls;

  els.msgToolResults.textContent = stats.counts.toolResults;

  els.msgTotal.textContent = stats.counts.total;

  els.tokenInput.textContent = formatNumber(stats.input);

  els.tokenOutput.textContent = formatNumber(stats.output);

  els.tokenCache.textContent = formatNumber(stats.cache);

  els.tokenTotal.textContent = formatNumber(stats.total);

  const ctxLimit = stats.ctxLimit || 128000;

  const ctxLabel = ctxLimit >= 1000000 ? "1M" : ctxLimit >= 200000 ? "200K" : "128K";

  els.tokenContext.textContent = `${stats.contextPct.toFixed(0)}%（${formatCompact(stats.contextTokens || 0)} / ${formatCompact(stats.ctxLimit || 200000)}）`;

}



function splitThoughtContent(text = "") {

  const thinkRegex = /<think>([\s\S]*?)<\/think>/i;

  const match = text.match(thinkRegex);

  if (!match) return { thought: "", content: text };

  return {

    thought: match[1].trim(),

    content: text.replace(thinkRegex, "").trim(),

  };

}



// ── Syntax highlighting (lightweight) ──



const SYNTAX_PATTERNS = {

  javascript: [

    [/\b(function|const|let|var|return|if|else|for|while|async|await|class|import|export|from|default|try|catch|throw|new|this|typeof|instanceof|of|in|null|undefined|true|false)\b/g, "syn-kw"],

    [/(["'`])(?:\\.|(?!\1).)*?\1/g, "syn-str"],

    [/(\/\/.*$)/gm, "syn-com"],

    [/(\/\*[\s\S]*?\*\/)/g, "syn-com"],

    [/\b(\d+\.?\d*)\b/g, "syn-num"],

    [/(=>|\b(?:===?|!==?|[+\-*/%])\b)/g, "syn-op"],

  ],

  js: "javascript", jsx: "javascript", ts: "javascript", typescript: "javascript",

  python: [

    [/\b(def|class|return|if|elif|else|for|while|import|from|as|try|except|raise|with|and|or|not|in|is|None|True|False|pass|break|continue|yield|async|await|lambda|global|nonlocal)\b/g, "syn-kw"],

    [/(["'])(?:\\.|(?!\1).)*?\1/g, "syn-str"],

    [/(#.*$)/gm, "syn-com"],

    [/(\"\"\"[\s\S]*?\"\"\")|('''[\s\S]*?''')/g, "syn-com"],

    [/\b(\d+\.?\d*)\b/g, "syn-num"],

    [/@\w+/g, "syn-op"],

  ],

  py: "python",

  html: [

    [/(<\/?)(\w+)/g, "syn-kw"],

    [/("(?:[^"\\]|\\.)*")/g, "syn-str"],

    [/(<!--[\s\S]*?-->)/g, "syn-com"],

    [/(\w+)=/g, "syn-fn"],

  ],

  css: [

    [/([.#]?[a-zA-Z_-]+)(?=\s*\{)/g, "syn-fn"],

    [/(:(?:[^;{]+))/g, "syn-str"],

    [/(\/\*[\s\S]*?\*\/)/g, "syn-com"],

    [/\b(\d+\.?\d*(?:px|em|rem|%|vh|vw|s)?)\b/g, "syn-num"],

    [/\b(important|bold|normal|italic|none|block|inline|flex|grid|hidden|visible|auto|inherit|initial)\b/g, "syn-kw"],

  ],

};



function _resolveSyntaxPatterns(lang) {

  if (!lang) return null;

  let patterns = SYNTAX_PATTERNS[lang];

  if (!patterns) return null;

  if (typeof patterns === "string") return _resolveSyntaxPatterns(patterns);

  if (!Array.isArray(patterns)) return null;

  return patterns;

}



function highlightSyntax(code, lang) {

  const patterns = _resolveSyntaxPatterns(lang) || _resolveSyntaxPatterns("javascript");

  let result = escapeHtml(code);

  // Apply each pattern: wrap matches in <span class="...">

  patterns.forEach(([regex, cls]) => {

    result = result.replace(regex, (match, ...groups) => {

      // For patterns with capture groups (like HTML tags), preserve the structure

      if (groups.length > 1 && groups[0] !== undefined && match.length > groups[0].length) {

        // Complex replacement for patterns that capture parts

        return match;

      }

      return `<span class="${cls}">${match}</span>`;

    });

  });

  return result;

}



// ── Diff rendering ──



function renderDiff(text) {

  const lines = text.split("\n");

  const html = lines.map((line) => {

    const escaped = escapeHtml(line);

    if (line.startsWith("+++") || line.startsWith("---")) return `<span class="diff-line diff-header">${escaped}</span>`;

    if (line.startsWith("@@")) return `<span class="diff-line diff-hunk">${escaped}</span>`;

    if (line.startsWith("+")) return `<span class="diff-line diff-add">${escaped}</span>`;

    if (line.startsWith("-")) return `<span class="diff-line diff-remove">${escaped}</span>`;

    return `<span class="diff-line diff-context">${escaped}</span>`;

  }).join("");

  return `<div class="code-block diff-block"><div class="code-head"><span>diff</span></div><div class="diff-lines">${html}</div></div>`;

}



// ── ANSI rendering ──



function renderAnsi(text) {

  let result = escapeHtml(text);

  let stack = [];

  // Parse ANSI escape sequences: \x1b[...m or \033[...m

  result = result.replace(/\x1b\[(\d+(?:;\d+)*)m/g, (_, codes) => {

    const parts = codes.split(";").map(Number);

    let html = "";

    // Close previous spans

    while (stack.length) html += "</span>";

    stack = [];

    for (const code of parts) {

      if (code === 0) {

        stack = [];

        continue;

      }

      const cls = `ansi-${code}`;

      if (code >= 30 && code <= 37) stack.push(cls);

      else if (code === 1 || code === 3 || code === 4) stack.push(`ansi-${code}`);

    }

    for (const cls of stack) html += `<span class="${cls}">`;

    return html;

  });

  while (stack.length) { result += "</span>"; stack.pop(); }

  return result;

}



// ── Markdown rendering (powered by marked) ──



(function setupMarked() {

  const renderer = new marked.Renderer();

  renderer.code = function({ text, lang }) {

    if (lang === "diff" || lang === "diff ") {

      return renderDiff(text);

    }

    if (lang === "terminal" || lang === "ansi") {

      return `<div class="code-block"><div class="code-head"><span>terminal</span></div><div class="ansi-block">${renderAnsi(text)}</div></div>`;

    }

    const doHighlight = _resolveSyntaxPatterns(lang);

    const lines = text.split("\n");

    const lineHtml = lines

      .map((line, i) => {

        const escaped = escapeHtml(line || " ");

        const highlighted = doHighlight ? highlightSyntax(line || " ", lang) : escaped;

        return `<span class="line-no">${i + 1}</span><code class="line-code">${highlighted}</code>`;

      })

      .join("");

    return `<div class="code-block"><div class="code-head"><span>${escapeHtml(lang || "text")}</span><button class="copy-code" type="button">copy</button></div><pre class="code-lines">${lineHtml}</pre></div>`;

  };

  marked.setOptions({ renderer, breaks: false, gfm: true });

})();



function renderMarkdownLite(text) {

  if (!text) return "";

  return marked.parse(text);

}



function bindCopyButtons() {

  document.querySelectorAll(".copy-code").forEach((btn) => {

    btn.addEventListener("click", async () => {

      const target = document.getElementById(btn.dataset.codeId);

      if (!target) return;

      const text = Array.from(target.querySelectorAll(".line-code"))

        .map((node) => node.textContent)

        .join("\n");

      const ok = await copyText(text);

      btn.textContent = ok ? "copied" : "failed";

      setTimeout(() => {

        btn.textContent = "copy";

      }, 1200);

    });

  });



  document.querySelectorAll(".apply-edit-btn").forEach((btn) => {

    btn.addEventListener("click", (event) => {

      event.stopPropagation();

      applyPendingEdit(btn.dataset.editId);

    });

  });

}



// ── Compact tool card icons & labels ──



const TOOL_DISPLAY = {

  list_files:   { icon: "📂", label: "列出",   call: "列出目录",   done: "已列出" },

  read_file:    { icon: "📄", label: "读取",   call: "读取文件",   done: "已读取" },

  search_files: { icon: "🔍", label: "搜索",   call: "搜索代码",   done: "搜索完成" },

  glob_files:   { icon: "🔎", label: "匹配",   call: "glob 匹配",  done: "匹配完成" },

  propose_edit: { icon: "✏️", label: "修改",   call: "生成修改方案", done: "方案已生成" },

  apply_edit:   { icon: "✅", label: "应用",   call: "应用修改",   done: "修改已应用" },

  run_command:  { icon: "⚡", label: "命令",   call: "运行命令",   done: "命令完成" },

  write_file:   { icon: "📝", label: "写入",   call: "写入文件",   done: "已写入" },

  delete_file:  { icon: "🗑️", label: "删除",   call: "删除文件",   done: "已删除" },

  web_fetch:    { icon: "🌐", label: "抓取",   call: "抓取网页",   done: "已抓取" },

  task:         { icon: "🤖", label: "子任务", call: "启动子Agent", done: "子Agent完成" },

  use_skill:    { icon: "📌", label: "Skill", call: "加载Skill", done: "Skill已加载" },

};



function _toolIcon(action) { return (TOOL_DISPLAY[action] || {}).icon || "🔧"; }

function _toolLabel(action, isCall) {

  const d = TOOL_DISPLAY[action] || {};

  return isCall ? (d.call || action) : (d.done || `${action} 完成`);

}

function _toolTarget(meta) {

  if (!meta) return "";

  const tool = meta.tool || meta;

  if (tool.path) return tool.path;

  if (tool.pattern) return tool.pattern;

  if (tool.query) return `"${tool.query}"`;

  if (tool.command) return tool.command;

  if (tool.url) return tool.url;

  if (tool.prompt) return (tool.prompt || "").slice(0, 60);

  return "";

}



function _toolResultSummary(msg) {

  if (msg.role !== "tool-result") return "";

  const content = (getMsgText(msg)).trim();

  const meta = msg.meta || {};

  const action = meta.action || meta.tool?.action || "";

  // Quick extractions for specific tool types

  if (action === "list_files") {

    const m = content.match(/文件数量[：:]\s*(\d+)/);

    return m ? `${m[1]} 项` : "";

  }

  if (action === "read_file") {

    const p = meta.path || meta.tool?.path || "";
    return p ? p.split("/").pop() || p : "";

  }

  if (action === "search_files") {

    const m = content.match(/命中数量[：:]\s*(\d+)/);

    return m ? `${m[1]} 处匹配` : "";

  }

  if (action === "glob_files") {

    const m = content.match(/匹配数量[：:]\s*(\d+)/);

    return m ? `${m[1]} 个文件` : "";

  }

  if (action === "run_command") {

    const m = content.match(/退出码[：:]\s*(\d+)/);

    return m ? (m[1] === "0" ? "成功" : `退出码 ${m[1]}`) : "";

  }

  if (action === "web_fetch") {

    return content.includes("ok") || !content.includes("Failed") ? "已获取" : "失败";

  }

  if (action === "task") {

    const m = content.match(/轮次[：:]\s*(\d+)/);

    return m ? `${m[1]} 轮` : "";

  }

  // Generic: first meaningful line

  const firstLine = content.split("\n").find((l) => l.trim() && !l.startsWith("```"));

  return firstLine ? firstLine.trim().slice(0, 80) : "";

}



function renderToolMessage(msg) {

  if (!msg) return "";

  const meta = msg.meta || {};

  const action = meta.action || (meta.tool || {}).action || "tool";

  const isCall = msg.role === "tool-call";

  const icon = _toolIcon(action);

  const label = _toolLabel(action, isCall);

  const target = _toolTarget(meta);

  const summary = isCall ? "" : _toolResultSummary(msg);

  const pendingId = meta.pendingEditId;
  const applied = pendingId && state.pendingEdits[pendingId]?.applied;
  const cls = isCall ? "call" : "result";
  const error = !isCall && (getMsgText(msg)).startsWith("工具执行失败");
  const content = getMsgText(msg);
  const hasBody = content.length > 0 && action !== "read_file";
  const autoOpen = !isCall && (action === "propose_edit" || action === "write_file") ? " open" : "";
  const showApplyBar = pendingId && !applied;

  return `
    <details class="tool-inline ${cls}${error ? " error" : ""}"${autoOpen}>
      <summary class="tool-inline-head">
        <span class="tool-inline-icon">${icon}</span>
        <span class="tool-inline-label">${escapeHtml(label)}</span>
        ${target ? `<span class="tool-inline-target">${escapeHtml(target)}</span>` : ""}
        ${summary ? `<span class="tool-inline-summary">${escapeHtml(summary)}</span>` : ""}
        ${hasBody ? `<span class="tool-inline-expand">▾</span>` : ""}
      </summary>
      ${hasBody ? `<div class="tool-inline-body">${renderMarkdownLite(content)}</div>` : ""}
    </details>
    ${showApplyBar ? `<div class="apply-edit-bar"><button class="apply-edit-btn" type="button" data-edit-id="${pendingId}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>应用修改</button><span class="apply-edit-hint">写入文件并保留备份</span></div>` : ""}
    ${pendingId && applied ? `<div class="apply-edit-bar done"><span class="apply-edit-done">✓ 已应用</span></div>` : ""}
  `;
}
function renderProcessAssistant(msg) {

  const thought = msg.thought || "";

  const content = (getMsgText(msg)).trim();

  if (!thought && !content) return "";

  let html = "";

  if (thought) {

    html += `<details class="thought-inline"><summary>💭 ${escapeHtml(summarizeThought(thought))}</summary><div class="thought-body">${renderMarkdownLite(thought)}</div></details>`;

  }

  if (content) {

    html += `<div class="assistant-inline-text">${renderMarkdownLite(content)}</div>`;

  }

  return html;

}



function renderToolSection(tools, isStreaming) {

  if (!tools || tools.length === 0) return "";

  const count = tools.filter((t) => t.callMsg).length;

  // Merge call+result into a single compact card per tool
  const cards = tools.map((t, idx) => {
    const isLast = idx === tools.length - 1;
    const callMsg = t.callMsg;
    const resultMsg = t.resultMsg;
    const intermediate = t.intermediate || [];

    if (!callMsg && !resultMsg && intermediate.length) {
      return intermediate.map(renderProcessAssistant).join("");
    }
    if (!callMsg && resultMsg) {
      // Orphan result — render standalone
      return renderToolMessage(resultMsg);
    }

    // Merged call+result card
    const meta = callMsg ? (callMsg.meta || {}) : {};
    const action = meta.action || (meta.tool || {}).action || "tool";
    const icon = _toolIcon(action);
    const label = _toolLabel(action, true);
    const target = _toolTarget(meta);

    // Result content (skip body for read_file — too large, just show filename in summary)
    const resultContent = resultMsg ? getMsgText(resultMsg) : "";
    const resultError = resultContent.startsWith("工具执行失败");
    const hasResult = resultContent.length > 0 && action !== "read_file";

    // Expand if streaming (keep all tool cards open so user sees full progress)
    // or needs review (propose_edit / write_file with pending apply)
    const needsReview = resultMsg && (
      action === "propose_edit" || action === "write_file"
    );
    const openAttr = (isStreaming || needsReview) ? " open" : "";

    const pendingId = (resultMsg?.meta || {}).pendingEditId;
    const applied = pendingId && state.pendingEdits[pendingId]?.applied;
    const showApplyBar = pendingId && !applied;

    // Summary line
    const resultSummary = resultMsg ? _toolResultSummary(resultMsg) : "";
    const statusIcon = resultMsg ? (resultError ? "❌" : "✓") : (isStreaming && isLast ? "⏳" : "");

    let html = `<details class="tool-inline merged${resultError ? " error" : ""}"${openAttr}>
      <summary class="tool-inline-head">
        <span class="tool-inline-icon">${icon}</span>
        <span class="tool-inline-label">${escapeHtml(label)}</span>
        ${target ? `<span class="tool-inline-target">${escapeHtml(target)}</span>` : ""}
        ${resultSummary ? `<span class="tool-inline-summary">${escapeHtml(resultSummary)}</span>` : ""}
        ${statusIcon ? `<span class="tool-inline-status">${statusIcon}</span>` : ""}
        ${hasResult ? `<span class="tool-inline-expand">▾</span>` : ""}
      </summary>`;

    if (intermediate.length) {
      html += intermediate.map(renderProcessAssistant).join("");
    }
    if (hasResult) {
      html += `<div class="tool-inline-body">${renderMarkdownLite(resultContent)}</div>`;
    }
    html += `</details>`;

    if (showApplyBar) {
      html += `<div class="apply-edit-bar"><button class="apply-edit-btn" type="button" data-edit-id="${pendingId}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>应用修改</button><span class="apply-edit-hint">写入文件并保留备份</span></div>`;
    }
    if (pendingId && applied) {
      html += `<div class="apply-edit-bar done"><span class="apply-edit-done">✓ 已应用</span></div>`;
    }

    return html;
  }).join("");

  // Stats for summary
  const totalCalls = tools.filter((t) => t.callMsg).length;
  const successCount = tools.filter((t) => t.resultMsg && !(getMsgText(t.resultMsg)).startsWith("工具执行失败")).length;
  const failCount = tools.filter((t) => t.resultMsg && (getMsgText(t.resultMsg)).startsWith("工具执行失败")).length;

  // Check if any tool result needs user review (propose_edit or write_file with pending edit)
  const needsReview = tools.some((t) => {
    const a = (t.callMsg?.meta || {}).action || "";
    const pid = (t.resultMsg?.meta || {}).pendingEditId;
    return (a === "propose_edit" || a === "write_file") && pid && !state.pendingEdits[pid]?.applied;
  });

  if (isStreaming) {
    return `<div class="tool-section streaming">${cards}</div>`;
  }

  // After completion: wrap all tools in a mega-summary with stats
  // Keep open if any propose_edit / write_file still needs review
  const statsParts = [`${totalCalls} 次调用`];
  if (successCount) statsParts.push(`${successCount} 成功`);
  if (failCount) statsParts.push(`${failCount} 失败`);

  return `
    <details class="tool-section done"${needsReview ? " open" : ""}>
      <summary class="tool-section-summary">🔧 ${statsParts.join(" · ")}</summary>
      <div class="tool-section-body">${cards}</div>
    </details>
  `;

}



function renderMessages() {

  if (state.messages.length === 0) {

    els.chatPane.classList.add("empty-chat");

    els.messages.innerHTML = `
      <div class="welcome-screen">
        <div class="welcome-header">
          <svg class="welcome-logo" viewBox="0 0 24 24" width="28" height="28" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 22H7L12 12L17 22H22L12 2Z" fill="var(--accent)" />
            <path d="M12 12L7 22H17L12 12Z" fill="var(--accent-bg)" />
          </svg>
          <div class="welcome-brand">
            <h1 class="welcome-title">Agent Lite</h1>
            <p class="welcome-desc">开始对话，用自然语言驱动代码。</p>
          </div>
        </div>
      </div>
    `;

    document.getElementById("chatTimeline").innerHTML = "";

    updateStatsPanel();

    renderToolLog();

    return;

  }



  els.chatPane.classList.remove("empty-chat");



  // Parse messages into segments: tool-sections and standalone messages

  const segments = [];

  let i = 0;

  while (i < state.messages.length) {

    const msg = state.messages[i];

    // Collect consecutive tool messages into a section

    if (msg.role === "tool-call" || msg.role === "tool-result" || isProcessMessage(msg)) {

      const tools = [];

      while (i < state.messages.length) {

        const m = state.messages[i];

        if (m.role === "tool-call") {

          const callMsg = m;

          i++;

          // Look for matching result

          let resultMsg = null;

          const intermediate = [];

          while (i < state.messages.length) {

            const next = state.messages[i];

            if (next.role === "tool-result") {

              resultMsg = next;

              i++;

              break;

            } else if (next.role === "tool-call") {

              break; // next tool call without result

            } else if (isProcessMessage(next)) {

              intermediate.push(next);

              i++;

            } else if (next.role === "assistant" && /^准备调用/.test(getMsgText(next))) {
              // Skip placeholder assistant messages between tool groups — don't break
              i++;
            } else {

              break;

            }

          }

          tools.push({ callMsg, resultMsg, intermediate });

        } else if (m.role === "tool-result") {

          // Orphan result

          tools.push({ callMsg: null, resultMsg: m });

          i++;

        } else if (isProcessMessage(m)) {

          tools.push({ callMsg: null, resultMsg: null, intermediate: [m] });

          i++;

        } else {

          break;

        }

      }

      segments.push({ type: "tools", tools });

      continue;

    }



    // Standalone message (user, assistant, etc.)

    segments.push({ type: "msg", msg });

    i++;

  }

  // Render segments

  const streaming = state.isStreaming;

  // Detect if there's a real final answer after tool sections
  const hasFinalAnswer = segments.some((seg, idx) => {
    if (seg.type !== "msg") return false;
    const msg = seg.msg;
    if (msg.role !== "assistant") return false;
    // Has real content (not just a placeholder)
    const c = getMsgText(msg);
    return c && !/^准备调用/.test(c) && !/^$/.test(c);
  });

  // Find the index of the first real answer
  const finalAnswerIdx = segments.findIndex((seg) => {
    if (seg.type !== "msg") return false;
    const msg = seg.msg;
    if (msg.role !== "assistant") return false;
    const c = getMsgText(msg);
    return c && !/^准备调用/.test(c);
  });

  // Collect tool section indices before final answer
  const toolSectionIndices = [];
  segments.forEach((seg, idx) => {
    if (seg.type === "tools" && (finalAnswerIdx < 0 || idx < finalAnswerIdx)) {
      toolSectionIndices.push(idx);
    }
  });

  // Calculate total stats across all tool sections
  let totalCalls = 0, totalSuccess = 0, totalFail = 0;
  for (const idx of toolSectionIndices) {
    const tools = segments[idx].tools;
    totalCalls += tools.filter((t) => t.callMsg).length;
    totalSuccess += tools.filter((t) => t.resultMsg && !(getMsgText(t.resultMsg)).startsWith("工具执行失败")).length;
    totalFail += tools.filter((t) => t.resultMsg && (getMsgText(t.resultMsg)).startsWith("工具执行失败")).length;
  }

  let html = segments.map((seg, segIdx) => {

    if (seg.type === "tools") {
      // Collapse if final answer exists and is after this tool section
      const isBeforeFinal = hasFinalAnswer && (finalAnswerIdx < 0 || segIdx < finalAnswerIdx);
      const sectionHtml = renderToolSection(seg.tools, streaming && !isBeforeFinal);

      // Wrap first tool section with parent summary if there are multiple sections
      if (isBeforeFinal && toolSectionIndices.length > 1 && segIdx === toolSectionIndices[0]) {
        const statParts = [`${totalCalls} 次调用`];
        if (totalSuccess) statParts.push(`${totalSuccess} 成功`);
        if (totalFail) statParts.push(`${totalFail} 失败`);
        const rest = toolSectionIndices.slice(1).map((i) => segments[i]).map((s) => renderToolSection(s.tools, false)).join("");
        return `<details class="tool-section tool-section-parent"><summary class="tool-section-summary">🔧 ${statParts.join(" · ")}</summary><div class="tool-section-body">${sectionHtml}${rest}</div></details>`;
      }
      // Skip subsequent tool sections — already rendered inside parent
      if (isBeforeFinal && toolSectionIndices.length > 1 && segIdx !== toolSectionIndices[0]) {
        return "";
      }

      return sectionHtml;
    }

    const msg = seg.msg;

    if (msg.meta?.kind === "tool-round-limit") return renderRoundLimitMessage();

    // Skip placeholder assistant messages (just "准备调用工具..." with tool calls)
    if (msg.role === "assistant" && /^准备调用/.test(getMsgText(msg)) && msg.meta?.toolCalls) {
      return "";
    }

    if (msg.role === "user") {

      const origIdx = state.messages.indexOf(msg);

      const text = Array.isArray(msg.content) ? (msg.content.find((c) => c.type === "text")?.text || "") : (getMsgText(msg));

      const imagesHtml = (msg._images || []).map((img) =>

        `<img class="msg-img" src="data:${img.mime};base64,${img.base64}" alt="${escapeHtml(img.name)}" title="${escapeHtml(img.name)}" />`

      ).join("");

      return `<article class="msg user" data-msg-index="${origIdx}"><div class="bubble">${renderMarkdownLite(text)}${imagesHtml}</div></article>`;

    }

    const thought = msg.thought || "";

    const content = getMsgText(msg);

    const thoughtHtml = thought

      ? `<details class="thought"${msg.streaming ? " open" : ""}><summary>${escapeHtml(summarizeThought(thought))}</summary><div>${renderMarkdownLite(thought)}</div></details>`

      : "";

    const timerDisplay = state._timerDisplay || "0s";

    const status = msg.streaming ? `<span class="streaming-dot">思考中 <span class="streaming-timer">${timerDisplay}</span></span>` : "";

    const asstIdx = state.messages.indexOf(msg);

    return `

      <article class="msg assistant" data-msg-index="${asstIdx}">

        <div class="role">${escapeHtml(msg._model || getSelectedModel() || "Agent")} ${status}</div>

        ${thoughtHtml}

        ${renderAssistantContent(content)}

        ${(() => {

          const parts = [];

          const usage = msg._usage || (msg.meta || {})._usage;

          if (usage && usage.input) parts.push(`<svg class="stat-icon stat-arrow-svg" viewBox="0 0 1024 1024" width="14" height="14"><path d="M478.3 927.5V175.2L259 394.5c-10.7 10.7-28.1 10.7-38.7 0l-6.5-6.5c-10.7-10.7-10.7-28.1 0-38.7L481.6 81.4c4.5-9.2 13.4-16 23.9-17.6 7.1-1.5 14.7-0.1 21 4 4 2.4 7.5 5.6 10.1 9.4l0.5 0.5c2.6 2.6 4.6 5.6 5.9 8.8l266.7 266.7c10.7 10.7 10.7 28.1 0 38.7l-6.5 6.5c-10.7 10.7-28.1 10.7-38.7 0l-222.3-222v751.1c0 17.6-14.4 32-32 32-17.5 0-31.9-14.4-31.9-32z" fill="currentColor"/></svg>${formatCompact(usage.input)}`);

          if (usage && usage.output) parts.push(`<svg class="stat-icon stat-arrow-svg" viewBox="0 0 1024 1024" width="14" height="14"><path d="M512 858.7a32 32 0 01-32-32V124.8a32 32 0 1164 0v701.9a32 32 0 01-32 32z" fill="currentColor"/><path d="M512 901.7L234.9 624.6a32 32 0 1145.3-45.3L512 811.2l231.8-231.8a32 32 0 0145.3 45.3z" fill="currentColor"/></svg>${formatCompact(usage.output)}`);

          if (usage && usage.cache) parts.push(`<svg class="stat-icon stat-cache-svg" viewBox="0 0 1024 1024" width="14" height="14"><path d="M241.8 881.5a127 127 0 01-127-127v-85.3a13 13 0 0113-13h14.3a13 13 0 0113 13v85.3a86.6 86.6 0 0086.5 86.5h540.4a86.6 86.6 0 0086.5-86.5v-85.4a13 13 0 0113-13H896a13 13 0 0113 13v85.4a127 127 0 01-126.9 126.9zM273.4 455.7a13 13 0 010-18.5l10.2-10.3a13 13 0 0118.5 0l164.9 164.3a15.4 15.4 0 0026.2-10.9v-404.5a13 13 0 0113-13h14.3a13 13 0 0113 13v404.5a15.4 15.4 0 009.5 14.2 15.4 15.4 0 0016.7-3.3l166.3-164.6a13 13 0 0118.5 0l10.2 10.2a13 13 0 010 18.5L512 695z" fill="currentColor"/></svg> ${formatCompact(usage.cache)}`);

          const respTime = msg._responseTime || (msg.meta || {})._responseTime;

          if (respTime) parts.push(`<svg class="stat-icon stat-time-svg" viewBox="0 0 1024 1024" width="14" height="14"><path d="M711.7 655.4c-5.1 0-10.2-1.5-14.8-4.1l-199.7-112.6c-9.7-5.6-15.9-15.9-15.9-26.6V276.5c0-16.9 13.8-30.7 30.7-30.7s30.7 13.8 30.7 30.7v217.6l183.8 103.9c14.8 8.2 20 27.1 11.8 42-5.6 9.7-15.9 15.4-26.6 15.4z" fill="currentColor"/><circle cx="512" cy="512" r="378.9" fill="none" stroke="currentColor" stroke-width="61.4"/></svg> ${escapeHtml(respTime)}`);

          return parts.length ? `<div class="response-info">${parts.join(" · ")}</div>` : "";

        })()}

      </article>

    `;

  }).join("");



  // Skip DOM update if HTML unchanged (prevents flicker during streaming)
  // ── Render queued messages (waiting to be sent after current task) ──
  let queueHtml = "";
  if (state.messageQueue.length > 0 && state.isStreaming) {
    queueHtml = state.messageQueue.map((q) => {
      const imagesHtml = (q.images || []).map((img) =>
        `<div class="queue-img-thumb"><img src="data:${img.mime};base64,${img.base64}" alt="${escapeHtml(img.name)}" /></div>`
      ).join("");
      return `
        <article class="msg queued">
          <div class="queue-badge">⏳ 等待中</div>
          <div class="bubble queue-bubble">${imagesHtml}${renderMarkdownLite(q.text || "(图片)")}</div>
        </article>`;
    }).join("");
    html += queueHtml;
  }

  // Skip DOM update if HTML unchanged (prevents flicker during streaming)
  // But always update if queue state changed
  const queueKey = state.messageQueue.length;
  if (state._lastRenderedHtml === html && state._lastQueueLen === queueKey) return;
  state._lastRenderedHtml = html;
  state._lastQueueLen = queueKey;

  els.messages.innerHTML = html;

  bindCopyButtons();

  bindMessageActions();

  // Auto-scroll only if user hasn't scrolled up (within 80px of bottom)

  if (state.isStreaming) {

    if (state._followOutput !== false) {

      els.messages.scrollTop = els.messages.scrollHeight;

    }

  } else {

    els.messages.scrollTop = els.messages.scrollHeight;

    state._followOutput = true;

  }

  updateStatsPanel();

  renderToolLog();

  renderTimeline();

}



function getToolLogDetail(msg) {

  const meta = msg.meta || {};

  const tool = meta.tool || {};

  const action = meta.action || tool.action || "tool";

  if (tool.path || meta.path) return tool.path || meta.path;

  if (tool.query || tool.pattern) return tool.query || tool.pattern;

  if (tool.command) return tool.command;

  if (meta.backupPath) return `backup: ${meta.backupPath}`;

  const firstLine = (getMsgText(msg)).split("\n").find(Boolean);

  return firstLine || action;

}



function formatCharCount(text) {

  const length = (text || "").trim().length;

  if (length < 1000) return `${length} 字`;

  return `${(length / 1000).toFixed(1)}k 字`;

}



function summarizeText(text, max = 120) {

  const normalized = (text || "")

    .replace(/```[\s\S]*?```/g, "[代码块]")

    .replace(/\s+/g, " ")

    .trim();

  if (!normalized) return "无摘要";

  return normalized.length > max ? `${normalized.slice(0, max)}...` : normalized;

}



function hasLargeCodeSection(text) {

  const matches = Array.from((text || "").matchAll(/```(\w+)?\n?([\s\S]*?)```/g));

  if (matches.length >= 3) return true;

  return matches.some((match) => (match[2] || "").length > 1200);

}



function summarizeThought(thought = "") {

  const size = formatCharCount(thought);

  if (/工具|tool|调用|read_file|list_files|search_files|propose_edit|run_command/i.test(thought)) {

    return `思考已折叠 · 工具判断 · ${size}`;

  }

  if (/错误|失败|异常|error|fail|debug|排查/i.test(thought)) {

    return `思考已折叠 · 排查判断 · ${size}`;

  }

  if (/代码|实现|修改|diff|文件|函数|组件/i.test(thought)) {

    return `思考已折叠 · 实现判断 · ${size}`;

  }

  return `思考已折叠 · ${size}`;

}



function isProcessMessage(msg) {

  if (!msg) return false;

  if (msg.role === "tool-call" || msg.role === "tool-result") return true;

  if (msg.role !== "assistant" || msg.streaming) return false;

  const content = (getMsgText(msg)).trim();

  // Skip placeholder messages like "准备调用 N 个工具"
  if (msg.meta?.toolCalls?.length) {
    if (/^准备调用/.test(content)) return false;
    return true;
  }

  return /^准备调用\s*\d*\s*个?工具/.test(content) || /^准备调用工具/.test(content);

}


function renderTimeline() {

  const tl = document.getElementById("chatTimeline");

  if (!tl) return;



  // Find timeline nodes: user messages + compact summaries

  const nodes = [];

  for (let i = 0; i < state.messages.length; i++) {

    const msg = state.messages[i];

    if (msg.role === "user") {

      nodes.push({ index: i, label: getMsgText(msg).replace(/\n/g, " "), type: "user" });

    } else if (msg.meta?.kind === "compact-summary") {

      nodes.push({ index: i, label: "📋 上下文已压缩", type: "compact" });

    }

  }

  if (nodes.length === 0) { tl.innerHTML = ""; return; }



  const dots = nodes.map((n) => {

    return `<div class="tl-dot-wrap" data-index="${n.index}"><div class="tl-dot ${n.type}"></div><span class="tl-bubble">${escapeHtml(n.label)}</span></div>`;

  }).join("");



  tl.innerHTML = `<div class="tl-track">${dots}</div>`;



  tl.querySelectorAll(".tl-dot-wrap").forEach((dot) => {

    dot.addEventListener("click", () => {

      const idx = dot.dataset.index;

      const target = els.messages.querySelector(`[data-msg-index="${idx}"]`);

      if (target) {

        target.scrollIntoView({ behavior: "smooth", block: "start" });

      }

    });

  });

}



function renderToolLog() {

  if (!els.toolLogList || !els.toolLogSummary) return;

  const items = state.messages

    .map((msg, index) => ({ msg, index }))

    .filter(({ msg }) => msg.role === "tool-call" || msg.role === "tool-result");



  if (items.length === 0) {

    els.toolLogSummary.textContent = "暂无工具动作";

    els.toolLogList.innerHTML = `<div class="muted-line">工具调用、搜索、读文件、修改确认和命令执行会显示在这里。</div>`;

    return;

  }



  const callCount = items.filter(({ msg }) => msg.role === "tool-call").length;

  const resultCount = items.filter(({ msg }) => msg.role === "tool-result").length;

  const errorCount = items.filter(({ msg }) => (getMsgText(msg)).startsWith("工具执行失败")).length;

  els.toolLogSummary.textContent = `${items.length} 条工具动作：${callCount} 次调用，${resultCount} 条结果${errorCount ? `，${errorCount} 条失败` : ""}`;

  els.toolLogList.innerHTML = items

    .map(({ msg, index }) => {

      const meta = msg.meta || {};

      const action = meta.action || meta.tool?.action || "tool";

      const isResult = msg.role === "tool-result";

      const isError = isResult && (getMsgText(msg)).startsWith("工具执行失败");

      const kind = isResult ? "result" : "call";

      const detail = getToolLogDetail(msg);

      const source = meta.native ? "native" : "text";

      return `

        <div class="tool-log-item ${kind} ${isError ? "error" : ""}">

          <div class="tool-log-title">${escapeHtml(action)}</div>

          <div class="tool-log-detail" title="${escapeHtml(detail)}">#${index + 1} ${escapeHtml(detail)}</div>

          <span class="tool-log-pill">${isError ? "error" : kind} · ${source}</span>

        </div>

      `;

    })

    .join("");

}



function renderAssistantContent(content) {
  return `<div class="bubble">${renderMarkdownLite(content)}</div>`;
}



function renderRoundLimitMessage() {

  return `

    <article class="msg assistant">

      <div class="round-limit-card">

        <div>

          <strong>工具调用较多，已暂停等待继续。</strong>

          <p>当前轮次已达到安全上限，避免 Agent 长时间自动执行。确认方向没问题后，可以让它继续接着处理。</p>

        </div>

        <button class="continue-agent-btn" type="button">继续处理</button>

      </div>

    </article>

  `;

}



function bindMessageActions() {

  document.querySelectorAll(".continue-agent-btn").forEach((btn) => {

    btn.addEventListener("click", () => continueAgentRun());

  });

}



async function continueAgentRun() {

  if (state.isStreaming) return;

  state.messages = state.messages.filter((msg) => msg.meta?.kind !== "tool-round-limit");

  renderMessages();

  await saveCurrentSession();

  setStreaming(true);

  try {

    await runAgentLoop();

  } catch (err) {

    if (err.name === "AbortError") {

      state.messages.forEach((msg) => { msg.streaming = false; });

      const last = state.messages.at(-1);

      if (last?.role === "assistant") last.content = `${last.content || ""}\n\n[已暂停输出]`;

      renderMessages();

      await saveCurrentSession();

    } else {

      state.messages = state.messages.filter((msg) => !msg.streaming);

      appendSystemError(err.message);

    }

  } finally {

    state.abortController = null;

    setStreaming(false);

  }

}



function getPinnedSessions() {

  try { return JSON.parse(localStorage.getItem("agent-lite-pinned") || "[]"); } catch { return []; }

}

function togglePinSession(id) {

  const pinned = getPinnedSessions();

  const idx = pinned.indexOf(id);

  if (idx >= 0) pinned.splice(idx, 1); else pinned.unshift(id);

  localStorage.setItem("agent-lite-pinned", JSON.stringify(pinned));

  renderSessions();

}



function renderSessions() {

  if (state.sessions.length === 0) {

    els.sessionList.innerHTML = `<div class="muted-line" style="padding:12px;">暂无历史会话</div>`;

    return;

  }

  const pinned = getPinnedSessions();

  const sorted = [...state.sessions].sort((a, b) => {

    const pa = pinned.includes(a.id) ? 0 : 1;

    const pb = pinned.includes(b.id) ? 0 : 1;

    if (pa !== pb) return pa - pb;

    return 0;

  });

  els.sessionList.innerHTML = sorted

    .map((session) => {

      const date = session.updatedAt ? session.updatedAt.slice(0, 10).replaceAll("-", "/") : "";

      return `

        <button class="session-item ${session.id === state.sessionId ? "active" : ""}" type="button" data-session-id="${session.id}">

          <span>${escapeHtml(session.title || "未命名会话")}</span>

          <small>${date}</small>

        </button>

      `;

    })

    .join("");

  document.querySelectorAll(".session-item").forEach((btn) => {

    btn.addEventListener("click", () => loadSession(btn.dataset.sessionId));

  });

}



function serializeSessionMessages(messages = state.messages) {

  return messages.map((msg) => ({

    role: msg.role,

    content: msg.content || "",

    thought: msg.thought || "",

    meta: msg.meta || {},

    _images: msg._images || undefined,

  }));

}



async function renameSession(sessionId, title) {

  const nextTitle = title.trim();

  if (!nextTitle) return;

  const isCurrent = sessionId === state.sessionId;

  const session = isCurrent ? null : await apiJson(`/api/sessions/${encodeURIComponent(sessionId)}`);

  await apiJson(`/api/sessions/${encodeURIComponent(sessionId)}`, {

    method: "PUT",

    body: JSON.stringify({

      title: nextTitle,

      messages: isCurrent ? serializeSessionMessages() : serializeSessionMessages(session.messages || []),

      stats: isCurrent ? state.stats : (session.stats || {}),

    }),

  });

  if (isCurrent) els.sessionTitle.value = nextTitle;

  state.renamingSessionId = null;

  await refreshSessions();

}



async function deleteSession(sessionId) {

  const session = state.sessions.find((item) => item.id === sessionId);

  const title = session?.title || "未命名会话";

  showDeleteConfirm(sessionId, title);

}



function hideDeleteConfirm() {

  document.getElementById("deleteConfirmModal").classList.add("hidden");

}



function showDeleteConfirm(sessionId, title) {

  const modal = document.getElementById("deleteConfirmModal");

  document.getElementById("deleteConfirmText").textContent = `删除会话"${title}"？此操作不可恢复。`;

  modal.classList.remove("hidden");



  const confirmBtn = document.getElementById("confirmDeleteSession");

  const cancelBtn = document.getElementById("cancelDeleteSession");

  const closeBtn = document.getElementById("closeDeleteConfirm");



  const onModal = (e) => { if (e.target === modal) cleanup(); };



  const cleanup = () => {

    confirmBtn.removeEventListener("click", handler);

    cancelBtn.removeEventListener("click", cleanup);

    closeBtn.removeEventListener("click", cleanup);

    modal.removeEventListener("click", onModal);

    modal.classList.add("hidden");

  };



  const handler = async () => {

    cleanup();

    await apiJson(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });

    if (state.sessionId !== sessionId) {

      await refreshSessions();

      return;

    }

    state.sessionId = null;

    state.messages = [];

    state.pendingEdits = {};

    state.stats = { input: 0, output: 0, cache: 0 };

    els.sessionTitle.value = "";

    localStorage.removeItem("agent-lite-last-session");

    await refreshSessions();

    renderMessages();

    updateSendButtonState();

  };



  confirmBtn.addEventListener("click", handler);

  cancelBtn.addEventListener("click", cleanup);

  closeBtn.addEventListener("click", cleanup);

  modal.addEventListener("click", onModal);

  document.addEventListener("keydown", function onEsc(e) {

    if (e.key === "Escape") { document.removeEventListener("keydown", onEsc); cleanup(); }

  });

}



function getPinnedSessions() {

  try { return JSON.parse(localStorage.getItem("agent-lite-pinned") || "[]"); } catch { return []; }

}

function togglePinSession(id) {

  const pinned = getPinnedSessions();

  const idx = pinned.indexOf(id);

  if (idx >= 0) pinned.splice(idx, 1); else pinned.unshift(id);

  localStorage.setItem("agent-lite-pinned", JSON.stringify(pinned));

  renderSessions();

}



function renderSessions() {

  if (state.sessions.length === 0) {

    els.sessionList.innerHTML = `<div class="muted-line" style="padding:12px;">暂无历史会话</div>`;

    return;

  }

  const pinned = getPinnedSessions();

  const pinnedSessions = state.sessions.filter((s) => pinned.includes(s.id));

  const unpinnedSessions = state.sessions.filter((s) => !pinned.includes(s.id));

  const sorted = [...pinnedSessions, ...unpinnedSessions];

  els.sessionList.innerHTML = sorted

    .map((session, idx) => {

      const isFirstPinned = idx === 0 && pinnedSessions.length > 0;

      const isFirstUnpinned = idx === pinnedSessions.length && unpinnedSessions.length > 0;

      const title = session.title || "未命名会话";

      const labelHtml = isFirstPinned ? `<div class="session-group-label">置顶</div>`

        : isFirstUnpinned ? `<div class="session-group-label">聊天</div>` : "";

      if (state.renamingSessionId === session.id) {

        return `

          ${labelHtml}

          <div class="session-row active" data-session-id="${escapeHtml(session.id)}">

            <input class="session-rename-inline" value="${escapeHtml(title)}" data-session-id="${escapeHtml(session.id)}" data-original="${escapeHtml(title)}" aria-label="会话名称" />

          </div>

        `;

      }

      return `

        ${labelHtml}

        <div class="session-row ${session.id === state.sessionId ? "active" : ""}" data-session-id="${escapeHtml(session.id)}">

          <button class="session-main" type="button" data-session-id="${escapeHtml(session.id)}">

            <span>${escapeHtml(title)}</span>

          </button>

          <div class="session-more-wrap">

            <button class="session-more-btn" type="button" title="更多操作" data-session-id="${escapeHtml(session.id)}">⋮</button>

          </div>

        </div>

      `;

    })

    .join("");



  document.querySelectorAll(".session-main").forEach((btn) => {

    btn.addEventListener("click", () => loadSession(btn.dataset.sessionId));

  });

  // Session more menu - render to body to avoid overflow clipping

  document.querySelectorAll(".session-more-btn").forEach((btn) => {

    btn.addEventListener("click", (e) => {

      e.stopPropagation();

      closeAllSessionMenus();

      const id = btn.dataset.sessionId;

      const rect = btn.getBoundingClientRect();

      const menu = document.createElement("div");

      menu.className = "session-more-menu";

      menu.style.position = "fixed";

      menu.style.left = (rect.right - 90) + "px";

      menu.style.top = (rect.bottom + 2) + "px";

      menu.innerHTML = `

        <button class="session-more-item pin${getPinnedSessions().includes(id) ? ' pinned' : ''}" data-action="pin">${getPinnedSessions().includes(id) ? '取消置顶' : '置顶'}</button>

        <button class="session-more-item" data-action="rename">重命名</button>

        <button class="session-more-item danger" data-action="delete">删除</button>

      `;

      menu.querySelectorAll(".session-more-item").forEach((item) => {

        item.addEventListener("click", () => {

          if (item.dataset.action === "rename") {

            state.renamingSessionId = id;

            renderSessions();

            document.querySelector(".session-rename-input")?.select();

          } else if (item.dataset.action === "pin") {

            togglePinSession(id);

          } else if (item.dataset.action === "delete") {

            deleteSession(id).catch((err) => appendSystemError(err.message));

          }

          menu.remove();

        });

      });

      document.body.appendChild(menu);

    });

  });



  document.querySelectorAll(".session-rename-inline").forEach((input) => {

    input.select();

    input.focus();

    const save = () => {

      const id = input.dataset.sessionId;

      const val = input.value.trim();

      const original = input.dataset.original || "";

      if (val && val !== original) {

        renameSession(id, val).catch(() => {});

      }

      state.renamingSessionId = null;

      renderSessions();

    };

    input.addEventListener("blur", save);

    input.addEventListener("keydown", (e) => {

      if (e.key === "Enter") { e.preventDefault(); save(); }

      if (e.key === "Escape") {

        input.value = input.dataset.original || "";

        save();

      }

    });

  });

}



function closeAllSessionMenus() {

  document.querySelectorAll(".session-more-menu").forEach((m) => m.remove());

}



async function refreshSessions() {

  const data = await apiJson("/api/sessions");

  state.sessions = data.data || [];

  renderSessions();

}



async function createSession(title = "新会话") {

  const session = await apiJson("/api/sessions", {

    method: "POST",

    body: JSON.stringify({ title }),

  });

  state.sessionId = session.id;

  state.messages = session.messages || [];

  state.pendingEdits = {};

  state.stats = { input: 0, output: 0, cache: 0 };

  els.sessionTitle.value = session.title || "新会话";

  localStorage.setItem("agent-lite-last-session", session.id);

  await refreshSessions();

  renderMessages();

  return session;

}



async function loadSession(sessionId) {

  const session = await apiJson(`/api/sessions/${encodeURIComponent(sessionId)}`);

  state.sessionId = session.id;

  state.messages = (session.messages || []).map((msg) => ({

    ...msg,

    _images: msg._images || undefined,

  }));

  state.pendingEdits = {};

  for (const msg of state.messages) {

    if (msg.role === "tool-result" && msg.meta?.pendingEditId && msg.meta?.newContent) {

      state.pendingEdits[msg.meta.pendingEditId] = {

        path: msg.meta.path,

        newContent: msg.meta.newContent,

        applied: Boolean(msg.meta.applied),

      };

    }

  }

  state.stats = session.stats || { input: 0, output: 0, cache: 0, cost: 0 };

  els.sessionTitle.value = session.title || "未命名会话";

  localStorage.setItem("agent-lite-last-session", session.id);

  renderSessions();

  renderMessages();

}



async function saveCurrentSession() {

  if (!state.sessionId) await createSession(els.sessionTitle.value || "新会话");

  await apiJson(`/api/sessions/${encodeURIComponent(state.sessionId)}`, {

    method: "PUT",

    body: JSON.stringify({

      title: els.sessionTitle.value.trim() || "未命名会话",

      messages: state.messages.map((msg) => ({

        role: msg.role,

        content: msg.content || "",

        thought: msg.thought || "",

        meta: msg.meta || {},

        _images: msg._images || undefined,

        _model: msg._model || undefined,

      })),

      stats: state.stats,

    }),

  });

  await refreshSessions();

}



function shortPath(path = "") {

  const normalized = path.replaceAll("/", "\\");

  const parts = normalized.split("\\").filter(Boolean);

  if (parts.length <= 2) return normalized || "~";

  return `~\\${parts.slice(-2).join("\\")}`;

}



async function loadConfig() {

  const config = await apiJson("/api/config");

  if (els.projectRoot) els.projectRoot.value = config.projectRoot || "";

  els.cwdPathText.textContent = config.projectRoot ? shortPath(config.projectRoot) : "~";

  els.projectRootShort.title = config.projectRoot || "点击管理项目目录";

  await loadFiles("");

}



async function saveProjectRoot(newPath) {

  const path = (newPath || (els.projectRoot ? els.projectRoot.value : "") || "").trim();

  if (!path) return;

  const config = await apiJson("/api/config", {

    method: "POST",

    body: JSON.stringify({ projectRoot: path }),

  });

  els.cwdPathText.textContent = config.projectRoot ? shortPath(config.projectRoot) : "~";

  els.projectRootShort.title = config.projectRoot || "点击管理项目目录";

  state._noProject = false;

  localStorage.removeItem("agent-lite-no-project");

  addRecentFolder(config.projectRoot);

  await loadFiles("");

  await loadProjectContext();

}



function formatSize(bytes) {

  if (bytes < 1024) return `${bytes} B`;

  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;

}



function languageFromPath(path = "") {

  const ext = path.split(".").pop()?.toLowerCase() || "";

  const map = {

    bat: "bat",

    c: "c",

    cpp: "cpp",

    cs: "csharp",

    css: "css",

    csv: "csv",

    diff: "diff",

    go: "go",

    h: "c",

    html: "html",

    java: "java",

    js: "javascript",

    json: "json",

    jsx: "jsx",

    log: "log",

    md: "markdown",

    php: "php",

    ps1: "powershell",

    py: "python",

    rb: "ruby",

    rs: "rust",

    sh: "shell",

    sql: "sql",

    ts: "typescript",

    tsx: "tsx",

    txt: "text",

    xml: "xml",

    yaml: "yaml",

    yml: "yaml",

  };

  return map[ext] || "text";

}



function makeSessionTitle(text = "") {

  const cleaned = text

    .replace(/\s+/g, " ")

    .replace(/[。！？!?]$/, "")

    .trim();

  if (!cleaned) return "新会话";

  return cleaned.length > 22 ? `${cleaned.slice(0, 22)}...` : cleaned;

}



async function generateSessionTitle(userText) {

  const model = getSelectedModel();

  const key = els.apiKey.value.trim();

  if (!model || !key) return;

  try {

    const payload = {

      model,

      stream: false,

      max_tokens: 30,

      temperature: 0.1,

      messages: [

        { role: "system", content: "你是一个标题生成器。根据用户的第一个问题，生成一个极简标题（5-15字，不要引号，直接输出标题本身）。" },

        { role: "user", content: userText.slice(0, 200) },

      ],

    };

    const baseUrl = els.baseUrl.value.trim() || "http://localhost:3000";

    const res = await fetch("/proxy/chat", {

      method: "POST",

      headers: { "Content-Type": "application/json", "X-Base-URL": baseUrl, Authorization: `Bearer ${key}` },

      body: JSON.stringify(payload),

    });

    if (res.ok) {

      const data = await res.json();

      const title = (data.choices?.[0]?.message?.content || "").replace(/[""]/g, "").trim();

      if (title && title.length >= 2) {

        els.sessionTitle.value = title.slice(0, 30);

        saveCurrentSession().catch(() => {});

      }

    }

  } catch (_) { /* ignore, fallback to makeSessionTitle */ }

}



function isAutoSessionTitle(title = "") {

  return ["", "新会话", "未命名会话"].includes(title.trim());

}



function applyPreviewWidth(width = state.previewWidth) {

  const viewportLimit = Math.max(320, window.innerWidth - 520);

  // Min 250px = title(~60) + gap + language(88) + refresh(28) + copy(28) + padding
  const next = Math.min(Math.max(Number(width) || 420, 250), viewportLimit);

  state.previewWidth = next;

  document.documentElement.style.setProperty("--preview-width", `${next}px`);

  localStorage.setItem("agent-lite-preview-width", String(next));

}



function applySidebarWidth(width = state.sidebarWidth) {

  const next = Math.min(Math.max(Number(width) || 264, 200), 480);

  state.sidebarWidth = next;

  document.documentElement.style.setProperty("--sidebar-width", `${next}px`);

  localStorage.setItem("agent-lite-sidebar-width", String(next));

}



function applySidebarSessionHeight(height = state.sidebarSessionHeight) {

  const explorerEl = document.querySelector(".explorer");

  if (explorerEl?.classList.contains("collapsed")) return;

  const sidebar = document.querySelector(".pi-sidebar");

  const min = 60;

  const max = Math.max(120, sidebar.clientHeight - 260);

  const next = Math.min(Math.max(Number(height) || 230, min), max);

  state.sidebarSessionHeight = next;

  document.documentElement.style.setProperty("--explorer-height", `${next}px`);

  localStorage.setItem("agent-lite-session-height", String(next));

}



function renderPreviewNotice(title, body = "") {

  els.filePreview.className = "file-preview empty";

  document.getElementById("previewTitle").textContent = title;

  document.getElementById("previewMeta").textContent = body || "";

  els.previewLanguage.textContent = "";

  els.refreshPreview.disabled = true;

  els.copyPreview.disabled = true;

  els.filePreview.innerHTML = `

    <div class="preview-notice">

      <strong>${escapeHtml(title)}</strong>

      ${body ? `<span>${escapeHtml(body)}</span>` : ""}

    </div>

  `;

}



function renderCodePreview(content = "") {

  const normalized = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  const lines = normalized.length ? normalized.split("\n") : [""];

  const lang = languageFromPath(state.previewPath || "");

  const doHighlight = _resolveSyntaxPatterns(lang);

  els.filePreview.className = "file-preview code-preview";

  els.filePreview.innerHTML = lines

    .map((line, index) => {

      const highlighted = doHighlight ? highlightSyntax(line, lang) : escapeHtml(line);

      return `

      <div class="code-line" data-line="${index + 1}">

        <span class="line-no">${index + 1}</span>

        <span class="line-code">${highlighted || " "}</span>

      </div>

    `;})

    .join("");

  // Click line to highlight

  els.filePreview.querySelectorAll(".code-line").forEach((el) => {

    el.addEventListener("click", () => {

      els.filePreview.querySelectorAll(".code-line").forEach((e) => e.classList.remove("active-line"));

      el.classList.add("active-line");

      const lineNum = el.dataset.line;

      copyText(`${state.previewPath}:${lineNum}`);

    });

  });

}



function renderImagePreview(content = "", mime = "image/png") {

  els.filePreview.className = "file-preview image-preview";

  els.filePreview.innerHTML = `<img src="data:${mime};base64,${content}" alt="preview" />`;

}




function markActiveFile() {

  document.querySelectorAll(".file-item").forEach((btn) => {

    btn.classList.toggle("active", btn.dataset.path === state.previewPath);

  });

}



async function copyText(text = "") {

  try {

    await navigator.clipboard.writeText(text);

    return true;

  } catch {

    const textarea = document.createElement("textarea");

    textarea.value = text;

    textarea.setAttribute("readonly", "");

    textarea.style.position = "fixed";

    textarea.style.left = "-9999px";

    document.body.appendChild(textarea);

    textarea.select();

    const ok = document.execCommand("copy");

    textarea.remove();

    return ok;

  }

}



function insertPromptText(text) {

  const current = els.prompt.value.trimEnd();

  els.prompt.value = current ? `${current}\n${text}` : text;

  els.prompt.focus();

  els.prompt.selectionStart = els.prompt.value.length;

  els.prompt.selectionEnd = els.prompt.value.length;

  updateSendButtonState();

}



function arrayBufferToBase64(buffer) {

  const bytes = new Uint8Array(buffer);

  const chunkSize = 0x8000;

  let binary = "";

  for (let index = 0; index < bytes.length; index += chunkSize) {

    binary += String.fromCharCode.apply(null, bytes.subarray(index, index + chunkSize));

  }

  return btoa(binary);

}



async function uploadAttachment(file) {

  const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());

  return apiJson("/api/attachments", {

    method: "POST",

    body: JSON.stringify({

      name: file.name,

      contentBase64,

    }),

  });

}



async function pickProjectFile() {

  if (!els.filePicker) return;

  els.filePicker.value = "";

  els.filePicker.click();

}



async function resolvePickedFile(file) {

  if (!file) return;

  if (els.attachFile) els.attachFile.disabled = true;

  try {

    const data = await uploadAttachment(file);

    insertPromptText(data.path);

  } catch (err) {

    const message = err.message || "选择文件失败";

    alert(message);

  } finally {

    if (els.attachFile) els.attachFile.disabled = false;

  }

}



function renderFileTree() {

  if (state._noProject) {

    els.fileTree.innerHTML = `<div class="muted-line" style="padding:12px;">未选择项目目录</div>`;

    els.goUp.disabled = true;

    els.newFolderBtn.disabled = true;

    els.refreshFiles.disabled = true;

    return;

  }

  els.goUp.disabled = false;

  els.newFolderBtn.disabled = false;

  els.refreshFiles.disabled = false;

  const query = els.fileSearch.value.trim().toLowerCase();

  const items = state._fileItems || [];

  const filtered = query ? items.filter((item) => item.name.toLowerCase().includes(query)) : items;

  els.fileTree.innerHTML = filtered.length

    ? filtered.map((item) => `

      <div class="file-item-row ${item.path === state.previewPath ? "active" : ""}">

        <button class="file-item ${item.type}" type="button" data-path="${escapeHtml(item.path)}" data-type="${item.type}">

          <span class="file-name">${item.type === "dir" ? "📂 " : ""}${escapeHtml(item.name)}</span>

          <small>${item.type === "dir" ? "" : formatSize(item.size || 0)}</small>

        </button>

        <button class="file-at-btn" type="button" data-path="${escapeHtml(item.path)}" title="引用到输入框">@</button>

      </div>

    `).join("")

    : `<div class="muted-line" style="padding:8px;">${query ? "无匹配文件" : "该目录为空"}</div>`;



  document.querySelectorAll(".file-item").forEach((btn) => {

    btn.addEventListener("click", () => {

      if (btn.dataset.type === "dir") {

        loadFiles(btn.dataset.path);

      } else {

        loadFile(btn.dataset.path);

      }

    });

  });



  document.querySelectorAll(".file-at-btn").forEach((btn) => {

    btn.addEventListener("click", (e) => {

      e.stopPropagation();

      const path = btn.dataset.path;

      insertPromptText(`@${path} `);

    });

  });

}



async function loadFiles(path = state.currentDir) {

  const data = await apiJson(`/api/files?path=${encodeURIComponent(path || "")}`);

  state.currentDir = data.path || "";

  els.filePathBar.textContent = state.currentDir ? `/${state.currentDir}` : "/";

  els.cwdPathText.textContent = shortPath(data.root || "");

  els.fileSearch.value = "";

  state._fileItems = data.items || [];

  els.goUp.disabled = !state.currentDir;

  renderFileTree();

}



async function loadFile(path, mtime) {

  const data = await apiJson(`/api/file?path=${encodeURIComponent(path)}`);

  els.workbench.classList.add("preview-open");

  localStorage.setItem("agent-lite-preview-open", "1");

  localStorage.setItem("agent-lite-preview-path", path);

  state.previewPath = data.path || path;

  state._previewMtime = data.updatedAt || "";

  const language = languageFromPath(state.previewPath);

  markActiveFile();

  els.previewTitle.textContent = data.name || "File";

  els.previewMeta.textContent = `${data.path} · ${formatSize(data.size || 0)}${data.truncated ? " · truncated" : ""}`;

  els.previewLanguage.textContent = language;

  els.refreshPreview.disabled = false;

  // Image preview — fetch raw base64 from backend

  const ext = (data.name || "").split(".").pop()?.toLowerCase();

  if (ext && /^(png|jpg|jpeg|gif|webp|svg|bmp|ico)$/i.test(ext)) {

    try {

      const raw = await apiJson(`/api/file?path=${encodeURIComponent(path)}&raw=1`);

      state.previewContent = raw.content || "";

      renderImagePreview(state.previewContent, raw.mime || `image/${ext === "jpg" ? "jpeg" : ext}`);

    } catch (_) {

      renderPreviewNotice("加载失败", "无法读取图片文件");

    }

    els.copyPreview.disabled = true;

    return;

  }

  if (data.binary) {

    state.previewContent = "";

    renderPreviewNotice("二进制文件", "无法预览。图片/数据库/压缩包/可执行文件");

    els.copyPreview.disabled = true;

    return;

  }

  state.previewContent = data.content || "";

  if (state.previewContent) {

    renderCodePreview(state.previewContent);

  } else {

    renderPreviewNotice("空文件", "暂无文本内容");

  }

  els.copyPreview.disabled = false;

  // Start auto-refresh polling

  startPreviewAutoRefresh();

}



let _previewPollTimer = null;

function startPreviewAutoRefresh() {

  clearInterval(_previewPollTimer);

  _previewPollTimer = setInterval(async () => {

    if (!state.previewPath || !els.workbench.classList.contains("preview-open")) return;

    try {

      const data = await apiJson(`/api/file?path=${encodeURIComponent(state.previewPath)}`);

      if (data.updatedAt && data.updatedAt !== state._previewMtime) {

        if (!data.binary) {

          state.previewContent = data.content || "";

          state._previewMtime = data.updatedAt;

          els.previewMeta.textContent = `${data.path} · ${formatSize(data.size || 0)} (已自动更新)`;

          renderCodePreview(state.previewContent);

        }

      }

    } catch (_) { /* file deleted or renamed, stop polling */ }

  }, 3000);

}



async function refreshModels() {

  const keys = getApiKeys();

  if (keys.length === 0) {

    alert("请先输入 API Key");

    return;

  }



  els.refreshModelsBtn.disabled = true;

  const baseUrl = els.baseUrl.value.trim() || "http://localhost:3000";

  const allModels = new Set();

  const modelKeyMap = {};

  let successCount = 0;



  for (const key of keys) {

    try {

      const res = await fetch("/proxy/models", { headers: { Authorization: `Bearer ${key}`, "X-Base-URL": baseUrl } });

      const data = await res.json();

      if (res.ok && data.data) {

        successCount++;

        for (const item of data.data) {

          if (item.id) {

            const cleanId = item.id.replace(/^models\//, "");

            // Skip non-chat models (image/video/audio/embedding gen)

            const skipPattern = /imagen|veo|lyria|chirp|embedding|tts|speech|whisper|dall|flux|stable-diffusion/i;

            if (skipPattern.test(cleanId)) continue;

            allModels.add(cleanId);

            if (!modelKeyMap[cleanId]) modelKeyMap[cleanId] = key;

          }

        }

      }

    } catch (_) { /* try next key */ }

  }

  state.modelKeyMap = modelKeyMap;



  if (allModels.size === 0) {

    alert(`未获取到模型列表（尝试了 ${keys.length} 个 key）`);

    els.refreshModelsBtn.disabled = false;

    return;

  }



  try {

    const models = [...allModels].sort((a, b) => a.localeCompare(b));

    // Group models by provider

    const PROVIDER_PATTERNS = [

      ["DeepSeek", /^deepseek|^deep\b/i],

      ["OpenAI", /^gpt|^o1|^o3|^openai|^davinci|^text-davinci/i],

      ["Anthropic", /^claude|^anthropic/i],

      ["Google", /^gemini|^gemma|^palm|^nano-banana|^imagen|^veo|^lyria|^chirp/i],

      ["通义千问", /^qwen|^tongyi/i],

      ["智谱", /^glm|^chatglm/i],

      ["Moonshot", /^moonshot|^kimi/i],

      ["零一万物", /^yi-/i],

      ["百度", /^ernie|^baidu/i],

      ["腾讯", /^hunyuan/i],

      ["Mistral", /^mistral|^mixtral/i],

      ["Meta", /^llama|^meta/i],

    ];

    const groups = {};

    for (const id of models) {

      let provider = "其他";

      for (const [name, re] of PROVIDER_PATTERNS) {

        if (re.test(id)) { provider = name; break; }

      }

      if (!groups[provider]) groups[provider] = [];

      groups[provider].push(id);

    }



    // Pill dropdown with optgroups

    let dropdownHtml = "";

    for (const [provider, ids] of Object.entries(groups)) {

      dropdownHtml += `<div class="model-pill-optgroup">`;

      dropdownHtml += `<div class="model-pill-optgroup-label">${escapeHtml(provider)}</div>`;

      dropdownHtml += ids.map((id) => `<button class="model-pill-option" type="button" data-model="${escapeHtml(id)}">${escapeHtml(id)}</button>`).join("");

      dropdownHtml += `</div>`;

    }

    els.modelPillDropdown.innerHTML = dropdownHtml;



    // Modal display list

    let listHtml = "";

    for (const [provider, ids] of Object.entries(groups)) {

      listHtml += `<div class="model-provider-group"><span class="model-provider-label">${escapeHtml(provider)}</span>`;

      listHtml += ids.map((id) => `<span class="model-name-tag">${escapeHtml(id)}</span>`).join("");

      listHtml += `</div>`;

    }

    els.modelListBox.innerHTML = listHtml;



    const savedModel = localStorage.getItem("agent-lite-model");

    if (savedModel && models.includes(savedModel)) {

      setSelectedModel(savedModel);

    }

  } catch (err) {

    alert(err.message);

  } finally {

    els.refreshModelsBtn.disabled = false;

  }

}



function appendSystemError(message) {

  state.messages.push({ role: "assistant", content: `请求失败：${message}` });

  renderMessages();

}



function setStreaming(active) {

  state.isStreaming = active;

  els.stopBtn.disabled = !active;

  updateSendButtonState();

  if (active) startLiveTimer(); else stopLiveTimer();

}



function startLiveTimer() {

  if (state._timerInterval) clearInterval(state._timerInterval);

  state.responseStartTime = Date.now();

  els.liveTimer.textContent = "0s";

  els.liveTimer.classList.add("visible");

  state._timerInterval = setInterval(() => {

    if (!state.isStreaming) return;

    const elapsed = Math.floor((Date.now() - state.responseStartTime) / 1000);

    let display;

    if (elapsed < 60) display = `${elapsed}s`;

    else if (elapsed < 3600) display = `${Math.floor(elapsed/60)}m ${elapsed%60}s`;

    else display = `${Math.floor(elapsed/3600)}h ${Math.floor((elapsed%3600)/60)}m`;

    state._timerDisplay = display;

    // Update in-message timer if visible

    const timer = document.querySelector(".streaming-timer");

    if (timer && timer.textContent !== display) timer.textContent = display;

  }, 200);

}



function stopLiveTimer() {

  state._timerDisplay = null;

  if (state._timerInterval) { clearInterval(state._timerInterval); state._timerInterval = null; }

  if (state.responseStartTime) {

    const elapsed = Math.floor((Date.now() - state.responseStartTime) / 1000);

    let display;

    if (elapsed < 3) { els.liveTimer.classList.remove("visible"); state.responseStartTime = null; return; }

    if (elapsed < 60) display = `${elapsed}s`;

    else if (elapsed < 3600) display = `${Math.floor(elapsed/60)}m ${elapsed%60}s`;

    else display = `${Math.floor(elapsed/3600)}h ${Math.floor((elapsed%3600)/60)}m`;

    els.liveTimer.innerHTML = `<svg class="stat-icon stat-time-svg" viewBox="0 0 1024 1024" width="13" height="13"><path d="M711.7 655.4c-5.1 0-10.2-1.5-14.8-4.1l-199.7-112.6c-9.7-5.6-15.9-15.9-15.9-26.6V276.5c0-16.9 13.8-30.7 30.7-30.7s30.7 13.8 30.7 30.7v217.6l183.8 103.9c14.8 8.2 20 27.1 11.8 42-5.6 9.7-15.9 15.4-26.6 15.4z" fill="currentColor"/><circle cx="512" cy="512" r="378.9" fill="none" stroke="currentColor" stroke-width="61.4"/></svg> ${display}`;

    state.responseStartTime = null;

    // Attach time to last assistant message

    const lastMsg = state.messages.at(-1);

    if (lastMsg && lastMsg.role === "assistant" && !lastMsg.streaming) {

      lastMsg._responseTime = display;

      lastMsg.meta = { ...(lastMsg.meta || {}), _responseTime: display };

      renderMessages();

    }

    // Keep visible then fade

    setTimeout(() => { els.liveTimer.classList.remove("visible"); }, 10000);

  }

}



function updateSendButtonState() {

  const hasContent = els.prompt.value.trim().length > 0 || state.attachedImages.length > 0;

  els.sendBtn.classList.toggle("ready", hasContent && !state.isStreaming);
  els.sendBtn.classList.toggle("running", state.isStreaming);
  els.sendBtn.disabled = !hasContent && !state.isStreaming;
  els.sendBtn.title = state.isStreaming ? "暂停输出" : (hasContent ? "发送消息 (Enter 排队)" : "请输入内容");

}



// ── Image attachments ──



function addImage(name, base64, mime) {

  if (state.attachedImages.length >= 6) return;

  state.attachedImages.push({ name, base64, mime: mime || "image/png" });

  renderImageThumbs();

  updateSendButtonState();

}



function removeImage(index) {

  state.attachedImages.splice(index, 1);

  renderImageThumbs();

  updateSendButtonState();

}



function renderImageThumbs() {

  let container = document.getElementById("imageThumbs");

  if (!container) {

    container = document.createElement("div");

    container.id = "imageThumbs";

    container.className = "image-thumbs";

    els.chatForm.insertBefore(container, els.chatForm.querySelector(".composer-bar"));

  }

  if (state.attachedImages.length === 0) {

    container.remove();

    return;

  }

  container.innerHTML = state.attachedImages.map((img, i) => `

    <div class="img-thumb">

      <img src="data:${img.mime};base64,${img.base64}" alt="${escapeHtml(img.name)}" />

      <button class="img-thumb-remove" type="button" title="移除" data-index="${i}">×</button>

    </div>

  `).join("");

  container.querySelectorAll(".img-thumb-remove").forEach((btn) => {

    btn.addEventListener("click", () => removeImage(parseInt(btn.dataset.index)));

  });

}



async function handleImageFile(file) {

  if (!file.type.startsWith("image/")) return;

  const base64 = await compressImage(file);

  addImage(file.name, base64, file.type);

}



async function compressImage(file, maxW = 1024, quality = 0.7) {

  return new Promise((resolve) => {

    const img = new Image();

    const url = URL.createObjectURL(file);

    img.onload = () => {

      URL.revokeObjectURL(url);

      let w = img.width, h = img.height;

      if (w > maxW || h > maxW) {

        const ratio = maxW / Math.max(w, h);

        w = Math.round(w * ratio);

        h = Math.round(h * ratio);

      }

      const canvas = document.createElement("canvas");

      canvas.width = w; canvas.height = h;

      const ctx = canvas.getContext("2d");

      ctx.drawImage(img, 0, 0, w, h);

      const mime = file.type === "image/png" ? "image/jpeg" : file.type;

      resolve(canvas.toDataURL(mime, quality).split(",")[1]);

    };

    img.src = url;

  });

}



async function handleImagePaste(e) {

  const items = e.clipboardData?.items;

  if (!items) return;

  for (const item of items) {

    if (item.type.startsWith("image/")) {

      e.preventDefault();

      handleImageFile(item.getAsFile());

    }

  }

}



function handleImageDrop(e) {

  const files = e.dataTransfer?.files;

  if (!files) return;

  for (const file of files) {

    if (file.type.startsWith("image/")) {

      e.preventDefault();

      handleImageFile(file);

    }

  }

}



function updateAssistantMessage(index, rawContent, streaming = true) {

  const { thought, content } = splitThoughtContent(rawContent);

  const previous = state.messages[index] || {};

  state.messages[index] = {

    ...previous,

    role: "assistant",

    thought,

    content: content || " ",

    streaming,

  };

  renderMessages();

}



function parseSseLine(line) {

  if (!line.startsWith("data:")) return null;

  const payload = line.slice(5).trim();

  if (!payload || payload === "[DONE]") return payload || null;

  try {

    return JSON.parse(payload);

  } catch {

    return null;

  }

}



function updateUsage(usage) {

  if (!usage) return;

  state.stats.input += usage.prompt_tokens || 0;

  state.stats.output += usage.completion_tokens || 0;

  state.stats.cache += usage.prompt_cache_hit_tokens || usage.cache_read_tokens || 0;

  if (state.responseUsage) {

    state.responseUsage.input += usage.prompt_tokens || 0;

    state.responseUsage.output += usage.completion_tokens || 0;

    state.responseUsage.cache += usage.prompt_cache_hit_tokens || usage.cache_read_tokens || 0;

  }

}



function getNativeTools() {

  if (els.toolPreset.value === "off") return [];

  const allowed = getAllowedToolNames();

  return nativeTools.filter((tool) => allowed.has(tool.function?.name));

}



function getPermissionProfile() {

  return getPermLevel() || state.permissionProfile || "accept";

}



function getAllowedToolNames() {

  const permissionProfile = getPermissionProfile();

  const base = new Set(toolPolicy[permissionProfile] || toolPolicy.confirm);

  if (els.toolPreset.value === "full" && permissionProfile !== "read") {

    base.add("run_command");

  }

  return base;

}



function isToolAllowed(action) {

  return getAllowedToolNames().has(action);

}



function shouldAskBeforeTool(action) {

  const profile = getPermissionProfile();

  if (profile === "bypass") return false;

  if (profile === "plan") return false; // 计划模式允许的工具都不会弹窗

  // accept mode: ask for destructive operations

  return action === "run_command" || action === "write_file" || action === "delete_file";

}



function describeToolForConfirm(tool) {

  if (tool.action === "run_command") return `命令：${tool.command || ""}`;

  if (tool.path) return `文件：${tool.path}`;

  if (tool.query) return `搜索：${tool.query}`;

  return JSON.stringify(tool, null, 2);

}



function showInlineConfirm(tool) {

  return new Promise((resolve) => {

    const action = tool.action || "tool";

    const icons = { run_command: "⚡", write_file: "📝", delete_file: "🗑️" };

    const icon = icons[action] || "🔧";

    const detail = describeToolForConfirm(tool);

    const id = `confirm-${Date.now()}`;

    const html = `

      <div class="inline-confirm" id="${id}">

        <div class="inline-confirm-icon">${icon}</div>

        <div class="inline-confirm-body">

          <strong>Agent 请求执行：${escapeHtml(action)}</strong>

          <span>${escapeHtml(detail)}</span>

        </div>

        <div class="inline-confirm-actions">

          <button class="inline-confirm-accept" type="button">允许</button>

          <button class="inline-confirm-reject" type="button">拒绝</button>

        </div>

      </div>`;

    els.messages.insertAdjacentHTML("beforeend", html);

    els.messages.scrollTop = els.messages.scrollHeight;



    const card = document.getElementById(id);

    card.querySelector(".inline-confirm-accept").addEventListener("click", () => {

      card.classList.add("resolved", "accepted");

      setTimeout(() => card.remove(), 300);

      resolve(true);

    });

    card.querySelector(".inline-confirm-reject").addEventListener("click", () => {

      card.classList.add("resolved", "rejected");

      setTimeout(() => card.remove(), 300);

      resolve(false);

    });

  });

}



function parseJsonLoose(text = "{}") {

  if (typeof text === "object" && text !== null) return text;

  try {

    return JSON.parse(text || "{}");

  } catch {

    return {};

  }

}



function buildNativeToolCallMessage(toolCall) {

  return {

    id: toolCall.id || `call_${Date.now()}`,

    type: toolCall.type || "function",

    function: {

      name: toolCall.function?.name || toolCall.name || "",

      arguments: toolCall.function?.arguments || toolCall.arguments || "{}",

    },

  };

}



function normalizeNativeToolCall(call) {

  const name = call?.function?.name || call?.name || "";

  const args = parseJsonLoose(call?.function?.arguments || call?.arguments || "{}");

  return {

    ...args,

    action: name,

    _native: true,

    _toolCallId: call?.id || `call_${Date.now()}_${Math.random().toString(16).slice(2)}`,

  };

}



function mergeToolCallDelta(map, part) {

  const index = Number.isInteger(part.index) ? part.index : map.size;

  const existing = map.get(index) || {

    id: "",

    type: "function",

    function: { name: "", arguments: "" },

  };

  if (part.id) existing.id = part.id;

  if (part.type) existing.type = part.type;

  if (part.function?.name) existing.function.name = part.function.name;

  if (part.function?.arguments) existing.function.arguments += part.function.arguments;

  map.set(index, existing);

}



function normalizeToolCallList(map) {

  return [...map.entries()]

    .sort((a, b) => a[0] - b[0])

    .map(([, call]) => buildNativeToolCallMessage(call))

    .filter((call) => call.function.name);

}



function shouldRetryWithoutNativeTools(errorText = "") {

  return /tool|function|tool_choice|unsupported|invalid|upstream error|do request failed|request failed/i.test(errorText);

}



function mapMessageForApi(msg, includeNativeTools = true) {

  if (msg.role === "assistant") {

    const toolCalls = includeNativeTools ? (msg.meta?.toolCalls || []) : [];

    if (toolCalls.length > 0) {

      return {

        role: "assistant",

        content: getMsgText(msg),

        tool_calls: toolCalls.map(buildNativeToolCallMessage),

      };

    }

    return { role: "assistant", content: getMsgText(msg) };

  }

  if (msg.role === "tool-call") {

    return null;

  }

  if (msg.role === "tool-result") {

    if (includeNativeTools && msg.meta?.toolCallId) {

      return {

        role: "tool",

        tool_call_id: msg.meta.toolCallId,

        content: getMsgText(msg),

      };

    }

    return { role: "user", content: `【工具结果】\n${getMsgText(msg)}` };

  }

  // User messages may have array content (text + images)

  if (msg.role === "user") {

    const content = msg.content || "";

    if (Array.isArray(content)) {

      return { role: "user", content };

    }

    return { role: "user", content };

  }

  return { role: "user", content: getMsgText(msg) };

}



async function callModelOnce(assistantIndex, useNativeTools = true) {

  const model = getSelectedModel();

  const tools = useNativeTools ? getNativeTools() : [];

  const payload = {

    model,

    stream: true,

    temperature: Number(els.temperature.value || 0.2),

    max_tokens: getEffectiveMaxTokens(model),

    messages: [

      { role: "system", content: getSystemPrompt() },

      ...(function buildMessages() {

        const result = [];

        let lastAssistantToolCallIds = new Set();

        for (const msg of state.messages) {

          if (msg.streaming) continue;

          const mapped = mapMessageForApi(msg, tools.length > 0);

          if (!mapped) {

            // tool-call messages are filtered out, but we still track them

            if (msg.role === "tool-call" && msg.meta?.toolCallId) {

              lastAssistantToolCallIds.add(msg.meta.toolCallId);

            }

            continue;

          }

          // Validate: if this is a tool message, it must follow an assistant with matching tool_calls

          if (mapped.role === "tool" && !lastAssistantToolCallIds.has(mapped.tool_call_id)) {

            // Downgrade to user text — orphaned tool result

            result.push({ role: "user", content: `【工具结果】\n${mapped.content || ""}` });

            continue;

          }

          result.push(mapped);

          // Track tool_calls from assistant messages

          if (mapped.role === "assistant" && mapped.tool_calls) {

            lastAssistantToolCallIds = new Set(mapped.tool_calls.map((tc) => tc.id));

          } else if (mapped.role === "assistant") {

            lastAssistantToolCallIds = new Set();

          }

        }

        return result;

      })(),

    ],

  };

  if (tools.length > 0) {

    payload.tools = tools;

    payload.tool_choice = "auto";

  }



  // Thinking / reasoning control

  const thinkingMode = getThinkingLevel();

  if (/claude|opus|sonnet|haiku/i.test(model)) {

    if (thinkingMode === "off") {

      payload.thinking = { type: "disabled" };

    } else {

      const budgets = { auto: 4000, high: 8000, max: 16000 };

      payload.thinking = { type: "enabled", budget_tokens: budgets[thinkingMode] || 4000 };

    }

  } else if (/o1|o3|o4/i.test(model)) {

    if (thinkingMode !== "off") {

      payload.reasoning_effort = thinkingMode === "max" ? "high" : thinkingMode === "high" ? "medium" : "low";

    }

  } else if (/gemini|nano-banana/i.test(model)) {

    // Gemini 3+: reasoning_effort maps to thinkingLevel (low/medium/high)

    const efforts = { high: "high", max: "high" };

    if (efforts[thinkingMode]) {

      payload.reasoning_effort = efforts[thinkingMode];

    }

    // off/auto: don't send reasoning_effort (off disables, auto uses model default)

  }



  state.abortController = new AbortController();

  const FETCH_TIMEOUT_MS = 180000;  // 3 min safety net

  const baseUrl = els.baseUrl.value.trim() || "http://localhost:3000";

  const fallbackKeys = getFallbackKeys(model);

  const totalKeys = fallbackKeys.length;

  let res;

  let lastError = "";



  for (let ki = 0; ki < fallbackKeys.length; ki++) {

    const key = fallbackKeys[ki];

    for (let attempt = 0; attempt < 3; attempt++) {

      try {

        const timeoutId = setTimeout(() => state.abortController.abort(), FETCH_TIMEOUT_MS);
        res = await fetch("/proxy/chat", {

          method: "POST",

          headers: {

            "Content-Type": "application/json",

            "X-Base-URL": baseUrl,

            Authorization: `Bearer ${key}`,

          },

          body: JSON.stringify(payload),

          signal: state.abortController.signal,

        });

        clearTimeout(timeoutId);
        if (res.ok) break;

        lastError = `HTTP ${res.status}`;

        // Don't retry same key on 4xx (bad request), but allow fallback to next key

        if (res.status >= 400 && res.status < 500 && res.status !== 429) break;

      } catch (err) {

        clearTimeout(timeoutId);
        if (err.name === "AbortError") throw err;

        lastError = err.message;

      }

    }

    if (res && res.ok) break;



    // Notify user about retry / fallback

    if (ki < fallbackKeys.length - 1) {

      const msg = fallbackKeys.length > 1

        ? `请求失败（${lastError}），正在尝试下一个 key（${ki + 2}/${totalKeys}）...`

        : `请求失败（${lastError}），正在重试...`;

      state.messages.push({ role: "assistant", content: `🔄 ${msg}`, meta: { kind: "key-fallback" } });

      renderMessages();

    }

  }



  if (!res || !res.ok) {

    let errText = lastError || `HTTP ${res?.status || "error"}`;

    let errCode = "";

    try {

      if (res) {

        const data = await res.json();

        errText = data?.error?.message || data?.error || errText;

        errCode = data?.error?.code || data?.error?.type || "";

      }

    } catch {

      try { errText = res ? await res.text() : errText; } catch {}

    }

    // Retry once if New API transient "no access" error (channel flapping)

    if (errCode === "new_api_error" && errText.includes("no access to model") && !state._retriedModelAccess) {

      state._retriedModelAccess = true;

      await new Promise((r) => setTimeout(r, 2000));

      const retry = await callModelOnce(assistantIndex, useNativeTools);

      state._retriedModelAccess = false;

      return retry;

    }

    state._retriedModelAccess = false;

    state.messages = state.messages.filter((m) => m.meta?.kind !== "key-fallback");

    if (tools.length > 0 && shouldRetryWithoutNativeTools(errText)) {

      return callModelOnce(assistantIndex, false);

    }

    throw new Error(errText);

  }

  // Clean up fallback messages on success

  state.messages = state.messages.filter((m) => m.meta?.kind !== "key-fallback");



  const reader = res.body.getReader();

  const decoder = new TextDecoder();

  let buffer = "";

  let rawThought = "";

  let rawContent = "";

  const toolCallsByIndex = new Map();



  while (true) {

    const { value, done } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split(/\r?\n/);

    buffer = lines.pop() || "";



    for (const line of lines) {

      const data = parseSseLine(line);

      if (!data) continue;

      if (data === "[DONE]") {

        const finalText = rawThought ? `<think>${rawThought}</think>\n${rawContent}` : rawContent;

        const toolCalls = normalizeToolCallList(toolCallsByIndex);

        updateAssistantMessage(assistantIndex, finalText || (toolCalls.length ? "" : "(空回复)"), false);

        if (toolCalls.length) {

          state.messages[assistantIndex].meta = {

            ...(state.messages[assistantIndex].meta || {}),

            toolCalls,

          };

          renderMessages();

        }

        return { content: rawContent, toolCalls };

      }

      const delta = data.choices?.[0]?.delta || {};

      if (Array.isArray(delta.tool_calls)) {

        delta.tool_calls.forEach((part) => mergeToolCallDelta(toolCallsByIndex, part));

      }

      if (Array.isArray(data.choices?.[0]?.message?.tool_calls)) {

        data.choices[0].message.tool_calls.forEach((part, index) => mergeToolCallDelta(toolCallsByIndex, { ...part, index }));

      }

      const reasoning = delta.reasoning_content || delta.thinking || "";

      const text = delta.content || data.choices?.[0]?.message?.content || "";

      if (reasoning) rawThought += reasoning;

      if (text) rawContent += text;

      if (reasoning || text) {

        const combined = rawThought ? `<think>${rawThought}</think>\n${rawContent}` : rawContent;

        updateAssistantMessage(assistantIndex, combined, true);

      }

      if (data.usage) {

        state.lastUsage = data.usage;

        updateUsage(data.usage);

      }

    }

  }



  const finalCombined = rawThought ? `<think>${rawThought}</think>\n${rawContent}` : rawContent;

  const toolCalls = normalizeToolCallList(toolCallsByIndex);

  updateAssistantMessage(assistantIndex, finalCombined || (toolCalls.length ? "" : "(空回复)"), false);

  if (toolCalls.length) {

    state.messages[assistantIndex].meta = {

      ...(state.messages[assistantIndex].meta || {}),

      toolCalls,

    };

    renderMessages();

  }

  return { content: rawContent, toolCalls };

}



function extractToolCall(text = "") {

  const fenced = text.match(/```agent-tool\s*([\s\S]*?)```/i);

  const tagged = text.match(/<agent-tool>([\s\S]*?)<\/agent-tool>/i);

  const raw = fenced?.[1] || tagged?.[1];

  if (!raw) return null;

  try {

    return JSON.parse(raw.trim());

  } catch {

    return { action: "invalid", raw: raw.trim() };

  }

}



function stripToolBlock(text = "") {

  return text

    .replace(/```agent-tool\s*[\s\S]*?```/gi, "")

    .replace(/<agent-tool>[\s\S]*?<\/agent-tool>/gi, "")

    .trim();

}



function truncateForDisplay(text = "", max = 12000) {

  if (String(text).length <= max) return String(text);

  return `${String(text).slice(0, max)}\n\n...内容较长，已截断显示...`;

}



function formatToolCall(tool) {

  const displayTool = { ...tool };

  delete displayTool._native;

  delete displayTool._toolCallId;

  const prefix = tool._native ? "原生工具调用" : "准备调用工具";

  return `${prefix}：${tool.action || "unknown"}\n\n\`\`\`json\n${JSON.stringify(displayTool, null, 2)}\n\`\`\``;

}



function formatToolResult(result) {

  if (!result.ok) {

    return `工具执行失败：${result.error || "unknown error"}`;

  }

  if (result.action === "list_files") {

    const rows = (result.items || []).map((item) => {

      const kind = item.type === "dir" ? "dir " : "file";

      const size = item.type === "dir" ? "" : ` ${formatSize(item.size || 0)}`;

      return `- [${kind}] ${item.path}${size}`;

    });

    return `目录：${result.path || "/"}\n文件数量：${result.count}\n${result.truncated ? "结果较多，已截断显示\n" : ""}\n${rows.join("\n") || "目录为空"}`;

  }

  if (result.action === "read_file") {

    const lineText = result.lineRange ? `\n行范围：${result.lineRange.start}-${result.lineRange.end}` : "";

    const lang = languageFromPath(result.path || "");

    return `已读取文件：${result.path}\n大小：${formatSize(result.size || 0)}${result.truncated ? "，内容已截断" : ""}${lineText}\n\n\`\`\`${lang}\n${truncateForDisplay(result.content || "")}\n\`\`\``;

  }

  if (result.action === "search_files") {

    const modeLabel = result.regex ? "正则搜索" : "搜索";

    const rows = (result.results || []).map((item) => {

      const matches = (item.matches || []).map((m) => {

        if (m.context) {

          return m.context.map((c) => `  L${c.line}: ${c.text}${c.line === m.line ? " ←" : ""}`).join("\n");

        }

        return `  L${m.line}: ${m.text}`;

      }).join("\n");

      return `- ${item.path}${item.nameMatch ? "（文件名匹配）" : ""}${matches ? `\n${matches}` : ""}`;

    });

    const info = [result.regex ? "模式：正则" : "", result.truncated ? "结果已截断" : ""].filter(Boolean).join(" · ");

    return `${modeLabel}关键词：${result.query}\n命中数量：${result.count}${info ? `\n${info}` : ""}\n\n${rows.join("\n") || "没有找到匹配项"}`;

  }

  if (result.action === "glob_files") {

    const rows = (result.results || []).map((item) => {

      const kind = item.type === "dir" ? "dir " : "file";

      const size = item.type === "file" ? ` ${formatSize(item.size || 0)}` : "";

      return `- [${kind}] ${item.path}${size}`;

    });

    return `glob 模式：${result.pattern}\n匹配数量：${result.count}${result.truncated ? "（结果已截断）" : ""}\n\n${rows.join("\n") || "没有匹配项"}`;

  }

  if (result.action === "propose_edit") {

    return `已生成修改方案：${result.path}\n\n\`\`\`diff\n${truncateForDisplay(result.diff || "")}\n\`\`\``;

  }

  if (result.action === "apply_edit") {

    return `已应用修改：${result.path}${result.backupPath ? `\n备份：${result.backupPath}` : ""}\n\n\`\`\`diff\n${truncateForDisplay(result.diff || "")}\n\`\`\``;

  }

  if (result.action === "run_command") {

    return `命令：${result.command}\n目录：${result.cwd || "-"}\n退出码：${result.exitCode}\n\n**STDOUT:**\n\`\`\`terminal\n${truncateForDisplay(result.stdout || "")}\n\`\`\`\n\n**STDERR:**\n\`\`\`terminal\n${truncateForDisplay(result.stderr || "")}\n\`\`\``;

  }

  if (result.action === "task") {

    const ok = result.ok !== false;

    return `${ok ? "子 Agent 执行完成" : "子 Agent 执行失败"}\n任务：${result.prompt}\n轮次：${result.rounds || "?"} 轮 · 工具调用：${result.tool_rounds || 0} 次\n\n---\n\n${result.result || "(无返回内容)"}`;

  }

  if (result.action === "write_file") {

    const backup = result.backupPath ? `\n备份：${result.backupPath}` : "";

    return `已写入文件：${result.path}\n大小：${formatSize(result.size || 0)}${backup}\n\n\`\`\`diff\n${truncateForDisplay(result.diff || "")}\n\`\`\``;

  }

  if (result.action === "delete_file") {

    return `已删除文件：${result.path}\n原大小：${formatSize(result.size || 0)}\n备份：${result.backupPath || "无"}`;

  }

  if (result.action === "web_fetch") {

    const status = result.ok ? `HTTP ${result.status}` : "Failed";

    const trunc = result.truncated ? " · 内容已截断" : "";

    return `抓取：${result.url}\n状态：${status}${trunc}\n\n${truncateForDisplay(result.content || result.error || "")}`;

  }

  return `工具结果：\n\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``;

}



async function executeToolCall(tool) {

  if (!tool || !tool.action) {

    return { ok: false, action: "invalid", error: "工具调用缺少 action" };

  }

  if (tool.action === "invalid") {

    return { ok: false, action: "invalid", error: "工具调用 JSON 无法解析", raw: tool.raw };

  }

  if (tool.action === "apply_edit") {

    return { ok: false, action: "apply_edit", error: 'apply_edit 必须由用户点击"应用修改"触发，Agent 不能自动写入文件' };

  }

  const known = new Set(nativeTools.map((item) => item.function?.name).filter(Boolean));

  if (!known.has(tool.action)) {

    return { ok: false, action: tool.action, error: `未知工具：${tool.action}` };

  }

  if (!isToolAllowed(tool.action)) {

    return { ok: false, action: tool.action, error: `当前模式或权限不允许调用 ${tool.action}` };

  }

  if (shouldAskBeforeTool(tool.action)) {

    const ok = await showInlineConfirm(tool);

    if (!ok) {

      return { ok: false, action: tool.action, error: "用户取消了本次工具调用" };

    }

  }



  try {

    const extra = {

      permissionProfile: getPermissionProfile(),

      agentMode: state.mode,

    };

    if (tool.action === "task") {

      extra.model = getSelectedModel();

    }

    const headers = {};

    if (tool.action === "task") {

      const key = getBestKey(tool.model);

      if (key) headers.Authorization = `Bearer ${key}`;

    }

    const result = await apiJson(`/api/tools/${tool.action}`, {

      method: "POST",

      headers: Object.keys(headers).length ? headers : undefined,

      body: JSON.stringify({ ...tool, ...extra }),

    });

    return result;

  } catch (err) {

    return { ok: false, action: tool.action, error: err.message };

  }

}



async function applyPendingEdit(editId) {

  const edit = state.pendingEdits[editId];

  if (!edit || edit.applied) return;

  state.confirmingEditId = editId;

  els.confirmEditPath.textContent = edit.path;

  els.confirmApplyEdit.disabled = false;

  els.confirmApplyEdit.textContent = "确认写入";

  els.confirmEditModal.classList.remove("hidden");

}



function hideApplyConfirm() {

  state.confirmingEditId = null;

  els.confirmEditModal.classList.add("hidden");

  els.confirmApplyEdit.disabled = false;

  els.confirmApplyEdit.textContent = "确认写入";

}



async function commitPendingEdit() {

  const editId = state.confirmingEditId;

  const edit = state.pendingEdits[editId];

  if (!edit || edit.applied) {

    hideApplyConfirm();

    return;

  }



  els.confirmApplyEdit.disabled = true;

  els.confirmApplyEdit.textContent = "写入中...";



  let result;

  try {

    result = await apiJson("/api/tools/apply_edit", {

      method: "POST",

      body: JSON.stringify({

        action: "apply_edit",

        path: edit.path,

        newContent: edit.newContent,

      }),

    });

  } catch (err) {

    els.confirmApplyEdit.disabled = false;

    els.confirmApplyEdit.textContent = "确认写入";

    alert(`写入失败：${err.message}`);

    return;

  }



  hideApplyConfirm();

  edit.applied = true;

  for (const msg of state.messages) {

    if (msg.meta?.pendingEditId === editId) msg.meta.applied = true;

  }

  state.messages.push({

    role: "tool-result",

    content: formatToolResult(result),

    meta: { action: "apply_edit", path: result.path, backupPath: result.backupPath },

  });

  await saveCurrentSession();

  await loadFiles().catch(() => {});

  renderMessages();

}



async function runAgentLoop() {

  state._autoCompacted = false;



  for (let round = 0; round < MAX_TOOL_ROUNDS; round += 1) {

    // Check abort signal so stop button works even mid-tool-execution
    if (state.abortController?.signal.aborted) throw new DOMException("Aborted", "AbortError");

    // Auto-compact if context exceeds 80% and not already done this run

    if (!state._autoCompacted) {

      const ctxPct = calcStats().contextPct;

      if (ctxPct >= 80 && state.messages.length >= 8) {

        const key = els.apiKey.value.trim();

        const model = getSelectedModel();

        if (key && model) {

          try {

            const result = await apiJson("/api/compact", {

              method: "POST",

              headers: { Authorization: `Bearer ${key}` },

              body: JSON.stringify({

                model,

                messages: state.messages.map((m) => ({ role: m.role, content: m.content || "" })),

              }),

            });

            if (result.ok) {

              const keepCount = result.kept || 2;

              const kept = state.messages.slice(-keepCount);

              const summaryMsg = {

                role: "assistant",

                content: `📋 **上下文已自动压缩**（${result.compressed} 条消息 → 摘要，释放 ~${formatCompact(Math.ceil((result.compressed || 0) * 3000 * 0.7))} tokens）\n\n${result.summary}`,

                meta: { kind: "compact-summary" },

              };

              const oldSummaries = state.messages.filter((m) => m.meta?.kind === "compact-summary");

              state.messages = [summaryMsg, ...oldSummaries, ...kept.filter((m) => m.meta?.kind !== "compact-summary")];

              state.stats = { input: 0, output: 0, cache: 0 };

              state._autoCompacted = true;

              renderMessages();

            }

          } catch (_) { /* auto-compact failed silently, continue */ }

        }

      }

    }



    const assistantIndex = state.messages.push({ role: "assistant", content: "", streaming: true, _model: getSelectedModel() }) - 1;

    state.responseUsage = { input: 0, output: 0, cache: 0 };

    renderMessages();

    const modelResult = await callModelOnce(assistantIndex);

    // Attach usage to this response (store in meta for persistence)

    state.messages[assistantIndex].meta = {

      ...(state.messages[assistantIndex].meta || {}),

      _usage: { ...state.responseUsage },

    };

    state.responseUsage = null;

    const rawContent = modelResult.content || "";

    const nativeCalls = modelResult.toolCalls || [];



    if (nativeCalls.length > 0) {

      const current = state.messages[assistantIndex] || {};

      state.messages[assistantIndex] = {

        ...current,

        role: "assistant",

        content: (current.content || "").trim() || `准备调用 ${nativeCalls.length} 个工具`,

        streaming: false,

        meta: {

          ...(current.meta || {}),

          toolCalls: nativeCalls,

        },

      };



      for (const nativeCall of nativeCalls) {

        const tool = normalizeNativeToolCall(nativeCall);

        state.messages.push({

          role: "tool-call",

          content: formatToolCall(tool),

          meta: {

            action: tool.action,

            tool,

            toolCallId: tool._toolCallId,

            native: true,

          },

        });

        renderMessages();

        await saveCurrentSession();



        const result = await executeToolCall(tool);

        const meta = {

          action: result.action || tool.action,

          path: result.path,

          toolCallId: tool._toolCallId,

          native: true,

        };

        if (result.ok && result.action === "propose_edit") {

          const editId = `edit-${Date.now()}-${Math.random().toString(16).slice(2)}`;

          state.pendingEdits[editId] = {

            path: result.path,

            newContent: result.newContent,

            applied: false,

          };

          meta.pendingEditId = editId;

          meta.newContent = result.newContent;

          meta.applied = false;

        }

        state.messages.push({

          role: "tool-result",

          content: formatToolResult(result),

          meta,

        });

        renderMessages();

        // Notify if page is not visible and a permission-required action arrived
        if (document.hidden && (result.action === "propose_edit" || result.action === "write_file")) {
          notifyPermissionNeeded(result.action, result.path);
        }

        await saveCurrentSession();

      }

      continue;

    }



    // Only try text-based extraction if content actually contains agent-tool markers
    const hasToolMarker = /```agent-tool|<agent-tool>/i.test(rawContent);

    if (!hasToolMarker) {
      state.messages[assistantIndex].content = rawContent.trim();
      state.messages[assistantIndex].streaming = false;
      renderMessages();
      await saveCurrentSession();
      return;
    }

    const tool = extractToolCall(rawContent);

    if (!tool) {

      await saveCurrentSession();

      return;

    }



    const cleanContent = stripToolBlock(rawContent);

    state.messages[assistantIndex].content = cleanContent || "";

    state.messages[assistantIndex].streaming = false;



    state.messages.push({

      role: "tool-call",

      content: formatToolCall(tool),

      meta: { action: tool.action, tool },

    });

    renderMessages();

    await saveCurrentSession();



    const result = await executeToolCall(tool);

    const meta = { action: result.action || tool.action, path: result.path };

    if (result.ok && result.action === "propose_edit") {

      const editId = `edit-${Date.now()}-${Math.random().toString(16).slice(2)}`;

      state.pendingEdits[editId] = {

        path: result.path,

        newContent: result.newContent,

        applied: false,

      };

      meta.pendingEditId = editId;

      meta.newContent = result.newContent;

      meta.applied = false;

    }

    state.messages.push({

      role: "tool-result",

      content: formatToolResult(result),

      meta,

    });

    renderMessages();

    if (document.hidden && (result.action === "propose_edit" || result.action === "write_file")) {
      notifyPermissionNeeded(result.action, result.path);
    }

    await saveCurrentSession();

  }



  state.messages.push({

    role: "assistant",

    content: "本轮任务已达到较高的保护阈值，已暂停以避免无限执行。请让 Agent 总结当前进度或继续下一步。",

    meta: { kind: "tool-round-limit" },

  });

  await saveCurrentSession();

  renderMessages();

}



async function compactConversation() {

  if (state.isStreaming) { alert("请等待当前任务完成后再压缩"); return; }

  if (state.messages.length < 6) { alert("消息太少，无需压缩"); return; }



  const key = els.apiKey.value.trim();

  const model = getSelectedModel();

  if (!key || !model) { alert("请先配置 API Key 和模型"); return; }



  // Show confirmation dialog

  const totalMsgs = state.messages.length;

  const keepCount = Math.max(2, Math.min(6, Math.floor(totalMsgs / 4)));

  const compressCount = totalMsgs - keepCount;

  const totalChars = state.messages.slice(0, compressCount).reduce((s, m) => s + (m.content || "").length, 0);

  const estimatedTokens = Math.ceil(totalChars / 3.2);

  const estimatedSaved = Math.ceil(estimatedTokens * 0.7); // ~70% reduction after summarization



  document.getElementById("compactConfirmBody").innerHTML = `

    <p>将把较早的 <strong>${compressCount} 条消息</strong> 压缩为一段摘要，保留最近的 <strong>${keepCount} 条</strong>。</p>

    <div class="compact-stats">

      <div><span>待压缩</span><b>${compressCount} 条</b></div>

      <div><span>保留</span><b>${keepCount} 条</b></div>

      <div><span>预计节省</span><b>~${formatCompact(estimatedSaved)} tokens</b></div>

    </div>

    <p class="confirm-note">压缩后的摘要会保留关键信息（需求、操作、文件修改、未完成事项），但原始对话细节无法恢复。</p>

  `;

  document.getElementById("compactConfirmModal").classList.remove("hidden");



  // Confirmation handler (one-shot)

  const doCompact = async () => {

    hideCompactConfirm();

    els.compactBtn.disabled = true;

    els.compactBtn.textContent = "压缩中...";

    try {

      const result = await apiJson("/api/compact", {

        method: "POST",

        headers: { Authorization: `Bearer ${key}` },

        body: JSON.stringify({

          model,

          messages: state.messages.map((msg) => ({

            role: msg.role,

            content: getMsgText(msg),

          })),

        }),

      });



      if (!result.ok) throw new Error(result.error || "压缩失败");



      const kept = state.messages.slice(-keepCount);

      const summaryMsg = {

        role: "assistant",

        content: `📋 **上下文已压缩**（${result.compressed} 条消息 → 摘要）\n\n${result.summary}`,

        meta: { kind: "compact-summary" },

      };

      state.messages = [summaryMsg, ...kept];

      state.stats = { input: 0, output: 0, cache: 0 };

      renderMessages();

      await saveCurrentSession();

    } catch (err) {

      alert(`压缩失败：${err.message}`);

    } finally {

      els.compactBtn.disabled = false;

      els.compactBtn.textContent = "压缩";

    }

  };



  const cancelCompact = () => hideCompactConfirm();



  // Bind one-shot handlers

  const confirmBtn = document.getElementById("confirmCompact");

  const cancelBtn = document.getElementById("cancelCompact");

  const cancelX = document.getElementById("cancelCompactX");

  const modal = document.getElementById("compactConfirmModal");



  const cleanup = () => {

    confirmBtn.removeEventListener("click", doCompact);

    cancelBtn.removeEventListener("click", cancelCompact);

    cancelX.removeEventListener("click", cancelCompact);

    modal.removeEventListener("click", onModalClick);

  };



  const onModalClick = (e) => { if (e.target === modal) cancelCompact(); };



  confirmBtn.addEventListener("click", () => { cleanup(); doCompact(); });

  cancelBtn.addEventListener("click", () => { cleanup(); cancelCompact(); });

  cancelX.addEventListener("click", () => { cleanup(); cancelCompact(); });

  modal.addEventListener("click", onModalClick);

}



function hideCompactConfirm() {

  document.getElementById("compactConfirmModal").classList.add("hidden");

}



async function sendMessage(userText) {

  const key = els.apiKey.value.trim();

  const model = getSelectedModel();

  if (!key) throw new Error("请先在 Models 中输入 New API 子 key。");

  if (!model) throw new Error("请先刷新并选择模型。");

  if (!state.sessionId) await createSession(userText.slice(0, 24) || "新会话");



  // Build message content (text + images)

  let messageContent = userText;

  const images = [...state.attachedImages];

  if (images.length > 0) {

    messageContent = [{ type: "text", text: userText }];

    for (const img of images) {

      messageContent.push({ type: "image_url", image_url: { url: `data:${img.mime};base64,${img.base64}` } });

    }

  }



  // Slash command detection

  const slashMatch = userText.match(/^\/(\S+)(?:\s+(.*))?$/s);

  if (slashMatch) {

    const cmd = slashMatch[1].toLowerCase();

    const rest = (slashMatch[2] || "").trim();

    if (cmd === "help") {

      const active = state.skills.filter((s) => !state.disabledSkills.has(s.name));

      const list = active.map((s) => `- /${s.name}: ${s.description || "无描述"}`).join("\n");

      state.messages.push({ role: "user", content: "/help" });

      state.messages.push({ role: "assistant", content: `**可用 Skills：**\n\n${list || "暂无可用 Skill"}` });

      renderMessages();

      await saveCurrentSession();

      return;

    }

    const skill = state.skills.find((s) => s.name === cmd && !state.disabledSkills.has(s.name));

    if (skill) {

      state.explicitSkill = skill.name;

      userText = rest || `执行 ${skill.name} 任务`;

    }

  }



  const shouldAutoTitle = state.messages.length === 0 && isAutoSessionTitle(els.sessionTitle.value);

  if (shouldAutoTitle) {

    els.sessionTitle.value = makeSessionTitle(userText);

    generateSessionTitle(userText);

  }

  state.messages.push({ role: "user", content: messageContent, _images: images.length > 0 ? images : undefined, _model: getSelectedModel() });

  state.attachedImages = [];

  renderImageThumbs();

  renderMessages();

  await saveCurrentSession();

  setStreaming(true);

  let loopError = null;
  try {
    await runAgentLoop();
  } catch (err) {
    loopError = err;
  } finally {
    state.explicitSkill = null;
  }

  // Drain queued messages: push all as separate user messages, then one API call
  if (!loopError && state.messageQueue.length > 0) {
    const queued = [...state.messageQueue];
    state.messageQueue = [];
    renderMessages();  // clear queue cards immediately
    setStreaming(false);

    // Push each queued message as a separate user message
    for (const q of queued) {
      const imgs = q.images || [];
      const msgContent = imgs.length > 0
        ? [{ type: "text", text: q.text || "" }, ...imgs.map((img) => ({ type: "image_url", image_url: { url: `data:${img.mime};base64,${img.base64}` } }))]
        : (q.text || "");
      state.messages.push({ role: "user", content: msgContent, _images: imgs.length > 0 ? imgs : undefined, _model: getSelectedModel() });
    }
    state.attachedImages = [];
    renderImageThumbs();
    renderMessages();
    await saveCurrentSession();

    // One API call to respond to all queued messages
    setStreaming(true);
    let drainError = null;
    try {
      await runAgentLoop();
    } catch (err) {
      drainError = err;
    } finally {
      state.explicitSkill = null;
    }
    if (drainError) throw drainError;
  }

  if (loopError) throw loopError;  // propagate to chatForm handler
}



function getSelectedModel() {

  return els.modelPillBtn.dataset.model || "";

}



function setSelectedModel(modelId) {

  els.modelPillBtn.dataset.model = modelId;

  els.modelPillLabel.textContent = modelId || "选择模型";

  // Update dropdown checkmarks

  els.modelPillDropdown.querySelectorAll(".model-pill-option").forEach((opt) => {

    opt.classList.toggle("selected", opt.dataset.model === modelId);

  });

}



function getThinkingLevel() {

  return els.thinkingPillBtn.dataset.value || "auto";

}



function setThinkingLevel(value) {

  const labels = { auto: "自动", off: "关闭", high: "高", max: "最高" };

  els.thinkingPillBtn.dataset.value = value;

  els.thinkingPillLabel.textContent = labels[value] || value;

  els.thinkingPillDropdown.querySelectorAll(".model-pill-option").forEach((opt) => {

    opt.classList.toggle("selected", opt.dataset.value === value);

  });

}



function getPermLevel() {

  return els.permPillBtn.dataset.value || "accept";

}



function setPermLevel(value) {

  const labels = { plan: "计划", accept: "接受编辑", bypass: "自动" };

  els.permPillBtn.dataset.value = value;

  els.permPillLabel.textContent = labels[value] || value;

  els.permPillDropdown.querySelectorAll(".model-pill-option").forEach((opt) => {

    opt.classList.toggle("selected", opt.dataset.value === value);

  });

}



function saveLocalSettings() {

  localStorage.setItem("agent-lite-key", els.apiKey.value.trim());

  localStorage.setItem("agent-lite-base-url", els.baseUrl.value.trim());

  localStorage.setItem("agent-lite-model", getSelectedModel());

  localStorage.setItem("agent-lite-temperature", els.temperature.value);

  localStorage.setItem("agent-lite-max-tokens", els.maxTokens.value);

  localStorage.setItem("agent-lite-thinking", getThinkingLevel());

  localStorage.setItem("agent-lite-tool-preset", els.toolPreset.value);

  state.permissionProfile = getPermissionProfile();

  localStorage.setItem("agent-lite-permission-profile", state.permissionProfile);

  updateModePromptPreview();

}



function exportMarkdown() {

  const text = state.messages

    .map((msg) => {

      const titleMap = {

        user: "User",

        assistant: "Agent",

        "tool-call": "Tool Call",

        "tool-result": "Tool Result",

      };

      const thought = msg.thought ? `\n\n> Thinking：${msg.thought}` : "";

      return `## ${titleMap[msg.role] || msg.role}${thought}\n\n${msg.content}`;

    })

    .join("\n\n");

  const blob = new Blob([text || "# 空会话\n"], { type: "text/markdown;charset=utf-8" });

  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");

  a.href = url;

  a.download = `agent-chat-${new Date().toISOString().slice(0, 19).replaceAll(":", "")}.md`;

  a.click();

  URL.revokeObjectURL(url);

}



function goUpDir() {

  if (!state.currentDir) return;

  const parts = state.currentDir.split("/").filter(Boolean);

  parts.pop();

  loadFiles(parts.join("/"));

}



function showSettings(open = true) {

  els.settingsModal.classList.toggle("hidden", !open);

}



// ── Memory Panel ──



async function showMemoryPanel() {

  els.memoryModal.classList.remove("hidden");

  els.memoryName.value = "";

  els.memoryDesc.value = "";

  els.memoryBody.value = "";

  await renderMemoryList();

}



function hideMemoryPanel() {

  els.memoryModal.classList.add("hidden");

}



async function renderMemoryList() {

  try {

    const data = await apiJson("/api/memory");

    const memories = data.data || [];

    if (memories.length === 0) {

      els.memoryList.innerHTML = `<div class="muted-line" style="padding:12px;">暂无记忆。在下方创建第一条持久记忆。</div>`;

      return;

    }

    els.memoryList.innerHTML = memories.map((mem) => `

      <div class="memory-item">

        <span class="memory-item-name">${escapeHtml(mem.name)}</span>

        <button class="memory-item-btn" data-memory-edit="${escapeHtml(mem.name)}">编辑</button>

        <button class="memory-item-btn danger" data-memory-delete="${escapeHtml(mem.name)}">删除</button>

        ${mem.description ? `<span class="memory-item-desc">${escapeHtml(mem.description)}</span>` : ""}

      </div>

    `).join("");

    document.querySelectorAll("[data-memory-edit]").forEach((btn) => {

      btn.addEventListener("click", () => editMemory(btn.dataset.memoryEdit));

    });

    document.querySelectorAll("[data-memory-delete]").forEach((btn) => {

      btn.addEventListener("click", () => deleteMemory(btn.dataset.memoryDelete));

    });

  } catch (err) {

    els.memoryList.innerHTML = `<div class="muted-line" style="padding:12px;">加载失败：${escapeHtml(err.message)}</div>`;

  }

}



async function editMemory(name) {

  try {

    const mem = await apiJson(`/api/memory?file=${encodeURIComponent(name)}`);

    els.memoryName.value = mem.name || "";

    els.memoryDesc.value = (mem.meta || {}).description || "";

    els.memoryBody.value = mem.body || "";

  } catch (err) {

    showToast(`读取记忆失败：${err.message}`, "error");

  }

}



async function deleteMemory(name) {

  if (!window.confirm(`删除记忆 "${name}"？此操作不可恢复。`)) return;

  try {

    await apiJson(`/api/memory?file=${encodeURIComponent(name)}`, { method: "DELETE" });

    await renderMemoryList();

    await loadMemoryContext();

    updateModePromptPreview();

  } catch (err) {

    showToast(`删除失败：${err.message}`, "error");

  }

}



async function saveMemorySubmit() {

  const name = els.memoryName.value.trim();

  const desc = els.memoryDesc.value.trim();

  const body = els.memoryBody.value.trim();

  if (!name) { alert("请输入记忆名称"); return; }

  if (!body) { alert("请输入记忆内容"); return; }

  try {

    await apiJson("/api/memory", {

      method: "POST",

      body: JSON.stringify({

        name,

        meta: { description: desc },

        body,

      }),

    });

    els.memoryName.value = "";

    els.memoryDesc.value = "";

    els.memoryBody.value = "";

    await renderMemoryList();

    await loadMemoryContext();

    updateModePromptPreview();

  } catch (err) {

    showToast(`保存失败：${err.message}`, "error");

  }

}



let previewDragState = null;

let sidebarDragState = null;

let sidebarMainDragState = null;



function finishPreviewDrag(event) {

  if (!previewDragState) return;

  if (event?.pointerId !== undefined && els.previewResizer.hasPointerCapture(event.pointerId)) {

    els.previewResizer.releasePointerCapture(event.pointerId);

  }

  previewDragState = null;

  document.body.classList.remove("resizing-preview");

}



function finishSidebarDrag(event) {

  if (!sidebarDragState) return;

  if (event?.pointerId !== undefined && els.sidebarSplitter.hasPointerCapture(event.pointerId)) {

    els.sidebarSplitter.releasePointerCapture(event.pointerId);

  }

  sidebarDragState = null;

  document.body.classList.remove("resizing-sidebar");

}





els.messages.addEventListener("scroll", () => {

  if (!state.isStreaming) return;

  const el = els.messages;

  const distToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;

  state._followOutput = distToBottom < 80;

});



els.prompt.addEventListener("paste", (e) => { handleImagePaste(e); });

els.prompt.addEventListener("drop", (e) => { e.preventDefault(); handleImageDrop(e); });

els.prompt.addEventListener("dragover", (e) => { e.preventDefault(); });

els.chatForm.addEventListener("drop", (e) => { e.preventDefault(); handleImageDrop(e); });

els.chatForm.addEventListener("dragover", (e) => { e.preventDefault(); });



els.prompt.addEventListener("input", () => {

  updateSendButtonState();

  // Auto-grow by counting lines, cap at 5

  const ta = els.prompt;

  const lines = ta.value.split("\n").reduce((n, line) => n + Math.max(1, Math.ceil(line.length / 60)), 0);

  ta.rows = Math.max(2, Math.min(lines, 5));

  // Slash suggestion

  showSlashSuggestions();

});



els.prompt.addEventListener("keydown", (event) => {

  if (event.key === "Enter" && !event.shiftKey) {

    event.preventDefault();

    els.chatForm.requestSubmit();

  }

});





els.stopBtn.addEventListener("click", () => {

  if (state.abortController) state.abortController.abort();

});



els.sendBtn.addEventListener("click", (event) => {
  if (!state.isStreaming) return;  // idle → let form submit send
  event.preventDefault();
  if (state.abortController) state.abortController.abort();
});



els.attachFile.addEventListener("click", pickProjectFile);

els.refreshModelsBtn.addEventListener("click", refreshModels);

els.filePicker.addEventListener("change", () => {

  const file = els.filePicker.files?.[0];

  resolvePickedFile(file);

});

function getEffectiveMaxTokens(model) {

  const val = els.maxTokens.value;

  if (val !== "auto") return Number(val);

  if (!model) return 4096;

  if (/claude|opus|sonnet|haiku/i.test(model)) return 8192;

  if (/deepseek.*r1|deepseek.*reason/i.test(model)) return 8192;

  if (/o1|o3|gpt-5/i.test(model)) return 16384;

  return 4096;

}



// Model pill dropdown

els.modelPillBtn.addEventListener("click", (e) => {

  e.stopPropagation();

  const opening = els.modelPillDropdown.classList.contains("hidden");

  if (opening) {

    // Decide direction: if there are messages (composer is near bottom), flip upward

    const btnRect = els.modelPillBtn.getBoundingClientRect();

    const dropdownH = 360; // max-height

    const spaceBelow = window.innerHeight - btnRect.bottom;

    if (spaceBelow < dropdownH + 16) {

      els.modelPillDropdown.classList.add("up");

    } else {

      els.modelPillDropdown.classList.remove("up");

    }

  }

  els.modelPillWrap.classList.toggle("open");

  els.modelPillDropdown.classList.toggle("hidden");

});



els.modelPillDropdown.addEventListener("click", (e) => {

  const opt = e.target.closest(".model-pill-option");

  if (!opt) return;

  setSelectedModel(opt.dataset.model);

  els.modelPillWrap.classList.remove("open");

  els.modelPillDropdown.classList.add("hidden");

  saveLocalSettings();

  updateStatsPanel();

});



document.addEventListener("click", (e) => {

  if (!els.modelPillWrap.contains(e.target)) {

    els.modelPillWrap.classList.remove("open");

    els.modelPillDropdown.classList.add("hidden");

  }

});



els.apiKey.addEventListener("change", saveLocalSettings);

els.temperature.addEventListener("change", saveLocalSettings);

els.maxTokens.addEventListener("change", saveLocalSettings);



// Thinking pill dropdown

els.thinkingPillBtn.addEventListener("click", (e) => {

  e.stopPropagation();

  const dd = els.thinkingPillDropdown;

  const opening = dd.classList.contains("hidden");

  if (opening) {

    const btnRect = els.thinkingPillBtn.getBoundingClientRect();

    const spaceBelow = window.innerHeight - btnRect.bottom;

    dd.classList.toggle("up", spaceBelow < 200 + 16);

  }

  els.thinkingPillWrap.classList.toggle("open");

  dd.classList.toggle("hidden");

});



els.thinkingPillDropdown.addEventListener("click", (e) => {

  const opt = e.target.closest(".model-pill-option");

  if (!opt) return;

  setThinkingLevel(opt.dataset.value);

  els.thinkingPillWrap.classList.remove("open");

  els.thinkingPillDropdown.classList.add("hidden");

  saveLocalSettings();

});



document.addEventListener("click", (e) => {

  if (!els.thinkingPillWrap.contains(e.target)) {

    els.thinkingPillWrap.classList.remove("open");

    els.thinkingPillDropdown.classList.add("hidden");

  }

});

els.toolPreset.addEventListener("change", saveLocalSettings);

els.permissionProfile?.addEventListener("change", saveLocalSettings);

els.systemPromptText.addEventListener("change", saveSystemPrompt);

els.systemPromptText.addEventListener("input", updateModePromptPreview);

els.resetSystemPrompt.addEventListener("click", () => {

  els.systemPromptText.value = defaultSystemPrompt;

  saveSystemPrompt();

});

// saveProjectRoot now called with path parameter from pickFolder / recent items



// Project directory dropdown

const cwdDropdown = document.getElementById("cwdDropdown");

const cwdRecent = document.getElementById("cwdRecentFolders");



function toggleCwdDropdown() {

  const open = !cwdDropdown.classList.contains("hidden");

  if (open) { cwdDropdown.classList.add("hidden"); return; }



  renderRecentFolders();

  const rect = els.projectRootShort.getBoundingClientRect();

  const spaceBelow = window.innerHeight - rect.bottom;



  // Position relative to button

  cwdDropdown.style.position = "fixed";

  cwdDropdown.style.left = rect.left + "px";

  cwdDropdown.style.right = "auto";

  cwdDropdown.style.width = rect.width + "px";

  cwdDropdown.style.margin = "4px 0 0 0";



  if (spaceBelow < 200) {

    cwdDropdown.style.top = "auto";

    cwdDropdown.style.bottom = (window.innerHeight - rect.top + 4) + "px";

  } else {

    cwdDropdown.style.top = rect.bottom + "px";

    cwdDropdown.style.bottom = "auto";

  }

  cwdDropdown.classList.remove("hidden");

}



function renderRecentFolders() {

  const recents = JSON.parse(localStorage.getItem("agent-lite-recent-folders") || "[]");

  if (recents.length === 0) {

    cwdRecent.innerHTML = "";

    cwdRecent.style.display = "none";

    return;

  }

  cwdRecent.style.display = "block";

  cwdRecent.innerHTML = `<div class="cwd-dropdown-label">最近使用</div>` +

    recents.slice(0, 5).map((p) =>

      `<button class="cwd-dropdown-item cwd-recent-item" data-path="${escapeHtml(p)}">${escapeHtml(shortPath(p))}</button>`

    ).join("");

  cwdRecent.querySelectorAll(".cwd-recent-item").forEach((btn) => {

    btn.addEventListener("click", () => {

      saveProjectRoot(btn.dataset.path).catch((err) => alert(err.message));

      cwdDropdown.classList.add("hidden");

    });

  });

}



function addRecentFolder(p) {

  if (!p) return;

  const recents = JSON.parse(localStorage.getItem("agent-lite-recent-folders") || "[]");

  const filtered = recents.filter((r) => r !== p);

  filtered.unshift(p);

  localStorage.setItem("agent-lite-recent-folders", JSON.stringify(filtered.slice(0, 8)));

}



async function pickFolder() {

  try {

    const data = await apiJson("/api/pick-folder");

    if (data.cancelled) return;

    await saveProjectRoot(data.path);

  } catch (err) { alert(err.message); }

}



els.projectRootShort.addEventListener("click", toggleCwdDropdown);



function cwdPickFolderAction() { cwdDropdown.classList.add("hidden"); pickFolder(); }

function cwdNewFolderAction() { document.getElementById("newFolderModal").classList.remove("hidden"); document.getElementById("newFolderName").value = ""; document.getElementById("newFolderName").focus(); }

function cwdClearFolderAction() {

  cwdDropdown.classList.add("hidden");

  els.cwdPathText.textContent = "未选择";

  els.projectRootShort.title = "未选择项目目录";

  state._fileItems = [];

  state._noProject = true;

  localStorage.setItem("agent-lite-no-project", "1");

  renderFileTree();

}

document.addEventListener("click", (e) => {

  if (!e.target.closest(".cwd-dropdown") && !e.target.closest("#projectRootShort")) {

    cwdDropdown.classList.add("hidden");

  }

});

document.getElementById("closeNewFolder").addEventListener("click", hideNewFolder);

document.getElementById("cancelNewFolder").addEventListener("click", hideNewFolder);

document.getElementById("newFolderModal").addEventListener("click", (e) => {

  if (e.target === e.currentTarget) hideNewFolder();

});

document.getElementById("confirmNewFolder").addEventListener("click", async () => {

  const input = document.getElementById("newFolderName");

  const name = input.value.trim();

  if (!name) return;

  try {

    await apiJson("/api/mkdir", {

      method: "POST",

      body: JSON.stringify({ name, parent: state.currentDir }),

    });

    hideNewFolder();

    await loadFiles(state.currentDir);

  } catch (err) { alert(err.message); }

});

document.getElementById("newFolderName").addEventListener("keydown", (e) => {

  if (e.key === "Enter") document.getElementById("confirmNewFolder").click();

  if (e.key === "Escape") hideNewFolder();

});



function hideNewFolder() {

  document.getElementById("newFolderModal").classList.add("hidden");

}

els.refreshFiles.addEventListener("click", (e) => { e.stopPropagation(); loadFiles().catch((err) => alert(err.message)); });

els.newFolderBtn.addEventListener("click", (e) => { e.stopPropagation(); cwdNewFolderAction(); });

els.fileSearch.addEventListener("input", () => renderFileTree());

els.goUp.addEventListener("click", (e) => { e.stopPropagation(); goUpDir(); });

els.refreshPreview.addEventListener("click", () => {

  if (!state.previewPath) return;

  loadFile(state.previewPath).catch((err) => alert(err.message));

});

els.copyPreview.addEventListener("click", async () => {

  const ok = await copyText(state.previewContent || "");

  els.copyPreview.textContent = ok ? "已复制" : "复制失败";

  setTimeout(() => { els.copyPreview.textContent = "复制"; }, 1200);

});

els.copySessionPath.addEventListener("click", () => copyText(sessionFilePath()));

els.copySessionId.addEventListener("click", () => copyText(state.sessionId || ""));

// Sidebar toggle: click to collapse (peek mode), click again to restore
els.toggleSidebar.addEventListener("click", () => {
  const hidden = els.shell.classList.toggle("sidebar-hidden");
  els.shell.classList.remove("peek");
  localStorage.setItem("agent-lite-sidebar-hidden", hidden ? "1" : "0");
});

// Peek behavior: hover on left edge temporarily shows sidebar
els.sidebarPeekZone.addEventListener("mouseenter", () => {
  if (els.shell.classList.contains("sidebar-hidden")) {
    els.shell.classList.add("peek");
  }
});

// Hide peek when mouse leaves BOTH the peek zone AND the sidebar
const hidePeek = (e) => {
  if (!els.shell.classList.contains("peek")) return;
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  // Small delay to check if mouse entered sidebar
  setTimeout(() => {
    const overZone = els.sidebarPeekZone.matches(":hover");
    const overSidebar = sidebar.matches(":hover");
    if (!overZone && !overSidebar) {
      els.shell.classList.remove("peek");
    }
  }, 100);
};

els.sidebarPeekZone.addEventListener("mouseleave", hidePeek);
document.getElementById("sidebar").addEventListener("mouseleave", hidePeek);

els.togglePreview.addEventListener("click", () => {

  els.workbench.classList.toggle("preview-open");

  if (!els.workbench.classList.contains("preview-open")) {

    clearInterval(_previewPollTimer);

    state.previewPath = ""; state.previewContent = "";

    localStorage.removeItem("agent-lite-preview-open");

    localStorage.removeItem("agent-lite-preview-path");

  }

});

els.previewResizer.addEventListener("pointerdown", (event) => {

  if (!els.workbench.classList.contains("preview-open")) return;

  previewDragState = { startX: event.clientX, startWidth: state.previewWidth };

  els.previewResizer.setPointerCapture(event.pointerId);

  document.body.classList.add("resizing-preview");

});

els.previewResizer.addEventListener("pointermove", (event) => {

  if (!previewDragState) return;

  applyPreviewWidth(previewDragState.startWidth - (event.clientX - previewDragState.startX));

});

els.previewResizer.addEventListener("pointerup", finishPreviewDrag);

els.previewResizer.addEventListener("pointercancel", finishPreviewDrag);

els.sidebarSplitter.addEventListener("pointerdown", (event) => {

  const explorer = document.querySelector(".explorer");

  const height = explorer.getBoundingClientRect().height;

  sidebarDragState = { startY: event.clientY, startHeight: height };

  els.sidebarSplitter.setPointerCapture(event.pointerId);

  document.body.classList.add("resizing-sidebar");

});

els.sidebarSplitter.addEventListener("pointermove", (event) => {

  if (!sidebarDragState) return;

  applySidebarSessionHeight(sidebarDragState.startHeight - (event.clientY - sidebarDragState.startY));

});

els.sidebarSplitter.addEventListener("pointerup", finishSidebarDrag);

els.sidebarSplitter.addEventListener("pointercancel", finishSidebarDrag);



// Sidebar main width resizer

function finishSidebarMainDrag(event) {

  if (!sidebarMainDragState) return;

  if (event?.pointerId !== undefined && els.sidebarResizer.hasPointerCapture(event.pointerId)) {

    els.sidebarResizer.releasePointerCapture(event.pointerId);

  }

  sidebarMainDragState = null;

  document.body.classList.remove("resizing-sidebar-main");

}

els.sidebarResizer.addEventListener("pointerdown", (event) => {

  sidebarMainDragState = { startX: event.clientX, startWidth: state.sidebarWidth };

  els.sidebarResizer.setPointerCapture(event.pointerId);

  document.body.classList.add("resizing-sidebar-main");

});

els.sidebarResizer.addEventListener("pointermove", (event) => {

  if (!sidebarMainDragState) return;

  applySidebarWidth(sidebarMainDragState.startWidth + (event.clientX - sidebarMainDragState.startX));

});

els.sidebarResizer.addEventListener("pointerup", finishSidebarMainDrag);

els.sidebarResizer.addEventListener("pointercancel", finishSidebarMainDrag);



window.addEventListener("resize", () => {

  applyPreviewWidth(state.previewWidth);

  applySidebarSessionHeight(state.sidebarSessionHeight);

  applySidebarWidth(state.sidebarWidth);

});

els.toolLogToggle.addEventListener("click", () => {

  const open = !els.toolLogPanel.classList.contains("open");

  closeTopPanels();

  renderToolLog();

  els.toolLogPanel.classList.toggle("open", open);

  els.toolLogToggle.classList.toggle("active", open);

});

els.usageStrip.addEventListener("click", () => {

  const open = !els.statsPanel.classList.contains("open");

  closeTopPanels();

  els.statsPanel.classList.toggle("open", open);

  els.usageStrip.classList.toggle("active", open);

});

function applyTheme(mode) {

  const isDark = mode === "dark" || (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  document.body.classList.toggle("theme-dark", isDark);

  localStorage.setItem("agent-lite-theme", mode);

  updateThemeButtons();

}



// Listen for system theme changes when in system mode

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {

  if ((localStorage.getItem("agent-lite-theme") || "light") === "system") {

    applyTheme("system");

  }

});

// Settings dropdown

const settingsDropdown = document.getElementById("settingsDropdown");

document.getElementById("settingsMenuBtn").addEventListener("click", () => {

  openSettingsPage("models");

});

// ── Unified Settings Page ──

function openSettingsPage(panel = "models") {

  document.getElementById("settingsPage").classList.remove("hidden");

  switchSettingsPanel(panel);

}



function switchSettingsPanel(panel) {

  document.querySelectorAll(".settings-nav-item").forEach((el) => {

    el.classList.toggle("active", el.dataset.panel === panel);

  });

  const detail = document.getElementById("settingsDetail");

  switch (panel) {

    case "models": renderModelsPanel(detail); break;

    case "memory": renderMemoryPanel(detail); break;

    case "skills": renderSkillsInSettings(detail); break;

    case "system": renderSystemPanel(detail); break;

    case "theme": renderThemePanel(detail); break;

    case "language": renderLanguagePanel(detail); break;

  }

}



function renderModelsPanel(container) {

  container.innerHTML = `

    <h3 style="margin:0 0 14px">${t("models")}</h3>

    <label class="field"><span>${t("baseUrl")}</span><input id="settingsBaseUrl" value="${escapeHtml(els.baseUrl.value)}" placeholder="http://localhost:3000" autocomplete="off" /></label>

    <label class="field"><span>${t("apiKeys")}</span>

      <div class="key-list" id="settingsKeyList">${renderKeyEditor(els.apiKey.value)}</div>

      <div id="settingsKeyAddArea">

        <button id="settingsKeyAddRow" class="key-add-btn" type="button">${t("addKey")}</button>

      </div>

    </label>

    <div class="model-list-header"><span>${t("availableModels")} <button id="settingsRefreshModels" class="icon-refresh-btn" type="button" title="${t("refreshModels")}"><svg width="14" height="14" viewBox="0 0 14 14"><path d="M1 7a6 6 0 0111.1-3.5M13 7a6 6 0 01-11.1 3.5" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round"/><path d="M12 1v3H9M2 13v-3h3" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button></span></div>

    <div id="settingsModelList" class="model-list-display">${els.modelListBox.innerHTML}</div>

    <div class="grid-two">

      <label class="field"><span>${t("temperature")}</span><input id="settingsTemperature" type="number" min="0" max="2" step="0.1" value="${els.temperature.value}" /></label>

      <label class="field"><span>${t("maxTokens")}</span><select id="settingsMaxTokens">${els.maxTokens.innerHTML}</select></label>

    </div>

  `;

  document.getElementById("settingsBaseUrl").addEventListener("change", () => { els.baseUrl.value = document.getElementById("settingsBaseUrl").value; saveLocalSettings(); });

  document.getElementById("settingsRefreshModels").addEventListener("click", () => { els.refreshModelsBtn.click(); setTimeout(() => { document.getElementById("settingsModelList").innerHTML = els.modelListBox.innerHTML; }, 2000); });

  document.getElementById("settingsTemperature").addEventListener("change", () => { els.temperature.value = document.getElementById("settingsTemperature").value; saveLocalSettings(); });

  document.getElementById("settingsMaxTokens").addEventListener("change", () => { els.maxTokens.value = document.getElementById("settingsMaxTokens").value; saveLocalSettings(); });

  // Key editor with name:key pairs

  const keyList = document.getElementById("settingsKeyList");

  bindKeyEditorEvents(keyList);

  // Toggle key visibility

  let keyVisible = false;

  document.getElementById("settingsKeyToggle").addEventListener("click", () => {

    keyVisible = !keyVisible;

    keyList.querySelectorAll(".key-value-input").forEach((inp) => {

      inp.type = keyVisible ? "text" : "password";

    });

    document.getElementById("settingsKeyToggle").textContent = keyVisible ? "隐藏" : "显示";

  });

  document.getElementById("settingsKeyList").addEventListener("dblclick", () => {

    keyVisible = true;

    keyList.querySelectorAll(".key-value-input").forEach((inp) => { inp.type = "text"; });

    document.getElementById("settingsKeyToggle").textContent = "隐藏";

  });

}



function renderMemoryPanel(container) {

  state._editingMemory = null;

  container.innerHTML = `<h3 style="margin:0 0 14px">${t("memory")}</h3><div id="settingsMemoryList" class="memory-list" style="max-height:300px; overflow:auto"></div>

    <div id="settingsMemoryForm" class="memory-form">

      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;height:24px">

        <span id="memFormLabel" style="font-weight:700;font-size:13px;color:var(--text)">${t("newMemory")}</span>

        <button id="memCancelBtn" class="mini-btn" type="button" style="visibility:hidden">取消</button>

      </div>

      <input id="settingsMemName" placeholder="name（英文+数字+_-，如 coding-conventions）" autocomplete="off" />

      <input id="settingsMemDesc" placeholder="description（一行描述）" autocomplete="off" />

      <textarea id="settingsMemBody" rows="5" placeholder="记忆内容…" spellcheck="false"></textarea>

      <div class="memory-form-actions"><button id="settingsSaveMem" class="mini-btn" type="button">保存</button></div>

    </div>`;

  setTimeout(() => refreshSettingsMemoryList(), 100);

  document.getElementById("settingsSaveMem").addEventListener("click", async () => {

    const name = document.getElementById("settingsMemName").value.trim();

    const desc = document.getElementById("settingsMemDesc").value.trim();

    const body = document.getElementById("settingsMemBody").value.trim();

    if (!name || !body) { showToast("名称和内容不能为空", "error"); return; }

    if (!/^[a-zA-Z0-9_-]+$/.test(name)) { showToast("名称只能包含英文、数字、下划线和连字符", "error"); return; }

    if (state._editingMemory && state._editingMemory !== name) {

      // Renamed: delete old first

      try { await apiJson(`/api/memory?file=${encodeURIComponent(state._editingMemory)}`, { method: "DELETE" }); } catch (_) {}

    }

    await apiJson("/api/memory", { method: "POST", body: JSON.stringify({ name, meta: { description: desc }, body }) });

    clearMemoryForm();

    refreshSettingsMemoryList();

    loadMemoryContext();

  });

  document.getElementById("memCancelBtn").addEventListener("click", clearMemoryForm);

}



function clearMemoryForm() {

  state._editingMemory = null;

  document.getElementById("settingsMemName").value = "";

  document.getElementById("settingsMemDesc").value = "";

  document.getElementById("settingsMemBody").value = "";

  document.getElementById("memFormLabel").textContent = t("newMemory");

  document.getElementById("memCancelBtn").style.visibility = "hidden";

  document.getElementById("settingsMemName").disabled = false;

}



async function refreshSettingsMemoryList() {

  const list = document.getElementById("settingsMemoryList");

  if (!list) return;

  try {

    const data = await apiJson("/api/memory");

    const memories = data.data || [];

    list.innerHTML = memories.length ? memories.map((m) => `

      <div class="memory-item ${state._editingMemory === m.name ? 'editing' : ''}" data-name="${escapeHtml(m.name)}">

        <span class="memory-item-name">${escapeHtml(m.name)}</span>

        ${m.description ? `<span class="memory-item-desc">${escapeHtml(m.description)}</span>` : `<span></span>`}

        <div class="memory-item-actions">

          <button class="memory-item-btn" data-edit="${escapeHtml(m.name)}" title="编辑">

            <svg width="14" height="14" viewBox="0 0 1097 1024"><path d="M925.72 1024H161.13C72 1024 0 952.32 0 863.57V160.43C0 71.68 72 0 161.16 0h613.67c20.58 0 34.3 13.65 34.3 34.13s-13.72 34.14-34.3 34.14H161.16a91.99 91.99 0 00-92.55 92.16v699.73c0 54.61 41.13 95.57 92.55 95.57h764.59c51.44 0 92.57-40.96 92.57-92.16V337.92c0-20.48 13.7-34.13 34.28-34.13s34.28 13.65 34.28 34.13v525.65c3.41 88.75-72 160.43-161.16 160.43zM456 658.77c-10.29 0-17.14-3.41-24-10.24-13.72-13.65-13.72-34.13 0-47.78L1038.85 23.89a33.26 33.26 0 0148.03 0c13.7 13.66 13.7 34.14 0 47.79L479.96 648.53c-6.83 6.83-13.7 10.24-24 10.24z" fill="currentColor"/></svg>

          </button>

          <button class="memory-item-btn danger" data-del="${escapeHtml(m.name)}" title="删除">

            ${trashIcon()}

          </button>

        </div>

      </div>`).join("") : `<div class="muted-line" style="padding:12px">暂无记忆</div>`;

    list.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", async () => {

      const mem = await apiJson(`/api/memory?file=${encodeURIComponent(b.dataset.edit)}`);

      state._editingMemory = mem.name;

      document.getElementById("settingsMemName").value = mem.name || "";

      document.getElementById("settingsMemName").disabled = true;

      document.getElementById("settingsMemDesc").value = (mem.meta || {}).description || "";

      document.getElementById("settingsMemBody").value = mem.body || "";

      document.getElementById("memFormLabel").textContent = `编辑中: ${mem.name}`;

      document.getElementById("memCancelBtn").style.visibility = "";

      document.querySelectorAll(".memory-item").forEach((el) => {

        el.classList.toggle("editing", el.dataset.name === mem.name);

      });

    }));

    list.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => {

      const item = b.closest(".memory-item");

      const name = b.dataset.del;

      document.querySelector(".key-delete-confirm")?.remove();

      const confirm = document.createElement("div");

      confirm.className = "key-delete-confirm";

      confirm.innerHTML = `

        <span>删除记忆「${escapeHtml(name)}」？</span>

        <button class="key-confirm-yes" type="button">确认</button>

        <button class="key-confirm-no" type="button">取消</button>

      `;

      item.after(confirm);

      confirm.querySelector(".key-confirm-yes").addEventListener("click", async () => {

        confirm.remove();

        await apiJson(`/api/memory?file=${encodeURIComponent(name)}`, { method: "DELETE" });

        if (state._editingMemory === name) clearMemoryForm();

        refreshSettingsMemoryList();

        loadMemoryContext();

      });

      confirm.querySelector(".key-confirm-no").addEventListener("click", () => confirm.remove());

    }));

  } catch (_) {}

}



function renderSkillsInSettings(container) {

  container.innerHTML = `<h3 style="margin:0 0 10px">${t("skills")}</h3>

    <div class="skills-layout-inner">

      <div class="skills-sidebar-inner" id="settingsSkillsSidebar"></div>

      <div class="skills-detail-inner" id="settingsSkillsDetail"></div>

    </div>`;

  renderSettingsSkillsSidebar();

}



function renderSettingsSkillsSidebar() {

  const sidebar = document.getElementById("settingsSkillsSidebar");

  const active = state.skills.filter((s) => !state.disabledSkills.has(s.name));

  const disabled = state.skills.filter((s) => state.disabledSkills.has(s.name));

  const sorted = [...active, ...disabled];

  sidebar.innerHTML = sorted.length ? sorted.map((s) => {

    const on = !state.disabledSkills.has(s.name);

    return `<div class="skill-list-item" data-skill-name="${escapeHtml(s.name)}">

      <span class="dot ${on ? 'on' : 'off'}"></span>

      <span>${escapeHtml(s.name)}</span>

    </div>`;

  }).join("") : `<div class="muted-line" style="padding:12px;font-size:12px">暂无 Skill</div>`;

  sidebar.querySelectorAll(".skill-list-item").forEach((item) => {

    item.addEventListener("click", () => {

      sidebar.querySelectorAll(".skill-list-item").forEach((el) => el.classList.remove("active"));

      item.classList.add("active");

      const skill = state.skills.find((s) => s.name === item.dataset.skillName);

      showSkillDetailInSettings(skill);

    });

  });

  // Auto-select first

  if (sorted.length > 0) {

    const first = sidebar.querySelector(".skill-list-item");

    first?.classList.add("active");

    showSkillDetailInSettings(sorted[0]);

  }

}



function showSkillDetailInSettings(skill) {

  const panel = document.getElementById("settingsSkillsDetail");

  if (!skill) { panel.innerHTML = `<div class="skills-detail-empty">← 选择左侧 Skill</div>`; return; }

  const isOn = !state.disabledSkills.has(skill.name);

  panel.innerHTML = `

    <div class="skill-detail-head">

      <div class="skill-detail-name">${escapeHtml(skill.name)}</div>

      <div class="skill-detail-head-actions">

        <label class="toggle-switch" title="${isOn ? '已启用' : '已禁用'}">

          <input type="checkbox" ${isOn ? 'checked' : ''} id="settingsSkillToggle" />

          <span class="toggle-track"><span class="toggle-thumb"></span></span>

        </label>

        <button class="skill-edit-icon" id="settingsSkillEdit" title="编辑">

          <svg class="icon" viewBox="0 0 1097 1024" width="14" height="14"><path d="M925.72 1024H161.13C72 1024 0 952.32 0 863.57V160.43C0 71.68 72 0 161.16 0h613.67c20.58 0 34.3 13.65 34.3 34.13s-13.72 34.14-34.3 34.14H161.16a91.99 91.99 0 00-92.55 92.16v699.73c0 54.61 41.13 95.57 92.55 95.57h764.59c51.44 0 92.57-40.96 92.57-92.16V337.92c0-20.48 13.7-34.13 34.28-34.13s34.28 13.65 34.28 34.13v525.65c3.41 88.75-72 160.43-161.16 160.43zM456 658.77c-10.29 0-17.14-3.41-24-10.24-13.72-13.65-13.72-34.13 0-47.78L1038.85 23.89a33.26 33.26 0 0148.03 0c13.7 13.66 13.7 34.14 0 47.79L479.96 648.53c-6.83 6.83-13.7 10.24-24 10.24z" fill="currentColor"/></svg>

        </button>

      </div>

    </div>

    ${["dispatching-parallel-agents", "subagent-driven-development", "executing-plans", "writing-plans"].includes(skill.name) ? `<div class="skill-detail-note">此 Skill 仅支持显式调用 /${escapeHtml(skill.name)}，不会被关键词自动匹配</div>` : ""}

    <div class="skill-detail-section">

      <div class="skill-detail-label">描述</div>

      <div class="skill-detail-value">${escapeHtml(skill.description || "无")}</div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">关键词</div>

      <div class="skill-detail-value">${escapeHtml((skill.keywords || []).join(", ") || "无")}</div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">工具</div>

      <div class="skill-detail-value">${escapeHtml((skill.tools || []).join(", ") || "无")}</div>

    </div>

    <div class="skill-detail-section">

      <div class="skill-detail-label">文件路径</div>

      <div class="skill-detail-value">${escapeHtml(skill.path || `data/skills/${skill.dir || skill.name}/SKILL.md`)}</div>

    </div>

  `;

  document.getElementById("settingsSkillToggle").addEventListener("change", () => {

    toggleSkill(skill.name);

    showSkillDetailInSettings(state.skills.find((s) => s.name === skill.name));

    renderSettingsSkillsSidebar();

  });

  document.getElementById("settingsSkillEdit").addEventListener("click", () => openSkillEditor(skill));

}



function renderSystemPanel(container) {

  container.innerHTML = `<h3 style="margin:0 0 14px">${t("system")}</h3>

    <textarea id="settingsSystemText" class="system-prompt-text" style="height:400px" spellcheck="false">${escapeHtml(els.systemPromptText.value)}</textarea>

    <div class="panel-actions" style="margin-top:8px"><span>决定 Agent 的工作边界与编程风格。</span><button id="settingsResetSystem" class="mini-btn" type="button">恢复默认</button></div>`;

  document.getElementById("settingsSystemText").addEventListener("change", () => { els.systemPromptText.value = document.getElementById("settingsSystemText").value; saveSystemPrompt(); });

  document.getElementById("settingsResetSystem").addEventListener("click", () => { els.systemPromptText.value = defaultSystemPrompt; document.getElementById("settingsSystemText").value = defaultSystemPrompt; saveSystemPrompt(); });

}



function renderLanguagePanel(container) {

  const cur = state.lang || "zh";

  container.innerHTML = `<h3 style="margin:0 0 14px">Language</h3>

    <div class="lang-options">

      <button class="lang-opt ${cur === 'zh' ? 'active' : ''}" data-lang="zh">中文</button>

      <button class="lang-opt ${cur === 'en' ? 'active' : ''}" data-lang="en">English</button>

    </div>`;

  container.querySelectorAll(".lang-opt").forEach((b) => {

    b.addEventListener("click", () => {

      setLang(b.dataset.lang);

      renderLanguagePanel(container);

    });

  });

}



function renderThemePanel(container) {

  const current = localStorage.getItem("agent-lite-theme") || "light";

  const themes = [{ v: "light", l: t("light") }, { v: "dark", l: t("dark") }, { v: "system", l: t("system") }];

  container.innerHTML = `<h3 style="margin:0 0 14px">Theme</h3>

    <div class="settings-theme-row" style="max-width:240px">${themes.map((t) => `<button class="theme-opt settings-theme-btn ${t.v === current ? 'active' : ''}" data-theme="${t.v}">${t.l}</button>`).join("")}</div>`;

  container.querySelectorAll(".settings-theme-btn").forEach((b) => {

    b.addEventListener("click", () => { applyTheme(b.dataset.theme); renderThemePanel(container); });

  });

}



// Wire nav clicks

document.getElementById("settingsNav").addEventListener("click", (e) => {

  if (e.target.classList.contains("settings-nav-item")) {

    switchSettingsPanel(e.target.dataset.panel);

  }

});



document.getElementById("closeSettingsPage").addEventListener("click", () => {

  document.getElementById("settingsPage").classList.add("hidden");

});

document.getElementById("settingsPage").addEventListener("click", (e) => {

  if (e.target === e.currentTarget) e.currentTarget.classList.add("hidden");

});



// Redirect old settings buttons to unified page

document.getElementById("settingsModels").addEventListener("click", () => {

  settingsDropdown.classList.add("hidden");

  openSettingsPage("models");

});

document.getElementById("settingsMemory").addEventListener("click", () => {

  settingsDropdown.classList.add("hidden");

  openSettingsPage("memory");

});

document.getElementById("settingsSkills").addEventListener("click", () => {

  settingsDropdown.classList.add("hidden");

  openSettingsPage("skills");

});

document.getElementById("closeSkills").addEventListener("click", () => {

  document.getElementById("skillsModal").classList.add("hidden");

});

document.getElementById("skillsModal").addEventListener("click", (e) => {

  if (e.target === e.currentTarget) e.currentTarget.classList.add("hidden");

});

document.getElementById("skillAddBtn").addEventListener("click", () => openSkillEditor(null));

document.getElementById("closeSkillEditor").addEventListener("click", closeSkillEditor);

document.getElementById("cancelSkillEdit").addEventListener("click", closeSkillEditor);

document.getElementById("saveSkillEdit").addEventListener("click", saveSkillEdit);

document.getElementById("skillEditorModal").addEventListener("click", (e) => {

  if (e.target === e.currentTarget) closeSkillEditor();

});

document.getElementById("settingsSystem").addEventListener("click", () => {

  settingsDropdown.classList.add("hidden");

  openSettingsPage("system");

});

document.getElementById("closeSystemPrompt").addEventListener("click", () => {

  document.getElementById("systemPromptModal").classList.add("hidden");

});

document.getElementById("systemPromptModal").addEventListener("click", (e) => {

  if (e.target === e.currentTarget) e.currentTarget.classList.add("hidden");

});

document.querySelectorAll(".theme-opt").forEach((btn) => {

  btn.addEventListener("click", () => {

    applyTheme(btn.dataset.theme);

    updateThemeButtons();

  });

});



function updateThemeButtons() {

  const current = localStorage.getItem("agent-lite-theme") || "light";

  document.querySelectorAll(".theme-opt").forEach((btn) => {

    btn.classList.toggle("active", btn.dataset.theme === current);

  });

}

document.addEventListener("click", (e) => {

  if (!e.target.closest(".settings-dropdown")) settingsDropdown.classList.add("hidden");

  if (!e.target.closest(".session-more-btn") && !e.target.closest(".session-more-menu")) {

    closeAllSessionMenus();

  }

});

els.closeSettings.addEventListener("click", () => showSettings(false));

els.closeMemory.addEventListener("click", () => hideMemoryPanel());

els.cancelMemory.addEventListener("click", () => hideMemoryPanel());

els.memoryModal.addEventListener("click", (event) => {

  if (event.target === els.memoryModal) hideMemoryPanel();

});

els.memoryForm.addEventListener("submit", (event) => {

  event.preventDefault();

  saveMemorySubmit();

});

els.settingsModal.addEventListener("click", (event) => {

  if (event.target === els.settingsModal) showSettings(false);

});

els.cancelApplyEdit.addEventListener("click", hideApplyConfirm);

els.cancelApplyEditX.addEventListener("click", hideApplyConfirm);

els.confirmApplyEdit.addEventListener("click", () => commitPendingEdit());

els.confirmEditModal.addEventListener("click", (event) => {

  if (event.target === els.confirmEditModal) hideApplyConfirm();

});

document.addEventListener("keydown", (event) => {

  if (event.key === "Escape" && !els.confirmEditModal.classList.contains("hidden")) {

    hideApplyConfirm();

  }

});



document.getElementById("explorerHead").addEventListener("click", () => {

  const explorer = document.querySelector(".explorer");

  explorer.classList.toggle("collapsed");

  localStorage.setItem("agent-lite-explorer-collapsed", explorer.classList.contains("collapsed") ? "1" : "0");

});



// Perm pill dropdown

els.permPillBtn.addEventListener("click", (e) => {

  e.stopPropagation();

  const dd = els.permPillDropdown;

  const opening = dd.classList.contains("hidden");

  if (opening) {

    const btnRect = els.permPillBtn.getBoundingClientRect();

    const spaceBelow = window.innerHeight - btnRect.bottom;

    dd.classList.toggle("up", spaceBelow < 180 + 16);

  }

  els.permPillWrap.classList.toggle("open");

  dd.classList.toggle("hidden");

});



els.permPillDropdown.addEventListener("click", (e) => {

  const opt = e.target.closest(".model-pill-option");

  if (!opt) return;

  const val = opt.dataset.value;

  setPermLevel(val);

  state.permissionProfile = val;

  localStorage.setItem("agent-lite-permission-profile", val);

  els.permPillWrap.classList.remove("open");

  els.permPillDropdown.classList.add("hidden");

});



document.addEventListener("click", (e) => {

  if (!els.permPillWrap.contains(e.target)) {

    els.permPillWrap.classList.remove("open");

    els.permPillDropdown.classList.add("hidden");

  }

});



els.sessionTitle.addEventListener("change", () => saveCurrentSession().catch(() => {}));



els.chatForm.addEventListener("submit", async (event) => {

  event.preventDefault();

  const text = els.prompt.value.trim();
  const hasImages = state.attachedImages.length > 0;
  if (!text && !hasImages) return;

  if (state.isStreaming) {
    // Queue message instead of aborting
    state.messageQueue.push({ text, images: [...state.attachedImages] });
    els.prompt.value = "";
    els.prompt.rows = 2;
    state.attachedImages = [];
    renderImageThumbs();
    updateSendButtonState();
    renderMessages();
    return;
  }

  els.prompt.value = "";

  els.prompt.rows = 2;

  updateSendButtonState();

  // Request notification permission on first send (for permission-needed alerts)
  if ("Notification" in window && Notification.permission === "default") {
    try { Notification.requestPermission(); } catch (_) {}
  }

  try {

    await sendMessage(text);

  } catch (err) {

    if (err.name === "AbortError") {

      state.messages.forEach((msg) => { msg.streaming = false; });

      const last = state.messages.at(-1);

      if (last?.role === "assistant") last.content = `${last.content || ""}\n\n[已暂停输出]`;

      renderMessages();

      await saveCurrentSession();

    } else {

      state.messages = state.messages.filter((msg) => !msg.streaming);

      appendSystemError(err.message);

    }

  } finally {

    state.abortController = null;

    setStreaming(false);

    els.messages.scrollTop = els.messages.scrollHeight;

    if (state.sessionId) saveCurrentSession().catch(() => {});

  }

});



els.newChat.addEventListener("click", () => {

  if (state.abortController) state.abortController.abort();
  state.messageQueue = [];

  state.sessionId = null;

  state.messages = [];

  state._lastRenderedHtml = null;
  state._lastQueueLen = 0;

  state.stats = { input: 0, output: 0, cache: 0 };

  state.pendingEdits = {};

  els.sessionTitle.value = "";

  localStorage.removeItem("agent-lite-last-session");

  renderMessages();

  renderSessions();

  updateStatsPanel();

  updateSendButtonState();

});



els.exportChat.addEventListener("click", exportMarkdown);



async function init() {

    applyTheme(localStorage.getItem("agent-lite-theme") || "light");

    applyPreviewWidth();

    applySidebarSessionHeight();

    // Restore sidebar collapsed state
    if (localStorage.getItem("agent-lite-sidebar-hidden") === "1") {
      els.shell.classList.add("sidebar-hidden");
    }

    applySidebarWidth();

    // Restore explorer collapsed state

    if (localStorage.getItem("agent-lite-explorer-collapsed") === "1") {

      document.querySelector(".explorer").classList.add("collapsed");

    }

    els.apiKey.value = localStorage.getItem("agent-lite-key") || "";

    els.baseUrl.value = localStorage.getItem("agent-lite-base-url") || "http://localhost:3000";

  els.temperature.value = localStorage.getItem("agent-lite-temperature") || "0.2";

  const savedMax = localStorage.getItem("agent-lite-max-tokens") || "auto";

  els.maxTokens.value = savedMax;

  setThinkingLevel(localStorage.getItem("agent-lite-thinking") || "auto");

  els.toolPreset.value = localStorage.getItem("agent-lite-tool-preset") || "default";

  const savedPerm = localStorage.getItem("agent-lite-permission-profile") || "accept";

  state.permissionProfile = savedPerm;

  setPermLevel(savedPerm);

  els.systemPromptText.value = localStorage.getItem("agent-lite-system-prompt") || defaultSystemPrompt;

  updateModePromptPreview();



  // Restore no-project state before loading files

  if (localStorage.getItem("agent-lite-no-project") === "1") {

    state._noProject = true;

    els.cwdPathText.textContent = "未选择";

    els.projectRootShort.title = "未选择项目目录";

  }



  renderMessages();

  if (!state._noProject) {

    await loadConfig().catch((err) => {

      els.fileTree.innerHTML = `<div class="muted-line" style="padding:8px;">${escapeHtml(err.message)}</div>`;

    });

  } else {

    renderFileTree();

  }

  await loadProjectContext();

  await loadMemoryContext();

  await loadSkills();

  await refreshSessions();

  // Restore last active session if any, otherwise stay on welcome page

  const lastId = localStorage.getItem("agent-lite-last-session");

  if (lastId && state.sessions.some((s) => s.id === lastId)) {

    await loadSession(lastId);

  }

  if (els.apiKey.value.trim()) await refreshModels();

  // Restore preview state

  // Restore preview pane state — must be after config/session load
  if (localStorage.getItem("agent-lite-preview-open") === "1") {

    const savedPath = localStorage.getItem("agent-lite-preview-path");

    if (savedPath) {

      try {
        await loadFile(savedPath);
      } catch (_) {
        // File may no longer exist or path changed — clean up
        localStorage.removeItem("agent-lite-preview-open");
        localStorage.removeItem("agent-lite-preview-path");
      }

    }

  }

  updateSendButtonState();

  updateStatsPanel();

}



init().catch((err) => appendSystemError(err.message));

