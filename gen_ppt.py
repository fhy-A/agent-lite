"""
Agent Lite product intro PPT — 13 slides, brand-blue + two-column layout.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pathlib import Path

OUTPUT = Path.home() / "Desktop" / "Agent-Lite-产品介绍.pptx"

# Colors
PRI  = RGBColor(0x25, 0x63, 0xEB)  # primary blue
DRK  = RGBColor(0x1D, 0x4D, 0xD8)  # dark blue
LIT  = RGBColor(0x60, 0xA5, 0xFA)  # light blue
GRY  = RGBColor(0x6F, 0x79, 0x88)  # gray
WHT  = RGBColor(0xFF, 0xFF, 0xFF)
BLK  = RGBColor(0x1D, 0x23, 0x2C)
LGRY = RGBColor(0xF5, 0xF6, 0xF9)  # light gray bg
GN   = RGBColor(0x22, 0xC5, 0x5E)
RD   = RGBColor(0xDC, 0x26, 0x26)

FW = 13.333  # full width in inches
FH = 7.5

prs = Presentation()
prs.slide_width = Inches(FW)
prs.slide_height = Inches(FH)


def bg(s, c):
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = c


def rect(s, x, y, w, h, c, r=0):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE if r == 0 else MSO_SHAPE.ROUNDED_RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = c; sh.line.fill.background()
    if r: sh.adjustments[0] = 0.05
    return sh


def tb(s, x, y, w, h, t, fs=18, c=BLK, b=False, a=PP_ALIGN.LEFT):
    bx = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    bx.text_frame.word_wrap = True
    p = bx.text_frame.paragraphs[0]
    p.text = t; p.font.size = Pt(fs); p.font.color.rgb = c
    p.font.bold = b; p.font.name = "Microsoft YaHei"; p.alignment = a
    return bx.text_frame


def card(s, x, y, w, h, title, body, tc=PRI, bc=LGRY):
    r = rect(s, x, y, w, h, bc, r=1)
    tb(s, x+0.2, y+0.1, w-0.4, 0.4, title, fs=16, c=tc, b=True)
    tb(s, x+0.2, y+0.5, w-0.4, h-0.7, body, fs=12, c=BLK)


# ── Cover ──
def cover(number=""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, DRK)
    rect(s, 0, 0, 0.15, FH, LIT)  # left accent bar
    rect(s, 0.15, 0, 0.06, FH, RGBColor(0x37, 0x73, 0xF0))
    tb(s, 1, 2.2, 11, 1.2, "Agent Lite", fs=52, c=WHT, b=True)
    tb(s, 1, 3.4, 11, 1.5, "一个真正能操作你项目文件的 AI 编程助手", fs=22, c=RGBColor(0xBA, 0xD5, 0xFF))
    if number:
        tb(s, 1, 0.5, 2, 0.6, number, fs=72, c=RGBColor(0x37, 0x73, 0xF0), b=True)
    rect(s, 1, 5.5, 2.5, 0.03, LIT)
    tb(s, 1, 5.8, 6, 0.5, "v0.5.2  ·  github.com/fhy-A/agent-lite", fs=14, c=RGBColor(0x8F, 0xB4, 0xF0))
    return s


# ── Content slide with title bar ──
def content(title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, WHT)
    rect(s, 0, 0, FW, 0.04, PRI)
    tb(s, 0.8, 0.25, 11, 0.6, title, fs=26, c=DRK, b=True)
    rect(s, 0.8, 0.75, 1.5, 0.03, LIT)
    return s


# ── Two-column layout ──
def two_col(s, left_title, left_items, right_title, right_items):
    # Left panel
    card_left = rect(s, 0.6, 1.2, 5.8, 5.8, LGRY, r=1)
    tb(s, 0.9, 1.4, 5.2, 0.4, left_title, fs=18, c=DRK, b=True)
    y = 2.0
    for item in left_items:
        tb(s, 1.2, y, 5.1, 0.35, item, fs=13, c=BLK)
        y += 0.42

    # Right panel
    card_right = rect(s, 6.8, 1.2, 5.8, 5.8, LGRY, r=1)
    tb(s, 7.1, 1.4, 5.2, 0.4, right_title, fs=18, c=DRK, b=True)
    y = 2.0
    for item in right_items:
        tb(s, 7.4, y, 5.1, 0.35, item, fs=13, c=BLK)
        y += 0.42


# ── Cards row ──
def card_row(s, cards):
    """cards: list of (title, body, color)"""
    n = len(cards)
    w = (FW - 1.6 - (n-1)*0.3) / n
    x = 0.8
    for title, body, c in cards:
        r = rect(s, x, 1.5, w, 4.5, LGRY, r=1)
        tb(s, x+0.2, 1.7, w-0.4, 0.4, title, fs=16, c=c, b=True)
        tb(s, x+0.2, 2.2, w-0.4, 3.6, body, fs=12, c=BLK)
        x += w + 0.3


# ════════════════════════════════════════════════
# SLIDE 1: Cover
# ════════════════════════════════════════════════
cover()

# ════════════════════════════════════════════════
# SLIDE 2: Positioning
# ════════════════════════════════════════════════
s = content("定位：谁用、为什么用")
cards = [
    ("目标用户", "独立开发者 / 小团队\n重视数据隐私的程序员\n不想被特定 IDE 绑定的开发者", PRI),
    ("产品定位", "不是 VS Code 插件 — 不绑定编辑器\n不是 SaaS 服务 — 数据不传云端\n不是 CLI 工具 — 有完整图形界面\n\n一个本地运行的、浏览器打开的、\n能直接操作文件的 AI 编程搭档", DRK),
    ("核心理念", "本地优先 — 127.0.0.1\n安全可控 — 权限分级 + 审批\n零门槛 — 打开浏览器即用\n数据自主 — 代码不离开电脑", LIT),
]
card_row(s, cards)

# ════════════════════════════════════════════════
# SLIDE 3: Pain points
# ════════════════════════════════════════════════
s = content("为什么还需要另一个 AI 工具？")
two_col(s, "用通用 AI 写代码的 6 个痛点",
    ["✗ 只能聊天 — 让它改文件，它输出整段让你自己动手",
     "✗ 来回复制粘贴 — 编辑器和聊天窗口来回切换",
     "✗ 上下文爆炸 — 50 轮后开始遗忘或胡言乱语",
     "✗ 串行等待 — 多个任务只能一个一个排队",
     "✗ 无法回退 — 试错只能新建聊天，丢失上下文",
     "✗ 数据外传 — 公司代码不敢往第三方平台贴"],
    "Agent Lite 的 6 个解法",
    ["✓ 直接在你的项目里读写、搜索、执行命令",
     "✓ 生成 diff → 你审批 → 自动写入，原件自动备份",
     "✓ 超 95% 自动压缩为摘要，保留关键信息",
     "✓ 一次启动 3 个子 Agent 并行分析不同模块",
     "✓ 当前消息一键分叉，独立探索后随时切回",
     "✓ 100% 本地运行，数据不离开你的电脑"])

# ════════════════════════════════════════════════
# SLIDE 4-7: Scenarios
# ════════════════════════════════════════════════
for num, title, scenario, steps, diff in [
    (1, "场景一：代码重构",
     '"帮我把 app.js 里超过 200 行的函数拆小"',
     ["search_files 正则定位所有函数定义和行号",
      "read_file 逐个读取长函数内容，分析拆分点",
      "propose_edit 生成 diff → 你逐条审批",
      "apply_edit 一键写入 + 自动备份原文件",
      "run_command 跑 pytest 验证没破坏测试"],
     "从提出需求到代码落盘，全程在浏览器内闭环。\n不像 Chat：复制一段 → 输出修改 → 粘贴回去 → 漏了换行还要排查。"),
    (2, "场景二：数据分析",
     '"分析 sales.xlsx 季度趋势，生成 Word 报告"',
     ["openpyxl 读取所有 Sheet，pandas 做数据透视",
      "python -c 执行分析脚本，stdout 直接返回结果",
      "python-docx 生成图文报告，保存到 output/",
      "文件树里直接预览生成的报告"],
     "Excel → 分析 → 报告，全程不离开 Agent Lite。\n不像 Chat：上传 → 输出表格 → 你手动排版到 Word。\n支持 docx / xlsx / pptx / pdf / csv 读 + 写 + 创建。"),
    (3, "场景三：并行探索",
     '"同时检查 app.js、server.py、styles.css 的潜在问题"',
     ["主 Agent 拆分为 3 个独立任务，各自指定文件范围",
      "3 个子 Agent 同时运行，各自读取文件并分析",
      "主 Agent 收集 3 份报告，去重合并输出审查结论",
      "每个子 Agent 独立上下文 + 独立用量跟踪"],
     "3 个文件的审查同时完成，不是串行等。\n不像 Chat：问完一个再问下一个 → 等 3 轮 → 丢失上下文。"),
    (4, "场景四：方案对比",
     '"Flask 改 FastAPI 试试？不好再切回来"',
     ["点击 Branches → 新建分支，当前上下文自动复制",
      "新分支里用 FastAPI 重写，原分支完全不受影响",
      "测试后满意就继续；不满意点原节点秒切回",
      "支持多层嵌套 A→B→C，删除父分支自动升级子分支"],
     "分支独立保存，互不影响。\n不像 Chat：新建聊天 → 重新描述背景 → 还是丢了之前的上下文。"),
]:
    s = content(title)
    # Left: scenario + steps
    card(s, 0.6, 1.2, 5.8, 4.0, scenario, "", PRI)
    y = 1.6
    for i, step in enumerate(steps):
        tb(s, 1.0, y, 5.2, 0.3, f"{i+1}. {step}", fs=13, c=BLK)
        y += 0.42
    # Right: diff highlight
    card(s, 6.8, 1.2, 5.8, 4.0, "💡 差异", diff, GN)
    # Label
    tb(s, 0.6, 5.6, 1.5, 0.3, f"场景 0{num}", fs=11, c=GRY)

# ════════════════════════════════════════════════
# SLIDE 8: Skills + Memory
# ════════════════════════════════════════════════
s = content("Skill 系统 + 记忆系统")
card(s, 0.6, 1.2, 5.8, 5.5, "Skill 系统（14 个内置技能）",
    "可复用的自动化任务模板，Agent 根据对话自动匹配并执行\n\n"
    "▸ office-files — Word/Excel/PPT/PDF 读写\n"
    "▸ code-review / receiving-code-review — 代码审查全流程\n"
    "▸ test-driven-development — TDD 驱动开发\n"
    "▸ python-testing — Python 测试框架\n"
    "▸ design-aesthetics — UI 设计规范\n"
    "▸ brainstorming / writing-plans / executing-plans\n\n"
    "支持用户自定义 — Markdown 编写，0 代码门槛", PRI)
card(s, 6.8, 1.2, 5.8, 5.5, "记忆系统",
    "跨会话、跨项目保留关键信息\n\n"
    "▸ 自动提取：对话结束后 Agent 主动提炼关键信息\n"
    "▸ 手动管理：Memory 面板增删改查\n"
    "▸ 智能匹配：新对话根据上下文自动注入相关记忆\n\n"
    "Skill = 可复用的能力模板\n"
    "Memory = 跨会话的知识库\n\n"
    "两者结合让 Agent 越用越懂你的项目。", DRK)

# ════════════════════════════════════════════════
# SLIDE 9: Permission
# ════════════════════════════════════════════════
s = content("权限体系：人机协作的安全模型")
cards = [
    ("Plan 计划模式", "只读 + 生成方案\n修改操作需要审批\n\n适合：调研、代码审查\n学习陌生项目", PRI),
    ("Accept 审批模式（默认）", "读 + 写 + 执行\n文件修改弹窗确认\n\n适合：日常开发\n推荐大多数场景使用", DRK),
    ("Bypass 自动执行", "全自动\n跳过审批\n\n适合：完全信任的脚本\n批量自动化任务", LIT),
]
card_row(s, cards)
tb(s, 0.8, 6.2, 11, 0.8,
   "核心理念：Agent 有权限做事，但你不点头它不会改你的文件。"
   "安全不是「锁死权限」，而是「每步都可审、可拒、可撤销」。"
   "  |  每次写入前自动备份原件到 data/file-backups/，改错了随时回滚。",
   fs=13, c=GRY)

# ════════════════════════════════════════════════
# SLIDE 10: Safety
# ════════════════════════════════════════════════
s = content("你的代码安全吗？")
tb(s, 0.8, 1.0, 11, 0.5, "当 AI 能操作你的文件时，安全不是「信不信它」，而是「你能控到哪一步」。", fs=16, c=GRY)
cards = [
    ("🛡 命令拦截", "即使模型被诱导执行危险命令也会拒绝\n\nrm -rf / → 拦截\nformat C: → 拦截\ncurl ... | bash → 拦截\nPowerShell 编码命令 → 拦截", PRI),
    ("🛡 文件保护", "任何时候不会意外覆盖或删除\n\n写入项目外路径 → 重定向到安全目录\n访问系统目录 → 拒绝\n每次写入前自动备份原件", DRK),
    ("🛡 网络隔离", "Agent 不会成为内网渗透跳板\n\n127.0.0.1 → 拦截\n192.168.x.x → 拦截\n内网 IP 全拦截\n链接本地地址 → 拦截", LIT),
    ("🛡 提示注入防护", "精心设计的恶意提示词也能识别\n\n12 种攻击模式实时扫描\n指令覆盖/角色混淆/信息提取\n零宽字符/编码绕过 → 检测", GN),
]
card_row(s, cards)

# ════════════════════════════════════════════════
# SLIDE 11: Comparison
# ════════════════════════════════════════════════
s = content("主流编程 Agent 对比")
# Simplified comparison as bullet cards
two_col(s,
    "Agent Lite vs 其他产品的关键差异",
    ["· 唯一无需安装任何运行时 — 浏览器即用",
     "· 唯一 100% 本地存储 — 代码不经第三方服务器",
     "· 唯一支持会话分支 — 多层树形，试错成本最低",
     "· 唯一完全免费开源",
     "· 安装包仅 30 MB — 最轻量的选择",
     "· 零配置开箱即用 — 下载、双击、开始"],
    "同类产品参考信息",
    ["Cursor: VS Code 分支 IDE, $20-200/月, Cloud",
     "Copilot: IDE 插件, $10-39/月, Cloud",
     "Claude Code: CLI 工具, $20/月, npm 安装",
     "Codex Desktop: 桌面应用, 需会员, OpenAI 限定",
     "",
     "* 以上信息基于 2026 年 7 月公开资料",
     "* 各产品持续更新，具体以官方为准"],
)

# ════════════════════════════════════════════════
# SLIDE 12: Tech stack
# ════════════════════════════════════════════════
s = content("技术栈")
cards = [
    ("零前端依赖", "无 npm / webpack / babel\n纯 JavaScript 12,000 行\n单文件 · 零构建步骤\n21 个 Feather SVG 图标", PRI),
    ("Python stdlib", "http.server 原生 HTTP\n无 Flask / Django / FastAPI\nJSON 文件存储\n可选: docx, openpyxl, PyPDF2", DRK),
    ("412 项自动化测试", "20 秒全量运行\n零外部依赖 (除 requests)\nCI 就绪 · 改完即知\nP0 安全 + P0 路由 + P1 并发", LIT),
    ("轻量分发", "127.0.0.1 本地运行\n数据绝不离开电脑\n可编译为 30 MB .exe\n系统托盘 + 自动更新", GN),
]
card_row(s, cards)

# ════════════════════════════════════════════════
# SLIDE 13: Roadmap + End
# ════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, DRK)
rect(s, 0, 0, 0.15, FH, LIT)
rect(s, 0.15, 0, 0.06, FH, RGBColor(0x37, 0x73, 0xF0))
tb(s, 1, 0.4, 11, 0.7, "路线图", fs=30, c=WHT, b=True)
rect(s, 1, 0.95, 1.5, 0.03, LIT)

phases = [
    ("已完成 v0.5.2", "独立 Web 版",
     "命令安全策略\n子 Agent 并行调度\n会话分支功能\nSkill 系统 14 技能\n办公文档全支持\ni18n 中英双语\n412 项自动化测试"),
    ("进行中", "轻量集成",
     "API Key 自主配置\n自由切换模型\n深色/浅色主题\n一键 EXE 分发"),
    ("规划中", "生态扩展",
     "更多模型适配\nmacOS / Linux 支持\n插件/扩展体系\n协作功能探索"),
]
x = 0.8
for label, title, desc in phases:
    r = rect(s, x, 1.8, 3.7, 4.5, RGBColor(0xF0, 0xF4, 0xFD), r=1)
    tb(s, x+0.2, 2.0, 3.3, 0.35, label, fs=13, c=PRI, b=True)
    tb(s, x+0.2, 2.4, 3.3, 0.35, title, fs=17, c=DRK, b=True)
    tb(s, x+0.2, 2.9, 3.3, 3.2, desc, fs=13, c=BLK)
    x += 4.1

tb(s, 1, 6.5, 11, 0.5, "支持自主配置 API Key 和 Base URL，接入任意兼容 OpenAI 协议的模型服务", fs=12, c=RGBColor(0x8F, 0xB4, 0xF0))

# End
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, DRK)
rect(s, 0, 0, 0.15, FH, LIT)
rect(s, 0.15, 0, 0.06, FH, RGBColor(0x37, 0x73, 0xF0))
tb(s, 1, 2.0, 11, 1.2, "开始你的第一个项目", fs=48, c=WHT, b=True)
tb(s, 1, 3.5, 11, 2.0,
   "打开终端 → cd 到项目目录 → 运行 agent-lite\n\n"
   "浏览器打开 127.0.0.1:3010\n\n"
   "用自然语言驱动代码",
   fs=20, c=RGBColor(0xBA, 0xD5, 0xFF))
rect(s, 1, 5.8, 2.5, 0.03, LIT)
tb(s, 1, 6.1, 6, 0.5, "github.com/fhy-A/agent-lite", fs=14, c=RGBColor(0x8F, 0xB4, 0xF0))

prs.save(str(OUTPUT))
print(f"PPT saved: {OUTPUT}")
