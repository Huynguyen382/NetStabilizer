@echo off
title NetStabilizer - Server Node (May Chu / May Bi Dieu Khien)
cd /d "%~dp0"
echo ======================================================================
echo  NETSTABILIZER - SERVER NODE
echo  Dang mo KCP/UDP Tunnel lang nghe ket noi tren cong 29999
echo  Chuyen tiep toi dich vu RDP goc (127.0.0.1:3389)
echo ======================================================================
python main.py --server --lport 29999 --rport 3389 --tport 29999
pause
