@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\configure_zhipu.py" --model glm-5.3-flash
pause
