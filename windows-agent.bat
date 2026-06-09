@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%windows-agent.ps1" %*
if errorlevel 1 (
  echo.
  echo VisionDesk Agent exited with an error.
  pause
)
