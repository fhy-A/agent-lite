from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, parse, request
import base64
import ctypes
import datetime as dt
import difflib
import json
import mimetypes
import os
import re
import subprocess
import uuid


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("AGENT_LITE_DATA_DIR") or (APP_DIR / "data"))
SESSIONS_DIR = DATA_DIR / "sessions"
FILE_BACKUP_DIR = DATA_DIR / "file-backups"
ATTACHMENTS_DIR = DATA_DIR / "attachments"
MEMORY_DIR = DATA_DIR / "memory"
MEMORY_INDEX_PATH = MEMORY_DIR / "MEMORY.md"
SKILLS_DIR = DATA_DIR / "skills"
CONFIG_PATH = DATA_DIR / "config.json"
NEW_API_BASE_URL = os.environ.get("NEW_API_BASE_URL", "").rstrip("/")
PORT = int(os.environ.get("AGENT_LITE_PORT", "3010"))
MAX_PREVIEW_BYTES = 1024 * 1024
MAX_TOOL_READ_BYTES = 512 * 1024
MAX_SEARCH_FILE_BYTES = 1024 * 1024
MAX_SEARCH_RESULTS = 100
MAX_COMMAND_SECONDS = 60
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def _hidden_subprocess_kwargs():
    """Return kwargs to prevent console windows on Windows."""
    if os.name != "nt":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    # CREATE_NO_WINDOW (0x08000000): prevent console allocation
    # DETACHED_PROCESS  (0x00000008): don't inherit parent console
    return {
        "startupinfo": si,
        "creationflags": 0x08000008,
    }


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".turbo",
    ".cache",
    "logs",
    "backups",
    "sessions",
    "file-backups",
}

SAFE_COMMAND_PREFIXES = (
    # 文件查看
    "dir",
    "dir ",
    "ls",
    "type ",
    "findstr ",
    "select-string ",
    "get-childitem",
    "get-content ",
    "where ",
    # 解释器 + 包管理（只放行运行/构建，-c/-e 被 DENIED_RUNTIME_PATTERN 拦截）
    "python ",
    "python -m ",
    "py ",
    "node ",
    "npm ",
    "npx ",
    "pnpm ",
    "yarn ",
    # 版本控制
    "git status",
    "git diff",
    "git log",
    "git show",
    # 容器
    "docker compose ps",
    "docker compose logs",
    "docker compose config",
    # 系统信息（纯查看，只读）
    "echo",
    "echo ",
    "date ",
    "time ",
    "get-date",
    "ver",
    "whoami",
    "hostname",
    "systeminfo",
)

DENIED_COMMAND_PATTERN = re.compile(
    r"(^|\s)(del|erase|rmdir|rd|rm|remove-item|move-item|copy-item|set-content|add-content|"
    r"format|shutdown|restart-computer|reg|takeown|icacls|net\s+user)\b|[;&|<>`]",
    re.IGNORECASE,
)

# Block inline code execution via runtime interpreters (python -c, node -e, etc.)
DENIED_RUNTIME_PATTERN = re.compile(
    r"\b(python|python3?|py|node|ruby|perl)\s+(?:-[ce]\s+|--(?:command|eval|execute)\s+)",
    re.IGNORECASE,
)

def _set_dpi_aware():
    """Enable high-DPI awareness on Windows to prevent blurry tkinter dialogs."""
    if os.name != "nt":
        return
    # Try modern API first (Win 8.1+), fall back to legacy
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_set_dpi_aware()

DATA_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
FILE_BACKUP_DIR.mkdir(exist_ok=True)
ATTACHMENTS_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)
SKILLS_DIR.mkdir(exist_ok=True)


def now_iso():
    return dt.datetime.now().replace(microsecond=0).isoformat()


def json_bytes(data, status=200):
    payload = json.dumps(data, ensure_ascii=False, indent=None).encode("utf-8")
    return status, payload


def read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return default
    except Exception as exc:
        print(f"[WARN] read_json failed for {path}: {exc}")
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def default_project_root():
    return str(Path.home())


def load_config():
    config = read_json(CONFIG_PATH, {})
    config.setdefault("projectRoot", default_project_root())
    config.setdefault("newApiBaseUrl", "")
    return config


def save_config(config):
    current = load_config()
    current.update(config)
    write_json(CONFIG_PATH, current)
    return current


PROJECT_CONTEXT_FILES = ["CLAUDE.md", "AGENT.md", "CLAUDE.MD", "AGENT.MD"]


def load_project_context():
    """Scan project root for CLAUDE.md / AGENT.md and return its content."""
    config = load_config()
    root = Path(config["projectRoot"]).expanduser().resolve()
    for name in PROJECT_CONTEXT_FILES:
        candidate = root / name
        if candidate.is_file():
            try:
                content = candidate.read_text(encoding="utf-8-sig")
                return {
                    "found": True,
                    "path": str(candidate),
                    "name": candidate.name,
                    "content": content,
                }
            except Exception:
                pass
    return {"found": False, "path": None, "name": None, "content": None}


# ── Skills ───────────────────────────────────────────

def list_skills():
    """List all installed skills with their metadata."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8-sig")
            meta, body = parse_memory_frontmatter(text)
            skills.append({
                "name": meta.get("name", skill_dir.name),
                "description": meta.get("description", ""),
                "keywords": [k.strip() for k in meta.get("keywords", "").split(",") if k.strip()],
                "tools": [t.strip() for t in meta.get("tools", "").split(",") if t.strip()],
                "body": body.strip(),
                "dir": skill_dir.name,
                "path": str(skill_md.resolve()),
            })
        except Exception:
            pass
    return skills


def read_skill(name):
    """Read a single skill by name."""
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8-sig")
            meta, body = parse_memory_frontmatter(text)
            if meta.get("name") == name:
                return {
                    "name": meta.get("name", skill_dir.name),
                    "description": meta.get("description", ""),
                    "keywords": [k.strip() for k in meta.get("keywords", "").split(",") if k.strip()],
                    "tools": [t.strip() for t in meta.get("tools", "").split(",") if t.strip()],
                    "body": body.strip(),
                    "dir": skill_dir.name,
                    "path": str(skill_md.resolve()),
                }
        except Exception:
            pass
    raise ValueError("skill not found")


def match_skills(user_message):
    """Find skills whose keywords, name, or description match the user message."""
    user_lower = (user_message or "").lower()
    matched = []
    for skill in list_skills():
        # Check explicit keywords first
        kw_list = skill.get("keywords") or []
        if any(kw.lower() in user_lower for kw in kw_list if len(kw) >= 2):
            matched.append(skill)
            continue
        # Check skill name
        name = (skill.get("name") or "").lower()
        if name and len(name) >= 2 and name in user_lower:
            matched.append(skill)
            continue
        # Check description
        desc = (skill.get("description") or "").lower()
        if not desc:
            continue
        keywords = [w for w in desc.replace(",", " ").split() if len(w) >= 2]
        if any(kw in user_lower for kw in keywords):
            matched.append(skill)
    return matched


def create_skill(name, description, body_text, tools="", keywords=""):
    """Create a new skill directory with SKILL.md."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", name)[:32]
    if not safe:
        raise ValueError("invalid skill name")
    skill_dir = SKILLS_DIR / safe
    if skill_dir.exists():
        raise ValueError("skill already exists")
    skill_dir.mkdir(parents=True)
    meta = {"name": safe, "description": description}
    if tools:
        meta["tools"] = tools
    if keywords:
        meta["keywords"] = keywords
    content = build_memory_file(meta, body_text)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return read_skill(safe)


