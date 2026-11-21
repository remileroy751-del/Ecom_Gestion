"""
Utilitaires partagés par les différents modules de l'application.
"""

import os
import sys

NOM_DOSSIER_DONNEES = "GestionStock"


def chemin_donnees_exe():
    """
    Emplacement du dossier de données de l'exécutable compilé
    (%LOCALAPPDATA%\\GestionStock). Ne crée rien : sert aussi à l'outil de
    nettoyage pour retrouver ce dossier.
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, NOM_DOSSIER_DONNEES)


def dossier_donnees():
    """
    Dossier où le logiciel stocke ses données locales (base de données,
    factures, logo...). Il est créé s'il n'existe pas.

    - Exécutable compilé (.exe) : %LOCALAPPDATA%\\GestionStock. Le dossier
      de l'exécutable est temporaire (PyInstaller) et ne convient pas.
    - Lancement depuis le code source (python main.py) : le dossier du
      projet, comme avant.
    """
    if getattr(sys, "frozen", False):
        dossier = chemin_donnees_exe()
    else:
        dossier = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dossier, exist_ok=True)
    return dossier


def fmt(valeur):
    """
    Formate un nombre avec un espace comme séparateur de milliers
    (ex: 1234567 -> "1 234 567"), sans virgule ni point.
    """
    try:
        return f"{valeur:,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(valeur)
