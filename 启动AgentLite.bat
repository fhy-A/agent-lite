@echo off
cd /d "%~dp0"

REM Replace exe if update was downloaded
if exist "dist\AgentLite.exe.new" (
  echo Applying update...
  del /f "dist\AgentLite.exe.old" 2>nul
  move /y "dist\AgentLite.exe" "dist\AgentLite.exe.old" 2>nul
  move /y "dist\AgentLite.exe.new" "dist\AgentLite.exe"
  echo Update applied.
)

REM Check if port 3010 already in use
netstat -ano 2>nul | find ":3010 " | find "LISTENING" >nul
if %errorlevel%==0 (
  REM Ask the connected page to refresh in place instead of opening a new tab.
  powershell -NoProfile -Command "try {Invoke-WebRequest -Uri 'http://127.0.0.1:3010/api/request-browser-refresh' -TimeoutSec 2 -UseBasicParsing | Out-Null} catch {}" >nul 2>&1
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

REM Start server and wait until it is ready.
start "Agent Lite" /B %PY% server.py

set RETRY=0
:wait
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try {$r=Invoke-WebRequest -Uri 'http://127.0.0.1:3010' -TimeoutSec 1 -UseBasicParsing; exit 0} catch {exit 1}" >nul 2>&1 && goto :open
set /a RETRY+=1
if %RETRY% LSS 30 goto :wait

:open
REM Give an existing page time to reconnect and send its heartbeat.
set PAGE_RETRY=0
:wait_page
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try {$r=Invoke-RestMethod -Uri 'http://127.0.0.1:3010/api/has-browser' -TimeoutSec 1; if ($r.hasBrowser) {exit 0} else {exit 1}} catch {exit 1}" >nul 2>&1 && goto :page_connected
set /a PAGE_RETRY+=1
if %PAGE_RETRY% LSS 5 goto :wait_page

REM No page reconnected, so this is a fresh launch.
start "" http://127.0.0.1:3010
goto :eof

:page_connected
REM The page already refreshed itself after observing the new server instance ID.
REM Do not rotate the ID again, otherwise the browser visibly refreshes twice.
goto :eof
