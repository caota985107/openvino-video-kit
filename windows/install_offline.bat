@echo off
REM 一鍵離線安裝（雙擊即可）— 會呼叫同資料夾的 install_offline.ps1
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "install_offline.ps1"
echo.
pause
