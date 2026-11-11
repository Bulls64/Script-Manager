@echo off
setlocal
set "SCRIPTDIR=%~dp0"

REM Undoes Supprimer-fleche-raccourci.bat: puts the shortcut arrows back.

fltmc >nul 2>&1
if errorlevel 1 (
  set "SELF=%~f0"
  powershell.exe -NoProfile -Command "Start-Process -FilePath $env:SELF -Verb RunAs"
  exit /b
)

set "REGKEY=HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"

call :locate_data
set "BACKUP=%BACKUPDIR%ShellIcons-before-NoArrow.reg"
set "STATE=%BACKUPDIR%ShellIcons-before-NoArrow.state"

set "ORIGINAL=UNKNOWN"
if exist "%STATE%" set /p ORIGINAL=<"%STATE%"
echo Original state: %ORIGINAL%

REM 1. Remove the value set by the arrow-removal script.
reg delete "%REGKEY%" /v 29 /f >nul 2>&1

REM 2. Put back the original value, if there was one.
if exist "%BACKUP%" (
  reg import "%BACKUP%" >nul 2>&1
  if errorlevel 1 goto failed
)

REM 3. An old backup taken after the change may contain the blank icon itself: drop it.
reg query "%REGKEY%" /v 29 2>nul | findstr /i /c:"shell32.dll,-50" /c:"NoArrow.ico" >nul
if not errorlevel 1 reg delete "%REGKEY%" /v 29 /f >nul 2>&1

REM 4. If the key did not exist originally, remove it when it is now empty.
if /i "%ORIGINAL%"=="KEY_ABSENT" (
  powershell.exe -NoProfile -Command "$p='HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons'; if (Test-Path -LiteralPath $p) { $k=Get-Item -LiteralPath $p; if ($k.ValueCount -eq 0 -and $k.SubKeyCount -eq 0) { Remove-Item -LiteralPath $p } }"
)

echo The registry was restored.
echo Windows Explorer must restart for the change to show: its open windows will close.
choice /c YN /n /m "Restart Windows Explorer now? (Y = now, N = at the next sign-in) "
if errorlevel 2 (
  echo OK. The arrows will come back after the next sign-in.
) else (
  call :restart_explorer
)
echo Done. The state, backup and icon files were kept: %BACKUPDIR%
pause
exit /b 0

:failed
echo Could not import the registry backup: %BACKUP%
pause
exit /b 1

:locate_data
REM Look for an existing state/backup (machine-wide folder, then the old
REM C:\NoArrow, then beside this script, then the project folder above it, where the
REM scripts lived before the scripts subfolder); otherwise use the machine-wide folder.
set "BACKUPDIR="
call :pick "%ProgramData%\Scripts-Windows\"
call :pick "C:\NoArrow\"
call :pick "%SCRIPTDIR%"
call :pick "%SCRIPTDIR%..\"
if not defined BACKUPDIR set "BACKUPDIR=%ProgramData%\Scripts-Windows\"
exit /b 0

:pick
if defined BACKUPDIR exit /b 0
if exist "%~1ShellIcons-before-NoArrow.state" set "BACKUPDIR=%~1"
if not defined BACKUPDIR if exist "%~1ShellIcons-before-NoArrow.reg" set "BACKUPDIR=%~1"
exit /b 0

:restart_explorer
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 2 /nobreak >nul
start "" explorer.exe
exit /b 0
