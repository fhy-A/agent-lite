"""
Agent Lite launcher — entry point for PyInstaller bundle.
"""
import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def kill_existing():
    """Kill any already-running AgentLite.exe or pythonw server processes."""
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
            cmdline = " ".join(parts[:-1]).lower()
            if any(kw in cmdline for kw in ["agent-lite", "agentlite", "launcher", "server.py"]):
                subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                               capture_output=True, timeout=5)
                killed += 1
    except Exception:
        pass
    return killed


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


def hide_console():
    """Hide the console window (--console build) so user only sees tray + browser."""
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def main():
    hide_console()
    try:
        _main()
    except Exception as e:
        import traceback
        crash_log = Path.home() / ".agent-lite" / "crash.log"
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        with open(crash_log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise


def _main():
    # Kill any existing agent-lite processes before starting
    killed = kill_existing()
    if killed:
        import time
        time.sleep(0.5)  # Wait for port to be released

    base = get_base_dir()
    data_dir = ensure_dirs()

    # Copy tray icon to data dir so pystray can load it reliably (PyInstaller
    # extraction can corrupt binary files in the temp directory)
    _ico_src = base / "agent-lite-icon.ico"
    _ico_dst = data_dir / "agent-lite-icon.ico"
    if _ico_src.exists():
        import shutil as _shutil
        _shutil.copy2(_ico_src, _ico_dst)

    # Copy bundled data files if this is first run
    bundled_data = base / "data"
    if bundled_data.exists():
        for sub in ["memory", "skills"]:
            src = bundled_data / sub
            dst = data_dir / sub
            if src.exists() and not any(dst.iterdir()):
                import shutil as _shutil
                for item in src.iterdir():
                    if item.is_file():
                        (dst / item.name).write_text(item.read_text(encoding="utf-8-sig"), encoding="utf-8")
                    elif item.is_dir():
                        _shutil.copytree(item, dst / item.name)

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

    # pystray's Windows backend requires its message loop on the main thread.
    # Keep the HTTP server in a worker so the packaged app gets a reliable tray.
    server_thread = threading.Thread(
        target=server_obj.serve_forever,
        daemon=False,
        name="agent-lite-http",
    )
    server_thread.start()
    print(f"Agent Lite running at http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")

    try:
        tray_started = server.run_tray_main_thread(port, server_obj)
        if not tray_started:
            server_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server_obj.shutdown()
        server_obj.server_close()
        server_thread.join(timeout=5)


if __name__ == "__main__":
    main()
