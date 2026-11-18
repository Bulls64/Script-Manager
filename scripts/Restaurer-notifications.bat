@echo off
setlocal
REM Puts back the notification settings saved by Desactiver-notifications.bat.
REM Logic in Reglages-Windows.bat.
call "%~dp0Reglages-Windows.bat" notifications restaurer
set "RC=%errorlevel%"
pause
exit /b %RC%
