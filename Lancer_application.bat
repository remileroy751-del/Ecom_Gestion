@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Une erreur s'est produite. Verifiez que Python et les dependances
    echo sont bien installes ^(voir README.md^).
    pause
)
