@echo off
cd /d "%~dp0"
echo Installation de PyInstaller...
pip install pyinstaller
echo.
echo Construction de l'executable...
pyinstaller --onefile --windowed --name GestionStock main.py
echo.
echo Termine ! L'executable se trouve dans le dossier "dist" (GestionStock.exe).
echo Vous pouvez creer un raccourci de ce fichier sur le Bureau pour un
echo lancement en un clic, sans avoir besoin de Python installe sur le
echo poste final.
pause
