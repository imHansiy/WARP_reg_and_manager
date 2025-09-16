#!/usr/bin/env pwsh

# Windows PowerShell script to start Warp terminal with proxy configuration
# This ensures Warp uses the mitmproxy for account switching

param(
    [switch]$DisableProxyOnExit = $false
)

# Proxy configuration
$PROXY_HOST = "127.0.0.1"
$PROXY_PORT = "8080"
$PROXY_URL = "http://${PROXY_HOST}:${PROXY_PORT}"

# Common Warp terminal paths on Windows
$WARP_PATHS = @(
    "${env:LOCALAPPDATA}\Programs\Warp\Warp.exe",
    "${env:PROGRAMFILES}\Warp\Warp.exe",
    "${env:PROGRAMFILES(X86)}\Warp\Warp.exe",
    "${env:USERPROFILE}\AppData\Local\Programs\Warp\Warp.exe",
    "${env:USERPROFILE}\scoop\apps\warp\current\Warp.exe",
    "${env:PROGRAMFILES}\WindowsApps\*Warp*\Warp.exe"
)

Write-Host "🚀 Starting Warp Terminal with Proxy Configuration (Windows)" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host "Proxy: ${PROXY_URL}" -ForegroundColor Yellow
Write-Host ""
Write-Host "ℹ️  Note: Make sure to start Warp Account Manager and enable proxy" -ForegroundColor Cyan
Write-Host "   for account switching to work properly." -ForegroundColor Cyan
Write-Host ""

# Find Warp executable
$WARP_PATH = ""
foreach ($path in $WARP_PATHS) {
    # Handle wildcard paths (like WindowsApps)
    if ($path -match '\*') {
        $foundPaths = Get-ChildItem -Path ($path -replace '\*.*', '*') -Recurse -Name "Warp.exe" -ErrorAction SilentlyContinue | ForEach-Object {
            Join-Path (Split-Path $path -Parent) $_
        }
        foreach ($foundPath in $foundPaths) {
            if (Test-Path $foundPath) {
                $WARP_PATH = $foundPath
                break
            }
        }
    } else {
        if (Test-Path $path) {
            $WARP_PATH = $path
            break
        }
    }
    
    if ($WARP_PATH -ne "") { break }
}

if ($WARP_PATH -eq "") {
    Write-Host "❌ ERROR: Warp terminal not found in any of these locations:" -ForegroundColor Red
    foreach ($path in $WARP_PATHS) {
        Write-Host "   - $path" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "   Please install Warp or update the WARP_PATHS array in this script" -ForegroundColor Red
    Write-Host "   Installation methods:" -ForegroundColor Red
    Write-Host "   - Download from: https://www.warp.dev/" -ForegroundColor Red
    Write-Host "   - Or find warp executable: Get-Command warp" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Warp terminal found: $WARP_PATH" -ForegroundColor Green
Write-Host ""
Write-Host "🔄 Starting Warp with proxy environment variables..." -ForegroundColor Yellow
Write-Host "   Warp will use proxy: ${PROXY_URL}" -ForegroundColor Yellow
Write-Host "   Start Warp Account Manager proxy for account switching" -ForegroundColor Yellow
Write-Host ""

# Set proxy environment variables for the current process
$env:http_proxy = $PROXY_URL
$env:https_proxy = $PROXY_URL
$env:HTTP_PROXY = $PROXY_URL
$env:HTTPS_PROXY = $PROXY_URL

# Additional proxy and SSL settings for Windows
$env:REQUESTS_CA_BUNDLE = ""
$env:CURL_CA_BUNDLE = ""
$env:SSL_CERT_FILE = ""
$env:SSL_CERT_DIR = ""
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
$env:PYTHONHTTPSVERIFY = "0"
$env:NODE_EXTRA_CA_CERTS = ""

# Windows specific proxy settings
$env:no_proxy = "localhost,127.0.0.1,::1,.local"
$env:NO_PROXY = "localhost,127.0.0.1,::1,.local"

# Start Warp with proxy configuration
Write-Host "Executing: $WARP_PATH $args" -ForegroundColor Cyan

# Enable system proxy in registry (HKCU) before launching Warp
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
# Save previous values to restore later if needed
$prevProxyEnable = $null
$prevProxyServer = $null
$prevProxyOverride = $null
try {
    $prev = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
    if ($prev) {
        $prevProxyEnable = $prev.ProxyEnable
        $prevProxyServer = $prev.ProxyServer
        $prevProxyOverride = $prev.ProxyOverride
    }
} catch {}

try {
    New-ItemProperty -Path $regPath -Name ProxyServer -Value "127.0.0.1:8080" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name ProxyOverride -Value "localhost;127.0.0.1;<local>" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name ProxyEnable -Value 1 -PropertyType DWord -Force | Out-Null
    # Apply changes to WinINet
    Start-Process -FilePath "rundll32.exe" -ArgumentList "wininet.dll,InternetSetOption", "0", "37", "0", "0" -WindowStyle Hidden -NoNewWindow
    Write-Host "✅ System proxy enabled (HKCU) -> 127.0.0.1:8080" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning: Failed to enable system proxy in registry: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Start Warp process with proxy environment variables
$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = $WARP_PATH
$processInfo.Arguments = $args -join " "
$processInfo.UseShellExecute = $false

# Set all environment variables for the new process
$processInfo.EnvironmentVariables["http_proxy"] = $PROXY_URL
$processInfo.EnvironmentVariables["https_proxy"] = $PROXY_URL
$processInfo.EnvironmentVariables["HTTP_PROXY"] = $PROXY_URL
$processInfo.EnvironmentVariables["HTTPS_PROXY"] = $PROXY_URL
$processInfo.EnvironmentVariables["no_proxy"] = "localhost,127.0.0.1,::1,.local"
$processInfo.EnvironmentVariables["NO_PROXY"] = "localhost,127.0.0.1,::1,.local"
$processInfo.EnvironmentVariables["REQUESTS_CA_BUNDLE"] = ""
$processInfo.EnvironmentVariables["CURL_CA_BUNDLE"] = ""
$processInfo.EnvironmentVariables["SSL_CERT_FILE"] = ""
$processInfo.EnvironmentVariables["SSL_CERT_DIR"] = ""
$processInfo.EnvironmentVariables["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
$processInfo.EnvironmentVariables["PYTHONHTTPSVERIFY"] = "0"
$processInfo.EnvironmentVariables["NODE_EXTRA_CA_CERTS"] = ""

try {
    $process = [System.Diagnostics.Process]::Start($processInfo)
    Write-Host "✅ Warp started successfully with PID: $($process.Id)" -ForegroundColor Green

    # Wait for Warp to exit, then disable proxy
    $process.WaitForExit()

    if ($DisableProxyOnExit) {
        try {
            if ($null -ne $prevProxyEnable) {
                New-ItemProperty -Path $regPath -Name ProxyEnable -Value $prevProxyEnable -PropertyType DWord -Force | Out-Null
            } else {
                New-ItemProperty -Path $regPath -Name ProxyEnable -Value 0 -PropertyType DWord -Force | Out-Null
            }
            # Apply changes
            Start-Process -FilePath "rundll32.exe" -ArgumentList "wininet.dll,InternetSetOption", "0", "37", "0", "0" -WindowStyle Hidden -NoNewWindow
            Write-Host "🔌 System proxy state restored (after Warp exit)" -ForegroundColor Yellow
        } catch {
            Write-Host "⚠️ Warning: Failed to restore system proxy after Warp exit: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

} catch {
    Write-Host "❌ ERROR: Failed to start Warp: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
