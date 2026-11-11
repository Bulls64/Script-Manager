@echo off
setlocal
REM Deletes every System Restore point except the most recent one
REM (lists the points and asks first).
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
# Supprime tous les points de restauration système, sauf le plus récent.
# Même effet que Nettoyage de disque > Nettoyer les fichiers système > Autres options >
# Restauration du système et clichés instantanés, mais les points sont listés avant
# et une confirmation est demandée. Administrateur requis.
#
# La suppression passe par SRRemoveRestorePoint (srclient.dll), qui retire un point
# précis par son numéro : les autres clichés instantanés du disque ne sont pas touchés.
$ErrorActionPreference = "Stop"
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "ce script doit être lancé en administrateur."
    }

    function Format-RestorePoint($point) {
        $when = [Management.ManagementDateTimeConverter]::ToDateTime($point.CreationTime)
        "{0}  n° {1}  {2}" -f $when.ToString("dd/MM/yyyy HH:mm"), $point.SequenceNumber, $point.Description
    }

    $points = @(Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Sort-Object SequenceNumber)
    if ($points.Count -eq 0) {
        Write-Host "Aucun point de restauration sur ce PC : rien à supprimer." -ForegroundColor Yellow
        exit 0
    }
    $latest = $points[-1]
    if ($points.Count -eq 1) {
        Write-Host "Un seul point de restauration, le plus récent : il est conservé." -ForegroundColor Green
        Write-Host "  $(Format-RestorePoint $latest)"
        exit 0
    }
    $old = @($points[0..($points.Count - 2)])

    Write-Host "Point conservé (le plus récent) :" -ForegroundColor Green
    Write-Host "  $(Format-RestorePoint $latest)"
    Write-Host ""
    Write-Host "Points à supprimer ($($old.Count)) :" -ForegroundColor Yellow
    foreach ($point in $old) {
        Write-Host "  $(Format-RestorePoint $point)"
    }
    Write-Host ""
    $answer = Read-Host "Les supprimer définitivement ? Il ne sera plus possible d’y revenir (O/N)"
    if ($answer -notmatch "^[oOyY]") {
        Write-Host "Rien n’a été supprimé."
        exit 0
    }

    if (-not ("ScriptsWindows.SystemRestore" -as [type])) {
        Add-Type -Namespace ScriptsWindows -Name SystemRestore -MemberDefinition @"
[DllImport("srclient.dll")]
public static extern int SRRemoveRestorePoint(int index);
"@
    }

    $failed = 0
    foreach ($point in $old) {
        $code = [ScriptsWindows.SystemRestore]::SRRemoveRestorePoint([int]$point.SequenceNumber)
        if ($code -eq 0) {
            Write-Host "Supprimé : $(Format-RestorePoint $point)"
        } else {
            Write-Host "Échec (erreur $code) : $(Format-RestorePoint $point)" -ForegroundColor Red
            $failed++
        }
    }
    Write-Host ""
    if ($failed -gt 0) {
        Write-Host "$failed point(s) n’ont pas pu être supprimés." -ForegroundColor Red
        exit 1
    }
    Write-Host "Terminé : $($old.Count) point(s) supprimé(s), le plus récent est conservé." -ForegroundColor Green
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
