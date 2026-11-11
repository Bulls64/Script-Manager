@echo off
setlocal
set "SCRIPTDIR=%~dp0"

REM Removes the arrow overlay from shortcut icons (machine-wide, HKLM).
REM Uses NoArrow\NoArrow.ico, copied to %ProgramData%\Scripts-Windows; falls back
REM to the blank icon built into shell32.dll when the file is missing.

REM Request administrator rights when needed (path passed through an
REM environment variable so that an apostrophe in the path cannot break it).
fltmc >nul 2>&1
if errorlevel 1 (
  set "SELF=%~f0"
  powershell.exe -NoProfile -Command "Start-Process -FilePath $env:SELF -Verb RunAs"
  exit /b
)

set "REGKEY=HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"
set "DATADIR=%ProgramData%\Scripts-Windows\"
set "ICONSRC=%SCRIPTDIR%NoArrow\NoArrow.ico"
set "ICONDST=%DATADIR%NoArrow.ico"
set "ICONREF=%windir%\System32\shell32.dll,-50"

call :locate_data
set "BACKUP=%BACKUPDIR%ShellIcons-before-NoArrow.reg"
set "STATE=%BACKUPDIR%ShellIcons-before-NoArrow.state"

call :prepare_dir || goto failed

REM Prefer the bundled transparent icon: its path never changes between Windows builds.
if exist "%ICONSRC%" copy /y "%ICONSRC%" "%ICONDST%" >nul 2>&1 && set "ICONREF=%ICONDST%,0"

REM Record the original state once, before the first change.
if not exist "%STATE%" call :record_state || goto failed

reg add "%REGKEY%" /v 29 /t REG_SZ /d "%ICONREF%" /f >nul
if errorlevel 1 goto failed

echo The registry setting was applied (icon: %ICONREF%).
echo Windows Explorer must restart for the change to show: its open windows will close.
choice /c YN /n /m "Restart Windows Explorer now? (Y = now, N = at the next sign-in) "
if errorlevel 2 (
  echo OK. The arrows will disappear after the next sign-in.
) else (
  call :restart_explorer
)
echo Done.
echo Original state recorded in: %STATE%
if exist "%BACKUP%" echo Registry backup: %BACKUP%
echo To undo, run Restaurer-fleche-raccourci.bat.
pause
exit /b 0

:record_state
REM KEY_ABSENT      : the "Shell Icons" key did not exist (clean Windows install).
REM VALUE_ABSENT    : the key existed but had no value 29.
REM VALUE_PRESENT   : value 29 existed with another icon (saved in the .reg backup).
REM ALREADY_APPLIED : an earlier run already set value 29 to the blank icon;
REM                   the true original state is unknown.
reg query "%REGKEY%" >nul 2>&1
if errorlevel 1 (
  (echo KEY_ABSENT)>"%STATE%" || exit /b 1
  exit /b 0
)
reg query "%REGKEY%" /v 29 2>nul | findstr /i /c:"shell32.dll,-50" /c:"NoArrow.ico" >nul
if not errorlevel 1 (
  (echo ALREADY_APPLIED)>"%STATE%" || exit /b 1
  exit /b 0
)
reg query "%REGKEY%" /v 29 >nul 2>&1
if errorlevel 1 (
  (echo VALUE_ABSENT)>"%STATE%" || exit /b 1
) else (
  (echo VALUE_PRESENT)>"%STATE%" || exit /b 1
)
if not exist "%BACKUP%" (
  reg export "%REGKEY%" "%BACKUP%" /y >nul || exit /b 1
)
exit /b 0

:failed
echo An error occurred. Check that you accepted the administrator prompt
echo and that %%ProgramData%%\Scripts-Windows is writable by administrators.
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

:prepare_dir
REM Machine-wide data folder: writable by SYSTEM and Administrators only
REM (S-1-5-18 = SYSTEM, S-1-5-32-544 = Administrators, S-1-5-32-545 = Users).
if exist "%DATADIR%" exit /b 0
mkdir "%DATADIR%" || exit /b 1
icacls "%DATADIR%" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F *S-1-5-32-545:(OI)(CI)RX >nul 2>&1
exit /b 0

:restart_explorer
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 2 /nobreak >nul
start "" explorer.exe
exit /b 0
