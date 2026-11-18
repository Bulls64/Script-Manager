@echo off
setlocal
REM Turns off Windows notifications or widgets, or puts the original settings back.
REM Usage: Reglages-Windows.bat notifications|widgets [restaurer]
REM Called by Desactiver-notifications.bat, Restaurer-notifications.bat,
REM Desactiver-widgets.bat and Restaurer-widgets.bat.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SM_ARG1=%~1"
set "SM_ARG2=%~2"
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
exit /b %RC%
#PS1#
# Désactive les notifications ou les widgets de Windows, ou remet les réglages d'origine (« restaurer »).
# Groupes :
#   notifications : compte courant (HKCU), sans droits administrateur.
#   widgets       : stratégies de l'ordinateur (HKLM), droits administrateur requis.
# L'état d'origine est enregistré avant la première modification : dans %LOCALAPPDATA%\Scripts-Windows
# pour les notifications, dans %ProgramData%\Scripts-Windows (accès réservé aux administrateurs) pour
# les widgets. Une seconde exécution ne l'écrase pas.
$Group = $env:SM_ARG1
$Restaurer = $env:SM_ARG2 -eq 'restaurer'

$ErrorActionPreference = 'Stop'
$advanced = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
# Value : valeur appliquée. Optional : une écriture refusée n'est pas une erreur (réglage protégé
# par Windows, que la stratégie couvre déjà).
$groups = @{
    notifications = @{
        Machine = $false
        Explorer = $false
        Done = "Notifications désactivées. Les applications déjà ouvertes peuvent encore en afficher jusqu’à la prochaine connexion."
        Undo = "« Restaurer les notifications » remet les réglages d’origine."
        Settings = @(
            @{ Path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications'; Name = 'ToastEnabled'
               Value = 0; Label = 'Notifications des applications et des autres expéditeurs' },
            @{ Path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings'
               Name = 'NOC_GLOBAL_SETTING_ALLOW_TOASTS_ABOVE_LOCK'; Value = 0
               Label = "Notifications sur l’écran de verrouillage" },
            @{ Path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'
               Name = 'SubscribedContent-338389Enabled'; Value = 0; Label = 'Conseils et suggestions de Windows' }
        )
    }
    widgets = @{
        Machine = $true
        Explorer = $true
        Done = "Widgets désactivés : le bouton de la barre des tâches, le panneau et Windows+W."
        Undo = "« Restaurer les widgets » remet les réglages d’origine."
        Settings = @(
            @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Dsh'; Name = 'AllowNewsAndInterests'; Value = 0
               Label = 'Widgets (Windows 11)' },
            @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds'; Name = 'EnableFeeds'; Value = 0
               Label = "Actualités et centres d’intérêt (Windows 10)" },
            @{ Path = $advanced; Name = 'TaskbarDa'; Value = 0; Optional = $true
               Label = 'Bouton Widgets de la barre des tâches' }
        )
    }
}

function Get-Current($setting) {
    $item = Get-ItemProperty -LiteralPath $setting.Path -Name $setting.Name -ErrorAction SilentlyContinue
    if ($null -eq $item) { return $null }
    return $item.($setting.Name)
}

function Set-Value($setting, $value) {
    if (-not (Test-Path -LiteralPath $setting.Path)) { New-Item -Path $setting.Path -Force | Out-Null }
    Set-ItemProperty -LiteralPath $setting.Path -Name $setting.Name -Value ([int]$value) -Type DWord
}

function Invoke-Optional($setting, [scriptblock]$action) {
    try {
        & $action
        return $true
    } catch {
        if (-not $setting.Optional) { throw }
        Write-Host ("  {0} : protégé par Windows, laissé tel quel" -f $setting.Label) -ForegroundColor Yellow
        return $false
    }
}

