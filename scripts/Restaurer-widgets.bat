@echo off
setlocal
REM Puts back the widget settings saved by Desactiver-widgets.bat.
REM Logic in Reglages-Windows.bat.
REM Request administrator rights when needed (path passed through an
REM environment variable so that an apostrophe in the path cannot break it).
fltmc >nul 2>&1
if errorlevel 1 (
  set "SELF=%~f0"
  powershell.exe -NoProfile -Command "Start-Process -FilePath $env:SELF -Verb RunAs"
  exit /b
)
call "%~dp0Reglages-Windows.bat" widgets restaurer
set "RC=%errorlevel%"
pause
exit /b %RC%
