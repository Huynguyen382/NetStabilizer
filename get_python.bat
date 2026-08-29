@echo off
setlocal enabledelayedexpansion
title NetStabilizer - Setup Python

:: 1. Check if python is already available in PATH
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [✓] Da tim thay Python tren he thong.
    goto :done
)

:: 2. Check if local portable python exists
if exist "%~dp0python_runtime\python.exe" (
    echo [✓] Da tim thay Python Portable cuc bo.
    goto :done
)

echo ======================================================================
echo  NETSTABILIZER - TU DONG CAI DAT PYTHON PORTABLE (KHONG CAN ADMIN)
echo ======================================================================
echo  May cua ban chua co Python. Dang tu dong tai Python Portable (~15MB)...
echo.

set "PY_ZIP=%~dp0python_embed.zip"
set "PY_DIR=%~dp0python_runtime"

:: Download official Python Embeddable 64-bit using PowerShell
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Dang tai Python 3.11 Embeddable tu python.org...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%PY_ZIP%'"

if not exist "%PY_ZIP%" (
    echo [!] Khong the tai Python tu dong. Vui long cai Python thu cong tu https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Dang giai nen Python Portable...
powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PY_DIR%' -Force"
del /f /q "%PY_ZIP%" >nul 2>&1

:: Enable site-packages / standard imports in embeddable python
if exist "%PY_DIR%\python311._pth" (
    powershell -Command "(Get-Content '%PY_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%PY_DIR%\python311._pth'"
)

echo [✓] Cai dat Python Portable thanh cong!
echo.

:done
exit /b 0
