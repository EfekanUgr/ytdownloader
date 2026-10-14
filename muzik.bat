@echo off
cd /d "%~dp0"
title Muzik Indirici (MP3 - en yuksek kalite)

call "%~dp0ortak.bat"
if errorlevel 1 exit /b 1

"%PYEXE%" "%~dp0indirici.py" muzik
if errorlevel 1 pause
