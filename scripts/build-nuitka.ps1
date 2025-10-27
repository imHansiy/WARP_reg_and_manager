param(
  [ValidateSet('onedir','onefile')]
  [string]$Mode = 'onedir',
  [string]$Name = 'WarpAccountManager',
  [switch]$UseVenv = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Fail($m){ Write-Host "[ERROR] $m" -ForegroundColor Red; exit 1 }

$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

# Python
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { Fail 'Python not found. Install Python 3.11+ and add to PATH.' }

if ($UseVenv) {
  $venvPy = Join-Path $Root '.venv/Scripts/python.exe'
  if (-not (Test-Path $venvPy)) { & $py -m venv .venv }
  $py = $venvPy
}

Info 'Install Nuitka + deps'
& $py -m pip install --upgrade pip nuitka ordered-set zstandard==0.23.0 pillow | Out-Null

# Make ICO from PNG
$png = 'src/static/img/logo.png'
$ico = 'src/static/img/logo.ico'
if (Test-Path $png) { & $py scripts/make_ico.py $png $ico | Out-Null }

# Clean
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist-nuitka

# Nuitka args
$nu = @(
  '--standalone',
  '--enable-plugin=pyqt5',
  '--include-qt-plugins=platforms,styles,iconengines,imageformats',
  '--windows-console-mode=disable',
  '--follow-stdlib',
  '--jobs=2',
  '--output-dir=dist-nuitka',
  "--output-filename=$Name"
)
if ($Mode -eq 'onefile') { $nu += '--onefile' }
if (Test-Path $ico) { $nu += "--windows-icon-from-ico=$ico" }

# Include resources
$nu += @(
  '--include-data-files=src/ui/dark_theme.qss=src/ui/dark_theme.qss',
  '--include-data-files=src/static/img/logo.png=src/static/img/logo.png',
  '--include-data-files=src/proxy/warp_proxy_script.py=src/proxy/warp_proxy_script.py'
)

Info 'Build with Nuitka (this may take a while)'
$argsAll = @('main.py') + $nu
Write-Host ("ARGS=> " + ($argsAll -join " || ")) -ForegroundColor Yellow
& $py -m nuitka $argsAll

# Summarize
$exe = Get-ChildItem -Path dist-nuitka -Recurse -Filter "$Name*.exe" | Select-Object -First 1
if (-not $exe) { Fail 'Nuitka build failed (exe not found).' }
Info ("EXE: " + $exe.FullName)
