@echo off
setlocal
REM Caps the Windows display delays (menus, hover, taskbar previews) at 200 ms,
REM or puts the original values back with the argument "restaurer".
REM Called by Reduire-animations.bat and Restaurer-animations.bat.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SM_ARG1=%~1"
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
exit /b %RC%
#PS1#
# Ramène à 200 ms au plus les délais d'affichage réglables de Windows, ou les restaure (-Restaurer).
# Windows ne permet pas de régler la durée des animations elles-mêmes (seulement de les couper) :
# ce sont les délais avant l'apparition des sous-menus, des info-bulles et des aperçus qui sont réduits.
# Tout est dans HKCU : aucun droit administrateur, seul le compte courant est concerné.
# L'état d'origine est enregistré avant la première modification, dans
# %LOCALAPPDATA%\Scripts-Windows\animations-origine.json ; les valeurs déjà plus courtes restent telles quelles.
$Restaurer = $env:SM_ARG1 -eq 'restaurer'

$ErrorActionPreference = 'Stop'
$Max = 200
$advanced = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
# Spi : action SystemParametersInfo qui applique la valeur tout de suite (0 = redémarrage de l'Explorateur).
# Default : valeur utilisée par Windows quand la valeur du Registre est absente.
$settings = @(
    @{ Name = 'MenuShowDelay'; Path = 'HKCU:\Control Panel\Desktop'; Type = 'String'; Default = 400; Spi = 0x006B
       Label = 'Ouverture des sous-menus' },
    @{ Name = 'MouseHoverTime'; Path = 'HKCU:\Control Panel\Mouse'; Type = 'String'; Default = 400; Spi = 0x0067
       Label = 'Survol (info-bulles, aperçus)' },
    @{ Name = 'ExtendedUIHoverTime'; Path = $advanced; Type = 'DWord'; Default = 400; Spi = 0
       Label = 'Aperçus des fenêtres dans la barre des tâches' },
    @{ Name = 'DesktopLivePreviewHoverTime'; Path = $advanced; Type = 'DWord'; Default = 500; Spi = 0
       Label = 'Aperçu du Bureau (coin droit de la barre des tâches)' }
)
$backupDir = Join-Path $env:LOCALAPPDATA 'Scripts-Windows'
$backup = Join-Path $backupDir 'animations-origine.json'

Add-Type -Namespace ScriptsWindows -Name Spi -MemberDefinition @'
[DllImport("user32.dll", SetLastError = true)]
public static extern bool SystemParametersInfo(uint action, uint uiParam, System.IntPtr pvParam, uint flags);
'@

function Get-Current($setting) {
    $item = Get-ItemProperty -Path $setting.Path -Name $setting.Name -ErrorAction SilentlyContinue
    if ($null -eq $item) { return $null }
    return [string]$item.($setting.Name)
}

function Set-Delay($setting, [int]$value) {
    if ($setting.Spi -ne 0) {
        # SPIF_UPDATEINIFILE | SPIF_SENDCHANGE : écrit le Registre et prévient les applications ouvertes.
        if ([ScriptsWindows.Spi]::SystemParametersInfo([uint32]$setting.Spi, [uint32]$value, [IntPtr]::Zero, 3)) {
            return
        }
    }
    if (-not (Test-Path -LiteralPath $setting.Path)) { New-Item -Path $setting.Path -Force | Out-Null }
    $data = if ($setting.Type -eq 'String') { [string]$value } else { $value }
    Set-ItemProperty -Path $setting.Path -Name $setting.Name -Value $data -Type $setting.Type
}

function Request-ExplorerRestart {
    Write-Host ''
    Write-Host "Les aperçus de la barre des tâches changent au redémarrage de l'Explorateur : ses fenêtres ouvertes se fermeront."
    $answer = Read-Host "Redémarrer l'Explorateur maintenant ? (O = maintenant, N = à la prochaine connexion)"
    if ($answer -match '^[oOyY]') {
        Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) { Start-Process explorer.exe }
        Write-Host "Explorateur redémarré." -ForegroundColor Green
    }
}

try {
    if ($Restaurer) {
        if (-not (Test-Path -LiteralPath $backup)) {
            Write-Host "Aucune sauvegarde trouvée : les délais n'ont pas été modifiés par Reduire-animations, rien à restaurer." -ForegroundColor Yellow
            exit 0
        }
        $saved = Get-Content -LiteralPath $backup -Raw -Encoding UTF8 | ConvertFrom-Json
        $explorer = $false
        foreach ($setting in $settings) {
            $original = $saved.($setting.Name)
            if ($null -eq $original) {
                # Valeur absente à l'origine : on la retire, Windows reprend son délai par défaut.
                Remove-ItemProperty -Path $setting.Path -Name $setting.Name -ErrorAction SilentlyContinue
                if ($setting.Spi -ne 0) { Set-Delay $setting $setting.Default }
                Remove-ItemProperty -Path $setting.Path -Name $setting.Name -ErrorAction SilentlyContinue
                $text = "valeur retirée (défaut de Windows, $($setting.Default) ms)"
            } else {
                Set-Delay $setting ([int]$original)
                $text = "$original ms"
            }
            if ($setting.Spi -eq 0) { $explorer = $true }
            Write-Host ("  {0} : {1}" -f $setting.Label, $text)
        }
        Remove-Item -LiteralPath $backup -Force
        Write-Host "Délais d’origine restaurés." -ForegroundColor Green
        if ($explorer) { Request-ExplorerRestart }
        exit 0
    }

    $changes = @()
    $state = [ordered]@{}
    foreach ($setting in $settings) {
        $current = Get-Current $setting
        $state[$setting.Name] = $current
        $effective = $setting.Default
        if ($null -ne $current -and $current -match '^\s*\d+\s*$') { $effective = [int]$current }
        if ($effective -le $Max) {
            Write-Host ("  {0} : {1} ms, déjà court, inchangé" -f $setting.Label, $effective)
        } else {
            $changes += [pscustomobject]@{ Setting = $setting; From = $effective }
        }
    }
    if ($changes.Count -eq 0) {
        Write-Host "Tous les délais sont déjà à $Max ms ou moins : rien à changer." -ForegroundColor Green
        exit 0
    }

    # Première modification seulement : une seconde exécution ne doit pas écraser l'état d'origine.
    if (-not (Test-Path -LiteralPath $backup)) {
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        $state | ConvertTo-Json | Set-Content -LiteralPath $backup -Encoding UTF8
    }

    $explorer = $false
    foreach ($change in $changes) {
        Set-Delay $change.Setting $Max
        if ($change.Setting.Spi -eq 0) { $explorer = $true }
        Write-Host ("  {0} : {1} ms -> {2} ms" -f $change.Setting.Label, $change.From, $Max)
    }
    Write-Host "Délais ramenés à $Max ms. « Restaurer les délais d’animation » remet les valeurs d’origine." -ForegroundColor Green
    if ($explorer) { Request-ExplorerRestart }
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