function Request-ExplorerRestart {
    Write-Host ''
    Write-Host "La barre des tâches change au redémarrage de l'Explorateur : ses fenêtres ouvertes se fermeront."
    $answer = Read-Host "Redémarrer l'Explorateur maintenant ? (O = maintenant, N = à la prochaine connexion)"
    if ($answer -match '^[oOyY]') {
        Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) { Start-Process explorer.exe }
        Write-Host "Explorateur redémarré." -ForegroundColor Green
    }
}

function New-DataFolder([string]$folder, [bool]$machine) {
    if (Test-Path -LiteralPath $folder) { return }
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    if ($machine) {
        # SYSTEM et Administrateurs en contrôle total, Utilisateurs en lecture.
        # SYSTEM and Administrators full control, Users read only.
        & icacls $folder /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null
    }
}

try {
    $config = $groups[$Group]
    if ($null -eq $config) { throw "Groupe inconnu « $Group » (notifications ou widgets attendu)." }
    if ($config.Machine) {
        $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            throw "Ce réglage demande les droits administrateur."
        }
        $backupDir = Join-Path $env:ProgramData 'Scripts-Windows'
    } else {
        $backupDir = Join-Path $env:LOCALAPPDATA 'Scripts-Windows'
    }
    $backup = Join-Path $backupDir "$Group-origine.json"

    if ($Restaurer) {
        if (-not (Test-Path -LiteralPath $backup)) {
            Write-Host "Aucune sauvegarde trouvée : ces réglages n'ont pas été modifiés par ce script, rien à restaurer." -ForegroundColor Yellow
            exit 0
        }
        $saved = Get-Content -LiteralPath $backup -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($setting in $config.Settings) {
            $entry = $saved.($setting.Name)
            $done = Invoke-Optional $setting {
                if ($null -eq $entry -or $null -eq $entry.Value) {
                    Remove-ItemProperty -LiteralPath $setting.Path -Name $setting.Name -ErrorAction SilentlyContinue
                    # Clé créée par ce script et restée vide : retirée elle aussi.
                    # Key created by this script and left empty: removed too.
                    if ($null -ne $entry -and -not $entry.KeyExisted -and (Test-Path -LiteralPath $setting.Path)) {
                        $key = Get-Item -LiteralPath $setting.Path
                        if ($key.ValueCount -eq 0 -and $key.SubKeyCount -eq 0) {
                            Remove-Item -LiteralPath $setting.Path -Force
                        }
                    }
                } else {
                    Set-Value $setting $entry.Value
                }
            }
            if ($done) {
                $text = if ($null -eq $entry -or $null -eq $entry.Value) { 'valeur retirée (réglage par défaut de Windows)' } else { "$($entry.Value)" }
                Write-Host ("  {0} : {1}" -f $setting.Label, $text)
            }
        }
        Remove-Item -LiteralPath $backup -Force
        Write-Host "Réglages d’origine restaurés." -ForegroundColor Green
        if ($config.Explorer) { Request-ExplorerRestart }
        exit 0
    }

    # Première modification seulement : une seconde exécution ne doit pas écraser l'état d'origine.
    # First change only: a second run must not overwrite the original state.
    if (-not (Test-Path -LiteralPath $backup)) {
        $state = [ordered]@{}
        foreach ($setting in $config.Settings) {
            $state[$setting.Name] = [ordered]@{
                KeyExisted = [bool](Test-Path -LiteralPath $setting.Path)
                Value = Get-Current $setting
            }
        }
        New-DataFolder $backupDir $config.Machine
        $state | ConvertTo-Json | Set-Content -LiteralPath $backup -Encoding UTF8
    }

    foreach ($setting in $config.Settings) {
        $current = Get-Current $setting
        if ($null -ne $current -and [string]$current -eq [string]$setting.Value) {
            Write-Host ("  {0} : déjà désactivé" -f $setting.Label)
            continue
        }
        if (Invoke-Optional $setting { Set-Value $setting $setting.Value }) {
            Write-Host ("  {0} : désactivé" -f $setting.Label)
        }
    }
    Write-Host $config.Done -ForegroundColor Green
    Write-Host $config.Undo
    if ($config.Explorer) { Request-ExplorerRestart }
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
