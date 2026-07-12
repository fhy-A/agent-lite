"""
Agent Lite product intro PPT — polished layout, flow charts, balanced spacing.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pathlib import Path

OUTPUT = Path.home() / "Desktop" / "Agent-Lite-产品介绍.pptx"

BLUE   = RGBColor(0x25, 0x63, 0xEB)
BLUE05 = RGBColor(0xF0, 0xF4, 0xFD)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
DARK   = RGBColor(0x1E, 0x29, 0x3B)
BODY   = RGBColor(0x3B, 0x44, 0x54)
MUTED  = RGBColor(0x8A, 0x94, 0xA6)
LIGHT  = RGBColor(0xF2, 0xF3, 0xF7)
GREEN  = RGBColor(0x16, 0xA7, 0x5C)
RED    = RGBColor(0xDC, 0x35, 0x35)
GOLD   = RGBColor(0xD9, 0x7A, 0x0C)
BG_D   = RGBColor(0x1A, 0x23, 0x33)

FW, FH = 13.333, 7.5
prs = Presentation()
prs.slide_width  = Inches(FW)
prs.slide_height = Inches(FH)


def bg(s, c): s.background.fill.solid(); s.background.fill.fore_color.rgb = c


def tb(s, x, y, w, h, t, fs=16, c=BODY, bold=False, align=PP_ALIGN.LEFT, name="Microsoft YaHei"):
    bx = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    bx.text_frame.word_wrap = True
    p = bx.text_frame.paragraphs[0]
    p.text = t; p.font.size = Pt(fs); p.font.color.rgb = c
    p.font.bold = bold; p.font.name = name; p.alignment = align
    return bx.text_frame


def rule(s, x, y, w, c=RGBColor(0xE0, 0xE4, 0xEA)):
    sh = s.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Pt(1))
    sh.fill.solid(); sh.fill.fore_color.rgb = c; sh.line.fill.background()


def rect(s, x, y, w, h, c, r=0):
    sh = s.shapes.add_shape(5 if r else 1, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = c; sh.line.fill.background()
    if r: sh.adjustments[0] = 0.04
    return sh


def tbox(s, x, y, w, h, text, fs=13, c=WHITE, bold=False, align=PP_ALIGN.CENTER):
    """Centered text box with vertical centering"""
    bx = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    bx.text_frame.word_wrap = True
    bx.text_frame.paragraphs[0].alignment = align
    # Vertical centering
    bx.text_frame.paragraphs[0].space_before = Pt(0)
    bx.text_frame.paragraphs[0].space_after = Pt(0)
    p = bx.text_frame.paragraphs[0]
    p.text = text; p.font.size = Pt(fs); p.font.color.rgb = c
    p.font.bold = bold; p.font.name = "Microsoft YaHei"; p.alignment = align
    return bx


def arrow_right(s, x, y, w=0.4):
    """Simple right arrow between flow boxes"""
    sh = s.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Pt(2))
    sh.fill.solid(); sh.fill.fore_color.rgb = BLUE; sh.line.fill.background()
    # arrowhead
    tx = x + w
    for dx, dy in [(0, -2), (0, 2), (3, 0)]:
        pass  # skip complex arrow, just use line
    return sh


def card(s, x, y, w, h, title="", body="", accent=BLUE, center_body=False):
    box = rect(s, x, y, w, h, LIGHT, r=1)
    ac = rect(s, x, y+0.12, Pt(3), h-0.24, accent)
    if title:
        tb(s, x+0.25, y+0.12, w-0.5, 0.35, title, fs=15, c=DARK, bold=True)
    if body:
        al = PP_ALIGN.CENTER if center_body else PP_ALIGN.LEFT
        lines = body.count("\n") + 1
        body_h = min(h - 0.55, lines * 0.22)
        yb = y + (h - body_h) / 2 + 0.1 if center_body else y + 0.5
        tb(s, x+0.25, yb, w-0.5, h-0.7, body, fs=12, c=BODY, align=al)


# ── flow_box: a rounded rect with centered text ──
def flow_box(s, x, y, w, h, text, c=BLUE, fs=11):
    box = rect(s, x, y, w, h, c, r=1)
    tbox(s, x+0.05, y+0.05, w-0.1, h-0.1, text, fs=fs, bold=False)
    return box


def flow_arrow(s, x, y):
    """Draw a right-pointing arrow between flow boxes"""
    line = s.shapes.add_connector(1, Inches(x), Inches(y), Inches(x+0.35), Inches(y))
    line.line.color.rgb = BLUE; line.line.width = Pt(1.5)
    # triangle marker
    arr = s.shapes.add_shape(6, Inches(x+0.3), Inches(y-0.04), Inches(0.1), Inches(0.08))
    arr.fill.solid(); arr.fill.fore_color.rgb = BLUE; arr.line.fill.background()


def flow_chart(s, x, y, steps, box_w=1.8, box_h=0.65, gap=0.5):
    """Render horizontal flow chart: [step1] → [step2] → ... with centered text"""
    n = len(steps)
    total_w = n * box_w + (n-1) * gap
    start_x = (FW - total_w) / 2
    for i, step in enumerate(steps):
        bx = start_x + i * (box_w + gap) + gap/2
        by = y + 0.1
        flow_box(s, bx, by, box_w, box_h, step, BLUE, fs=11)
        if i < n - 1:
            flow_arrow(s, bx + box_w, by + box_h/2)


# ── COVER ──
def cover():
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, DARK)
    # subtle texture: diagonal line
    for i in range(20):
        alpha = 0.015 - i * 0.0005
        if alpha <= 0: break
    rect(s, 0, 0, FW, FH, DARK)
    rule(s, 2.5, 3.5, 3, RGBColor(0x50, 0x85, 0xF0))
    tb(s, 2.5, 2.2, 9, 1, "Agent Lite", fs=56, c=WHITE, bold=True)
    tb(s, 2.5, 3.8, 9, 0.8, "一个真正能操作你项目文件的 AI 编程助手", fs=22, c=RGBColor(0xA0, 0xBE, 0xF5))
    tb(s, 2.5, 5.8, 6, 0.4, "v0.5.2  ·  github.com/fhy-A/agent-lite", fs=13, c=RGBColor(0x70, 0x90, 0xD0))


def section(number, title, subtitle=""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, BLUE05)
    rule(s, 2, 3.4, 2)
    tb(s, 2, 2.2, 9, 0.5, number, fs=15, c=MUTED, bold=True)
    tb(s, 2, 2.7, 9, 0.8, title, fs=36, c=DARK, bold=True)
    if subtitle:
        tb(s, 2, 3.8, 9, 0.6, subtitle, fs=15, c=MUTED)


def content(title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, WHITE)
    tb(s, 1.2, 0.45, 10, 0.55, title, fs=24, c=DARK, bold=True)
    rule(s, 1.2, 0.98, 2)
    return s


def card_row(s, items, y=1.5, h=4.8):
    n = len(items)
    gap = 0.3
    w = (FW - 1.6 - gap*(n-1)) / n
    x = 0.8
    for title, body, accent in items:
        card(s, x, y, w, h, title, body, accent, center_body=True)
        x += w + gap


def two_col(s, left_title, left_items, right_title, right_items, y=1.4):
    card(s, 0.7, y, 5.8, 5.3, left_title, left_items, RED)
    card(s, 7.3, y, 5.8, 5.3, right_title, right_items, GREEN)


# ═══════════════════════════════════
# 1. COVER
# ═══════════════════════════════════
cover()

# ═══════════════════════════════════
# 2. POSITIONING
# ═══════════════════════════════════
s = content("定位：谁用、为什么用")
card_row(s, [
    ("目标用户", "独立开发者 / 小团队\n重视数据隐私的程序员\n不想被特定 IDE 绑定的开发者", BLUE),
    ("产品定位", "不是 VS Code 插件 — 不绑定编辑器\n不是 SaaS 服务 — 数据不传云端\n不是 CLI 工具 — 有完整图形界面\n\n一个本地运行、浏览器打开的\n能直接操作文件的 AI 编程搭档", BLUE),
    ("核心理念", "本地优先 — 127.0.0.1\n安全可控 — 权限分级 + 审批\n零门槛 — 打开浏览器即用\n数据自主 — 代码不离开电脑", BLUE),
])

# ═══════════════════════════════════
# 3. PAIN POINTS
# ═══════════════════════════════════
s = content("为什么还需要另一个 AI 工具？")
two_col(s,
    "通用 AI 写代码的 6 个痛点",
    "✗ 只能聊天 — 让它改代码它输出整段\n✗ 来回复制粘贴 — 来回切换\n✗ 上下文爆炸 — 50 轮后胡言乱语\n✗ 多任务串行 — 一个等一个\n✗ 试错无法回退 — 只能新建聊天\n✗ 数据外传 — 代码不敢贴",
    "Agent Lite 的 6 个解法",
    "✓ 直接读写项目文件，不是聊天\n✓ 生成 diff → 审批 → 自动写入+备份\n✓ 超 95% 自动压缩为摘要\n✓ 一次启动 3 个子 Agent 并行\n✓ 一键分叉，随时切回\n✓ 100% 本地，数据不离开电脑",
    y=1.3)

# ═══════════════════════════════════
# 4-7. SCENARIOS with flow charts
# ═══════════════════════════════════
scenarios = [
    ("场景一：代码重构",
     '"帮我把 app.js 里超过 200 行的函数拆小"',
     ["search_files\n定位函数", "read_file\n读取内容", "propose_edit\n生成 diff", "apply_edit\n写入+备份", "pytest\n验证"],
     "差异：全程在浏览器内闭环。\n不像 Chat：复制 → 输出修改 → 粘贴回去 → 漏了换行还要排查。"),
    ("场景二：数据分析",
     '"分析 sales.xlsx 季度趋势，生成 Word 报告"',
     ["openpyxl\n读取 Excel", "pandas\n数据透视", "python-docx\n生成报告", "output/\n保存预览"],
     "差异：Excel → 分析 → 报告，全程不离开。\n不像 Chat：上传 → 输出表格 → 手动排版。\n支持 docx/xlsx/pptx/pdf/csv。"),
    ("场景三：并行探索",
     '"同时检查 app.js、server.py、styles.css"',
     ["主 Agent\n拆分 3 个任务", "子 Agent 1\n检查 app.js", "子 Agent 2\n检查 server.py", "子 Agent 3\n检查 css", "合并输出\n审查报告"],
     "差异：3 个文件同时审查，不是串行等。\n不像 Chat：问完一个再问下一个 → 等 3 轮。"),
    ("场景四：方案对比",
     '"Flask 改 FastAPI 试试？不好再切回来"',
     ["Branches\n新建分支", "新分支\n独立探索", "满意则\n继续推进", "不满意\n秒切回"],
     "差异：分支独立保存，互不影响。\n不像 Chat：新建聊天 → 重新描述背景 → 丢了上下文。"),
]

for title, scenario, steps, diff in scenarios:
    s = content(title)
    # Left: description + flow
    card(s, 0.7, 1.3, 5.8, 1.6, scenario, "", BLUE)
    # Flow chart
    n = len(steps)
    box_w = min(1.5, 5.5 / n - 0.15)
    gap = (5.5 - n * box_w) / (n + 1)
    x = 0.7 + gap
    y = 3.3
    for i, step in enumerate(steps):
        flow_box(s, x, y, box_w, 0.7, step, BLUE, fs=10)
        if i < n - 1:
            ax = x + box_w
            ay = y + 0.35
            a = s.shapes.add_shape(6, Inches(ax), Inches(ay-0.03), Inches(gap*0.6), Inches(0.06))
            a.fill.solid(); a.fill.fore_color.rgb = BLUE; a.line.fill.background()
        x += box_w + gap
    # Right: diff
    card(s, 7.3, 1.3, 5.8, 3.0, "差异", diff, GREEN)

# ═══════════════════════════════════
# 8. SKILLS + MEMORY
# ═══════════════════════════════════
s = content("Skill 系统 + 记忆系统")
card(s, 0.7, 1.3, 5.8, 5.3, "Skill 系统（14 个内置技能）",
    "可复用的自动化任务模板，Agent 根据对话自动匹配。\n\n"
    "office-files — Word / Excel / PPT / PDF 读写\n"
    "code-review — 代码审查全流程\n"
    "test-driven-development — TDD 驱动开发\n"
    "python-testing — Python 测试框架\n"
    "design-aesthetics — UI 设计规范\n"
    "brainstorming / writing-plans / executing-plans\n\n"
    "支持自定义 — Markdown 编写，零代码门槛", BLUE)
card(s, 7.3, 1.3, 5.8, 5.3, "记忆系统",
    "跨会话、跨项目保留关键信息。\n\n"
    "自动提取 — Agent 对话结束后主动提炼\n"
    "手动管理 — Memory 面板增删改查\n"
    "智能匹配 — 新对话自动注入相关记忆\n\n"
    "Skill = 可复用的能力模板\n"
    "Memory = 跨会话的知识库\n\n"
    "两者结合：Agent 越用越懂你的项目。", BLUE)

# ═══════════════════════════════════
# 9. PERMISSION
# ═══════════════════════════════════
s = content("权限体系：人机协作的安全模型")
card_row(s, [
    ("Plan 计划模式", "只读 + 生成方案\n修改操作需要审批\n\n适合：调研、代码审查\n学习陌生项目", BLUE),
    ("Accept 审批模式（默认）", "读 + 写 + 执行\n文件修改弹窗确认\n\n适合：日常开发\n推荐大多数场景使用", BLUE),
    ("Bypass 自动执行", "全自动 · 跳过审批\n\n适合：完全信任的脚本\n批量自动化任务", BLUE),
])
tb(s, 1.2, 6.6, 10, 0.6,
   "核心理念：Agent 有权限做事，但你点头前它不会改文件。"
   "安全不是「锁死权限」，而是「每步可审、可拒、可撤销」。"
   "  |  每次写入前备份原件，改错随时回滚。",
   fs=13, c=MUTED)

# ═══════════════════════════════════
# 10. SAFETY
# ═══════════════════════════════════
s = content("你的代码安全吗？")
tb(s, 1.2, 1.1, 10, 0.4, "当 AI 能操作你的文件时，安全不是「信不信它」，而是「你能控到哪一步」。", fs=14, c=MUTED)
card_row(s, [
    ("命令拦截", "即使模型被诱导执行危险命令\n也会被 Agent Lite 拒绝\n\nrm -rf / → 拦截\nformat C: → 拦截\ncurl ... | bash → 拦截\n编码命令 → 拦截", BLUE),
    ("文件保护", "任何时候不会意外覆盖或删除\n\n写入项目外 → 重定向到安全目录\n访问系统目录 → 拒绝\n每次写入前自动备份原件", BLUE),
    ("网络隔离", "Agent 不会成为内网渗透跳板\n\n127.0.0.1 → 拦截\n192.168.x.x → 拦截\n内网 IP 全拦截", BLUE),
    ("提示注入防护", "精心设计的恶意提示词\n也能实时识别并警告\n\n12 种攻击模式扫描\n指令覆盖 / 角色混淆 / 编码绕过", BLUE),
], y=1.7, h=5.0)

# ═══════════════════════════════════
# 11. COMPARISON
# ═══════════════════════════════════
s = content("主流编程 Agent 对比")
card(s, 0.7, 1.3, 5.8, 5.3, "Agent Lite 的关键差异",
    "唯一无需安装任何运行时 — 浏览器即用\n\n"
    "唯一 100% 本地存储 — 代码不经第三方服务器\n\n"
    "唯一支持会话分支 — 多层树形，试错成本最低\n\n"
    "唯一完全免费开源\n\n"
    "安装包仅 30 MB — 最轻量的选择\n\n"
    "零配置开箱即用 — 下载、双击、开始", BLUE)
card(s, 7.3, 1.3, 5.8, 5.3, "同类产品参考（2026.07 公开资料）",
    "Cursor: VS Code 分支 IDE, $20–200/月, Cloud\n\n"
    "Copilot: IDE 插件, $10–39/月, Cloud\n\n"
    "Claude Code: CLI 工具, $20/月, npm 安装\n\n"
    "Codex Desktop: 桌面应用, 需会员, OpenAI\n\n"
    "以上信息基于公开资料，各产品持续更新\n具体以官方最新文档为准", MUTED)

# ═══════════════════════════════════
# 12. TECH STACK
# ═══════════════════════════════════
s = content("技术栈")
card_row(s, [
    ("零前端依赖", "无 npm / webpack / babel\n纯 JavaScript 12,000+ 行\n单文件 · 零构建步骤\n21 个 Feather SVG 图标", BLUE),
    ("Python stdlib", "http.server 原生 HTTP\n无 Flask / Django / FastAPI\nJSON 文件存储\n可选: docx, openpyxl, PyPDF2", BLUE),
    ("412 项测试 · 20 秒", "全量自动化 · 零外部依赖\nCI 就绪 · 改完即知\nP0 安全 + P0 路由\nP1 编辑 + P1 并发", BLUE),
    ("轻量分发", "127.0.0.1 本地运行\n数据绝不离开电脑\n可编译为 30 MB .exe\n系统托盘 + 自动更新", BLUE),
])

# ═══════════════════════════════════
# 13. ROADMAP
# ═══════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, DARK)
tb(s, 2, 0.7, 9, 0.6, "路线图", fs=28, c=WHITE, bold=True)
rule(s, 2, 1.2, 2, RGBColor(0x50, 0x85, 0xF0))

phases = [
    ("已完成 v0.5.2", "独立 Web 版",
     "命令安全策略\n子 Agent 并行调度\n会话分支功能\nSkill 系统 14 技能\n办公文档全支持\ni18n 中英双语\n412 项自动化测试"),
    ("进行中", "轻量集成",
     "API Key 自主配置\n自由切换模型\n深色 / 浅色主题\n一键 EXE 分发"),
    ("规划中", "生态扩展",
     "更多模型适配\nmacOS / Linux 支持\n插件 / 扩展体系\n协作功能探索"),
]
gap = 0.3
w = (FW - 2.4 - 2*gap) / 3
x = 1.2
for label, title, desc in phases:
    rect(s, x, 1.8, w, 4.6, RGBColor(0x24, 0x2E, 0x40), r=1)
    tb(s, x+0.3, 2.0, w-0.6, 0.3, label, fs=12, c=BLUE, bold=True)
    tb(s, x+0.3, 2.4, w-0.6, 0.35, title, fs=18, c=WHITE, bold=True)
    tb(s, x+0.3, 2.9, w-0.6, 3.2, desc, fs=13, c=RGBColor(0xB0, 0xBE, 0xD4))
    x += w + gap

tb(s, 2, 6.6, 9, 0.5,
   "支持自主配置 API Key 和 Base URL，接入任意兼容 OpenAI 协议的模型服务",
   fs=12, c=RGBColor(0x70, 0x90, 0xD0))

# ═══════════════════════════════════
# 14. END
# ═══════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, DARK)
tb(s, 2.5, 2.2, 8, 0.9, "开始你的第一个项目", fs=44, c=WHITE, bold=True)
tb(s, 2.5, 3.5, 8, 1.8,
   "打开终端 → cd 到项目目录 → 运行 agent-lite\n\n浏览器打开 127.0.0.1:3010\n\n用自然语言驱动代码",
   fs=18, c=RGBColor(0xA0, 0xBE, 0xF5))
rule(s, 2.5, 5.5, 2.5, RGBColor(0x50, 0x85, 0xF0))
tb(s, 2.5, 5.9, 6, 0.4, "github.com/fhy-A/agent-lite", fs=13, c=RGBColor(0x70, 0x90, 0xD0))

# ── save ──
prs.save(str(OUTPUT))
print(f"PPT saved: {OUTPUT}")
