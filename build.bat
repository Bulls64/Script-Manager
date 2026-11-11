@echo off
setlocal
pushd "%~dp0"
set "VENV=%~dp0.venv-build"

REM Prefer the py launcher: "python" is often the Microsoft Store alias,
REM which opens the Store instead of running Python.
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Python 3 was not found. Install Python 3 from python.org and try again.
  goto failed
)

REM Isolated build environment, so PyInstaller is not installed globally and
REM the pinned version in requirements-build.txt makes builds reproducible.
if not exist "%VENV%\Scripts\python.exe" (
  echo Creating the build environment in .venv-build...
  %PY% -m venv "%VENV%"
  if errorlevel 1 goto failed
)
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements-build.txt
if errorlevel 1 goto failed

"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath "%~dp0dist" --workpath "%TEMP%\Script-Manager-build" Script-Manager.spec
if errorlevel 1 goto failed
if not exist "dist\Script-Manager\Script-Manager.exe" goto failed

echo.
echo Build complete: dist\Script-Manager\Script-Manager.exe
echo The EXE reads scripts.json from this folder and the scripts from scripts\.
echo Keep the dist folder here, or copy the whole dist\Script-Manager
echo folder next to scripts.json and the scripts folder.
pause
popd
exit /b 0

:failed
echo.
echo Build failed. Review the error above.
pause
popd
exit /b 1