def delete_skill(name):
    """Delete a skill directory."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", name)[:32]
    skill_dir = SKILLS_DIR / safe
    if not skill_dir.exists():
        raise ValueError("skill not found")
    import shutil
    shutil.rmtree(skill_dir)
    return {"ok": True}


# ── Memory ────────────────────────────────────────────

MEMORY_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_memory_frontmatter(text):
    """Parse YAML-like frontmatter from memory file. Returns (meta, body)."""
    match = MEMORY_FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end():]
    meta = {}
    for line in raw.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body.strip()


def build_memory_file(meta, body):
    """Build a memory file content from meta dict and body string."""
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def safe_memory_name(name):
    """Validate and sanitize a memory file slug."""
    if not name or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name):
        raise ValueError("invalid memory name")
    return name


def list_memories():
    """List all memory files with their frontmatter."""
    memories = []
    for path in sorted(MEMORY_DIR.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
            meta, body = parse_memory_frontmatter(text)
            memories.append({
                "name": path.stem,
                "description": meta.get("description", ""),
                "type": (meta.get("metadata", "") or "").split("type:")[-1].strip() if "type:" in (meta.get("metadata", "") or "") else meta.get("type", ""),
                "size": len(body),
            })
        except Exception:
            pass
    return memories


def read_memory(name):
    """Read a single memory file."""
    safe = safe_memory_name(name)
    path = MEMORY_DIR / f"{safe}.md"
    if not path.is_file():
        raise ValueError("memory not found")
    text = path.read_text(encoding="utf-8-sig")
    meta, body = parse_memory_frontmatter(text)
    return {"name": safe, "meta": meta, "body": body, "raw": text}


def write_memory(name, meta, body):
    """Create or update a memory file."""
    safe = safe_memory_name(name)
    path = MEMORY_DIR / f"{safe}.md"
    content = build_memory_file(meta, body)
    path.write_text(content, encoding="utf-8")
    _rebuild_memory_index()
    return {"name": safe, "meta": meta, "body": body}


def delete_memory(name):
    """Delete a memory file."""
    safe = safe_memory_name(name)
    path = MEMORY_DIR / f"{safe}.md"
    if path.is_file():
        path.unlink()
    _rebuild_memory_index()
    return {"ok": True}


def _rebuild_memory_index():
    """Rebuild MEMORY.md index from all memory files."""
    items = []
    for mem in list_memories():
        desc = mem.get("description", "") or ""
        items.append(f"- [{mem['name']}]({mem['name']}.md) — {desc}")
    MEMORY_INDEX_PATH.write_text("\n".join(items) + "\n", encoding="utf-8")


def load_memory_context():
    """Return memory contents for system prompt injection, filtered by current project."""
    memories = list_memories()
    if not memories:
        return {"found": False, "content": None, "memories": []}
    current_project = load_config().get("projectRoot", "")
    parts = []
    for mem in memories:
        try:
            full = read_memory(mem["name"])
            mem_project = (full.get("meta") or {}).get("project", "")
            # Include if same project OR if memory has no project (legacy) OR project is "*"
            if mem_project and current_project and mem_project != current_project and mem_project != "*":
                continue
            desc = mem.get("description", "") or ""
            parts.append(f"### {mem['name']}\n{desc}\n\n{full['body']}")
        except Exception:
            pass
    if not parts:
        return {"found": False, "content": None, "memories": []}
    content = "以下是本项目相关的持久记忆，请始终参考这些信息：\n\n" + "\n\n---\n\n".join(parts)
    return {"found": True, "content": content, "count": len(parts)}


def safe_session_id(session_id):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,64}", session_id or ""):
        raise ValueError("invalid session id")
    return session_id


def session_path(session_id):
    return SESSIONS_DIR / f"{safe_session_id(session_id)}.json"


def session_summary(session):
    messages = session.get("messages") or []
    return {
        "id": session["id"],
        "title": session.get("title") or "未命名会话",
        "createdAt": session.get("createdAt"),
        "updatedAt": session.get("updatedAt"),
        "messageCount": len(messages),
    }


def resolve_project_path(relative_path=""):
    config = load_config()
    root = Path(config["projectRoot"]).expanduser().resolve()
    target = (root / (relative_path or "")).resolve()
    if root != target and root not in target.parents:
        raise ValueError("path is outside project root")
    return root, target


def to_project_relative(root, target):
    return str(target.relative_to(root)).replace("\\", "/")


def sanitize_filename(name):
    name = Path(str(name or "attachment")).name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name[:120] or "attachment"


def resolve_attachment_path(relative_path):
    rel = str(relative_path or "").replace("\\", "/")
    if rel.startswith("attachment:"):
        rel = rel.removeprefix("attachment:").lstrip("/")
    elif rel.startswith("attachments/"):
        rel = rel.removeprefix("attachments/")
    else:
        return None, None
    target = (ATTACHMENTS_DIR / rel).resolve()
    if ATTACHMENTS_DIR != target and ATTACHMENTS_DIR not in target.parents:
        raise ValueError("attachment path is outside attachments directory")
    return ATTACHMENTS_DIR, target


def display_attachment_path(root, target):
    return f"attachments/{to_project_relative(root, target)}"


def is_probably_text(data):
    if b"\x00" in data[:4096]:
        return False
    return True


def read_text_limited(path, limit_bytes):
    data = path.read_bytes()
    truncated = len(data) > limit_bytes
    preview = data[:limit_bytes]
    if not is_probably_text(preview):
        raise ValueError("binary file is not supported")
    return preview.decode("utf-8", errors="replace"), len(data), truncated


def make_unified_diff(old_text, new_text, rel_path):
    return "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
    )


def is_safe_command(command):
    normalized = re.sub(r"\s+", " ", command.strip())
    lower = normalized.lower()
    if not normalized:
        return False, "命令不能为空"
    if DENIED_COMMAND_PATTERN.search(normalized):
        return False, "命令包含写入、删除、重定向或危险操作，已被安全策略拦截"
    if DENIED_RUNTIME_PATTERN.search(normalized):
        return False, "不允许通过 -c/-e 等参数执行内联代码"
    if not any(lower == prefix.strip() or lower.startswith(prefix) for prefix in SAFE_COMMAND_PREFIXES):
        return False, "当前只允许查看、测试、构建、git diff/status/log、docker compose 查询等低风险命令"
    return True, ""


def open_native_folder_picker(root):
    """Open a native folder browser dialog and return the selected path."""
    import tkinter as tk
    try:
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        try:
            window.attributes("-topmost", True)
        except Exception:
            pass
        selected = filedialog.askdirectory(
            title="选择项目文件夹",
            initialdir=str(root),
            mustexist=True,
        )
        window.destroy()
        if selected:
            return str(selected)
    except Exception:
        pass
    # Fallback: return empty, frontend will show manual input
    # User cancelled
    return None


def open_native_file_picker(root):
    if os.name == "nt":
        try:
            title = json.dumps("选择要添加到对话的项目文件", ensure_ascii=False)
            initial_dir = json.dumps(str(root), ensure_ascii=False)
            script = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = {title}
$dialog.InitialDirectory = {initial_dir}
$dialog.Multiselect = $false
$dialog.CheckFileExists = $true
$dialog.CheckPathExists = $true
$dialog.AutoUpgradeEnabled = $true
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  Write-Output $dialog.FileName
}}
"""
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-STA",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
                **_hidden_subprocess_kwargs(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise ValueError("当前环境无法打开文件选择窗口，请从左侧文件树选择文件路径或手动输入相对路径") from exc

    window = tk.Tk()
    window.withdraw()
    window.attributes("-topmost", True)
    try:
        return filedialog.askopenfilename(
            title="选择要添加到对话的项目文件",
            initialdir=str(root),
        )
    finally:
        window.destroy()


# ── Sub-agent ───────────────────────────────────────

SUBAGENT_MAX_ROUNDS = 5
SUBAGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出项目目录中的文件和文件夹。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "可选的相对目录"},
                    "maxDepth": {"type": "integer", "description": "递归层数，默认 1"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取项目内的文本文件内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对路径"},
                    "startLine": {"type": "integer", "description": "起始行"},
                    "endLine": {"type": "integer", "description": "结束行"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "按关键词或正则搜索文件内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "path": {"type": "string", "description": "搜索目录"},
                    "regex": {"type": "boolean", "description": "是否正则"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "按 glob 模式匹配文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "glob 模式"},
                    "path": {"type": "string", "description": "搜索起始目录"},
                },
                "required": ["pattern"],
            },
        },
    },
]


