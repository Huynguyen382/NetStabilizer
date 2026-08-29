@echo off
title NetStabilizer - Server Node (May Chu / May Bi Dieu Khien)
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

echo ======================================================================
echo  NETSTABILIZER - SERVER NODE
echo  Dang mo KCP/UDP Tunnel lang nghe ket noi tren cong 29999
echo  Chuyen tiep toi dich vu RDP goc (127.0.0.1:3389)
echo ======================================================================
"%PY_CMD%" main.py --server --lport 29999 --rport 3389 --tport 29999
pause
