#!/usr/bin/env python3
"""stats_report.py — 分析 data/sessions/ 下所有会话 JSON，生成 report.md。"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, date

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sessions")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")


def load_sessions():
    sessions = []
    if not os.path.isdir(SESSIONS_DIR):
        print(f"[ERROR] 会话目录不存在: {SESSIONS_DIR}")
        return sessions

    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] 跳过 {fname}: {e}")
    return sessions


def compute_stats(sessions):
    total_sessions = len(sessions)

    # 消息数
    total_messages = sum(len(s.get("messages", [])) for s in sessions)

    # Token 按日期统计
    daily_input = defaultdict(int)
    daily_output = defaultdict(int)
    daily_cache = defaultdict(int)
    total_input = 0
    total_output = 0
    total_cache = 0

    # 工具统计
    tool_counter = Counter()

    # 模型统计：从 assistant 消息的 _model 字段
    model_counter = Counter()

    for s in sessions:
        # 用 createdAt 的日期部分
        created = s.get("createdAt", "")
        day = created[:10] if created else "unknown"

        for msg in s.get("messages", []):
            role = msg.get("role", "")

            # Token 统计：优先从 meta._usage，其次从 top-level stats
            usage = None
            if isinstance(msg.get("meta"), dict):
                u = msg["meta"].get("_usage")
                if isinstance(u, dict):
                    usage = u

            if usage:
                inp = usage.get("input", 0) or 0
                out = usage.get("output", 0) or 0
                cache = usage.get("cache", 0) or 0
                daily_input[day] += inp
                daily_output[day] += out
                daily_cache[day] += cache
                total_input += inp
                total_output += out
                total_cache += cache

            # 工具统计
            if role == "tool-call":
                action = ""
                meta = msg.get("meta", {})
                if isinstance(meta, dict):
                    action = meta.get("action", "")
                if not action:
                    # fallback: 从 content 中解析
                    pass
                if action:
                    tool_counter[action] += 1

            # 模型统计
            model = msg.get("_model", "")
            if model:
                model_counter[model] += 1

    # 日均 token
    all_days = set(daily_input.keys()) | set(daily_output.keys()) | set(daily_cache.keys())
    days_count = len(all_days)
    avg_input = total_input / days_count if days_count > 0 else 0
    avg_output = total_output / days_count if days_count > 0 else 0
    avg_cache = total_cache / days_count if days_count > 0 else 0

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "days_count": days_count,
        "total_input": total_input,
        "total_output": total_output,
        "total_cache": total_cache,
        "avg_input": avg_input,
        "avg_output": avg_output,
        "avg_cache": avg_cache,
        "daily_input": dict(daily_input),
        "daily_output": dict(daily_output),
        "daily_cache": dict(daily_cache),
        "tool_counter": tool_counter,
        "model_counter": model_counter,
    }


def format_number(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def generate_report(stats):
    lines = []
    lines.append("# Agent Lite 会话统计报告\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## 1. 总览\n")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 会话总数 | {stats['total_sessions']} |")
    lines.append(f"| 消息总数 | {stats['total_messages']} |")
    lines.append(f"| 统计天数 | {stats['days_count']} |")
    lines.append("")

    lines.append("## 2. Token 消耗\n")
    lines.append(f"| 类型 | 总量 | 日均 |")
    lines.append(f"|------|------|------|")
    lines.append(f"| Input | {format_number(stats['total_input'])} | {format_number(stats['avg_input'])} |")
    lines.append(f"| Output | {format_number(stats['total_output'])} | {format_number(stats['avg_output'])} |")
    lines.append(f"| Cache | {format_number(stats['total_cache'])} | {format_number(stats['avg_cache'])} |")
    lines.append("")

    # 每日明细
    lines.append("### 每日 Token 消耗明细\n")
    lines.append(f"| 日期 | Input | Output | Cache | 合计 |")
    lines.append(f"|------|-------|--------|-------|------|")
    all_days = sorted(
        set(stats["daily_input"].keys())
        | set(stats["daily_output"].keys())
        | set(stats["daily_cache"].keys())
    )
    for day in all_days:
        inp = stats["daily_input"].get(day, 0)
        out = stats["daily_output"].get(day, 0)
        cache = stats["daily_cache"].get(day, 0)
        total = inp + out + cache
        lines.append(
            f"| {day} | {format_number(inp)} | {format_number(out)} | {format_number(cache)} | {format_number(total)} |"
        )
    lines.append("")

    lines.append("## 3. 工具使用统计\n")
    if stats["tool_counter"]:
        lines.append(f"| 工具 | 调用次数 | 占比 |")
        lines.append(f"|------|----------|------|")
        total_calls = sum(stats["tool_counter"].values())
        for tool, count in stats["tool_counter"].most_common():
            pct = (count / total_calls * 100) if total_calls > 0 else 0
            lines.append(f"| `{tool}` | {count} | {pct:.1f}% |")
        lines.append(f"\n> 工具调用总计：{total_calls} 次\n")
    else:
        lines.append("> 无工具调用记录\n")

    lines.append("## 4. 模型使用统计\n")
    if stats["model_counter"]:
        lines.append(f"| 模型 | 消息数 | 占比 |")
        lines.append(f"|------|--------|------|")
        total_model_msgs = sum(stats["model_counter"].values())
        for model, count in stats["model_counter"].most_common():
            pct = (count / total_model_msgs * 100) if total_model_msgs > 0 else 0
            # 标记最常用模型
            suffix = " **(最常用)**" if count == stats["model_counter"].most_common(1)[0][1] else ""
            lines.append(f"| `{model}` | {count} | {pct:.1f}%{suffix} |")
    else:
        lines.append("> 无模型使用记录\n")

    return "\n".join(lines) + "\n"


def main():
    sessions = load_sessions()
    if not sessions:
        print("没有找到任何会话文件，退出。")
        return

    stats = compute_stats(sessions)
    report = generate_report(stats)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"报告已生成：{OUTPUT_FILE}")
    print(f"  - 会话数：{stats['total_sessions']}")
    print(f"  - 消息数：{stats['total_messages']}")
    print(f"  - 工具调用：{sum(stats['tool_counter'].values())}")
    print(f"  - 模型数：{len(stats['model_counter'])}")


if __name__ == "__main__":
    main()
