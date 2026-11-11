@echo off
setlocal
REM Creates the "Fermer toutes les fenetres" desktop shortcut.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
pause
exit /b %RC%
#PS1#
# Crée sur le Bureau le raccourci « Fermer toutes les fenêtres ».
# Le raccourci est autonome : la commande est dans le raccourci lui-même, il ne dépend pas de ce dossier.
# Chaque fenêtre est fermée poliment (comme un clic sur la croix) : une application qui a un document
# non enregistré le demande, rien n'est tué de force. Les fenêtres de l'Explorateur sont fermées aussi ;
# le Bureau, la barre des tâches et le menu Démarrer restent en place.
$ErrorActionPreference = 'Stop'
try {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $command = @'
$keep = 'explorer','ApplicationFrameHost','TextInputHost','ShellExperienceHost','StartMenuExperienceHost','SearchHost','SystemSettings','LockApp'
try { (New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.Quit() } } catch {}
Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.Id -ne $PID -and $keep -notcontains $_.ProcessName } | ForEach-Object { $null = $_.CloseMainWindow() }
'@
    $command = ($command -split "`r?`n" | Where-Object { $_ }) -join '; '

    $powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut((Join-Path $desktop 'Fermer toutes les fenêtres.lnk'))
    $link.TargetPath = $powershell
    $link.Arguments = '-NoProfile -WindowStyle Hidden -Command "' + $command + '"'
    $link.WindowStyle = 7
    $link.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',27'
    $link.Description = 'Ferme toutes les fenêtres ouvertes'
    $link.Save()
    Write-Host 'Raccourci « Fermer toutes les fenêtres » créé sur le Bureau.' -ForegroundColor Green
    Write-Host 'Chaque fenêtre est fermée comme avec la croix : une application qui a un travail non enregistré le demande.'
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
