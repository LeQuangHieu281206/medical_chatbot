@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay chay scripts\cai_dat_app.bat truoc.
    pause
    exit /b 1
)
if not defined OLLAMA_MODEL (
    if exist "ollama_model.txt" set /p OLLAMA_MODEL=<ollama_model.txt
)
".venv\Scripts\python.exe" -m streamlit run "app\ui.py"
pause
