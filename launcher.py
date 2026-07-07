"""
Agent Lite launcher — entry point for PyInstaller bundle.
"""
import os
import subprocess
import sys
import webbrowser
import tkinter as tk
from pathlib import Path

GITHUB_REPO = "fhy-A/agent-lite"


def kill_existing():
    """Kill any already-running AgentLite.exe or pythonw server processes."""
    import signal
    current_pid = os.getpid()
    killed = 0
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "name='AgentLite.exe' or name='pythonw.exe' or name='python.exe'",
             "get", "ProcessId,CommandLine"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if not parts:
                continue
            pid_str = parts[-1]
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            if pid == current_pid:
                continue
            # Only kill if it's an agent-lite process
            cmdline = " ".join(parts[:-1]).lower()
            if "agent-lite" in cmdline or "agentlite" in cmdline or "launcher" in cmdline:
                try:
                    os.kill(pid, signal.SIGTERM)
                    killed += 1
                except Exception:
                    pass
            elif "server.py" in cmdline:
                try:
                    os.kill(pid, signal.SIGTERM)
                    killed += 1
                except Exception:
                    pass
    except Exception:
        pass
    return killed


def apply_pending_update():
    """If AgentLite.exe.new exists, replace the current exe with it."""
    if not getattr(sys, 'frozen', False):
        return
    current_exe = Path(sys.executable)
    new_exe = current_exe.parent / "AgentLite.exe.new"
    if new_exe.exists():
        old_exe = current_exe.parent / "AgentLite.exe.old"
        try:
            if old_exe.exists():
                old_exe.unlink()
            current_exe.rename(old_exe)
            new_exe.rename(current_exe)
        except Exception:
            pass
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/VERSION"
RELEASE_EXE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/AgentLite.exe"


def get_base_dir():
    """Get the directory containing app files (handles PyInstaller bundle)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def ensure_dirs():
    """Create required directories if they don't exist."""
    data_home = Path.home() / ".agent-lite"
    for sub in ["sessions", "memory", "skills", "attachments", "file-backups"]:
        (data_home / sub).mkdir(parents=True, exist_ok=True)
    return data_home


def read_local_version():
    """Read local VERSION file."""
    vfile = get_base_dir() / "VERSION"
    if vfile.exists():
        return vfile.read_text(encoding="utf-8").strip()
    return "0.0.0"


def read_remote_version():
    """Fetch remote VERSION from GitHub raw."""
    import urllib.request
    try:
        resp = urllib.request.urlopen(VERSION_URL, timeout=3)
        return resp.read().decode("utf-8").strip()
    except Exception:
        return None


def check_and_update():
    """Check for updates and apply if newer version available."""
    local = read_local_version()
    remote = read_remote_version()
    if not remote or remote == local:
        return False
    # Simple semver comparison
    try:
        lv = tuple(int(x) for x in local.split("."))
        rv = tuple(int(x) for x in remote.split("."))
        if rv <= lv:
            return False
    except Exception:
        return False

    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    if not mb.askyesno("Agent Lite 更新", f"发现新版本 v{remote}（当前 v{local}）\n\n是否立即更新？"):
        return False

    # Show progress window
    pw = tk.Toplevel()
    pw.title("Agent Lite 更新中")
    pw.geometry("420x130")
    pw.resizable(False, False)
    lbl = tk.Label(pw, text=f"正在下载 v{remote}...", font=("Microsoft YaHei UI", 10))
    lbl.pack(pady=(24, 6))
    progress = tk.Label(pw, text="0%", font=("Microsoft YaHei UI", 9), fg="#888")
    progress.pack()
    pw.update()

    try:
        import urllib.request
        if getattr(sys, 'frozen', False):
            target_dir = Path(sys.executable).parent
        else:
            target_dir = get_base_dir() / "dist"
        target_dir.mkdir(parents=True, exist_ok=True)
        new_exe = target_dir / "AgentLite.exe.new"

        last_pct = [0]
        def report_progress(block_count, block_size, total_size):
            if total_size <= 0:
                return
            pct = min(int(block_count * block_size / total_size * 100), 100)
            if pct - last_pct[0] >= 5:
                last_pct[0] = pct
                progress.config(text=f"{pct}%")
                pw.update()

        urllib.request.urlretrieve(RELEASE_EXE_URL, str(new_exe), reporthook=report_progress)

        pw.destroy()
        root.destroy()

        mb.showinfo("更新完成", f"Agent Lite v{remote} 已下载至：\n{target_dir}\n\n请重启应用以完成更新。")
    except Exception as e:
        pw.destroy()
        root.destroy()
        mb.showwarning("更新失败", f"下载失败：{e}\n\n请检查网络后重试。")
        return False

    return True


def main():
    # Apply pending update if downloaded
    apply_pending_update()

    # Kill any existing agent-lite processes before starting
    killed = kill_existing()
    if killed:
        import time
        time.sleep(0.5)  # Wait for port to be released

    # Start server first, then check for updates in background
    import threading
    threading.Thread(target=check_and_update, daemon=True).start()

    base = get_base_dir()
    data_dir = ensure_dirs()

    # Copy bundled data files if this is first run
    bundled_data = base / "data"
    if bundled_data.exists():
        for sub in ["memory", "skills"]:
            src = bundled_data / sub
            dst = data_dir / sub
            if src.exists() and not any(dst.iterdir()):
                for f in src.iterdir():
                    if f.is_file():
                        (dst / f.name).write_text(f.read_text(encoding="utf-8-sig"), encoding="utf-8")

    # Set environment for server
    os.environ["AGENT_LITE_PORT"] = "3010"
    os.environ["AGENT_LITE_DATA_DIR"] = str(data_dir)

    # Import and start server
    os.chdir(str(base))
    import server
    import threading
    from http.server import ThreadingHTTPServer

    # Override DATA_DIR paths in server module
    server.DATA_DIR = data_dir
    server.SESSIONS_DIR = data_dir / "sessions"
    server.MEMORY_DIR = data_dir / "memory"
    server.SKILLS_DIR = data_dir / "skills"
    server.ATTACHMENTS_DIR = data_dir / "attachments"
    server.FILE_BACKUP_DIR = data_dir / "file-backups"
    server.CONFIG_PATH = data_dir / "config.json"
    for d in [server.DATA_DIR, server.SESSIONS_DIR, server.MEMORY_DIR,
              server.SKILLS_DIR, server.ATTACHMENTS_DIR, server.FILE_BACKUP_DIR]:
        d.mkdir(exist_ok=True)

    port = int(os.environ.get("AGENT_LITE_PORT", "3010"))
    server_obj = ThreadingHTTPServer(("127.0.0.1", port), server.AgentLiteHandler)

    print(f"Agent Lite running at http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")

    try:
        server_obj.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_obj.shutdown()


if __name__ == "__main__":
    main()
