@echo off
setlocal
REM Downloads WinUtil (Chris Titus Tech) from its official GitHub release, checks its
REM Authenticode signature, then runs it as administrator.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
REM Administrator rights are required: started directly, the script asks for them.
fltmc >nul 2>&1
if errorlevel 1 (
  set "SELF=%~f0"
  powershell.exe -NoProfile -Command "Start-Process -FilePath $env:SELF -Verb RunAs"
  exit /b
)

set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
if not "%RC%"=="0" pause
exit /b %RC%
#PS1#
# Lance WinUtil (Chris Titus Tech, MIT). Le script est pris directement dans la dernière release GitHub
# du projet, et non par « irm christitus.com/win | iex » : il est enregistré dans un fichier temporaire,
# sa signature Authenticode est vérifiée, puis il est exécuté. Sans signature valide, une confirmation
# est demandée. Codes de sortie : 0 terminé, 1 erreur, 2 lancement refusé.
$ErrorActionPreference = "Stop"
$url = "https://github.com/ChrisTitusTech/winutil/releases/latest/download/winutil.ps1"
$file = Join-Path $env:TEMP "winutil.ps1"
$code = 0
try {
    Write-Host "Téléchargement de WinUtil depuis sa release GitHub officielle…"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $file

    $signature = Get-AuthenticodeSignature -LiteralPath $file
    $run = $true
    if ($signature.Status -eq "Valid") {
        Write-Host "Signature valide : $($signature.SignerCertificate.Subject)" -ForegroundColor Green
    } else {
        Write-Host "WinUtil n’a pas de signature valide ($($signature.Status))." -ForegroundColor Yellow
        Write-Host "Le fichier vient bien de GitHub, mais son auteur ne peut pas être vérifié."
        $run = (Read-Host "Le lancer quand même ? (O/N)") -match "^[oOyY]"
    }
    if ($run) {
        & $file
    } else {
        Write-Host "WinUtil n’a pas été lancé."
        $code = 2
    }
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    $code = 1
}
# Nettoyage avant de quitter : le fichier temporaire ne reste pas dans %TEMP%.
Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
exit $code
