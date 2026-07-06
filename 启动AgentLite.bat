@echo off
cd /d "%~dp0"

REM Check if port 3010 already in use
netstat -ano 2>nul | find ":3010 " | find "LISTENING" >nul
if %errorlevel%==0 (
  start "" http://127.0.0.1:3010
  goto :eof
)

REM Find Python (prefer pythonw for no console)
set PY=
where pythonw >nul 2>nul && set PY=pythonw
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python not found. Please install Python first.
  pause
  goto :eof
)

REM Start server and wait, then open browser
start "Agent Lite" /B %PY% server.py

set RETRY=0
:wait
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try {$r=Invoke-WebRequest -Uri 'http://127.0.0.1:3010' -TimeoutSec 1 -UseBasicParsing; exit 0} catch {exit 1}" >nul 2>&1 && goto :open
set /a RETRY+=1
if %RETRY% LSS 30 goto :wait

:open
start "" http://127.0.0.1:3010
