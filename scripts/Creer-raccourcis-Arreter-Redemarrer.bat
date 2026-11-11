@echo off
setlocal
REM Creates the shutdown, restart and cancel shortcuts.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
pause
exit /b %RC%
#PS1#
# Crée les raccourcis Arrêter, Redémarrer et Annuler l'arrêt sur le Bureau.
# Arrêter et Redémarrer attendent 10 secondes : Annuler l'arrêt (shutdown -a)
# les interrompt pendant ce délai.
$ErrorActionPreference = 'Stop'
try {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $shutdown = Join-Path $env:SystemRoot 'System32\shutdown.exe'
    $shell = New-Object -ComObject WScript.Shell
    $items = @(
        @{ Name = 'Arrêter';         Arguments = '-s -t 10'; Description = 'Arrêter Windows dans 10 secondes' },
        @{ Name = 'Redémarrer';      Arguments = '-r -t 10'; Description = 'Redémarrer Windows dans 10 secondes' },
        @{ Name = "Annuler l’arrêt"; Arguments = '-a';       Description = 'Annuler un arrêt ou un redémarrage programmé' }
    )
    foreach ($item in $items) {
        $link = $shell.CreateShortcut((Join-Path $desktop ($item.Name + '.lnk')))
        $link.TargetPath = $shutdown
        $link.Arguments = $item.Arguments
        $link.Description = $item.Description
        $link.Save()
    }
    Write-Host "Raccourcis Arrêter, Redémarrer et Annuler l’arrêt créés sur le Bureau." -ForegroundColor Green
    Write-Host 'Arrêter et Redémarrer laissent 10 secondes avant de fermer la session ;'
    Write-Host "pendant ce délai, Annuler l’arrêt annule l’opération."
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
