@echo off
cd /d "%~dp0"
if exist "dist\AgentLite.exe" (
    start "" "dist\AgentLite.exe"
) else if exist "server.py" (
    pythonw server.py
) else (
    echo AgentLite.exe 和 server.py 均未找到，请检查文件是否完整。
    pause
)
