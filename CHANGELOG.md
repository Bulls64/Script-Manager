# Changelog

All notable changes to Script Manager. Versions before 2.17.0 were not published.

## 2.17.0 — 2026-11-11

First public release.

- MIT license (previously all rights reserved, personal use).
- README rewritten in English and French, with screenshots.
- GitHub repository files: line endings fixed by `.gitattributes` (`.bat` files stay CRLF), CI (Ruff, mypy, pytest), release workflow that builds the EXE from a `v*` tag, bug report template, pinned development tools.

## 2.16.0

- Super God Mode is downloaded again when the local copy is more than 7 days old, through a temporary file; the existing copy is used if GitHub does not answer.
- WinUtil is downloaded from its official GitHub release instead of `irm christitus.com/win | iex`; its Authenticode signature is checked, and you are asked to confirm if it is not validly signed.
- Warning at startup when the scripts folder is in Downloads, on a removable drive or on a network drive.

## 2.15.0

- Python code cleanup: dead code and duplicates removed.
- Fixed: helper scripts offered as favorites; "Running…" not translated; script paths containing `&` or `^`; administrator scripts tracked forever when Windows can no longer watch the process; DWM calls without prototypes; error when no editor is associated with `.bat`; settings written without a temporary file; favorites duplicated or restored because of letter case; columns beyond the sixth on very wide screens.

## 2.14.0

- The nine `.ps1` scripts became self-contained `.bat` files: the PowerShell code is at the end of the file, after a `#PS1#` line.

## 2.13.0

- New script: delete the temporary files of every account and of Windows, after showing the sizes and asking. Links are removed without being followed; files in use stay.

## 2.12.0

- New scripts: shorten Windows display delays (submenus, hover, taskbar previews) to 200 ms at most, and restore them.

## 2.11.0 – 2.11.1

- English interface, with a French / English / system language setting.
- English translation of the Python comments, after the French ones.

## 2.10.0

- Transparency slider (0 to 70 %): translucent background, pane and cards, with Acrylic blur on Windows 11.

## 2.8.0 – 2.9.1

- App renamed Script Manager (data folders keep the `Scripts-Windows` name).
- New script: "Close all windows" desktop shortcut.
- Matrix Rain script removed.

## 2.4 – 2.7.0

- System restore points: on demand, automatically before administrator or Registry scripts, and a script that deletes all but the most recent one.
- Favorites section for your own `.bat` and `.cmd` scripts.
- All scripts moved to the `scripts` folder.

## 2.2 – 2.2.1

- PySide6 interface in the WinUI 3 style (light, dark and system themes, accent color, Mica, log) replacing Tkinter; real launch tracking with exit codes.
- Faster log rendering, startup and theme switching.

## 2.0

- Audit fixes: shortcut arrow backup on a clean Windows, shutdown shortcuts with a delay and a cancel shortcut, UAC cancellation detected, `scripts.json` manifest, launch log, isolated PyInstaller build.
