@echo off
title Local AI Installer
echo Installing your free Local AI team. This downloads about 60 GB,
echo so it can take a while. Click "Yes" if Windows asks for permission.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-local-ai.ps1"
echo.
pause
