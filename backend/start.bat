@echo off
cd /d "%~dp0"
title Downloader(+) API Sunucusu

call "%~dp0..\ortak.bat"
if errorlevel 1 exit /b 1

echo Gerekli paketler kontrol ediliyor...
"%PYEXE%" -m pip install -q -r "%~dp0requirements.txt"

echo API Sunucusu baslatiliyor...
"%PYEXE%" "%~dp0main.py"
pause
