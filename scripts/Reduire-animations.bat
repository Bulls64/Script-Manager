@echo off
setlocal
REM Caps the Windows display delays (menus, hover, taskbar previews) at 200 ms.
REM Logic in Animations-Windows.bat; Restaurer-animations.bat puts the original values back.
call "%~dp0Animations-Windows.bat"
set "RC=%errorlevel%"
pause
exit /b %RC%
