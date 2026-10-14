@echo off
cd /d "%~dp0"
title Altyazi Indirici (sadece altyazi)

call "%~dp0ortak.bat"
if errorlevel 1 exit /b 1

"%PYEXE%" "%~dp0indirici.py" altyazi
if errorlevel 1 pause
