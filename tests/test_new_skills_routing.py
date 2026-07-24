"""Quick smoke test for new skill routing and slash commands."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def run_smoke_test():
    """Run the skill routing smoke test. Returns exit code (0 = pass, 1 = fail)."""
    from server import match_skills, list_skills

    ALL_SKILLS = {s["name"]: s for s in list_skills()}
    print(f"Total skills: {len(ALL_SKILLS)}\n")

    # ── Test cases: prompt → expected skill(s) ──
    CASES = {
        # Office four-piece (high priority)
        "帮我创建一份带目录和页眉的 Word 周报": ["docx"],
        "用这个模板生成一份季度汇报 PPT，要图表": ["pptx"],
        "读取这个 xlsx 做公式审计，检查有没有错误": ["xlsx"],
        "把这份 PDF 里的表格提取出来存为 csv": ["pdf", "office-files"],

        # Learn
        "教我理解二叉树的遍历，不要直接给答案": ["learn"],
        "帮我讲解一下时间复杂度这个概念": ["learn"],

        # Consolidate memory
        "整理一下我的记忆文件，去重合并": ["consolidate-memory"],
        "帮我清理过时的项目记忆": ["consolidate-memory"],

        # Doc coauthoring
        "帮我写一份技术方案文档": ["doc-coauthoring"],
        "一起协作写一个产品需求文档": ["doc-coauthoring"],

        # Theme factory
        "给这个 HTML 页面换一套配色主题": ["theme-factory"],
        "帮我选一套适合金融报告的配色方案": ["theme-factory"],

        # Algorithmic art
        "用 p5.js 生成一副流场粒子艺术作品": ["algorithmic-art"],

        # MCP builder
        "帮我搭建一个 MCP 服务器连接 GitHub API": ["mcp-builder"],

        # Web artifacts builder
        "创建一个带状态管理的 React 仪表盘组件": ["web-artifacts-builder"],

        # Regression: should NOT match (general questions)
        "Python 装饰器怎么用": [],
        "帮我修复 server.py 的 bug": [],
        "写一个链表反转函数": [],
    }

    print("─" * 60)
    failed = 0
    for prompt, expected in CASES.items():
        matched = match_skills(prompt)
        names = [s["name"] for s in matched]

        # Check that every expected skill IS in the matched list
        missing = [e for e in expected if e not in names]
        extra = [n for n in names if n not in expected]

        status = "PASS" if not missing else "FAIL"
        if missing or (not expected and names):
            failed += 1
            status = "FAIL"

        print(f"[{status}] {prompt[:50]:50s} → {names}")
        if missing:
            print(f"       MISSING: {missing}")
        if extra and expected:
            print(f"       EXTRA:   {extra}")

    print("─" * 60)
    print(f"\n{failed}/{len(CASES)} failures")

    # ── Check new skills exist ──
    print("\n── New skill presence ──")
    NEW = ["docx", "pptx", "xlsx", "pdf", "learn", "consolidate-memory",
           "doc-coauthoring", "theme-factory", "mcp-builder",
           "algorithmic-art", "web-artifacts-builder", "compact-chat"]
    for name in NEW:
        found = name in ALL_SKILLS
        print(f"  {'OK' if found else 'MISSING'} {name}")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(run_smoke_test())
