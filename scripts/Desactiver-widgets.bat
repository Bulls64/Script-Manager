@echo off
setlocal
REM Turns off Windows widgets (taskbar button, board, Windows+W) for the whole computer.
REM Logic in Reglages-Windows.bat; Restaurer-widgets.bat puts the original settings back.
REM Request administrator rights when needed (path passed through an
REM environment variable so that an apostrophe in the path cannot break it).
fltmc >nul 2>&1
if errorlevel 1 (
  set "SELF=%~f0"
  powershell.exe -NoProfile -Command "Start-Process -FilePath $env:SELF -Verb RunAs"
  exit /b
)
call "%~dp0Reglages-Windows.bat" widgets
set "RC=%errorlevel%"
pause
exit /b %RC%
