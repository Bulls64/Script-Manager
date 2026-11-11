@echo off
setlocal
REM Deletes the temporary files of every account on the PC and of Windows
REM (shows the sizes and asks first).
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
pause
exit /b %RC%
#PS1#
# Supprime les fichiers temporaires du PC : le dossier Temp de chaque compte et celui de Windows.
# Les tailles sont affichées et une confirmation est demandée avant de supprimer. Administrateur requis
# (dossiers des autres comptes et C:\Windows\Temp).
#
# Un fichier ouvert par une application est laissé en place : il sera supprimé à un prochain passage.
# Les liens (jonctions, liens symboliques) sont retirés eux-mêmes, jamais suivis : sous Windows
# PowerShell 5.1, Remove-Item -Recurse sur une jonction peut vider le dossier vers lequel elle pointe.
# Non touchés : la Corbeille, le cache de Windows Update, Prefetch et les caches des navigateurs.
$ErrorActionPreference = "Stop"
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "ce script doit être lancé en administrateur."
    }

    $reparse = [IO.FileAttributes]::ReparsePoint

    # Taille et nombre de fichiers d'un dossier, sans suivre les liens.
    function Measure-Folder([string]$path) {
        $size = [int64]0
        $count = 0
        foreach ($item in @(Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue)) {
            if ($item.Attributes -band $reparse) { continue }
            if ($item.PSIsContainer) {
                $inner = Measure-Folder $item.FullName
                $size += $inner.Size
                $count += $inner.Count
            } else {
                $size += $item.Length
                $count++
            }
        }
        [pscustomobject]@{ Size = $size; Count = $count }
    }

    # Vide un dossier sans le supprimer lui-même. Renvoie le nombre de fichiers laissés en place.
    function Clear-Folder([string]$path) {
        $kept = 0
        foreach ($item in @(Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue)) {
            try {
                if ($item.Attributes -band $reparse) {
                    # Le lien seul : sa cible n'est pas touchée.
                    if ($item.PSIsContainer) { [IO.Directory]::Delete($item.FullName, $false) }
                    else { [IO.File]::Delete($item.FullName) }
                } elseif ($item.PSIsContainer) {
                    $kept += Clear-Folder $item.FullName
                    # Échoue sans bruit s'il reste un fichier en cours d'utilisation dedans.
                    try { [IO.Directory]::Delete($item.FullName, $false) } catch { }
                } else {
                    if ($item.IsReadOnly) { $item.IsReadOnly = $false }
                    [IO.File]::Delete($item.FullName)
                }
            } catch {
                $kept++
            }
        }
        $kept
    }

    function Format-Size([int64]$bytes) {
        if ($bytes -ge 1GB) { return "{0:N1} Go" -f ($bytes / 1GB) }
        if ($bytes -ge 1MB) { return "{0:N1} Mo" -f ($bytes / 1MB) }
        if ($bytes -ge 1KB) { return "{0:N0} Ko" -f ($bytes / 1KB) }
        return "$bytes octets"
    }

    # Dossier Temp de chaque compte (profils réels, pas ceux des services), du compte courant et de Windows.
    $candidates = @()
    foreach ($userProfile in @(Get-CimInstance Win32_UserProfile -ErrorAction SilentlyContinue | Where-Object { -not $_.Special })) {
        if ($userProfile.LocalPath) { $candidates += Join-Path $userProfile.LocalPath "AppData\Local\Temp" }
    }
    $candidates += $env:TEMP
    $candidates += Join-Path $env:SystemRoot "Temp"
    $folders = @()
    foreach ($candidate in $candidates) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate -PathType Container)) { continue }
        $full = (Get-Item -LiteralPath $candidate -Force).FullName.TrimEnd("\")
        if ($folders -notcontains $full) { $folders += $full }
    }
    if ($folders.Count -eq 0) {
        Write-Host "Aucun dossier de fichiers temporaires trouvé." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "Mesure des fichiers temporaires…"
    $before = @{}
    $total = [int64]0
    $files = 0
    foreach ($folder in $folders) {
        $before[$folder] = Measure-Folder $folder
        $total += $before[$folder].Size
        $files += $before[$folder].Count
        Write-Host ("  {0,10}  {1,7} fichier(s)  {2}" -f (Format-Size $before[$folder].Size), $before[$folder].Count, $folder)
    }
    Write-Host ""
    if ($files -eq 0) {
        Write-Host "Les dossiers temporaires sont déjà vides : rien à supprimer." -ForegroundColor Green
        exit 0
    }
    Write-Host ("Total : {0} dans {1} fichier(s)." -f (Format-Size $total), $files) -ForegroundColor Yellow
    Write-Host "Ferme d'abord les installations en cours : elles peuvent avoir besoin de leurs fichiers temporaires."
    $answer = Read-Host "Supprimer ces fichiers définitivement ? Ils ne passent pas par la Corbeille (O/N)"
    if ($answer -notmatch "^[oOyY]") {
        Write-Host "Rien n’a été supprimé."
        exit 0
    }

    $kept = 0
    $freed = [int64]0
    foreach ($folder in $folders) {
        Write-Host "Nettoyage de $folder…"
        $kept += Clear-Folder $folder
        $freed += $before[$folder].Size - (Measure-Folder $folder).Size
    }
    Write-Host ""
    Write-Host ("Terminé : {0} libérés." -f (Format-Size ([math]::Max($freed, 0)))) -ForegroundColor Green
    if ($kept -gt 0) {
        Write-Host "$kept fichier(s) en cours d’utilisation laissé(s) en place : ils partiront à un prochain nettoyage, ou après un redémarrage."
    }
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
