@echo off
echo ==================================================
echo  WARP ACCOUNT MANAGER - CERTIFICATE INSTALLATION
echo ==================================================
echo.
echo This script will install the MITM proxy certificate 
echo into Windows Trusted Root Certification Authorities.
echo.
echo This is required for HTTPS websites to work properly.
echo.
pause

set CERT_PATH=%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer

if not exist "%CERT_PATH%" (
    echo ❌ ERROR: Certificate file not found!
    echo Expected: %CERT_PATH%
    echo.
    echo Please run the main application first to create the certificate.
    pause
    exit /b 1
)

echo 📁 Certificate found: %CERT_PATH%
echo.
echo 🔧 Installing certificate into Windows certificate store...

certutil -addstore root "%CERT_PATH%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ SUCCESS! Certificate installed successfully.
    echo.
    echo 🌐 Now restart your browser and try again.
    echo.
    echo 📋 To verify installation:
    echo    certutil -store root ^| findstr -i mitmproxy
) else (
    echo.
    echo ❌ ERROR: Failed to install certificate.
    echo.
    echo 💡 Possible solutions:
    echo    1. Run this file as administrator
    echo    2. Temporarily disable antivirus
    echo    3. Install certificate manually
    echo.
    echo 📖 Manual installation:
    echo    1. Open %CERT_PATH%
    echo    2. Click "Install Certificate"
    echo    3. Select "Local Machine"
    echo    4. Select "Place all certificates in the following store"
    echo    5. Select "Trusted Root Certification Authorities"
    echo    6. Complete the installation
)

echo.
pause