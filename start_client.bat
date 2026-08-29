@echo off
title NetStabilizer - Client Node (May Dieu Khien)
cd /d "%~dp0"
set /p TARGET_IP="Nhap dia chi IP cua May Chu (Server IP): "
if "%TARGET_IP%"=="" set TARGET_IP=127.0.0.1

echo ======================================================================
echo  NETSTABILIZER - CLIENT NODE
echo  Ket noi toi Server IP: %TARGET_IP%:29999
echo  Local Port mo tai: 127.0.0.1:13389
echo.
echo  -> Ban hay mo Remote Desktop va ket noi toi: 127.0.0.1:13389
echo ======================================================================
python main.py --client --host %TARGET_IP% --lport 13389 --tport 29999
pause
