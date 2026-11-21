"""
Génération et impression des factures de vente.

Les factures sont enregistrées en texte simple dans le dossier "factures/",
ce qui ne nécessite aucune dépendance supplémentaire. L'impression tente
d'utiliser la boîte de dialogue d'impression du système d'exploitation.
"""

import os
import sys
import subprocess

from utils import fmt, dossier_donnees

DOSSIER_FACTURES = os.path.join(dossier_donnees(), "factures")


def construire_texte_facture(data):
    lignes = [
        f"FACTURE N° {data.get('numero', '—')}",
        data.get("nom_entreprise", ""),
        f"Date : {data.get('date', '')}",
        "-" * 42,
        f"Produit       : {data['produit']}",
        f"Quantité      : {data['quantite']}",
        f"Prix unitaire : {fmt(data['prix_unitaire'])} FCFA",
        "-" * 42,
        f"MONTANT TOTAL : {fmt(data['montant_total'])} FCFA",
        "-" * 42,
    ]

    if data.get("client_nom") or data.get("client_telephone") or data.get("client_adresse"):
        lignes.append("")
        lignes.append("Client :")
        if data.get("client_nom"):
            lignes.append(f"  Nom       : {data['client_nom']}")
        if data.get("client_telephone"):
            lignes.append(f"  Téléphone : {data['client_telephone']}")
        if data.get("client_adresse"):
            lignes.append(f"  Adresse   : {data['client_adresse']}")

    lignes.append("")
    lignes.append("Merci de votre confiance.")
    return "\n".join(lignes)


def enregistrer_facture_fichier(data):
    os.makedirs(DOSSIER_FACTURES, exist_ok=True)
    numero = data.get("numero", "provisoire")
    chemin = os.path.join(DOSSIER_FACTURES, f"facture_{numero}.txt")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(construire_texte_facture(data))
    return chemin


def imprimer_facture(chemin_fichier):
    """
    Best-effort : envoie le fichier vers l'imprimante par défaut du système.
    En cas d'échec (pas d'imprimante configurée, etc.), le fichier reste
    disponible pour une impression manuelle.
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(chemin_fichier, "print")
        else:
            subprocess.run(["lpr", chemin_fichier], check=True)
        return True, f"Facture envoyée à l'impression. Fichier : {chemin_fichier}"
    except Exception as e:
        return False, f"Impression automatique impossible ({e}). Le fichier a été enregistré ici : {chemin_fichier}"
