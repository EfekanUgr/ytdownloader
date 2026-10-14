@echo off
cd /d "%~dp0"
title Downloader(+) Ev Web Sunucusu (Cloudflare Tunnel)

call "%~dp0ortak.bat"
if errorlevel 1 exit /b 1

"%PYEXE%" "%~dp0backend\bridge.py"
if errorlevel 1 pause
