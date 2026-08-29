@echo off
title NetStabilizer - 1-Click Network Optimizer
cd /d "%~dp0"

:: Check for administrative permissions
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run_opt
) else (
    echo [i] Dang yeu cau quyen Administrator de chinh sua Registry va TCP/IP...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\" admin\"' -Verb RunAs"
    exit /b
)

:run_opt
cls
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

"%PY_CMD%" main.py --optimize
echo.
pause
