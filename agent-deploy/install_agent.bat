@echo off
echo Iniciando instalacao do RDP System Agent...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0install_agent.ps1'"
echo.
echo Processo finalizado.
pause