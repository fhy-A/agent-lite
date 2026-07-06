"""
Agent Lite launcher — entry point for PyInstaller bundle.
"""
import os
import sys
import webbrowser
import zipfile
import tempfile
import shutil
import tkinter as tk
from pathlib import Path

GITHUB_REPO = "fhy-A/agent-lite"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/VERSION"
REPO_ZIP_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/master.zip"

# Files to update (NOT data directory)
APP_FILES = ["app.js", "index.html", "styles.css", "server.py", "launcher.py", "VERSION"]


def get_base_dir():
    """Get the directory containing app files (handles PyInstaller bundle)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_update_dir():
    """Get writable directory for updates (separate from bundled data)."""
    if getattr(sys, 'frozen', False):
        return Path.home() / ".agent-lite" / "app"
    return get_base_dir()


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
    import threading
    root = tk.Tk()
    root.withdraw()
    if not mb.askyesno("Agent Lite Update", f"New version {remote} available (current: {local}).\n\nUpdate now?"):
        return False

    # Show progress window
    pw = tk.Toplevel()
    pw.title("Agent Lite Update")
    pw.geometry("320x100")
    pw.resizable(False, False)
    lbl = tk.Label(pw, text=f"Downloading v{remote}...")
    lbl.pack(pady=20)
    pw.update()

    try:
        import urllib.request
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        urllib.request.urlretrieve(REPO_ZIP_URL, tmp.name)

        target = get_update_dir()
        target.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(tmp.name) as zf:
            # GitHub zip contains a top-level folder: agent-lite-master/
            prefix = zf.namelist()[0].split("/")[0] + "/"
            for name in zf.namelist():
                rel = name[len(prefix):]
                if rel in APP_FILES:
                    print(f"  Updating: {rel}")
                    zf.extract(name, target)
                    # Move from subfolder to target
                    extracted = target / name
                    if extracted.exists():
                        shutil.move(str(extracted), str(target / rel))
            # Clean up extracted subfolder
            subfolder = target / prefix.rstrip("/")
            if subfolder.exists():
                shutil.rmtree(str(subfolder), ignore_errors=True)

        os.unlink(tmp.name)
        pw.destroy()
        root.destroy()
        # Write new version
        (target / "VERSION").write_text(remote, encoding="utf-8")
        mb.showinfo("Update Complete", f"Updated to v{remote}. Agent Lite will now restart.")
        root.destroy()
    except Exception as e:
        print(f"Update failed: {e}")

    return True


def main():
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
