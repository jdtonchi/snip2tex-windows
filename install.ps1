# Installs snip2tex for Windows: Python deps (via uv) and a Start menu shortcut.
#   powershell -ExecutionPolicy Bypass -File install.ps1            # Start menu
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Startup   # also start with Windows
param([switch]$Startup)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "installing uv"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Push-Location $here
uv sync
Pop-Location

$py = Join-Path $here ".venv\Scripts\python.exe"
$pyw = Join-Path $here ".venv\Scripts\pythonw.exe"
$app = Join-Path $here "app.py"
$dir = Join-Path $env:USERPROFILE ".snip2tex"
New-Item -ItemType Directory -Force $dir | Out-Null
$ico = Join-Path $dir "snip2tex.ico"
& $py $app --icon $ico

$shell = New-Object -ComObject WScript.Shell
function New-Shortcut($path) {
    $s = $shell.CreateShortcut($path)
    $s.TargetPath = $pyw
    $s.Arguments = "`"$app`""
    $s.WorkingDirectory = $here
    $s.IconLocation = $ico
    $s.Description = "Snip2TeX"
    $s.Save()
}
$programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-Shortcut (Join-Path $programs "Snip2TeX.lnk")
if ($Startup) { New-Shortcut (Join-Path $programs "Startup\Snip2TeX.lnk") }
Write-Host "done. Start Snip2TeX from the Start menu."
