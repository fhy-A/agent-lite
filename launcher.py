"""
Agent Lite launcher — entry point for PyInstaller bundle.
"""
import os
import sys
import webbrowser
from pathlib import Path


def get_base_dir():
    """Get the directory containing app files (handles PyInstaller bundle)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def ensure_dirs():
    """Create required directories if they don't exist."""
    # Use user's home directory for writable data
    data_home = Path.home() / ".agent-lite"
    for sub in ["sessions", "memory", "skills", "attachments", "file-backups"]:
        (data_home / sub).mkdir(parents=True, exist_ok=True)
    return data_home


def main():
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
