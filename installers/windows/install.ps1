# ralph-whisper Windows installer.  UNTESTED template — adapt as needed.
# Creates a venv, installs deps, and adds a Startup shortcut that runs the daemon
# hidden at login. Run from the repo root:  powershell -ExecutionPolicy Bypass -File installers\windows\install.ps1

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path "$PSScriptRoot\..\..").Path
$Venv = Join-Path $Repo ".venv"

Write-Host "→ Creating venv"
python -m venv $Venv
& "$Venv\Scripts\python.exe" -m pip install --upgrade pip -q
& "$Venv\Scripts\pip.exe" install -q -e "$Repo[desktop]"   # add ',gpu' on NVIDIA

# Startup shortcut (runs pythonw so no console window)
$Startup = [Environment]::GetFolderPath("Startup")
$Lnk = Join-Path $Startup "ralph-whisper.lnk"
$Pyw = Join-Path $Venv "Scripts\pythonw.exe"
$WShell = New-Object -ComObject WScript.Shell
$sc = $WShell.CreateShortcut($Lnk)
$sc.TargetPath = $Pyw
$sc.Arguments = "-m ralph_whisper"
$sc.WorkingDirectory = $Repo
$sc.Save()

Write-Host "→ Installed. Default hotkey: Ctrl+Alt+D (set WD_HOTKEY_PYNPUT to change)."
Write-Host "  Start now:  & '$Pyw' -m ralph_whisper"
Write-Host "  Toggle:     & '$Venv\Scripts\python.exe' -m ralph_whisper toggle"
