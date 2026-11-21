@echo off
cd /d "%~dp0"
echo Installation de PyInstaller...
pip install pyinstaller
echo.
echo Construction de l'executable...
pyinstaller --onefile --windowed --name GestionStock --collect-all customtkinter --hidden-import babel.numbers main.py
echo.
echo Construction de l'outil de nettoyage...
pyinstaller --onefile --windowed --name NettoyageGestionStock nettoyage_residus.py
echo.
echo Termine ! Dans le dossier "dist" : GestionStock.exe (le logiciel) et
echo NettoyageGestionStock.exe (supprime les fichiers residuels apres desinstallation).
echo Vous pouvez creer un raccourci de ce fichier sur le Bureau pour un
echo lancement en un clic, sans avoir besoin de Python installe sur le
echo poste final.
pause