def _execute_subagent_tool(tool_call):
    """Execute a single tool call for sub-agent. Returns result string."""
    name = tool_call.get("function", {}).get("name", "")
    try:
        args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
    except Exception:
        args = {}
    args["action"] = name

    # Build a fake body dict that matches tool_* method expectations
    body = {"action": name}
    body.update(args)

    try:
        if name == "list_files":
            root, start = resolve_project_path(body.get("path") or "")
            if not start.exists() or not start.is_dir():
                return f"目录不存在: {body.get('path') or '/'}"
            max_depth = max(1, min(int(body.get("maxDepth") or 1), 3))
            items = []
            def walk_dir(current, depth):
                if len(items) >= 100:
                    return
                try:
                    children = sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                except OSError:
                    return
                for child in children:
                    if child.name in SKIP_DIRS:
                        continue
                    rel = to_project_relative(root, child)
                    if child.is_dir():
                        items.append(f"[dir]  {rel}/")
                        if depth < max_depth:
                            walk_dir(child, depth + 1)
                    elif child.is_file():
                        size = child.stat().st_size
                        items.append(f"[file] {rel} ({size} bytes)")
                    if len(items) >= 100:
                        return
            walk_dir(start, 1)
            return f"目录 {body.get('path') or '/'} 内容:\n" + "\n".join(items[:100])

        elif name == "read_file":
            path = body.get("path") or ""
            root, target = resolve_attachment_path(path)
            is_attachment = target is not None
            if not target:
                root, target = resolve_project_path(path)
            if not target.exists() or not target.is_file():
                return f"文件不存在: {path}"
            content, size, truncated = read_text_limited(target, MAX_TOOL_READ_BYTES)
            start_line = body.get("startLine")
            end_line = body.get("endLine")
            if start_line is not None or end_line is not None:
                lines = content.splitlines()
                s = max(1, int(start_line or 1))
                e = min(len(lines), int(end_line or len(lines)))
                content = "\n".join(lines[s-1:e])
            disp = display_attachment_path(root, target) if is_attachment else to_project_relative(root, target)
            return f"文件 {disp} ({size} bytes):\n{content[:8000]}"

        elif name == "search_files":
            query = (body.get("query") or body.get("pattern") or "").strip()
            start_path = body.get("path") or ""
            use_regex = bool(body.get("regex"))
            if not query:
                return "搜索关键词不能为空"
            root, start = resolve_project_path(start_path)
            if not start.exists():
                return f"路径不存在: {start_path}"
            if use_regex:
                try:
                    needle = re.compile(query, re.IGNORECASE)
                except re.error as exc:
                    return f"正则无效: {exc}"
            else:
                needle = query
            candidates = []
            if start.is_file():
                candidates = [start]
            else:
                for p in start.rglob("*"):
                    if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                        continue
                    if p.is_file():
                        candidates.append(p)
            results = []
            for p in candidates:
                if len(results) >= 50:
                    break
                rel = to_project_relative(root, p)
                matches = []
                try:
                    if p.stat().st_size <= MAX_SEARCH_FILE_BYTES:
                        content, _, _ = read_text_limited(p, MAX_SEARCH_FILE_BYTES)
                        for line_no, line in enumerate(content.splitlines(), start=1):
                            if use_regex:
                                hit = bool(needle.search(line))
                            else:
                                hit = needle.lower() in line.lower()
                            if hit:
                                matches.append(f"  L{line_no}: {line[:300]}")
                                if len(matches) >= 5:
                                    break
                except Exception:
                    pass
                if matches:
                    results.append(f"--- {rel} ---\n" + "\n".join(matches))
            return f"搜索 '{query}' 结果:\n\n" + ("\n".join(results) or "没有匹配项")

        elif name == "glob_files":
            pattern = (body.get("pattern") or "").strip()
            start_path = body.get("path") or ""
            if not pattern:
                return "glob 模式不能为空"
            root, start = resolve_project_path(start_path)
            if not start.exists():
                return f"路径不存在: {start_path}"
            results = []
            for p in root.rglob(pattern):
                if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                    continue
                rel = to_project_relative(root, p)
                kind = "dir " if p.is_dir() else "file"
                size = f" ({p.stat().st_size} bytes)" if p.is_file() else ""
                results.append(f"[{kind}] {rel}{size}")
                if len(results) >= 100:
                    break
            return f"glob '{pattern}' 匹配:\n" + ("\n".join(results) or "没有匹配项")

        else:
            return f"未知工具: {name}"

    except Exception as exc:
        return f"工具执行失败: {exc}"


