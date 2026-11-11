@echo off
setlocal
REM Downloads ThioJoe's Super God Mode script from GitHub, then runs it.
REM The copy kept in this folder is refreshed when it is more than 7 days old.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
pause
exit /b %RC%
#PS1#
# Lance Super God Mode (ThioJoe, GPL-3.0). Le script officiel est gardé dans le dossier des scripts
# et téléchargé de nouveau quand sa copie a plus de 7 jours. Le téléchargement passe par un fichier
# temporaire : une coupure réseau ne remplace jamais une copie valide par un fichier tronqué.
$ErrorActionPreference = "Stop"
$url = "https://github.com/ThioJoe/Windows-Super-God-Mode/releases/latest/download/Super_God_Mode.ps1"
$script = Join-Path (Split-Path -Parent $env:SELF) "Super_God_Mode.ps1"
$maxAgeDays = 7

$cached = Test-Path -LiteralPath $script
$stale = -not $cached -or ((Get-Date) - (Get-Item -LiteralPath $script).LastWriteTime).TotalDays -gt $maxAgeDays
if ($stale) {
    $temporary = "$script.tmp"
    try {
        Write-Host "Téléchargement de la dernière version de Super God Mode depuis GitHub…"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $temporary
        if ((Get-Item -LiteralPath $temporary).Length -eq 0) { throw "fichier vide" }
        Move-Item -LiteralPath $temporary -Destination $script -Force
    } catch {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        if (-not $cached) {
            Write-Host "Téléchargement impossible : $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "Vérifie la connexion à Internet, puis réessaie."
            exit 1
        }
        Write-Host "Mise à jour impossible ($($_.Exception.Message)) : la copie déjà présente est utilisée." -ForegroundColor Yellow
    }
}

try {
    & $script
    exit 0
} catch {
    Write-Host "Super God Mode s’est arrêté sur une erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
