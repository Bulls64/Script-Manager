@echo off
setlocal
REM Creates the God Mode folder on the Desktop.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
pause
exit /b %RC%
#PS1#
# Crée le dossier God Mode sur le Bureau réel de l'utilisateur.
# GetFolderPath('DesktopDirectory') suit aussi une redirection vers OneDrive.
$ErrorActionPreference = 'Stop'
try {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $folder = Join-Path $desktop 'GodMode.{ED7BA470-8E54-465E-825C-99712043E01C}'
    if (Test-Path -LiteralPath $folder) {
        Write-Host "Le dossier God Mode existe déjà sur le Bureau : $folder" -ForegroundColor Yellow
    } else {
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host "Dossier God Mode créé sur le Bureau : $folder" -ForegroundColor Green
    }
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
