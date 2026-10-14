@echo off
cd /d "%~dp0"
title Video Indirici (MP4 - en yuksek kalite)

call "%~dp0ortak.bat"
if errorlevel 1 exit /b 1

"%PYEXE%" "%~dp0indirici.py" video
if errorlevel 1 pause
