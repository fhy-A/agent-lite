#!/usr/bin/env python3
"""Summarize Python source files in this project.

Recursively counts Python files, code lines, and functions while ignoring
.git, .venv, build, dist, and data directories.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

IGNORED_DIRS = {".git", ".venv", "build", "dist", "data"}


@dataclass(frozen=True)
class ProjectSummary:
    python_files: int = 0
    code_lines: int = 0
    functions: int = 0


def iter_python_files(root: Path):
    """Yield Python files below root, pruning ignored directories."""
    for path in root.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def count_code_lines(source: str) -> int:
    """Count non-empty, non-comment physical lines as code lines."""
    total = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            total += 1
    return total


def count_functions(source: str, path: Path) -> int:
    """Count sync and async function definitions using Python's AST."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return 0
    return sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))


def summarize(root: Path) -> ProjectSummary:
    python_files = 0
    code_lines = 0
    functions = 0

    for path in iter_python_files(root):
        python_files += 1
        source = path.read_text(encoding="utf-8", errors="replace")
        code_lines += count_code_lines(source)
        functions += count_functions(source, path)

    return ProjectSummary(
        python_files=python_files,
        code_lines=code_lines,
        functions=functions,
    )


def render_markdown(summary: ProjectSummary, root: Path) -> str:
    return "\n".join(
        [
            "# Project Summary",
            "",
            f"Root: `{root}`",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Python files | {summary.python_files} |",
            f"| Code lines | {summary.code_lines} |",
            f"| Functions | {summary.functions} |",
            "",
            "Ignored directories: `.git`, `.venv`, `build`, `dist`, `data`.",
            "Code lines are counted as non-empty, non-comment physical lines.",
            "Functions are counted from AST `FunctionDef` and `AsyncFunctionDef` nodes.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Python files in the project.")
    parser.add_argument("--root", default=".", help="Project root to scan (default: current directory).")
    parser.add_argument("--output", default="data/project-summary.md", help="Markdown output path.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    summary = summarize(root)
    markdown = render_markdown(summary, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")

    print(f"Python files: {summary.python_files}")
    print(f"Code lines: {summary.code_lines}")
    print(f"Functions: {summary.functions}")
    print(f"Wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
