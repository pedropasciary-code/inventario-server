@echo off
REM Inicia o instalador do agent usando PowerShell sem depender da politica local.
echo Iniciando instalacao do RDP System Agent...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0install_agent.ps1'"

REM Mantem a janela aberta para o usuario conferir mensagens de sucesso ou erro.
echo.
echo Processo finalizado.
pause
