@echo off
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\cai_dat_app.ps1"
pause
