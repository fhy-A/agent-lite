"""
Agent Lite 集成测试 — 验证 2026-07-07 安全策略 + STDOUT 修复后的模型行为

用法：
  1. 确保 Agent Lite 服务已启动
  2. python tests/run_integration_tests.py --model deepseek-v4-pro

测试内容：
  P0  STDOUT 捕获正常
  P1  python -c 可以执行且输出可见
  P1  分号在 python 代码中不误拦
  P1  删除命令仍然会被拦截
  P2  项目根目录正确注入提示词
  P2  Office skill 触发 python -c 读取
"""

import json
import re
import sys
import time
import requests

BASE_URL = "http://127.0.0.1:3010"
PROXY_URL = f"{BASE_URL}/proxy/chat"
TOOL_URL = f"{BASE_URL}/api/tools/run_command"
CONFIG_URL = f"{BASE_URL}/api/config"

TESTS = []

# ── helpers ──

def t(name, desc, question, checks):
    """checks: dict of {check_name: fn(data) -> (pass:bool, detail:str)}"""
    TESTS.append({"name": name, "desc": desc, "question": question, "checks": checks})


def call_model(question, model, api_key="", base_url=""):
    """发送消息到模型，返回模型响应"""
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%Y/%m/%d %A %H:%M") + " (Beijing Time)"

    system = f"""你是 Agent Lite，一个运行在本地 Windows 环境中的 AI 编程助手。
当前时间：{date_str}
项目根目录：C:\\Users\\Admin

你可以使用工具。对于需要执行命令的任务，使用 run_command 工具。
读取 Word/Excel/PPT/PDF 文件时，用 python -c 配合相应库（docx/openpyxl/pptx/PyPDF2）。
命令用 PowerShell 语法。"""

    tools = [
        {"type": "function", "function": {
            "name": "run_command",
            "description": "Run a shell command (view, test, build, git, python scripts).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to execute."},
                    "description": {"type": "string", "description": "Short description."}
                },
                "required": ["command"]
            }
        }},
        {"type": "function", "function": {
            "name": "read_file",
            "description": "Read a text file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }},
        {"type": "function", "function": {
            "name": "write_file",
            "description": "Write a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"]
            }
        }},
        {"type": "function", "function": {
            "name": "delete_file",
            "description": "Delete a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }},
    ]

    payload = {
        "model": model,
        "stream": False,
        "temperature": 0,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        "tools": tools,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if base_url:
        headers["X-Base-URL"] = base_url

    resp = requests.post(PROXY_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                         headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()


def call_tool_direct(command):
    """直接调用 run_command API（绕过模型）"""
    resp = requests.post(
        TOOL_URL,
        data=json.dumps({"command": command, "action": "run_command"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    return resp.json()


# ── 定义测试 ──

# P0: STDOUT capture
t("p0_stdout_echo", "STDOUT 正常捕获",
  None,  # direct tool call, no model needed
  {"stdout_not_empty": lambda r: (bool(r.get("stdout", "").strip()), f"stdout={repr(r.get('stdout','')[:50])}")})

# P0: STDOUT capture for python
t("p0_stdout_python", "python -c print 输出可见",
  None,
  {"python_output_visible": lambda r: ("123" in r.get("stdout", ""), f"stdout={repr(r.get('stdout','')[:50])}")})

# P1: python -c allowed
t("p1_python_c_allowed", "python -c 不再被拦截",
  "请用 python -c \"print('hello_world_test')\" 运行并告诉我输出结果",
  {"not_blocked": lambda r: (r.get("ok") is not False, f"ok={r.get('ok')}, error={r.get('error','none')}")})

# P1: semicolons in python
t("p1_semicolon_ok", "python -c 含分号不误拦",
  "请用 python -c \"a=1; b=2; print(a+b)\" 运行并告诉我结果",
  {"not_blocked": lambda r: (r.get("ok") is not False, f"ok={r.get('ok')}, error={r.get('error','none')}")})

# P1: deletion still blocked
t("p1_del_blocked", "del 命令仍被拦截",
  None,
  {"blocked": lambda r: (r.get("ok") is False, f"ok={r.get('ok')}, error={r.get('error','none')}")})

t("p1_rm_blocked", "rm 命令仍被拦截",
  None,
  {"blocked": lambda r: (r.get("ok") is False, f"ok={r.get('ok')}, error={r.get('error','none')}")})

# P1: file write allowed
t("p1_write_allowed", "文件写入命令允许执行",
  None,
  {"allowed": lambda r: (r.get("ok") is not False, f"ok={r.get('ok')}, exitCode={r.get('exitCode')}")})

# P2: project root in model response
t("p2_project_root_known", "模型知道项目根目录",
  "你的当前工作目录（项目根目录）是什么？不要读文件，直接回答。",
  {"knows_root": lambda r: ("C:\\\\Users\\\\Admin" in str(r) or "C:/Users/Admin" in str(r),
                              f"model response sample: {str(r)[:100]}")})

# P2: Office skill triggers python -c
t("p2_office_skill", "遇到 docx 文件会尝试 python -c",
  "项目根目录是 C:\\Users\\Admin，帮我看看 Desktop\\Claude_Code_新手使用攻略.docx 这个 Word 文档里写了什么。如果读不到也没关系，我只需要看到你尝试用 python -c + docx 库去读。",
  {"uses_python_c": lambda r: ("python -c" in str(r).lower() or "from docx" in str(r).lower(),
                                 f"response sample: {str(r)[:200]}")})


# ── 运行测试 ──

def run_direct_tool_tests():
    """P0/P1: 直接调 API 测试（不经过模型）"""
    results = []
    print("\n── 直接 API 测试（不经过模型）──\n")

    for cmd, label, checks in [
        ("echo hello_integration_test", "echo 输出", [
            ("stdout_not_empty", lambda r: (bool(r.get("stdout", "").strip()),
                                            f"stdout={repr(r.get('stdout','')[:60])}"))
        ]),
        ('python -c "print(789)"', "python -c print", [
            ("output_contains_789", lambda r: ("789" in r.get("stdout", ""),
                                               f"stdout={repr(r.get('stdout','')[:60])}"))
        ]),
        ('python -c "x=1; y=2; print(x+y)"', "python 含分号", [
            ("output_contains_3", lambda r: ("3" in r.get("stdout", ""),
                                             f"stdout={repr(r.get('stdout','')[:60])}"))
        ]),
        ("del test_nonexistent_file.txt", "del 拦截", [
            ("blocked", lambda r: (r.get("ok") is False,
                                   f"ok={r.get('ok')}"))
        ]),
        ("rm test_nonexistent_file.txt", "rm 拦截", [
            ("blocked", lambda r: (r.get("ok") is False,
                                   f"ok={r.get('ok')}"))
        ]),
        ("mkdir _int_test_dir_2e7f9a", "mkdir 允许", [
            ("allowed", lambda r: (r.get("ok") is not False,
                                   f"ok={r.get('ok')}, exitCode={r.get('exitCode')}"))
        ]),
        ("rmdir _int_test_dir_2e7f9a", "rmdir 拦截", [
            ("blocked", lambda r: (r.get("ok") is False,
                                   f"ok={r.get('ok')}"))
        ]),
        ("set-content _int_test_hello.txt 'hello'", "set-content 允许", [
            ("allowed", lambda r: (r.get("ok") is not False,
                                   f"ok={r.get('ok')}"))
        ]),
        ("pip --version", "pip 允许", [
            ("allowed", lambda r: (r.get("ok") is not False,
                                   f"ok={r.get('ok')}"))
        ]),
    ]:
        print(f"[{label}] ", end="", flush=True)
        try:
            r = call_tool_direct(cmd)
            all_pass = True
            for check_name, check_fn in checks:
                passed, detail = check_fn(r)
                icon = "[PASS]" if passed else "[FAIL]"
                if not passed:
                    all_pass = False
                print(f"{icon} {check_name}: {detail}  ", end="")
            results.append({"label": label, "passed": all_pass})
        except Exception as e:
            print(f"[FAIL] 异常: {e}")
            results.append({"label": label, "passed": False, "error": str(e)})
        print()

    # cleanup
    for f in ["_int_test_copy.txt", "_test_write.txt"]:
        try:
            call_tool_direct(f"del {f}")
        except Exception:
            pass
    try:
        call_tool_direct("rmdir _integration_test_dir 2>$null")
    except Exception:
        pass

    return results


def run_model_tests(model, api_key="", base_url=""):
    """P2: 通过模型测试，提取返回值中的 tool_calls"""
    results = []
    print(f"\n── 模型测试（{model}）──\n")

    model_questions = [
        ("项目根目录感知", "你的当前工作目录（项目根目录）是什么？不要读文件，直接告诉我。",
         [("knows_path", lambda r: any(p in str(r).lower() for p in ["users\\\\admin", "users/admin", "c:\\\\users"]),
           "model mentions user directory")]),

        ("python -c 使用意愿", "请直接执行 python -c \"print('integration_test_abc')\" 并告诉我输出。只执行这一个命令，不要做其他事。",
         [("tool_call_present", lambda r: ("tool_calls" in str(r) or "call_" in str(r)),
           "model issued tool call"),
          ("uses_python_c", lambda r: ("python -c" in str(r).lower() or "python -c" in str(r).lower()),
           "model used python -c")]),
    ]

    for label, question, checks in model_questions:
        print(f"[{label}] ", end="", flush=True)
        try:
            data = call_model(question, model, api_key, base_url)
            all_pass = True
            for check_name, check_fn in checks:
                passed, detail = check_fn(data)
                icon = "[PASS]" if passed else "[FAIL]"
                if not passed:
                    all_pass = False
                print(f"{icon} {check_name}: {detail}  ", end="")

            # Show what model actually returned
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = (msg.get("content") or "")[:120]
            tool_calls = msg.get("tool_calls") or []
            tc_names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
            if tc_names:
                print(f"| tools: {','.join(tc_names)}", end="")
            if content:
                print(f"| reply: {content[:80]}", end="")

            results.append({"label": label, "passed": all_pass})
        except Exception as e:
            print(f"[FAIL] 异常: {e}")
            results.append({"label": label, "passed": False, "error": str(e)})
        print()
        time.sleep(1)

    return results


def print_summary(direct_results, model_results):
    all_results = direct_results + model_results
    passed = sum(1 for r in all_results if r.get("passed"))
    total = len(all_results)
    print(f"\n{'='*60}")
    print(f"  集成测试结果: {passed}/{total} 通过")
    print(f"{'='*60}")
    for r in all_results:
        icon = "[PASS]" if r.get("passed") else "[FAIL]"
        err = f" ({r['error']})" if r.get("error") else ""
        print(f"  {icon} {r['label']}{err}")
    print()

    if passed == total:
        print("ALL PASSED -  全部通过！")
    else:
        print(f"[WARN]  {total - passed} 项失败，需要检查。")
    return passed == total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agent Lite 集成测试 — 安全策略 + STDOUT")
    parser.add_argument("--model", default="", help="模型 ID（P2 模型测试需要）")
    parser.add_argument("--api-key", default="", help="API Key")
    parser.add_argument("--base-url", default="", help="LLM Base URL")
    parser.add_argument("--quick", action="store_true", help="只跑直接 API 测试（不经过模型，更快）")
    args = parser.parse_args()

    print("Agent Lite 集成测试 — 2026-07-07 改动验证")
    print(f"服务地址: {BASE_URL}")

    # 检查服务是否在线
    try:
        requests.get(CONFIG_URL, timeout=5)
        print("[PASS] 服务在线\n")
    except Exception:
        print("[FAIL] 服务未启动，请先启动 Agent Lite\n")
        sys.exit(1)

    # P0 + P1: Direct API tests
    direct_results = run_direct_tool_tests()

    # P2: Model tests (optional)
    model_results = []
    if not args.quick and args.model:
        print("\n(等待模型响应，可能需要 1-2 分钟...)")
        model_results = run_model_tests(args.model, args.api_key, args.base_url)
    elif not args.model:
        print("\n[WARN]  跳过模型测试（需 --model 参数）")

    ok = print_summary(direct_results, model_results)
    sys.exit(0 if ok else 1)
