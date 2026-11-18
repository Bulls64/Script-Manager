@echo off
setlocal
REM Turns off app notifications, lock screen notifications and Windows tips (current user).
REM Logic in Reglages-Windows.bat; Restaurer-notifications.bat puts the original settings back.
call "%~dp0Reglages-Windows.bat" notifications
set "RC=%errorlevel%"
pause
exit /b %RC%
