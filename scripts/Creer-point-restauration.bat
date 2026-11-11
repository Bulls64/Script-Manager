@echo off
setlocal
REM Creates a System Restore point. Started by the application, as administrator.
REM Exit codes: 0 created, 1 error, 2 recent point already exists, 3 protection disabled.
REM Usage: Creer-point-restauration.bat [description]
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SM_ARG1=%~1"
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
exit /b %RC%
#PS1#
# Crée un point de restauration système. Lancé par l'application, en administrateur.
# Checkpoint-Computer n'existe que dans Windows PowerShell 5.1 (powershell.exe), pas dans pwsh 7.
#
# Codes de sortie, lus par l'application :
#   0  point créé
#   2  un point de moins de 24 h existe déjà : Windows n'en crée pas d'autre
#   3  protection du système désactivée (ou interdite par une stratégie)
#   1  autre erreur
$Description = if ($env:SM_ARG1) { $env:SM_ARG1 } else { "Script Manager" }

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Point de restauration"

function Get-LatestRestorePoint {
    Get-ComputerRestorePoint -ErrorAction SilentlyContinue |
        Sort-Object SequenceNumber |
        Select-Object -Last 1
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Ce script doit être lancé en administrateur." -ForegroundColor Red
    exit 1
}

# Protection du système coupée : RPSessionInterval vaut 0, ou DisableSR vaut 1 par stratégie.
$config = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore" -ErrorAction SilentlyContinue
$policy = Get-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\SystemRestore" -ErrorAction SilentlyContinue
if (($config -and $config.RPSessionInterval -eq 0) -or ($policy -and $policy.DisableSR -eq 1)) {
    Write-Host "La protection du système est désactivée : aucun point de restauration possible." -ForegroundColor Red
    Write-Host "Pour l’activer : Panneau de configuration > Système > Protection du système > Configurer."
    exit 3
}

$before = Get-LatestRestorePoint
Write-Host "Création du point de restauration « $Description »…"
Write-Host "Cela peut prendre une minute."
try {
    Checkpoint-Computer -Description $Description -RestorePointType MODIFY_SETTINGS -WarningAction SilentlyContinue
} catch {
    Write-Host "Échec : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$after = Get-LatestRestorePoint
if ($after -and (-not $before -or $after.SequenceNumber -ne $before.SequenceNumber)) {
    Write-Host "Point de restauration créé." -ForegroundColor Green
    exit 0
}
if ($after) {
    $when = [Management.ManagementDateTimeConverter]::ToDateTime($after.CreationTime)
    Write-Host "Windows ne crée qu’un point de restauration toutes les 24 heures." -ForegroundColor Yellow
    Write-Host "Le plus récent date du $($when.ToString('dd/MM/yyyy à HH:mm')) : « $($after.Description) »."
    exit 2
}
Write-Host "Aucun point de restauration n’a été créé." -ForegroundColor Red
exit 1
