#!/usr/bin/env python3
"""读取 data/sessions/ 下体积最大的 3 个 session 文件，输出文件名和大小"""

from pathlib import Path

sessions_dir = Path("data/sessions")

if not sessions_dir.exists():
    print("data/sessions 目录不存在")
    exit(1)

files = []
for f in sessions_dir.glob("*.json"):
    if f.is_file():
        size = f.stat().st_size
        files.append((f.name, size))

files.sort(key=lambda x: x[1], reverse=True)

print("体积最大的 3 个 session 文件：")
for name, size in files[:3]:
    size_kb = size / 1024
    print(f"{name}: {size_kb:.2f} KB ({size} bytes)")
