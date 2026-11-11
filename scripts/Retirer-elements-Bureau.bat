@echo off
setlocal
REM Removes the Desktop items created by these scripts, after confirmation.
REM Self-contained: the PowerShell code is at the end of this file (after the marker line).
set "SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:SELF,[Text.Encoding]::UTF8); & ([scriptblock]::Create($t.Substring($t.LastIndexOf('#'+'PS1'+'#'))))"
set "RC=%errorlevel%"
pause
exit /b %RC%
#PS1#
# Retire du Bureau les éléments créés par les scripts de ce dossier :
# raccourcis Arrêter, Redémarrer, Annuler l'arrêt, Bureau.lnk, Fermer toutes les fenêtres et dossier God Mode.
# Un élément n'est retiré que s'il correspond encore à ce que le script a créé ;
# les raccourcis partent à la Corbeille.
$ErrorActionPreference = 'Stop'
try {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $shell = New-Object -ComObject WScript.Shell
    $shutdown = 'shutdown.exe'
    $explorer = 'explorer.exe'
    $expected = @(
        @{ File = 'Arrêter.lnk';         Target = $shutdown; Pattern = '^-s(\s|$)' },
        @{ File = 'Redémarrer.lnk';      Target = $shutdown; Pattern = '^-r(\s|$)' },
        @{ File = "Annuler l’arrêt.lnk"; Target = $shutdown; Pattern = '^-a$' },
        @{ File = 'Fermer toutes les fenêtres.lnk'; Target = 'powershell.exe'; Pattern = 'CloseMainWindow' },
        @{ File = 'Bureau.lnk';          Target = $explorer; Pattern = '^"?' + [regex]::Escape($desktop) + '"?$' }
    )

    $toRemove = @()
    foreach ($item in $expected) {
        $path = Join-Path $desktop $item.File
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $link = $shell.CreateShortcut($path)
        $targetName = Split-Path -Leaf $link.TargetPath
        if ($targetName -ieq $item.Target -and $link.Arguments.Trim() -match $item.Pattern) {
            $toRemove += [pscustomobject]@{ Kind = 'Raccourci'; Path = $path }
        } else {
            Write-Host "Laissé en place (modifié depuis sa création) : $path" -ForegroundColor Yellow
        }
    }

    $godMode = Join-Path $desktop 'GodMode.{ED7BA470-8E54-465E-825C-99712043E01C}'
    if (Test-Path -LiteralPath $godMode) {
        # PowerShell voit le vrai dossier sur le disque, vide, et non le contenu virtuel de God Mode.
        if (@(Get-ChildItem -LiteralPath $godMode -Force).Count -eq 0) {
            $toRemove += [pscustomobject]@{ Kind = 'Dossier'; Path = $godMode }
        } else {
            Write-Host "Laissé en place (contient des fichiers) : $godMode" -ForegroundColor Yellow
        }
    }

    if ($toRemove.Count -eq 0) {
        Write-Host "Aucun élément créé par ces scripts n’a été trouvé sur le Bureau." -ForegroundColor Green
        exit 0
    }

    Write-Host 'Éléments trouvés :'
    foreach ($entry in $toRemove) { Write-Host "  - $($entry.Path)" }
    $answer = Read-Host 'Les retirer ? Les raccourcis iront à la Corbeille (O/N)'
    if ($answer -notmatch '^[oOyY]') {
        Write-Host "Rien n’a été retiré."
        exit 0
    }

    Add-Type -AssemblyName Microsoft.VisualBasic
    foreach ($entry in $toRemove) {
        if ($entry.Kind -eq 'Raccourci') {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($entry.Path, 'OnlyErrorDialogs', 'SendToRecycleBin')
        } else {
            # Le dossier God Mode est vide sur le disque : suppression non récursive,
            # qui échoue d'elle-même si un fichier s'y trouvait malgré tout.
            [System.IO.Directory]::Delete($entry.Path, $false)
        }
        Write-Host "Retiré : $($entry.Path)" -ForegroundColor Green
    }
    exit 0
} catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
