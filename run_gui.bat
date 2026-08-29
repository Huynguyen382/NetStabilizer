@echo off
title NetStabilizer - Low Latency Network Controller
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

"%PY_CMD%" main.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] Gap loi khi chay NetStabilizer. Vui long kiem tra lai.
    pause
)
