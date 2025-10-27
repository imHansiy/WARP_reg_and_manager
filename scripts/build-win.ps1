param(
  [switch]$Clean = $true,
  [ValidateSet('onefile','onedir')]
  [string]$Mode = 'onefile',
  [switch]$NoConsole = $true,
  [string]$Name = "WarpAccountManager",
  [switch]$UseVenv = $true,
  [switch]$InstallUPX = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# Resolve project root
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
Info "Project root: $Root"

# Pick python (PowerShell 5.1 compatible)
$pythonCmd = $null
$cmdObj = Get-Command python -ErrorAction SilentlyContinue
if ($cmdObj) { $pythonCmd = $cmdObj.Source }
if (-not $pythonCmd) { Fail "Python not found. Please install Python 3.11+ and add to PATH" }

# Optional venv
if ($UseVenv) {
  $venvPy = Join-Path $Root ".venv/Scripts/python.exe"
  if (-not (Test-Path $venvPy)) {
Info "Create virtualenv .venv"
    & $pythonCmd -m venv .venv
  }
  $pythonCmd = $venvPy
}

# Upgrade pip and install deps
Info "Upgrade pip/setuptools/wheel"
& $pythonCmd -m pip install --upgrade pip setuptools wheel | Out-Null

Info "Install project dependencies"
& $pythonCmd -m pip install -r requirements.txt | Out-Null

Info "Install PyInstaller and hooks"
& $pythonCmd -m pip install pyinstaller pyinstaller-hooks-contrib | Out-Null

Info "Install Pillow for icon conversion"
& $pythonCmd -m pip install pillow | Out-Null

# Optional UPX (skipped locally to avoid permission/encoding issues)
if ($InstallUPX) {
Warn "Skip UPX installation locally (optional). If needed, install manually and re-run with -InstallUPX"
}

# Clean build artifacts
if ($Clean) {
Info "Clean build/ dist/ *.spec"
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist | Out-Null
  Get-ChildItem -Path . -Filter "*.spec" | Remove-Item -Force -ErrorAction SilentlyContinue
}

# Convert JPG -> ICO for exe icon
$icoIn = Join-Path $Root "src/static/img/logo.png"
$icoOut = Join-Path $Root "src/static/img/logo.ico"
try {
  & $pythonCmd "scripts/make_ico.py" $icoIn $icoOut | Out-Null
} catch {
  Warn "ICO conversion failed, proceeding without exe icon"
}

# Build PyInstaller args
$pyiArgs = @()
$pyiArgs += "--noconfirm"
if ($Clean) { $pyiArgs += "--clean" }
if ($Mode -eq 'onefile') { $pyiArgs += "--onefile" }
if ($NoConsole) { $pyiArgs += "--noconsole" }
$pyiArgs += @(
  "--name", $Name,
  "--paths", "src",
  "--exclude-module", "playwright",
  "--exclude-module", "playwright_stealth",
  "--exclude-module", "curl_cffi",
  "--exclude-module", "tests",
  "--hidden-import", "psutil",
  "--hidden-import", "PyQt5.sip",
  "--hidden-import", "src.core.warp_account_manager",
  "--hidden-import", "src.utils.utils",
  "--hidden-import", "src.config.languages",
  "--collect-submodules", "src",
  "--exclude-module", "PyQt5.QtWebEngineWidgets",
  "--exclude-module", "PyQt5.QtWebEngineCore",
  "--exclude-module", "PyQt5.QtWebEngine",
  "--exclude-module", "PyQt5.Qt3DCore",
  "--exclude-module", "PyQt5.Qt3DRender",
  "--exclude-module", "PyQt5.Qt3DInput",
  "--exclude-module", "PyQt5.Qt3DLogic",
  "--exclude-module", "PyQt5.Qt3DAnimation",
  "--exclude-module", "PyQt5.QtMultimedia",
  "--exclude-module", "PyQt5.QtMultimediaWidgets",
  "--exclude-module", "PyQt5.QtQml",
  "--exclude-module", "PyQt5.QtQuick",
  "--add-data", "src/ui/dark_theme.qss;src/ui",
  "--add-data", "src/static/img/logo.png;src/static/img",
  "--add-data", "src/proxy/warp_proxy_script.py;src/proxy"
)
if (Test-Path $icoOut) { $pyiArgs += @("--icon", "src/static/img/logo.ico") }

# Bootloader splash (appears before Python starts)
$pyiArgs += @("--splash", "src/static/img/logo.png")

# Detect minimal Qt plugin dlls and include only what we need
$pluginJson = & $pythonCmd "scripts/find_qt_plugins.py"
try { $pluginObj = $pluginJson | ConvertFrom-Json } catch { $pluginObj = $null }
if ($pluginObj -and $pluginObj.platforms) {
  foreach ($p in $pluginObj.platforms) { $pyiArgs += "--add-binary"; $pyiArgs += ("$p;qt_plugins/platforms") }
}
if ($pluginObj -and $pluginObj.imageformats) {
  foreach ($p in $pluginObj.imageformats) { $pyiArgs += "--add-binary"; $pyiArgs += ("$p;qt_plugins/imageformats") }
}

# Entry
$entry = "main.py"

Info "Start building: $Name"
& $pythonCmd -m PyInstaller @pyiArgs $entry

if ($Mode -eq 'onedir') {
  $exe = Join-Path $Root ("dist/" + $Name + "/" + $Name + ".exe")
} else {
  $exe = Join-Path $Root ("dist/" + $Name + ".exe")
}
if (-not (Test-Path $exe)) { Fail "Build failed: not found $exe" }

# UPX compress (if available) to reduce size
if (Get-Command upx -ErrorAction SilentlyContinue) {
  $targetDir = Join-Path $Root ("dist/" + $Name)
  if (Test-Path $targetDir) {
    Get-ChildItem -Path $targetDir -Recurse -Include *.pyd,*.dll |
      Where-Object { $_.Name -notmatch 'python\d+\.dll|vcruntime|ucrtbase|api-ms-|msvcp|concrt' } |
      ForEach-Object { try { upx --best --lzma --quiet $_.FullName } catch {} }
  }
}

# Zip artifact
$zip = Join-Path $Root "$Name-win64-min.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }

# Ensure not running and unlock files
try { Stop-Process -Name $Name -Force -ErrorAction SilentlyContinue } catch {}
$logPath = Join-Path $Root ("dist/" + $Name + "/app_error.log")
Remove-Item -Force -ErrorAction SilentlyContinue $logPath

if ($Mode -eq 'onedir') {
  Compress-Archive -Path (Join-Path $Root ("dist/" + $Name + "/*")) -DestinationPath $zip -Force
} else {
  Compress-Archive -Path $exe -DestinationPath $zip -Force
}

# Print summary
$exeSize = (Get-Item $exe).Length / 1MB
$zipSize = (Get-Item $zip).Length / 1MB
Info ("Build success: $exe  (~{0:N1} MB)") -f $exeSize
Info ("Zipped: $zip  (~{0:N1} MB)") -f $zipSize

Write-Host 'Run locally:' -ForegroundColor Green
Write-Host ("  " + $exe) -ForegroundColor Green
