"""
Test the restart PowerShell logic independently.
Creates fake old/new exes and verifies the replace-then-launch flow.
Run: python test_restart.py
"""
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def test_restart_logic():
    tmp = Path(tempfile.mkdtemp(prefix="agentlite_test_"))
    old_exe = tmp / "AgentLite-old.exe"
    new_exe = tmp / "AgentLite-v99.99.99.exe"

    # Create dummy files with identifiable content
    old_exe.write_bytes(b"OLD_VERSION_CONTENT")
    new_exe.write_bytes(b"NEW_VERSION_CONTENT")
    print(f"[setup] old: {old_exe}")
    print(f"[setup] new: {new_exe}")

    # Build the exact same PowerShell script _handle_restart would generate
    ps_script = (
        f'Start-Sleep -Seconds 1;'
        f'$ok = $false;'
        f'for ($i = 0; $i -lt 10; $i++) {{'
        f'  try {{ Remove-Item -Path "{old_exe}" -Force -ErrorAction Stop; $ok = $true; break }}'
        f'  catch {{ Start-Sleep -Seconds 1 }}'
        f'}};'
        f'if ($ok) {{'
        f'  Copy-Item -Path "{new_exe}" -Destination "{old_exe}" -Force;'
        f'  Remove-Item "{new_exe}" -Force -ErrorAction SilentlyContinue;'
        f'  Write-Output "SUCCESS"'
        f'}} else {{'
        f'  Write-Output "FAIL: could not delete old exe"'
        f'}}'
    )
    encoded = base64.b64encode(ps_script.encode("utf-16-le")).decode("ascii")

    print(f"[run] launching PowerShell...")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, timeout=30, cwd=str(tmp),
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    print(f"[run] stdout: {result.stdout.strip()}")
    if result.stderr:
        print(f"[run] stderr: {result.stderr.strip()}")

    # Verify
    errors = []
    if old_exe.exists():
        content = old_exe.read_bytes()
        if content == b"NEW_VERSION_CONTENT":
            print(f"[verify] PASS: old replaced with new content")
        else:
            errors.append(f"old exe has unexpected content: {content!r}")
    else:
        errors.append("old exe missing after script")

    if new_exe.exists():
        errors.append("new exe still present (should be deleted)")

    if errors:
        print("[verify] FAIL:")
        for e in errors:
            print(f"  - {e}")
        return False

    # Cleanup
    if old_exe.exists():
        old_exe.unlink()
    tmp.rmdir()
    print("[verify] ALL PASSED")
    return True


if __name__ == "__main__":
    ok = test_restart_logic()
    sys.exit(0 if ok else 1)
