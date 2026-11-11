@echo off
setlocal
REM Creates a shortcut to the Desktop folder.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
pause
exit /b %RC%
#PS1#
# Crée Bureau.lnk, qui ouvre le vrai dossier Bureau (y compris redirigé vers
# OneDrive), puis ouvre ce dossier pour épingler le raccourci à la barre des tâches.
$ErrorActionPreference = 'Stop'
try {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $linkPath = Join-Path $desktop 'Bureau.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($linkPath)
    $link.TargetPath = Join-Path $env:SystemRoot 'explorer.exe'
    $link.Arguments = '"' + $desktop + '"'
    # Icône 34 de shell32.dll : le Bureau.
    $link.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',34'
    $link.Description = "Ouvrir le dossier Bureau dans l’Explorateur"
    $link.Save()
    Write-Host "Raccourci créé : $linkPath" -ForegroundColor Green
    Write-Host "Dans la fenêtre de l’Explorateur qui s’ouvre, faites glisser Bureau.lnk sur la barre des tâches pour l’épingler." -ForegroundColor Cyan
    Write-Host 'Une fois épinglé, « Retirer les éléments ajoutés au Bureau » peut retirer Bureau.lnk du Bureau.' -ForegroundColor Cyan
    Start-Process -FilePath (Join-Path $env:SystemRoot 'explorer.exe') -ArgumentList ('"' + $desktop + '"')
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
