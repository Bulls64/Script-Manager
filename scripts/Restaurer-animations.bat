@echo off
setlocal
REM Puts back the display delays saved by Reduire-animations.bat.
REM Logic in Animations-Windows.bat.
call "%~dp0Animations-Windows.bat" restaurer
set "RC=%errorlevel%"
pause
exit /b %RC%
