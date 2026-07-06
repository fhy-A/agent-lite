"""
Build agent-lite into a standalone .exe with PyInstaller.
Run: python build_exe.py
"""
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

# Ensure data subdirs exist
for d in ["data", "data/sessions", "data/memory", "data/skills", "data/attachments", "data/file-backups"]:
    (APP_DIR / d).mkdir(exist_ok=True)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--name", "AgentLite",
    "--icon", str(APP_DIR / "agent-lite-icon.ico"),
    "--add-data", f"{APP_DIR / 'VERSION'}{';'}.",
    "--add-data", f"{APP_DIR / 'app.js'}{';'}.",
    "--add-data", f"{APP_DIR / 'index.html'}{';'}.",
    "--add-data", f"{APP_DIR / 'styles.css'}{';'}.",
    "--add-data", f"{APP_DIR / 'data'}{';'}data",
    "--hidden-import", "tkinter",
    "--hidden-import", "json",
    "--hidden-import", "mimetypes",
    "--clean",
    "--noconsole",
    str(APP_DIR / "launcher.py"),
]

print("Building AgentLite.exe...")
subprocess.run(cmd, cwd=str(APP_DIR))
print("\nDone! Output: dist/AgentLite.exe")
