@echo off
title NetStabilizer - Client Node (May Dieu Khien)
cd /d "%~dp0"

:: Check & Auto-download Portable Python if needed
set "PY_CMD=python"
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    if exist "%~dp0python_runtime\python.exe" (
        set "PY_CMD=%~dp0python_runtime\python.exe"
    ) else (
        call "%~dp0get_python.bat"
        if exist "%~dp0python_runtime\python.exe" (
            set "PY_CMD=%~dp0python_runtime\python.exe"
        )
    )
)

set /p TARGET_IP="Nhap dia chi IP cua May Chu (Server IP): "
if "%TARGET_IP%"=="" set TARGET_IP=127.0.0.1

echo ======================================================================
echo  NETSTABILIZER - CLIENT NODE
echo  Ket noi toi Server IP: %TARGET_IP%:29999
echo  Local Port mo tai: 127.0.0.1:13389
echo.
echo  -> Ban hay mo Remote Desktop va ket noi toi: 127.0.0.1:13389
echo ======================================================================
"%PY_CMD%" main.py --client --host %TARGET_IP% --lport 13389 --tport 29999
pause