def run_subagent(task_prompt, system_prompt, model, api_key):
    """Run a sub-agent with its own tool-using loop. Returns dict with result/rounds/errors."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_prompt},
    ]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key

    tool_rounds = 0

    for round_idx in range(SUBAGENT_MAX_ROUNDS):
        payload = {
            "model": model,
            "messages": messages,
            "tools": SUBAGENT_TOOLS,
            "tool_choice": "auto",
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 4096,
        }

        try:
            req = request.Request(
                NEW_API_BASE_URL + "/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers=headers,
            )
            with request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"ok": False, "result": f"Sub-agent API 调用失败: {exc}", "rounds": round_idx + 1}

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        finish = choice.get("finish_reason", "")

        # Collect content
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        # Add assistant message to history
        assistant_msg = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id", f"call_{round_idx}_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": tc.get("function", {}).get("arguments", "{}"),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]
        messages.append(assistant_msg)

        # If no tool calls, sub-agent is done
        if not tool_calls or finish == "stop":
            return {
                "ok": True,
                "result": content or "(sub-agent returned empty response)",
                "rounds": round_idx + 1,
                "tool_rounds": tool_rounds,
            }

        # Execute tools and add results
        for tc in assistant_msg.get("tool_calls", []):
            tool_rounds += 1
            result_text = _execute_subagent_tool(tc)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_text[:4000],
            })

    # Loop exhausted
    last_content = ""
    for m in reversed(messages):
        if m["role"] == "assistant" and m.get("content"):
            last_content = m["content"]
            break
    return {
        "ok": True,
        "result": last_content or "(sub-agent completed without final response)",
        "rounds": SUBAGENT_MAX_ROUNDS,
        "tool_rounds": tool_rounds,
    }


class AgentLiteHandler(BaseHTTPRequestHandler):
    server_version = "AgentLite/0.3"
    protocol_version = "HTTP/1.1"

    def handle(self):
        """Override to force Connection: close after every request, preventing thread leaks."""
        self.close_connection = True
        super().handle()

    def do_GET(self):
        if self.path.startswith("/proxy/models"):
            self.proxy("GET", "/v1/models")
            return

        parsed = parse.urlparse(self.path)
        route = parsed.path
        query = parse.parse_qs(parsed.query)

        try:
            if route == "/api/config":
                self.send_json(load_config())
                return
            if route == "/api/project-context":
                self.send_json(load_project_context())
                return
            if route == "/api/memory-context":
                self.send_json(load_memory_context())
                return
            if route == "/api/skills":
                file_name = query.get("name", [None])[0]
                if file_name:
                    self.send_json(read_skill(file_name))
                else:
                    self.send_json({"data": list_skills()})
                return
            if route == "/api/memory":
                file_name = query.get("file", [None])[0]
                if file_name:
                    self.send_json(read_memory(file_name))
                else:
                    self.send_json({"data": list_memories()})
                return
            if route == "/api/version":
                self.send_json({
                    "name": "Agent Lite",
                    "serverVersion": self.server_version,
                    "appDir": str(APP_DIR),
                    "features": ["pick-file-path"],
                })
                return
            if route == "/api/sessions":
                self.get_sessions()
                return
            if route.startswith("/api/sessions/"):
                self.get_session(route.rsplit("/", 1)[-1])
                return
            if route == "/api/files":
                self.get_files(query.get("path", [""])[0])
                return
            if route == "/api/file":
                self.get_file(query.get("path", [""])[0], raw=query.get("raw", [None])[0] == "1")
                return
            if route.rstrip("/") == "/api/pick-file":
                self.pick_file()
                return
            if route.rstrip("/") == "/api/pick-folder":
                self.pick_folder()
                return
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return

        target = route
        if target == "/":
            target = "/index.html"

        file_path = (APP_DIR / target.lstrip("/")).resolve()
        if APP_DIR != file_path and APP_DIR not in file_path.parents:
            self.send_error(404)
            return
        if not file_path.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.startswith("/proxy/chat"):
            self.proxy("POST", "/v1/chat/completions")
            return

        try:
            if self.path == "/api/config":
                self.update_config()
                return
            if self.path == "/api/memory":
                self.save_memory()
                return
            if self.path == "/api/skills":
                self.create_skill_handler()
                return
            if self.path == "/api/tools/use_skill":
                self.tool_use_skill()
                return
            if self.path == "/api/sessions":
                self.create_session()
                return
            if self.path == "/api/resolve-file-name":
                self.resolve_file_name()
                return
            if self.path == "/api/attachments":
                self.create_attachment()
                return
            if self.path == "/api/tools/list_files":
                self.tool_list_files()
                return
            if self.path == "/api/tools/read_file":
                self.tool_read_file()
                return
            if self.path == "/api/tools/search_files":
                self.tool_search_files()
                return
            if self.path == "/api/tools/glob_files":
                self.tool_glob_files()
                return
            if self.path == "/api/tools/propose_edit":
                self.tool_propose_edit()
                return
            if self.path == "/api/tools/apply_edit":
                self.tool_apply_edit()
                return
            if self.path == "/api/tools/run_command":
                self.tool_run_command()
                return
            if self.path == "/api/tools/task":
                self.tool_task()
                return
            if self.path == "/api/tools/write_file":
                self.tool_write_file()
                return
            if self.path == "/api/tools/delete_file":
                self.tool_delete_file()
                return
            if self.path == "/api/tools/web_fetch":
                self.tool_web_fetch()
                return
            if self.path == "/api/tools/save_memory":
                self.tool_save_memory()
                return
            if self.path == "/api/mkdir":
                self.create_directory()
                return
            if self.path == "/api/compact":
                self.compact()
                return
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return

        self.send_error(404)

    def do_PUT(self):
        try:
            if self.path.startswith("/api/sessions/") and self.path.endswith("/archive"):
                self.archive_session(self.path.rsplit("/", 2)[-2])
                return
            if self.path.startswith("/api/sessions/"):
                self.save_session(self.path.rsplit("/", 1)[-1])
                return
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        self.send_error(404)

    def do_DELETE(self):
        try:
            if self.path.startswith("/api/memory"):
                parsed = parse.urlparse(self.path)
                query = parse.parse_qs(parsed.query)
                file_name = query.get("file", [None])[0]
                if file_name:
                    self.send_json(delete_memory(file_name))
                    return
            if self.path.startswith("/api/skills"):
                parsed = parse.urlparse(self.path)
                query = parse.parse_qs(parsed.query)
                skill_name = query.get("name", [None])[0]
                if skill_name:
                    self.send_json(delete_skill(skill_name))
                    return
            if self.path.startswith("/api/sessions/"):
                self.delete_session(self.path.rsplit("/", 1)[-1])
                return
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        self.send_error(404)

    def read_body_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b"{}"
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def send_json(self, data, status=200):
        status, payload = json_bytes(data, status)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    # ── Skill management handlers ──

    def create_skill_handler(self):
        body = self.read_body_json()
        name = (body.get("name") or "").strip()
        desc = (body.get("description") or "").strip()
        body_text = (body.get("body") or "").strip()
        tools = (body.get("tools") or "").strip()
        keywords = (body.get("keywords") or "").strip()
        if not name:
            raise ValueError("skill name is required")
        if not body_text:
            raise ValueError("skill body is required")
        self.send_json(create_skill(name, desc, body_text, tools, keywords), 201)

    def tool_use_skill(self):
        body = self.read_body_json()
        skill_name = (body.get("name") or "").strip()
        if not skill_name:
            raise ValueError("skill name is required")
        try:
            skill = read_skill(skill_name)
            self.send_json({
                "ok": True,
                "action": "use_skill",
                "name": skill["name"],
                "description": skill["description"],
                "body": skill["body"],
                "tools": skill.get("tools", []),
            })
        except ValueError:
            available = [s["name"] for s in list_skills()]
            self.send_json({
                "ok": False,
                "action": "use_skill",
                "error": f"Skill '{skill_name}' not found. Available: {', '.join(available) or 'none'}",
            }, 400)

    def get_sessions(self):
        sessions = []
        for path in SESSIONS_DIR.glob("*.json"):
            session = read_json(path, None)
            if session:
                sessions.append(session_summary(session))
        sessions.sort(key=lambda item: item.get("updatedAt") or "", reverse=True)
        self.send_json({"data": sessions})

    def get_session(self, session_id):
        path = session_path(session_id)
        if not path.exists():
            self.send_json({"error": "session not found"}, 404)
            return
        self.send_json(read_json(path, {}))

    def create_session(self):
        body = self.read_body_json()
        session_id = uuid.uuid4().hex[:16]
        session = {
            "id": session_id,
            "title": body.get("title") or "新会话",
            "messages": [],
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        write_json(session_path(session_id), session)
        self.send_json(session, 201)

    def save_session(self, session_id):
        body = self.read_body_json()
        path = session_path(session_id)
        if path.exists():
            session = read_json(path, {})
        else:
            session = {"id": safe_session_id(session_id), "createdAt": now_iso()}
        session["title"] = body.get("title") or session.get("title") or "未命名会话"
        session["messages"] = body.get("messages") or []
        session["stats"] = body.get("stats") or session.get("stats") or {}
        session["updatedAt"] = now_iso()
        write_json(path, session)
        self.send_json(session)

    def archive_session(self, session_id):
        """Save a full-history backup before compaction."""
        body = self.read_body_json()
        messages = body.get("messages") or []
        if not messages:
            self.send_json({"ok": False, "error": "no messages to archive"}, 400)
            return
        archive_dir = SESSIONS_DIR / "archive"
        archive_dir.mkdir(exist_ok=True)
        ts = now_iso().replace(":", "-")
        path = archive_dir / f"{safe_session_id(session_id)}_{ts}.json"
        write_json(path, {"id": session_id, "archivedAt": now_iso(), "messageCount": len(messages), "messages": messages})
        self.send_json({"ok": True, "path": str(path)})

    def delete_session(self, session_id):
        path = session_path(session_id)
        if path.exists():
            path.unlink()
        self.send_json({"ok": True})

    def save_memory(self):
        body = self.read_body_json()
        name = body.get("name") or ""
        meta = body.get("meta") or {}
        body_text = body.get("body") or ""
        self.send_json(write_memory(name, meta, body_text), 201)

    def update_config(self):
        body = self.read_body_json()
        updates = {}
        if "projectRoot" in body:
            root = Path(body["projectRoot"]).expanduser().resolve()
            if not root.exists() or not root.is_dir():
                raise ValueError("项目目录不存在或不是文件夹")
            updates["projectRoot"] = str(root)
        self.send_json(save_config(updates))

    def get_files(self, relative_path):
        root, target = resolve_project_path(relative_path)
        if not target.exists():
            raise ValueError("路径不存在")
        if not target.is_dir():
            raise ValueError("当前路径不是文件夹")

        items = []
        for child in target.iterdir():
            if child.name in SKIP_DIRS:
                continue
            stat = child.stat()
            items.append({
                "name": child.name,
                "path": to_project_relative(root, child),
                "type": "dir" if child.is_dir() else "file",
                "size": stat.st_size,
                "updatedAt": dt.datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat(),
            })
        items.sort(key=lambda item: (item["type"] != "dir", item["name"].lower()))
        self.send_json({"root": str(root), "path": relative_path or "", "items": items[:500]})

    def get_file(self, relative_path, raw=False):
        root, target = resolve_attachment_path(relative_path)
        is_attachment = target is not None
        if not target:
            root, target = resolve_project_path(relative_path)
        if not target.exists() or not target.is_file():
            raise ValueError("文件不存在")
        display_path = display_attachment_path(root, target) if is_attachment else to_project_relative(root, target)
        data = target.read_bytes()
        truncated = len(data) > MAX_PREVIEW_BYTES
        preview = data[:MAX_PREVIEW_BYTES]
        # Raw mode: return base64 content for image preview
        if raw:
            import base64 as b64
            mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_json({
                "path": display_path,
                "name": target.name,
                "size": len(data),
                "mime": mime,
                "content": b64.b64encode(data).decode("ascii"),
                "truncated": truncated,
            })
            return
        if not is_probably_text(preview):
            self.send_json({
                "path": display_path,
                "name": target.name,
                "binary": True,
                "size": len(data),
                "content": "",
                "truncated": truncated,
            })
            return
        self.send_json({
            "path": display_path,
            "name": target.name,
            "binary": False,
            "size": len(data),
            "content": preview.decode("utf-8", errors="replace"),
            "truncated": truncated,
        })

    def pick_folder(self):
        config = load_config()
        root = Path(config["projectRoot"]).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("项目目录不存在")
        selected = open_native_folder_picker(root)
        if not selected:
            self.send_json({"cancelled": True})
            return
        target = Path(selected).expanduser().resolve()
        self.send_json({
            "cancelled": False,
            "path": str(target),
        })

    def pick_file(self):
        config = load_config()
        root = Path(config["projectRoot"]).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("项目目录不存在或不是文件夹")
        selected = open_native_file_picker(root)

        if not selected:
            self.send_json({"cancelled": True})
            return

        target = Path(selected).expanduser().resolve()
        if root != target and root not in target.parents:
            raise ValueError("请选择当前项目目录内的文件，或先切换项目目录")
        if not target.is_file():
            raise ValueError("请选择文件")

        self.send_json({
            "cancelled": False,
            "path": to_project_relative(root, target),
            "name": target.name,
            "size": target.stat().st_size,
        })

    def resolve_file_name(self):
        body = self.read_body_json()
        name = Path(str(body.get("name") or "")).name
        if not name:
            raise ValueError("文件名不能为空")
        expected_size = body.get("size")
        try:
            expected_size = int(expected_size)
        except (TypeError, ValueError):
            expected_size = None

        root, _ = resolve_project_path("")
        matches = []
        for current, dirs, files in os.walk(root):
            dirs[:] = [item for item in dirs if item not in SKIP_DIRS]
            if name not in files:
                continue
            candidate = Path(current) / name
            try:
                if expected_size is not None and candidate.stat().st_size != expected_size:
                    continue
            except OSError:
                continue
            matches.append(candidate.resolve())
            if len(matches) > 20:
                break

        if not matches:
            raise ValueError("没有在当前项目目录中找到该文件，请确认已先载入正确项目目录")
        if len(matches) > 1:
            sample = "、".join(to_project_relative(root, item) for item in matches[:5])
            raise ValueError(f"找到多个同名同大小文件，请从左侧文件树选择或手动输入路径：{sample}")

        target = matches[0]
        self.send_json({
            "path": to_project_relative(root, target),
            "name": target.name,
            "size": target.stat().st_size,
        })

    def create_attachment(self):
        body = self.read_body_json()
        name = sanitize_filename(body.get("name"))
        content_base64 = body.get("contentBase64") or ""
        if not content_base64:
            raise ValueError("附件内容不能为空")
        try:
            data = base64.b64decode(content_base64, validate=True)
        except Exception as exc:
            raise ValueError("附件内容格式不正确") from exc
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"附件超过大小限制：{MAX_ATTACHMENT_BYTES // 1024 // 1024}MB")

        stored_name = f"{uuid.uuid4().hex[:12]}-{name}"
        target = (ATTACHMENTS_DIR / stored_name).resolve()
        if ATTACHMENTS_DIR != target and ATTACHMENTS_DIR not in target.parents:
            raise ValueError("attachment path is outside attachments directory")
        target.write_bytes(data)
        self.send_json({
            "path": display_attachment_path(ATTACHMENTS_DIR, target),
            "name": name,
            "size": len(data),
        })

    def tool_list_files(self):
        body = self.read_body_json()
        relative_path = body.get("path") or ""
        try:
            max_depth = int(body.get("maxDepth") or 1)
        except (TypeError, ValueError):
            max_depth = 1
        max_depth = max(1, min(max_depth, 3))
        root, start = resolve_project_path(relative_path)
        if not start.exists() or not start.is_dir():
            raise ValueError("目录不存在")

        items = []

        def walk_dir(current, depth):
            if len(items) >= 200:
                return
            try:
                children = sorted(
                    current.iterdir(),
                    key=lambda item: (not item.is_dir(), item.name.lower()),
                )
            except OSError:
                return
            for child in children:
                if child.name in SKIP_DIRS:
                    continue
                rel = to_project_relative(root, child)
                if child.is_dir():
                    items.append({"type": "dir", "path": rel, "name": child.name})
                    if depth < max_depth:
                        walk_dir(child, depth + 1)
                elif child.is_file():
                    try:
                        size = child.stat().st_size
                    except OSError:
                        size = 0
                    items.append({"type": "file", "path": rel, "name": child.name, "size": size})
                if len(items) >= 200:
                    return

        walk_dir(start, 1)
        self.send_json({
            "ok": True,
            "action": "list_files",
            "path": relative_path or "/",
            "count": len(items),
            "maxDepth": max_depth,
            "truncated": len(items) >= 200,
            "items": items,
        })

    def tool_read_file(self):
        body = self.read_body_json()
        path = body.get("path") or ""
        root, target = resolve_attachment_path(path)
        is_attachment = target is not None
        if not target:
            root, target = resolve_project_path(path)
        if not target.exists() or not target.is_file():
            raise ValueError("文件不存在")
        content, size, truncated = read_text_limited(target, MAX_TOOL_READ_BYTES)
        line_range = None
        start_line = body.get("startLine")
        end_line = body.get("endLine")
        if start_line is not None or end_line is not None:
            lines = content.splitlines()
            try:
                start = max(1, int(start_line or 1))
                end = min(len(lines), int(end_line or len(lines)))
            except (TypeError, ValueError):
                raise ValueError("startLine/endLine 必须是数字")
            if end < start:
                raise ValueError("endLine 不能小于 startLine")
            content = "\n".join(lines[start - 1:end])
            line_range = {"start": start, "end": end}
        self.send_json({
            "ok": True,
            "action": "read_file",
            "path": display_attachment_path(root, target) if is_attachment else to_project_relative(root, target),
            "content": content,
            "size": size,
            "truncated": truncated,
            "lineRange": line_range,
        })

    def _resolve_search_candidates(self, root, start, glob_pattern):
        """Resolve file candidates for search tools."""
        if start.is_file():
            return [start]

        # Apply glob pattern to filter files
        if glob_pattern:
            try:
                candidates = list(start.glob(glob_pattern))
                # Also search subdirectories: rglob
                if "**" not in glob_pattern:
                    candidates += list(start.rglob(glob_pattern))
                candidates = sorted(set(candidates))
            except Exception:
                candidates = []
        else:
            candidates = []
            for path in start.rglob("*"):
                if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                    continue
                if path.is_file():
                    candidates.append(path)

        # Filter: skip dirs
        candidates = [p for p in candidates if p.is_file()]
        # Filter: skip skipped dirs
        candidates = [p for p in candidates if not any(part in SKIP_DIRS for part in p.relative_to(root).parts)]
        return candidates

    def tool_search_files(self):
        body = self.read_body_json()
        query = (body.get("query") or body.get("pattern") or "").strip()
        start_path = body.get("path") or ""
        use_regex = bool(body.get("regex") or body.get("useRegex") or False)
        file_types = body.get("type") or body.get("fileTypes") or ""
        glob_pattern = body.get("glob") or ""
        context_lines = int(body.get("contextAround") or body.get("contextLines") or 0)
        max_per_file = int(body.get("maxPerFile") or body.get("maxResultsPerFile") or 10)

        if not query:
            raise ValueError("搜索关键词或正则表达式不能为空")
        if use_regex:
            try:
                needle = re.compile(query, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"正则表达式无效：{exc}")
        else:
            needle = query

        # Determine file type filter
        allowed_exts = set()
        if file_types:
            allowed_exts = {ext.strip().lstrip(".").lower() for ext in file_types.replace(",", " ").split() if ext.strip()}

        root, start = resolve_project_path(start_path)
        if not start.exists():
            raise ValueError("搜索路径不存在")

        candidates = self._resolve_search_candidates(root, start, glob_pattern)

        results = []
        for path in candidates:
            if allowed_exts:
                ext = path.suffix.lstrip(".").lower()
                if ext not in allowed_exts:
                    continue
            if len(results) >= MAX_SEARCH_RESULTS:
                break
            rel = to_project_relative(root, path)

            # Name match
            if use_regex:
                matched_name = bool(needle.search(path.name))
            else:
                matched_name = needle.lower() in path.name.lower() or needle.lower() in rel.lower()

            matches = []
            try:
                if path.stat().st_size <= MAX_SEARCH_FILE_BYTES:
                    content, _, _ = read_text_limited(path, MAX_SEARCH_FILE_BYTES)
                    for line_no, line in enumerate(content.splitlines(), start=1):
                        if use_regex:
                            hit = bool(needle.search(line))
                        else:
                            hit = needle.lower() in line.lower()
                        if hit:
                            # Collect context lines
                            lines_for_context = content.splitlines()
                            ctx_start = max(0, line_no - 1 - context_lines)
                            ctx_end = min(len(lines_for_context), line_no - 1 + context_lines + 1)
                            ctx = []
                            for ctx_i in range(ctx_start, ctx_end):
                                ctx.append({
                                    "line": ctx_i + 1,
                                    "text": lines_for_context[ctx_i][:500],
                                })
                            matches.append({
                                "line": line_no,
                                "text": line[:500],
                                "context": ctx if context_lines > 0 else None,
                            })
                            if len(matches) >= max_per_file:
                                break
            except Exception:
                pass
            if matched_name or matches:
                results.append({
                    "path": rel,
                    "nameMatch": matched_name,
                    "matches": matches,
                })

        self.send_json({
            "ok": True,
            "action": "search_files",
            "query": query,
            "regex": use_regex,
            "count": len(results),
            "truncated": len(results) >= MAX_SEARCH_RESULTS,
            "results": results,
        })

    def tool_glob_files(self):
        body = self.read_body_json()
        pattern = (body.get("pattern") or "").strip()
        start_path = body.get("path") or ""
        if not pattern:
            raise ValueError("glob 模式不能为空")

        root, start = resolve_project_path(start_path)
        if not start.exists():
            raise ValueError("搜索路径不存在")

        results = []
        try:
            for path in start.rglob(pattern):
                if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                    continue
                rel = to_project_relative(root, path)
                if path.is_dir():
                    results.append({"path": rel, "type": "dir"})
                elif path.is_file():
                    try:
                        size = path.stat().st_size
                    except OSError:
                        size = 0
                    results.append({"path": rel, "type": "file", "size": size})
                if len(results) >= 200:
                    break
        except Exception as exc:
            raise ValueError(f"glob 模式无效：{exc}")

        if not results:
            root_rel = to_project_relative(root, root)
            results = []
            # Try rglob on root
            for path in root.rglob(pattern):
                if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                    continue
                rel = to_project_relative(root, path)
                if path.is_dir():
                    results.append({"path": rel, "type": "dir"})
                elif path.is_file():
                    try:
                        size = path.stat().st_size
                    except OSError:
                        size = 0
                    results.append({"path": rel, "type": "file", "size": size})
                if len(results) >= 200:
                    break

        self.send_json({
            "ok": True,
            "action": "glob_files",
            "pattern": pattern,
            "count": len(results),
            "truncated": len(results) >= 200,
            "results": results,
        })

    def _fuzzy_find(self, text, fragment):
        """Try to find fragment in text, falling back to whitespace-normalized matching."""
        # Normalize line endings first (Windows \r\n vs Unix \n)
        text = text.replace("\r\n", "\n")
        fragment = fragment.replace("\r\n", "\n")

        if fragment in text:
            return fragment  # exact match

        def _norm(s):
            """Normalize tabs to spaces."""
            return s.replace("\t", "    ")

        text_lines = text.splitlines()
        frag_lines = fragment.splitlines()

        # Strip trailing empty lines from fragment (model often adds them)
        while frag_lines and not frag_lines[-1].strip():
            frag_lines.pop()
        while frag_lines and not frag_lines[0].strip():
            frag_lines.pop(0)

        if not frag_lines:
            return None

        if len(frag_lines) == 1:
            stripped = fragment.strip()
            for line in text_lines:
                if line.strip() == stripped:
                    return line
            return None

        # Strategy 1: match with rstrip (trailing whitespace insensitive), skip blank frag lines
        for i in range(len(text_lines) - len(frag_lines) + 1):
            window = text_lines[i:i + len(frag_lines)]
            match = True
            for wl, fl in zip(window, frag_lines):
                if not fl.strip():
                    continue
                if wl.rstrip() != fl.rstrip():
                    match = False
                    break
            if match:
                return "\n".join(window)

        # Strategy 2: normalize tabs→spaces, rstrip match
        text_norm = [_norm(l) for l in text_lines]
        frag_norm = [_norm(l) for l in frag_lines]
        for i in range(len(text_norm) - len(frag_norm) + 1):
            window = text_norm[i:i + len(frag_norm)]
            match = True
            for wl, fl in zip(window, frag_norm):
                if not fl.strip():
                    continue
                if wl.rstrip() != fl.rstrip():
                    match = False
                    break
            if match:
                return "\n".join(text_lines[i:i + len(frag_norm)])

        # Strategy 3: full strip match (ignore all leading/trailing whitespace)
        for i in range(len(text_lines) - len(frag_lines) + 1):
            window = text_lines[i:i + len(frag_lines)]
            if all(wl.strip() == fl.strip() for wl, fl in zip(window, frag_lines)):
                return "\n".join(window)

        # Strategy 4: try with normalized leading whitespace too (tab→space + strip)
        for i in range(len(text_norm) - len(frag_norm) + 1):
            window = text_norm[i:i + len(frag_norm)]
            if all(wl.strip() == fl.strip() for wl, fl in zip(window, frag_norm)):
                return "\n".join(text_lines[i:i + len(frag_norm)])

        # Strategy 5: difflib approximate matching (for when model tweaks fragment content)
        frag_text = "\n".join(frag_norm)
        best_ratio = 0.0
        best_window = None
        for i in range(len(text_norm) - len(frag_norm) + 1):
            window = text_norm[i:i + len(frag_norm)]
            window_text = "\n".join(window)
            ratio = difflib.SequenceMatcher(None, window_text, frag_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_window = "\n".join(text_lines[i:i + len(frag_norm)])
        if best_ratio >= 0.65 and best_window is not None:
            return best_window

        return None

    def build_edit_payload(self, body):
        path = body.get("path") or ""
        root, target = resolve_project_path(path)
        rel = to_project_relative(root, target)
        old_text = ""
        if target.exists():
            if not target.is_file():
                raise ValueError("目标路径不是文件")
            old_text, _, _ = read_text_limited(target, MAX_TOOL_READ_BYTES)

        if "oldText" in body and "newText" in body:
            old_fragment = body.get("oldText") or ""
            new_fragment = body.get("newText") or ""
            found = self._fuzzy_find(old_text, old_fragment)
            if not found:
                preview = old_fragment[:120].replace("\n", "\\n")
                hint = (
                    f"oldText 在目标文件中未找到。文件可能已被修改，或 oldText 片段不完整。\n"
                    f"请用 read_file 重新读取 {rel} 的最新内容，精确复制需要替换的片段后重试。\n"
                    f"oldText 片段：{preview}..."
                )
                raise ValueError(hint)
            new_text = old_text.replace(found, new_fragment, 1)
        else:
            new_text = body.get("newContent")
            if new_text is None:
                new_text = body.get("content")
            if new_text is None:
                raise ValueError("缺少 newContent/content，或 oldText/newText")
            new_text = str(new_text)

        diff = make_unified_diff(old_text, new_text, rel)
        return root, target, rel, old_text, new_text, diff

    def tool_propose_edit(self):
        body = self.read_body_json()
        _, target, rel, _, new_text, diff = self.build_edit_payload(body)
        mtime = int(target.stat().st_mtime * 1000) if target.exists() else 0
        self.send_json({
            "ok": True,
            "action": "propose_edit",
            "path": rel,
            "diff": diff or "(no changes)",
            "newContent": new_text,
            "mtime": mtime,
        })

    def tool_apply_edit(self):
        body = self.read_body_json()
        _, target, rel, old_text, new_text, diff = self.build_edit_payload(body)
        expected_mtime = body.get("expectedMtime")
        if expected_mtime is not None and target.exists():
            current_mtime = int(target.stat().st_mtime * 1000)
            if current_mtime != int(expected_mtime):
                self.send_json({"ok": False, "action": "apply_edit", "path": rel, "error": "File modified by another session, please re-read.", "currentMtime": current_mtime}, 409)
                return
        backup_path = None
        if target.exists():
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", rel)
            backup_path = FILE_BACKUP_DIR / f"{safe_name}.{stamp}.bak"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(old_text, encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_text, encoding="utf-8")
        self.send_json({
            "ok": True,
            "action": "apply_edit",
            "path": rel,
            "diff": diff or "(no changes)",
            "backupPath": str(backup_path) if backup_path else None,
        })

    def tool_task(self):
        body = self.read_body_json()
        task_prompt = (body.get("prompt") or body.get("description") or "").strip()
        if not task_prompt:
            raise ValueError("子任务描述不能为空")

        # Build system prompt for sub-agent
        sub_system = (
            "你是一个编程子 Agent，负责完成主 Agent 分配的子任务。\n"
            "环境：Windows + PowerShell。你可以使用工具读取文件、搜索代码、列出目录。\n"
            "请高效完成任务：先用 glob_files 或 list_files 定位目标文件，再用 read_file 或 search_files 提取所需信息。\n"
            "将所有发现整理成清晰的报告返回给主 Agent。\n"
            "不要调用 run_command——你是只读分析角色，只能用文件/搜索工具。\n"
            f"项目根目录: {load_config()['projectRoot']}"
        )

        model = (body.get("model") or "").strip()
        api_key = self.headers.get("Authorization", "")

        if not model:
            raise ValueError("缺少模型名称")
        if not api_key:
            raise ValueError("缺少 API key")

        result = run_subagent(task_prompt, sub_system, model, api_key)
        self.send_json({
            "ok": result["ok"],
            "action": "task",
            "prompt": task_prompt,
            "result": result["result"],
            "rounds": result["rounds"],
            "tool_rounds": result.get("tool_rounds", 0),
        }, 200 if result["ok"] else 500)

    def tool_run_command(self):
        body = self.read_body_json()
        if body.get("permissionProfile") == "plan":
            self.send_json({
                "ok": False,
                "action": "run_command",
                "command": body.get("command") or "",
                "error": "当前权限模式为计划，不允许运行命令",
            }, 400)
            return
        command = (body.get("command") or "").strip()
        ok, reason = is_safe_command(command)
        if not ok:
            self.send_json({
                "ok": False,
                "action": "run_command",
                "command": command,
                "error": reason,
            }, 400)
            return

        root, _ = resolve_project_path("")
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=MAX_COMMAND_SECONDS,
            **_hidden_subprocess_kwargs(),
        )
        self.send_json({
            "ok": completed.returncode == 0,
            "action": "run_command",
            "command": command,
            "cwd": str(root),
            "exitCode": completed.returncode,
            "stdout": completed.stdout[-20000:],
            "stderr": completed.stderr[-20000:],
        })

    def tool_write_file(self):
        body = self.read_body_json()
        path = (body.get("path") or "").strip()
        content = body.get("content") or ""
        if not path:
            raise ValueError("文件路径不能为空")
        root, target = resolve_project_path(path)
        rel = to_project_relative(root, target)

        # Backup existing file
        backup_path = None
        old_content = ""
        if target.exists():
            if not target.is_file():
                raise ValueError("目标路径已存在且不是文件")
            try:
                old_content, _, _ = read_text_limited(target, MAX_TOOL_READ_BYTES)
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
                safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", rel)
                backup_path = FILE_BACKUP_DIR / f"{safe_name}.{stamp}.bak"
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                backup_path.write_text(old_content, encoding="utf-8")
            except Exception as exc:
                raise ValueError(f"备份原文件失败: {exc}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        diff = make_unified_diff(old_content, content, rel)

        self.send_json({
            "ok": True,
            "action": "write_file",
            "path": rel,
            "size": len(content.encode("utf-8")),
            "backupPath": str(backup_path) if backup_path else None,
            "diff": diff or "(new file)",
        })

    def tool_delete_file(self):
        body = self.read_body_json()
        path = (body.get("path") or "").strip()
        if not path:
            raise ValueError("文件路径不能为空")
        root, target = resolve_project_path(path)
        if not target.exists():
            raise ValueError("文件不存在")
        is_dir = target.is_dir()
        if not is_dir and not target.is_file():
            raise ValueError("只能删除文件或空目录")
        if is_dir and any(target.iterdir()):
            raise ValueError("目录不为空，无法删除")
        rel = to_project_relative(root, target)

        # Backup before deleting (files only)
        backup_path = None
        size = 0
        if target.is_file():
            try:
                content, _, _ = read_text_limited(target, MAX_TOOL_READ_BYTES)
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
                safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", rel)
                backup_path = FILE_BACKUP_DIR / f"{safe_name}.{stamp}.bak"
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                backup_path.write_text(content, encoding="utf-8")
            except Exception as exc:
                raise ValueError(f"备份文件失败: {exc}")
            size = target.stat().st_size
            target.unlink()
        else:
            target.rmdir()

        self.send_json({
            "ok": True,
            "action": "delete_file",
            "path": rel,
            "size": size,
            "backupPath": str(backup_path) if backup_path else None,
        })

    def tool_web_fetch(self):
        body = self.read_body_json()
        url = (body.get("url") or "").strip()
        if not url:
            raise ValueError("URL 不能为空")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        # SSRF protection: block internal/private IPs
        try:
            host = parse.urlparse(url).hostname or ""
            import ipaddress
            addr = ipaddress.ip_address(host)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                raise ValueError("不允许访问内网地址")
        except ValueError as exc:
            if "不允许访问内网地址" in str(exc):
                raise
            # If host is not an IP (e.g., a domain), allow it
            pass

        try:
            req = request.Request(url, method="GET", headers={
                "User-Agent": "AgentLite/0.4",
                "Accept": "text/html,text/plain,application/json",
            })
            with request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                charset = "utf-8"
                if "charset=" in content_type:
                    charset = content_type.split("charset=")[-1].split(";")[0].strip()

                max_bytes = 256 * 1024
                truncated = len(data) > max_bytes
                preview = data[:max_bytes]

                try:
                    text = preview.decode(charset, errors="replace")
                except Exception:
                    text = preview.decode("utf-8", errors="replace")

                # Strip HTML tags for cleaner output
                import html as html_mod
                if "text/html" in content_type:
                    # Simple HTML to text
                    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
                    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = re.sub(r"\s+", " ", text)
                    text = html_mod.unescape(text)
                    text = text.strip()

                self.send_json({
                    "ok": True,
                    "action": "web_fetch",
                    "url": url,
                    "status": resp.status,
                    "contentType": content_type,
                    "size": len(data),
                    "truncated": truncated,
                    "content": text[:50000],
                })
        except error.HTTPError as exc:
            self.send_json({
                "ok": False,
                "action": "web_fetch",
                "url": url,
                "status": exc.code,
                "error": f"HTTP {exc.code}: {exc.reason}",
            }, 400)
        except Exception as exc:
            self.send_json({
                "ok": False,
                "action": "web_fetch",
                "url": url,
                "error": str(exc),
            }, 400)

    def tool_save_memory(self):
        body = self.read_body_json()
        name = (body.get("name") or "").strip()
        description = (body.get("description") or "").strip()
        content = (body.get("body") or "").strip()
        if not name or not content:
            raise ValueError("name and body are required")
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", name)[:32]
        if not safe:
            raise ValueError("invalid memory name")
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        project = load_config().get("projectRoot", "")
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        md = f"---\nname: {safe}\ndescription: {description}\nproject: {project}\ncreated: {ts}\n---\n\n{content}"
        (MEMORY_DIR / f"{safe}.md").write_text(md, encoding="utf-8")
        self.send_json({"ok": True, "name": safe, "path": str(mem_dir / "MEMORY.md")}, 201)

    def create_directory(self):
        body = self.read_body_json()
        name = (body.get("name") or "").strip()
        parent = (body.get("parent") or "").strip()
        if not name:
            raise ValueError("文件夹名称不能为空")
        root, parent_dir = resolve_project_path(parent)
        if not parent_dir.exists() or not parent_dir.is_dir():
            raise ValueError("父目录不存在")
        target = (parent_dir / name).resolve()
        if root != target and root not in target.parents:
            raise ValueError("路径超出项目范围")
        if target.exists():
            raise ValueError("该路径已存在")
        target.mkdir(parents=False)
        self.send_json({
            "ok": True,
            "path": to_project_relative(root, target),
            "name": name,
        })

    def compact(self):
        body = self.read_body_json()
        messages = body.get("messages") or []
        model = (body.get("model") or "").strip()
        api_key = self.headers.get("Authorization", "")

        if not model:
            raise ValueError("缺少模型名称")
        if not api_key:
            raise ValueError("缺少 API key")
        if len(messages) < 6:
            raise ValueError("消息太少，无需压缩")

        # Keep the last few messages, summarize the rest
        keep_count = max(2, min(6, len(messages) // 4))
        to_compress = messages[:len(messages) - keep_count]

        # Format conversation as text
        lines = []
        for msg in to_compress:
            role = msg.get("role", "?")
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            label = {"user": "用户", "assistant": "Agent", "tool-call": "工具调用", "tool-result": "工具结果"}.get(role, role)
            # Truncate long content for the summary request
            short = content[:800] + ("..." if len(content) > 800 else "")
            lines.append(f"[{label}] {short}")

        conversation_text = "\n".join(lines)
        if len(conversation_text) > 24000:
            conversation_text = conversation_text[:24000] + "\n...(已截断)"

        prompt = (
            "请用中文简洁总结以下编程对话的关键内容，保留：\n"
            "1. 用户的核心需求和目标\n"
            "2. Agent 做了哪些关键操作（读/写了什么文件、做了什么修改）\n"
            "3. 最终达成的结果和当前状态\n"
            "4. 重要的未完成事项\n"
            "格式：用 3-8 句话的连续段落，不要列表。\n\n"
            f"{conversation_text}"
        )

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.1,
            "max_tokens": 1200,
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = api_key

        try:
            req = request.Request(
                NEW_API_BASE_URL + "/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers=headers,
            )
            with request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                summary = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                self.send_json({
                    "ok": True,
                    "summary": summary.strip() or "(压缩摘要生成失败)",
                    "compressed": len(to_compress),
                    "kept": keep_count,
                })
        except Exception as exc:
            self.send_json({"ok": False, "error": f"压缩失败: {exc}"}, 500)

    def proxy(self, method, upstream_path):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        is_stream = False
        if body:
            try:
                is_stream = bool(json.loads(body.decode("utf-8")).get("stream"))
            except Exception:
                is_stream = False
        api_key = self.headers.get("Authorization", "")
        base_url = self.headers.get("X-Base-URL", "") or NEW_API_BASE_URL
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = api_key

        upstream = request.Request(
            base_url + upstream_path,
            data=body,
            method=method,
            headers=headers,
        )

        headers_sent = False
        try:
            with request.urlopen(upstream, timeout=180) as resp:
                # Set a read timeout so readline() doesn't hang forever on stale connections
                import socket
                try: resp.fp._sock.settimeout(30)
                except Exception: pass
                if is_stream:
                    self.send_response(resp.status)
                    self.send_header("Content-Type", resp.headers.get("Content-Type", "text/event-stream"))
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    headers_sent = True
                    idle_ticks = 0
                    while True:
                        try:
                            chunk = resp.readline()
                        except socket.timeout:
                            idle_ticks += 1
                            if idle_ticks >= 2:  # 60s total idle — treat as dead
                                err_line = "data: [ERROR] Stream stalled (no data for 60s)\n\n".encode("utf-8")
                                try: self.wfile.write(err_line); self.wfile.flush()
                                except: pass
                                break
                            # Send keepalive comment
                            try: self.wfile.write(b": keepalive\n\n"); self.wfile.flush()
                            except: break
                            continue
                        idle_ticks = 0
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    return

                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                headers_sent = True
                self.wfile.write(data)
        except error.HTTPError as exc:
            data = exc.read()
            if not headers_sent:
                self.send_response(exc.code)
                self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            if headers_sent:
                # Headers already sent — can't send a proper HTTP error.
                # Write a best-effort SSE error line and close.
                try:
                    err_line = f"data: [ERROR] {exc}\\n\\n".encode("utf-8")
                    self.wfile.write(err_line)
                    self.wfile.flush()
                except Exception:
                    pass
            else:
                data = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    os.chdir(APP_DIR)
    ThreadingHTTPServer.daemon_threads = True
    server = ThreadingHTTPServer(("127.0.0.1", PORT), AgentLiteHandler)
    # Prevent accept() from blocking indefinitely; also keeps Ctrl+C responsive
    server.socket.settimeout(2.0)
    print(f"Agent Lite is running: http://127.0.0.1:{PORT}")
    print(f"Proxy upstream: {NEW_API_BASE_URL}")
    print(f"Project root: {load_config()['projectRoot']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
