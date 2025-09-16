@echo off
setlocal enabledelayedexpansion

REM Windows batch script to start Warp terminal with proxy configuration
REM Now also enables system proxy (HKCU) before starting Warp and restores it after exit

REM Proxy configuration
set PROXY_HOST=127.0.0.1
set PROXY_PORT=8080
set PROXY_URL=http://%PROXY_HOST%:%PROXY_PORT%

echo 🚀 Starting Warp Terminal with Proxy Configuration (Windows)
echo =============================================================
echo Proxy: %PROXY_URL%
echo.
echo ℹ️  Note: Make sure to start Warp Account Manager and enable proxy
echo    for account switching to work properly.
echo.

REM Common Warp terminal paths on Windows
set WARP_PATH=
set "PATHS[0]=%LOCALAPPDATA%\Programs\Warp\Warp.exe"
set "PATHS[1]=%PROGRAMFILES%\Warp\Warp.exe"
set "PATHS[2]=%PROGRAMFILES(X86)%\Warp\Warp.exe"
set "PATHS[3]=%USERPROFILE%\AppData\Local\Programs\Warp\Warp.exe"
set "PATHS[4]=%USERPROFILE%\scoop\apps\warp\current\Warp.exe"

REM Find Warp executable
for /L %%i in (0,1,4) do (
    if exist "!PATHS[%%i]!" (
        set "WARP_PATH=!PATHS[%%i]!"
        goto :found
    )
)

REM Check WindowsApps directory
for /d %%d in ("%PROGRAMFILES%\WindowsApps\*Warp*") do (
    if exist "%%d\Warp.exe" (
        set "WARP_PATH=%%d\Warp.exe"
        goto :found
    )
)

echo ❌ ERROR: Warp terminal not found in any of these locations:
echo    - %LOCALAPPDATA%\Programs\Warp\Warp.exe
echo    - %PROGRAMFILES%\Warp\Warp.exe
echo    - %PROGRAMFILES(X86)%\Warp\Warp.exe
echo    - %USERPROFILE%\AppData\Local\Programs\Warp\Warp.exe
echo    - %USERPROFILE%\scoop\apps\warp\current\Warp.exe
echo    - %PROGRAMFILES%\WindowsApps\*Warp*\Warp.exe
echo.
echo    Please install Warp or update the paths in this script
echo    Installation methods:
echo    - Download from: https://www.warp.dev/
echo    - Or find warp executable: where warp
pause
exit /b 1

:found
echo ✅ Warp terminal found: %WARP_PATH%
echo.
echo 🔄 Enabling system proxy (HKCU) for Warp session...

REM Save current ProxyEnable value
for /f "tokens=3" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2^>nul ^| find "REG_DWORD"') do set PREV_PROXY_ENABLE=%%a

REM Enable proxy and set server/override
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /t REG_SZ /d "%PROXY_HOST%:%PROXY_PORT%" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyOverride /t REG_SZ /d "localhost;127.0.0.1;<local>" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f >nul 2>&1

REM Apply changes (WinINet)
rundll32.exe wininet.dll,InternetSetOption 0 37 0 0

echo ✅ System proxy enabled: %PROXY_HOST%:%PROXY_PORT%
echo.
echo 🔄 Starting Warp with proxy environment variables...
echo    Warp will use proxy: %PROXY_URL%

REM Set proxy environment variables for this process (optional)
set http_proxy=%PROXY_URL%
set https_proxy=%PROXY_URL%
set HTTP_PROXY=%PROXY_URL%
set HTTPS_PROXY=%PROXY_URL%

REM Start Warp and wait until it exits
echo Executing: "%WARP_PATH%" %*
"%WARP_PATH%" %*
set EXITCODE=%ERRORLEVEL%

echo.
echo 🔌 Restoring system proxy state...
if defined PREV_PROXY_ENABLE (
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d %PREV_PROXY_ENABLE% /f >nul 2>&1
) else (
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul 2>&1
)
rundll32.exe wininet.dll,InternetSetOption 0 37 0 0
echo ✅ System proxy state restored

if %EXITCODE% equ 0 (
    echo ✅ Warp exited successfully
) else (
    echo ⚠️ Warp exited with code %EXITCODE%
)

exit /b %EXITCODE%
