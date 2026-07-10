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

version = (APP_DIR / "VERSION").read_text().strip()
name = f"AgentLite-v{version}"

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--name", name,
    "--icon", str(APP_DIR / "agent-lite-icon.ico"),
    "--version-file", str(APP_DIR / "file_version_info.txt"),
    "--add-data", f"{APP_DIR / 'VERSION'}{';'}.",
    "--add-data", f"{APP_DIR / 'app.js'}{';'}.",
    "--add-data", f"{APP_DIR / 'index.html'}{';'}.",
    "--add-data", f"{APP_DIR / 'styles.css'}{';'}.",
    "--add-data", f"{APP_DIR / 'agent-lite-icon.ico'}{';'}.",
    "--add-data", f"{APP_DIR / 'data' / 'skills'}{';'}data/skills",
    "--add-data", f"{APP_DIR / 'data' / 'memory'}{';'}data/memory",
    "--hidden-import", "tkinter",
    "--hidden-import", "json",
    "--hidden-import", "mimetypes",
    "--hidden-import", "pystray",
    "--hidden-import", "PIL.Image",
    "--exclude-module", "PIL.ImageQt",
    "--exclude-module", "PIL.ImageDraw2",
    "--exclude-module", "PIL.ImageFont",
    "--exclude-module", "PIL.ImageFilter",
    "--exclude-module", "PIL.ImageEnhance",
    "--exclude-module", "PIL.ImageMath",
    "--exclude-module", "PIL.ImageMorph",
    "--exclude-module", "PIL.ImageOps",
    "--exclude-module", "PIL.ImagePath",
    "--exclude-module", "PIL.ImageStat",
    "--exclude-module", "PIL.ImageTransform",
    "--exclude-module", "PIL.ImageWin",
    "--exclude-module", "PIL.ImImagePlugin",
    "--exclude-module", "PIL.BlpImagePlugin",
    "--exclude-module", "PIL.BmpImagePlugin",
    "--exclude-module", "PIL.BufrStubImagePlugin",
    "--exclude-module", "PIL.CurImagePlugin",
    "--exclude-module", "PIL.DcxImagePlugin",
    "--exclude-module", "PIL.DdsImagePlugin",
    "--exclude-module", "PIL.EpsImagePlugin",
    "--exclude-module", "PIL.FitsImagePlugin",
    "--exclude-module", "PIL.FliImagePlugin",
    "--exclude-module", "PIL.FpxImagePlugin",
    "--exclude-module", "PIL.FtexImagePlugin",
    "--exclude-module", "PIL.GbrImagePlugin",
    "--exclude-module", "PIL.GdImageFile",
    "--exclude-module", "PIL.GifImagePlugin",
    "--exclude-module", "PIL.GribStubImagePlugin",
    "--exclude-module", "PIL.Hdf5StubImagePlugin",
    "--exclude-module", "PIL.IcnsImagePlugin",
    "--exclude-module", "PIL.IcoImagePlugin",
    "--exclude-module", "PIL.ImImagePlugin",
    "--exclude-module", "PIL.ImtImagePlugin",
    "--exclude-module", "PIL.IptcImagePlugin",
    "--exclude-module", "PIL.Jpeg2KImagePlugin",
    "--exclude-module", "PIL.JpegImagePlugin",
    "--exclude-module", "PIL.McIdasImagePlugin",
    "--exclude-module", "PIL.MicImagePlugin",
    "--exclude-module", "PIL.MpegImagePlugin",
    "--exclude-module", "PIL.MpoImagePlugin",
    "--exclude-module", "PIL.MspImagePlugin",
    "--exclude-module", "PIL.PalmImagePlugin",
    "--exclude-module", "PIL.PcdImagePlugin",
    "--exclude-module", "PIL.PcxImagePlugin",
    "--exclude-module", "PIL.PdfImagePlugin",
    "--exclude-module", "PIL.PixarImagePlugin",
    "--exclude-module", "PIL.PngImagePlugin",
    "--exclude-module", "PIL.PpmImagePlugin",
    "--exclude-module", "PIL.PsdImagePlugin",
    "--exclude-module", "PIL.SgiImagePlugin",
    "--exclude-module", "PIL.SpiderImagePlugin",
    "--exclude-module", "PIL.SunImagePlugin",
    "--exclude-module", "PIL.TgaImagePlugin",
    "--exclude-module", "PIL.TiffImagePlugin",
    "--exclude-module", "PIL.WebPImagePlugin",
    "--exclude-module", "PIL.WmfImagePlugin",
    "--exclude-module", "PIL.XbmImagePlugin",
    "--exclude-module", "PIL.XpmImagePlugin",
    "--exclude-module", "PIL.XVThumbImagePlugin",
    "--clean",
    "--noconsole",
    str(APP_DIR / "launcher.py"),
]

print("Building AgentLite.exe...")
subprocess.run(cmd, cwd=str(APP_DIR))
print("\nDone! Output: dist/AgentLite.exe")
