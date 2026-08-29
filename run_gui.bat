@echo off
title NetStabilizer - Low Latency Network Controller
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] Gap loi khi chay NetStabilizer. Vui long kiem tra Python.
    pause
)
