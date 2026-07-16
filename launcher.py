"""
Code launcher — entry point for PyInstaller bundle.
"""
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def has_existing_browser(port=3010):
    """Check the old server before it is stopped so an existing tab can be reused."""
    import urllib.request as _request
    try:
        with _request.urlopen(f"http://127.0.0.1:{port}/api/has-browser", timeout=1.5) as response:
            return bool(json.loads(response.read()).get("hasBrowser"))
    except Exception:
        return False


def should_reuse_browser(port=3010, argv=None):
    """Reuse a connected page, including after the updater stopped the old server."""
    args = sys.argv if argv is None else argv
    return "--reuse-browser" in args or has_existing_browser(port)


def kill_existing():
    """Stop older packaged/dev instances while preserving this PyInstaller process pair."""
    protected_pids = {os.getpid(), os.getppid()}
    killed = 0
    try:
        # Formal builds are versioned (Code-v0.4.12.exe), so querying only
        # Code.exe misses the processes that users actually run. CIM also
        # gives us a stable PID-only output that is easier to parse than WMIC.
        script = r"""
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -match '^Code(?:-v[0-9.]+)?[.]exe$') -or
    (($_.Name -match '^pythonw?(?:[0-9.]+)?[.]exe$') -and
     ($_.CommandLine -match '(?i)(^|[\\/\s])server[.]py([\s\"]|$)'))
} | ForEach-Object { $_.ProcessId }
""".strip()
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in result.stdout.splitlines():
            pid_str = line.strip()
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            if pid in protected_pids:
                continue
            stopped = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if stopped.returncode == 0:
                killed += 1
    except Exception:
        pass
    return killed


def get_base_dir():
    """Get the directory containing app files (handles PyInstaller bundle)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def migrate_old_data_dir():
    """Migrate legacy ~/.agent-lite/ to ~/.code/ (brand rename)."""
    old_home = Path.home() / ".agent-lite"
    new_home = Path.home() / ".code"
    if not old_home.exists() or new_home.exists():
        return new_home
    try:
        import shutil
        shutil.copytree(str(old_home), str(new_home), dirs_exist_ok=True)
        shutil.rmtree(str(old_home), ignore_errors=True)
        print(f"Migrated data: {old_home} -> {new_home}")
    except Exception as e:
        print(f"Data migration failed (non-fatal): {e}")
    return new_home


def ensure_dirs():
    """Create required directories if they don't exist."""
    data_home = Path.home() / ".code"
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
        crash_log = Path.home() / ".code" / "crash.log"
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        with open(crash_log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise


def _main():
    port = 3010
    had_browser = should_reuse_browser(port)

    # Kill any existing Code processes before starting
    killed = kill_existing()
    if killed:
        import time
        time.sleep(0.5)  # Wait for port to be released

    base = get_base_dir()
    migrate_old_data_dir()
    data_dir = ensure_dirs()

    # Copy tray icon to data dir so pystray can load it reliably (PyInstaller
    # extraction can corrupt binary files in the temp directory)
    _ico_src = base / "code-icon.ico"
    _ico_dst = data_dir / "code-icon.ico"
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
    os.environ["CODE_PORT"] = "3010"
    os.environ["CODE_DATA_DIR"] = str(data_dir)

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

    port = int(os.environ.get("CODE_PORT", "3010"))
    server_obj = ThreadingHTTPServer(("127.0.0.1", port), server.CodeHandler)

    # pystray's Windows backend requires its message loop on the main thread.
    # Keep the HTTP server in a worker so the packaged app gets a reliable tray.
    server_thread = threading.Thread(
        target=server_obj.serve_forever,
        daemon=False,
        name="code-http",
    )
    server_thread.start()
    print(f"Code running at http://127.0.0.1:{port}")
    # Existing pages detect the new server instance and refresh themselves.
    # Open a browser only when no page was connected before the restart.
    if not had_browser:
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
